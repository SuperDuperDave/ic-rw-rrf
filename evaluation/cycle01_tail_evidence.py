#!/usr/bin/env python3
"""Descriptive depth intervention and tail-support associations on development data.

No labels choose a method or define specialist groups. Three list-depth arms
compare fixed k=60 and k=200 on identical eligible queries. Tail-support groups
are defined once from ORIGINAL full lists, independently of these interventions.
Intervals resample query deltas, not documents or repeated ensemble observations.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys

# Historical probe modules use sibling imports. Support direct CLI and unittest
# package imports without changing those preserved modules.
EVALUATION = Path(__file__).resolve().parent
if str(EVALUATION) not in sys.path:
    sys.path.insert(0, str(EVALUATION))

from cycle01_rank_geometry import CONFIGS, ROOT, paired_summary
from fusion_contract import canonical_rrf
from trec_eval_harness import ndcg_at_k, parse_qrels, parse_run_file, runs_to_ranked_lists


DEPTH_ARMS = ('full', 'equalized', 'top30_cap')
GROUPS = ('tail_supported', 'isolated')
STRATA = ('all_top10', 'rank1_3', 'rank4_10')
GROUP_METRICS = ('judged_fraction', 'relevance_ge2_among_judged',
                 'all_candidate_relevance_ge2', 'all_candidate_mean_graded_gain')
BOOTSTRAP = {'resamples': 4000, 'seed': 1847}


def average(values):
    values = list(values)
    return statistics.mean(values) if values else None


def paired(deltas, n_boot=4000):
    """Explicitly report empty eligible strata instead of inventing zero rates."""
    values = list(deltas)
    if not values:
        return {'n_queries': 0, 'mean_delta': None,
                'conditional_query_bootstrap_95': None,
                'wins': 0, 'losses': 0, 'ties': 0}
    return paired_summary(values, n_boot=n_boot, seed=BOOTSTRAP['seed'])


def rank_maps(lists):
    return [{doc: rank for rank, doc in enumerate(source, 1)} for source in lists]


def document_evidence(doc, names, maps):
    positions = {name: ranks.get(doc) for name, ranks in zip(names, maps)}
    present = [rank for rank in positions.values() if rank is not None]
    return {'source_ranks': positions, 'coverage_count': len(present),
            'coverage_fraction': len(present) / len(names) if names else 0.0,
            'top30_coverage_count': sum(rank <= 30 for rank in present)}


def depth_variants(lists):
    """Top30 caps each source separately; equalization uses this query's minimum."""
    minimum = min((len(source) for source in lists), default=0)
    return {'full': [list(source) for source in lists],
            'equalized': [list(source[:minimum]) for source in lists],
            'top30_cap': [list(source[:30]) for source in lists]}


def ranking_transition(old, new, names, active_lists, full_lists, qrel, cutoff=10):
    """Explain every changed position in the union of both top-cutoff lists.

    Fused positions refer to complete output rankings, so an entrant/exit's
    outside-cutoff position is retained. Source positions are always one-based.
    Reordering can change NDCG without changing membership.
    """
    old_top, new_top = old[:cutoff], new[:cutoff]
    old_set, new_set = set(old_top), set(new_top)
    old_positions = {doc: rank for rank, doc in enumerate(old, 1)}
    new_positions = {doc: rank for rank, doc in enumerate(new, 1)}
    active_maps, full_maps = rank_maps(active_lists), rank_maps(full_lists)
    changes = []
    for doc in sorted(old_set | new_set):
        before, after = old_positions.get(doc), new_positions.get(doc)
        if before == after:
            continue
        kind = ('entrant' if doc not in old_set else
                'exit' if doc not in new_set else 'reordered')
        grade = qrel.get(doc, 0)
        changes.append({'docid': doc, 'change': kind,
                        'k60_fused_rank': before, 'k200_fused_rank': after,
                        'judged': doc in qrel, 'grade_unjudged_zero': grade,
                        'gain_unjudged_zero': 2 ** grade - 1,
                        'active_source_evidence': document_evidence(doc, names, active_maps),
                        'full_source_evidence': document_evidence(doc, names, full_maps)})
    return {'k60_top10': old_top, 'k200_top10': new_top,
            'entrants': [doc for doc in new_top if doc not in old_set],
            'exits': [doc for doc in old_top if doc not in new_set],
            'ordered_top10_changed': old_top != new_top,
            'membership_changed': old_set != new_set,
            'position_changes': changes}


def specialist_candidates(names, lists, qrel):
    """Source top10, absent from EVERY OTHER source's top30, judged afterward.

    A document has exactly one possible owning source because another top10
    occurrence would also violate the other-top30 exclusion. Tail support is
    presence at position >30 in at least one other ORIGINAL full source list.
    """
    maps = rank_maps(lists)
    output, seen = [], set()
    for owner, (name, source) in enumerate(zip(names, lists)):
        for owner_rank, doc in enumerate(source[:10], 1):
            other_ranks = [ranks[doc] for index, ranks in enumerate(maps)
                           if index != owner and doc in ranks]
            if any(rank <= 30 for rank in other_ranks):
                continue
            if doc in seen:
                raise AssertionError('specialist eligibility must imply a unique owner')
            seen.add(doc)
            grade = qrel.get(doc, 0)
            output.append({'docid': doc, 'owner_source': name, 'owner_rank': owner_rank,
                           'stratum': 'rank1_3' if owner_rank <= 3 else 'rank4_10',
                           'group': 'tail_supported' if other_ranks else 'isolated',
                           'judged': doc in qrel, 'grade_unjudged_zero': grade,
                           'gain_unjudged_zero': 2 ** grade - 1,
                           'relevant_ge2_unjudged_zero': int(grade >= 2),
                           'full_source_evidence': document_evidence(doc, names, maps)})
    return output


def group_statistics(candidates):
    """Pooled candidate descriptions; no document-level confidence intervals."""
    n = len(candidates)
    judged = sum(row['judged'] for row in candidates)
    relevant_judged = sum(row['judged'] and row['grade_unjudged_zero'] >= 2
                         for row in candidates)
    relevant_all = sum(row['relevant_ge2_unjudged_zero'] for row in candidates)
    gain_sum = sum(row['gain_unjudged_zero'] for row in candidates)
    return {'n_candidates': n, 'n_judged': judged, 'n_unjudged': n - judged,
            'n_relevant_ge2': relevant_all, 'graded_gain_sum': gain_sum,
            'judged_fraction': judged / n if n else None,
            'relevance_ge2_among_judged': relevant_judged / judged if judged else None,
            'all_candidate_relevance_ge2': relevant_all / n if n else None,
            'all_candidate_mean_graded_gain': gain_sum / n if n else None}


def summarize_groups(candidates_by_query, stratum='all_top10', n_boot=4000):
    """Pair within query; a judged-only contrast also needs judgments in both groups."""
    if stratum not in STRATA:
        raise ValueError('unknown owner-rank stratum: ' + stratum)
    pooled = {group: [] for group in GROUPS}
    per_query = {}
    for qid, candidates in sorted(candidates_by_query.items()):
        selected = [row for row in candidates
                    if stratum == 'all_top10' or row['stratum'] == stratum]
        per_query[qid] = {}
        for group in GROUPS:
            members = [row for row in selected if row['group'] == group]
            pooled[group].extend(members)
            per_query[qid][group] = group_statistics(members)
    both = [qid for qid, stats in per_query.items()
            if all(stats[group]['n_candidates'] > 0 for group in GROUPS)]
    contrasts = {}
    for metric in GROUP_METRICS:
        eligible = [qid for qid in both
                    if all(per_query[qid][group][metric] is not None for group in GROUPS)]
        deltas = {qid: per_query[qid]['tail_supported'][metric] -
                  per_query[qid]['isolated'][metric] for qid in eligible}
        contrasts[metric] = {'eligible_qids': eligible, 'per_query_deltas': deltas,
                             'summary': paired(deltas.values(), n_boot=n_boot)}
    return {'stratum': stratum, 'n_queries_total': len(per_query),
            'n_queries_with_both_groups': len(both), 'qids_with_both_groups': both,
            'groups': {group: group_statistics(pooled[group]) for group in GROUPS},
            'paired_tail_supported_minus_isolated': contrasts,
            'per_query_group_statistics': per_query}


def evaluate_query(names, lists, qrel):
    arms = {}
    for name, active in depth_variants(lists).items():
        rank60 = canonical_rrf(active, k=60)
        rank200 = canonical_rrf(active, k=200)
        score60, score200 = ndcg_at_k(rank60, qrel, 10), ndcg_at_k(rank200, qrel, 10)
        arms[name] = {'source_depths': dict(zip(names, map(len, active))),
                      'n_candidates': len(rank60), 'ndcg10_k60': score60,
                      'ndcg10_k200': score200, 'ndcg10_delta_k200_minus_k60': score200-score60,
                      'transition': ranking_transition(rank60, rank200, names, active, lists, qrel)}
    for name in DEPTH_ARMS:
        row = arms[name]
        for k in (60, 200):
            key = 'ndcg10_k{}'.format(k)
            row[key + '_minus_full'] = row[key] - arms['full'][key]
        row['k_effect_delta_minus_full'] = (row['ndcg10_delta_k200_minus_k60'] -
                                           arms['full']['ndcg10_delta_k200_minus_k60'])
    return {'original_source_depths': dict(zip(names, map(len, lists))),
            'query_minimum_source_depth': min(map(len, lists), default=0),
            'arms': arms, 'specialist_candidates': specialist_candidates(names, lists, qrel)}


def summarize_depth(rows, n_boot=4000):
    output = {}
    for name in DEPTH_ARMS:
        values = [row['arms'][name] for row in rows.values()]
        output[name] = {'n_queries': len(values),
                        'mean_ndcg10_k60': average(row['ndcg10_k60'] for row in values),
                        'mean_ndcg10_k200': average(row['ndcg10_k200'] for row in values),
                        'k200_minus_k60': paired((row['ndcg10_delta_k200_minus_k60'] for row in values), n_boot),
                        'k_effect_change_vs_full': paired((row['k_effect_delta_minus_full'] for row in values), n_boot),
                        'k60_depth_change_vs_full': paired((row['ndcg10_k60_minus_full'] for row in values), n_boot),
                        'k200_depth_change_vs_full': paired((row['ndcg10_k200_minus_full'] for row in values), n_boot),
                        'n_ordered_top10_changes': sum(row['transition']['ordered_top10_changed'] for row in values),
                        'n_membership_changes': sum(row['transition']['membership_changed'] for row in values),
                        'n_pure_reorder_changes': sum(row['transition']['ordered_top10_changed'] and
                                                      not row['transition']['membership_changed'] for row in values),
                        'total_entrants': sum(len(row['transition']['entrants']) for row in values),
                        'total_exits': sum(len(row['transition']['exits']) for row in values)}
    return output


def evaluate_configuration(year, names, runs, qrels, n_boot=4000):
    missing_sources = sorted(set(names) - set(runs))
    if missing_sources:
        raise ValueError('missing required run files: ' + ', '.join(missing_sources))
    selected = {name: runs[name] for name in names}
    rows, excluded = {}, {}
    for qid in sorted(qrels):
        missing = [name for name in names if qid not in selected[name]]
        if missing or not any(grade > 0 for grade in qrels[qid].values()):
            excluded[qid] = {'missing_sources': missing,
                             'no_positive_qrel': not any(grade > 0 for grade in qrels[qid].values())}
            continue
        lists, _, _ = runs_to_ranked_lists(selected, qid)
        rows[qid] = evaluate_query(names, lists, qrels[qid])
    if not rows:
        raise ValueError('no eligible queries for {} {}'.format(year, names))
    candidates = {qid: row['specialist_candidates'] for qid, row in rows.items()}
    summary = {'year': year, 'rankers': names, 'n_queries': len(rows),
               'eligible_qids': sorted(rows), 'excluded_qids': excluded,
               'depth_arms': summarize_depth(rows, n_boot),
               'specialist_groups': {stratum: summarize_groups(candidates, stratum, n_boot)
                                     for stratum in STRATA}}
    return summary, rows


def aggregate_ensembles(configuration_rows, n_boot=4000):
    """Average paired effects within query before bootstrapping repeated ensembles."""
    if not configuration_rows:
        raise ValueError('no ensemble rows')
    labels = sorted(configuration_rows)
    qids = set(configuration_rows[labels[0]])
    if any(set(configuration_rows[label]) != qids for label in labels):
        raise ValueError('ensemble aggregate requires identical eligible query IDs')
    output = {}
    for arm in DEPTH_ARMS:
        metrics = {}
        for metric in ('ndcg10_delta_k200_minus_k60', 'k_effect_delta_minus_full',
                       'ndcg10_k60_minus_full', 'ndcg10_k200_minus_full'):
            per_query = {qid: average(configuration_rows[label][qid]['arms'][arm][metric]
                                      for label in labels) for qid in sorted(qids)}
            metrics[metric] = {'per_query_deltas': per_query,
                               'summary': paired(per_query.values(), n_boot)}
        output[arm] = metrics
    return {'configurations': labels, 'n_queries': len(qids), 'depth_arms': output,
            'group_scope': 'Specialist groups are reported per configuration; no pooled repeated-document inference.'}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_paths(paths):
    return {str(path.relative_to(ROOT)): sha256(path) for path in paths}


def input_paths():
    paths = []
    for year in (2019, 2020):
        directory = ROOT / 'data' / ('trec-dl-' + str(year))
        paths.append(directory / ('{}qrels-pass.txt'.format(year)))
        paths.extend(sorted((directory / 'runs').glob('*.txt')))
    return paths


def load_inputs(paths):
    """Called only AFTER start hashes have been recorded."""
    output = {}
    for year in (2019, 2020):
        directory = ROOT / 'data' / ('trec-dl-' + str(year))
        qrel_path = directory / ('{}qrels-pass.txt'.format(year))
        runs = {path.stem: parse_run_file(str(path)) for path in paths
                if path.parent == directory / 'runs'}
        output[year] = (runs, parse_qrels(str(qrel_path)))
    return output


def write_json(path, value):
    """Exclusive creation: evidence files are never overwritten."""
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def new_output_directory(path):
    path = path.resolve()
    path.mkdir(parents=True, exist_ok=False)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, required=True,
                        help='Frozen protocol path relative to the repository (or an absolute path within it)')
    parser.add_argument('--output', type=Path, required=True, help='A new, nonexistent evidence directory')
    args = parser.parse_args(argv)
    protocol = (ROOT / args.protocol).resolve() if not args.protocol.is_absolute() else args.protocol.resolve()
    try:
        protocol_relative = str(protocol.relative_to(ROOT))
    except ValueError:
        parser.error('protocol must be a repository file')
    if not protocol.is_file():
        parser.error('freeze the protocol file before running')
    source_paths = [Path(__file__).resolve(), EVALUATION / 'fusion_contract.py',
                    EVALUATION / 'trec_eval_harness.py', EVALUATION / 'cycle01_rank_geometry.py', protocol]
    data_paths = input_paths()
    start_sources, start_inputs = hash_paths(source_paths), hash_paths(data_paths)
    try:
        output = new_output_directory(args.output)
    except FileExistsError:
        parser.error('output path already exists; choose a new immutable evidence directory')
    provenance = {'status': 'started', 'started_utc': datetime.now(timezone.utc).isoformat(),
                  'argv': sys.argv if argv is None else [str(Path(__file__).resolve())] + list(argv),
                  'cwd': str(Path.cwd()), 'python_version': platform.python_version(),
                  'python_executable': sys.executable, 'protocol': protocol_relative,
                  'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  'git_dirty_status': subprocess.check_output(['git', '--no-optional-locks', 'status', '--short',
                                                               '--untracked-files=all'], cwd=ROOT, text=True).splitlines(),
                  'bootstrap': BOOTSTRAP, 'source_sha256_start': start_sources,
                  'input_sha256_start': start_inputs}
    write_json(output / 'manifest-start.json', provenance)
    inputs = load_inputs(data_paths)
    summaries, rows_by_configuration = [], {}
    for year, names in CONFIGS:
        label = '{}-n{}'.format(year, len(names))
        summary, rows = evaluate_configuration(year, names, *inputs[year])
        summaries.append(summary)
        rows_by_configuration[label] = rows
        print(label, json.dumps({arm: summary['depth_arms'][arm]['k200_minus_k60']['mean_delta']
                                 for arm in DEPTH_ARMS}), flush=True)
    result = {'protocol': protocol_relative, 'summary_kind': 'descriptive development evidence',
              'bootstrap': BOOTSTRAP, 'summaries': summaries,
              '2019_ensemble_mean_by_query': aggregate_ensembles(
                  {label: rows for label, rows in rows_by_configuration.items() if label.startswith('2019-')}),
              'definitions': {'specialist_groups': 'Original full lists only: owner top10 and absent from every OTHER source top30; another source rank>30 means tail_supported, otherwise isolated.',
                              'all_candidate_metrics': 'Unjudged documents receive relevance zero and graded gain zero; judged-only rates exclude them.',
                              'paired_group_contrasts': 'Tail-supported minus isolated within queries containing both groups; judged-only contrasts additionally require judgments in both.',
                              'intervals': 'Descriptive query bootstrap of fixed observed differences, not causal, confirmatory, or complete sampling uncertainty.'},
              'limits': ['Partial and nonrandom judgments can bias both judged-only and unjudged-zero summaries.',
                         'Groups are selected from source top10 and differ in source, rank, coverage, query difficulty, and retrieval quality; association is not causal.',
                         'Group composition uses original lists and is not redefined after truncation.',
                         'Depth interventions change available evidence and sometimes candidate sets; loss of a k advantage does not isolate a causal mechanism.',
                         'Existing annual TREC query sets are development data after extensive exploration; this is not a new-method performance claim.']}
    end_sources, end_inputs = hash_paths(source_paths), hash_paths(data_paths)
    unchanged = start_sources == end_sources and start_inputs == end_inputs
    provenance.update({'status': 'complete' if unchanged else 'invalid_source_or_input_change',
                       'finished_utc': datetime.now(timezone.utc).isoformat(),
                       'source_sha256_end': end_sources, 'input_sha256_end': end_inputs,
                       'sources_and_inputs_unchanged': unchanged})
    if not unchanged:
        write_json(output / 'manifest-invalid.json', provenance)
        raise RuntimeError('sources or inputs changed during the run; no valid result artifact written')
    write_json(output / 'summary.json', result)
    write_json(output / 'per_query.json', rows_by_configuration)
    provenance['output_sha256'] = {path.name: sha256(path) for path in sorted(output.glob('*.json'))}
    write_json(output / 'manifest.json', provenance)
    print('Wrote', output, flush=True)


if __name__ == '__main__':
    main()
