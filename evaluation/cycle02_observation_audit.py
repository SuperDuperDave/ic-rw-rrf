#!/usr/bin/env python3
"""Cycle02 observation feasibility inventory (Python 3.8+, standard library).

This phase uses qrel membership only. Explicit grade zero is judged, and missing
judgments stay missing. It computes no relevance outcomes, fusion, optimization,
effect contrasts, intervals, or sample-size adequacy claims. The deliberately
strict readers validate serialized ranks without the historical parser's silent
malformed-line skipping or sorting. All reported document ranks start at one.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
LEXICAL = ('bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet')
YEARS = (2019, 2020)
ARMS = ('full', 'shared_depth')
GROUPS = ('tail_supported', 'isolated')
CUTOFFS = (10, 30, 100)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def repository_file(value, root=None):
    """Resolve a required file, rejecting paths or symlinks outside the repo."""
    root = Path(root or ROOT).resolve()
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError('input path must remain inside the repository: ' + str(value)) from error
    if not path.is_file():
        raise ValueError('required input file is missing: ' + str(value))
    return path


def load_source_manifest(path, root=None):
    """Validate one prespecified source with exactly one canonical run per year."""
    manifest = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(manifest, dict):
        raise ValueError('source manifest must be a JSON object')
    source_id = manifest.get('source_id')
    if not isinstance(source_id, str) or not source_id.strip() or source_id in LEXICAL:
        raise ValueError('source_id must be a nonempty string distinct from lexical source names')
    entries = manifest.get('derived_runs')
    if not isinstance(entries, list) or len(entries) != len(YEARS):
        raise ValueError('derived_runs must contain exactly one run for 2019 and 2020')
    by_year = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('each derived_runs entry must be an object')
        year, relative, expected = entry.get('year'), entry.get('path'), entry.get('sha256')
        if type(year) is not int or year not in YEARS or year in by_year:
            raise ValueError('derived run years must be unique integers 2019 and 2020')
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise ValueError('derived run path must be a repository-relative string')
        run_path = repository_file(relative, root)
        if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', expected):
            raise ValueError('derived run sha256 must have 64 hexadecimal characters')
        if sha256(run_path) != expected.lower():
            raise ValueError('derived run hash does not match source manifest: ' + relative)
        by_year[year] = run_path
    if len(set(by_year.values())) != len(YEARS):
        raise ValueError('each year must have its own derived run file')
    return source_id, by_year


def read_ranked_run(path, rank_origin):
    """Read strict TREC rows in file order; ties retain that serialized order.

    Lexical historical files use rank_origin=0; canonical external files use 1.
    No score sorting, tie breaking, duplicate removal, or rank repair occurs.
    """
    if rank_origin not in (0, 1):
        raise ValueError('rank_origin must be zero or one')
    runs, seen, previous_score = {}, {}, {}
    with Path(path).open(encoding='utf-8') as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            parts = line.split()
            location = '{}:{}'.format(path, line_number)
            if len(parts) != 6:
                raise ValueError(location + ': expected six TREC run fields')
            qid, _, docid, raw_rank, raw_score, _ = parts
            try:
                rank, score = int(raw_rank), float(raw_score)
            except ValueError as error:
                raise ValueError(location + ': rank and score must be numeric') from error
            if not math.isfinite(score):
                raise ValueError(location + ': score must be finite')
            ranking = runs.setdefault(qid, [])
            documents = seen.setdefault(qid, set())
            if rank != len(ranking) + rank_origin:
                raise ValueError(location + ': ranks must be contiguous in serialized order, origin {}'.format(rank_origin))
            if docid in documents:
                raise ValueError(location + ': duplicate document within query')
            if qid in previous_score and score > previous_score[qid]:
                raise ValueError(location + ': scores must be nonincreasing')
            ranking.append(docid)
            documents.add(docid)
            previous_score[qid] = score
    if not runs:
        raise ValueError(str(path) + ': run contains no query rows')
    return runs


def read_judged_membership(path):
    """Discard grades immediately after syntax validation; keep qid/docid sets."""
    judged = {}
    with Path(path).open(encoding='utf-8') as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            parts = line.split()
            location = '{}:{}'.format(path, line_number)
            if len(parts) != 4:
                raise ValueError(location + ': expected four qrel fields')
            qid, _, docid, grade = parts
            try:
                int(grade)
            except ValueError as error:
                raise ValueError(location + ': qrel grade must be an integer') from error
            members = judged.setdefault(qid, set())
            if docid in members:
                raise ValueError(location + ': duplicate qrel document within query')
            members.add(docid)
    if not judged:
        raise ValueError(str(path) + ': qrels contain no query rows')
    return judged


def counts(documents, judged):
    documents = list(documents)
    n = len(documents)
    observed = sum(doc in judged for doc in documents)
    return {'n_candidates': n, 'n_judged': observed, 'n_unjudged': n - observed,
            'judged_fraction': observed / n if n else None}


def candidate_counts(candidates):
    n = len(candidates)
    observed = sum(row['judged'] for row in candidates)
    return {'n_candidates': n, 'n_judged': observed, 'n_unjudged': n - observed,
            'judged_fraction': observed / n if n else None}


def pooled_counts(rows):
    n = sum(row['n_candidates'] for row in rows)
    observed = sum(row['n_judged'] for row in rows)
    return {'n_candidates': n, 'n_judged': observed, 'n_unjudged': n - observed,
            'judged_fraction': observed / n if n else None}


def depth_arms(lists):
    """The new source enters as supplied top1000; cap ALL five lists equally."""
    full = {name: list(source) for name, source in lists.items()}
    depth = min([200] + [len(source) for source in full.values()])
    return {'full': full,
            'shared_depth': {name: source[:depth] for name, source in full.items()}}, depth


def specialist_candidates(active_lists, full_lists, judged):
    """FIXED full-arm cohort and labels, annotated with each arm's visibility.

    Owner original top10, absent every OTHER original top30. Cropping cannot
    create specialists or turn previously observed tail support into isolation.
    """
    active_maps = {name: {doc: rank for rank, doc in enumerate(source, 1)}
                   for name, source in active_lists.items()}
    full_maps = {name: {doc: rank for rank, doc in enumerate(source, 1)}
                 for name, source in full_lists.items()}
    result, seen = [], set()
    for owner, source in full_lists.items():
        for owner_rank, doc in enumerate(source[:10], 1):
            if any(doc in ranks and ranks[doc] <= 30
                   for name, ranks in full_maps.items() if name != owner):
                continue
            if doc in seen:
                raise AssertionError('specialist definition must imply a unique owner')
            seen.add(doc)
            other_full = [ranks[doc] for name, ranks in full_maps.items()
                          if name != owner and doc in ranks]
            result.append({'docid': doc, 'owner_source': owner, 'owner_rank': owner_rank,
                           'group': 'tail_supported' if any(rank > 30 for rank in other_full) else 'isolated',
                           'judged': doc in judged,
                           'owner_visible': doc in active_maps[owner],
                           'source_presence': {name: doc in ranks for name, ranks in active_maps.items()},
                           'source_ranks': {name: ranks.get(doc) for name, ranks in active_maps.items()},
                           'full_source_ranks': {name: ranks.get(doc) for name, ranks in full_maps.items()},
                           'active_tail_support_sources': [name for name, ranks in active_maps.items()
                                                           if name != owner and ranks.get(doc, 0) > 30],
                           'full_tail_support_sources': [name for name, ranks in full_maps.items()
                                                         if name != owner and ranks.get(doc, 0) > 30]})
    return result


def observed_documents(documents, judged):
    return {'counts': counts(documents, judged),
            'documents': [{'docid': doc, 'judged': doc in judged} for doc in documents]}


def inspect_query(raw_lists, source_id, judged):
    """Describe one complete query; never inspect a relevance value."""
    full_lists = {name: list(source if name != source_id else source[:1000])
                  for name, source in raw_lists.items()}
    variants, depth = depth_arms(full_lists)
    lexical_full_union = set().union(*(set(full_lists[name]) for name in LEXICAL))
    full_union = set().union(*(set(source) for source in full_lists.values()))
    source_full_outside = [doc for doc in full_lists[source_id] if doc not in lexical_full_union]
    arms = {}
    for arm, active in variants.items():
        sets = [set(source) for source in active.values()]
        union, intersection = set.union(*sets), set.intersection(*sets)
        lexical_sets = [set(active[name]) for name in LEXICAL]
        lexical_union = set.union(*lexical_sets)
        outside_full = [doc for doc in active[source_id] if doc not in lexical_full_union]
        outside_active = [doc for doc in active[source_id] if doc not in lexical_union]
        top10_outside = [doc for doc in active[source_id][:10] if doc not in lexical_full_union]
        arms[arm] = {
            'source_depths': {name: len(source) for name, source in active.items()},
            'candidate_union': counts(sorted(union), judged),
            'candidate_set_changed_from_full': union != full_union,
            'n_candidates_removed_from_full': len(full_union - union),
            'candidate_intersection': counts(sorted(intersection), judged),
            'lexical_candidate_union': counts(sorted(lexical_union), judged),
            'lexical_candidate_intersection': counts(sorted(set.intersection(*lexical_sets)), judged),
            'pairwise_source_overlap': {
                first: {second: {'n_intersection': len(set(active[first]) & set(active[second])),
                                 'n_union': len(set(active[first]) | set(active[second]))}
                        for second in active} for first in active},
            'source_judgment_coverage': {
                name: dict({'whole_source': counts(source, judged)},
                           **{'top{}'.format(cutoff): counts(source[:cutoff], judged)
                              for cutoff in CUTOFFS})
                for name, source in active.items()},
            'new_source_top10_outside_lexical_full_union': observed_documents(top10_outside, judged),
            'new_source_outside_lexical_full_union': counts(outside_full, judged),
            'new_source_outside_active_lexical_union': counts(outside_active, judged),
            'new_source_outside_only_due_to_lexical_cropping': counts(
                [doc for doc in outside_active if doc in lexical_full_union], judged),
            'specialist_candidates': specialist_candidates(active, full_lists, judged),
        }
    retained = [doc for doc in variants['shared_depth'][source_id] if doc not in lexical_full_union]
    removed = [doc for doc in source_full_outside if doc not in set(retained)]
    changed_sources = [name for name in full_lists if variants['full'][name] != variants['shared_depth'][name]]
    return {'raw_source_depths': {name: len(source) for name, source in raw_lists.items()},
            'shared_depth': depth, 'depth_arm_changed': bool(changed_sources),
            'changed_sources': changed_sources, 'arms': arms,
            'new_source_full_vs_capped_outside_candidate_coverage': {
                'reference': 'the original lexical full-list union in both arms',
                'full': counts(source_full_outside, judged), 'capped': counts(retained, judged),
                'removed_by_cap': counts(removed, judged)}}


def summarize_groups(candidates_by_query):
    """Descriptive denominators; documents and repeated arms are not samples."""
    per_query = {}
    for qid, candidates in sorted(candidates_by_query.items()):
        per_query[qid] = {group: candidate_counts([row for row in candidates if row['group'] == group])
                          for group in GROUPS}
    eligible = {
        'with_candidates': [qid for qid, row in per_query.items()
                            if any(row[group]['n_candidates'] for group in GROUPS)],
        'with_both_groups': [qid for qid, row in per_query.items()
                             if all(row[group]['n_candidates'] for group in GROUPS)],
        'with_judged_both_groups': [qid for qid, row in per_query.items()
                                   if all(row[group]['n_judged'] for group in GROUPS)],
    }
    return {'n_queries_total': len(per_query),
            'groups': {group: dict(pooled_counts([row[group] for row in per_query.values()]),
                                   n_queries_with_candidates=sum(row[group]['n_candidates'] > 0 for row in per_query.values()),
                                   n_queries_with_judgments=sum(row[group]['n_judged'] > 0 for row in per_query.values()))
                       for group in GROUPS},
            'eligibility': {key: {'n_queries': len(qids), 'qids': qids} for key, qids in eligible.items()},
            'per_query_denominators': per_query}


def owner_summaries(rows, arm, source_id, visible_only=False):
    candidates = {qid: row['arms'][arm]['specialist_candidates'] for qid, row in rows.items()}
    select = lambda owners: summarize_groups({qid: [row for row in members if row['owner_source'] in owners
                                                   and (not visible_only or row['owner_visible'])]
                                              for qid, members in candidates.items()})
    return {'new_source': select([source_id]), 'pooled_lexical': select(LEXICAL),
            'individual_lexical': {name: select([name]) for name in LEXICAL}}


def paired_observability(first, second):
    """Only identify common queries with observable groups; compute no contrast."""
    return {key: {'n_queries': len(qids), 'qids': qids}
            for key in first['eligibility']
            for qids in [sorted(set(first['eligibility'][key]['qids']) &
                                set(second['eligibility'][key]['qids']))]}


def summarize_year(year, source_id, runs, judgments):
    names = list(LEXICAL) + [source_id]
    eligible = sorted(qid for qid in judgments if all(runs[name].get(qid) for name in names))
    rows = {qid: inspect_query({name: runs[name][qid] for name in names}, source_id, judgments[qid])
            for qid in eligible}
    raw_inventory = {}
    for name in names:
        qids = set(runs[name])
        raw_inventory[name] = {
            'n_queries': len(qids), 'n_rows': sum(map(len, runs[name].values())),
            'raw_depths_by_query': {qid: len(source) for qid, source in sorted(runs[name].items())},
            'qids_missing_from_source': sorted(set(judgments) - qids),
            'qids_without_qrels': sorted(qids - set(judgments)),
        }
    arm_summaries = {}
    for arm in ARMS:
        active = [row['arms'][arm] for row in rows.values()]
        arm_summaries[arm] = {
            'n_queries': len(rows),
            'n_queries_candidate_set_changed_from_full': sum(row['candidate_set_changed_from_full'] for row in active),
            'owners': {cohort: owner_summaries(rows, arm, source_id, visible_only=cohort == 'visible_only')
                       for cohort in ('fixed_cohort', 'visible_only')},
            'source_judgment_coverage': {
                name: {cutoff: pooled_counts([row['source_judgment_coverage'][name][cutoff] for row in active])
                       for cutoff in ('whole_source', 'top10', 'top30', 'top100')}
                for name in names},
            'candidate_counts': {key: pooled_counts([row[key] for row in active])
                                 for key in ('candidate_union', 'candidate_intersection',
                                             'lexical_candidate_union', 'lexical_candidate_intersection',
                                             'new_source_outside_lexical_full_union',
                                             'new_source_outside_active_lexical_union',
                                             'new_source_outside_only_due_to_lexical_cropping')},
            'new_source_top10_outside_lexical_full_union': pooled_counts(
                [row['new_source_top10_outside_lexical_full_union']['counts'] for row in active]),
        }
    owners = [arm_summaries[arm]['owners']['visible_only'] for arm in ARMS]
    paired = {key: paired_observability(owners[0][key], owners[1][key])
              for key in ('new_source', 'pooled_lexical')}
    paired['individual_lexical'] = {
        name: paired_observability(owners[0]['individual_lexical'][name], owners[1]['individual_lexical'][name])
        for name in LEXICAL}
    summary = {
        'year': year, 'source_id': source_id, 'n_qrel_queries': len(judgments),
        'n_eligible_queries': len(eligible), 'eligible_qids': eligible,
        'excluded_qrel_queries': {qid: {'missing_sources': [name for name in names if not runs[name].get(qid)]}
                                  for qid in sorted(set(judgments) - set(eligible))},
        'raw_input_inventory': raw_inventory,
        'n_queries_depth_arm_changed': sum(row['depth_arm_changed'] for row in rows.values()),
        'qids_depth_arm_changed': [qid for qid, row in rows.items() if row['depth_arm_changed']],
        'n_queries_changed_by_source': {name: sum(name in row['changed_sources'] for row in rows.values()) for name in names},
        'arms': arm_summaries, 'same_query_paired_observability_across_arms': paired,
        'new_source_full_vs_capped_outside_candidate_coverage': {
            arm: pooled_counts([row['new_source_full_vs_capped_outside_candidate_coverage'][arm]
                                for row in rows.values()]) for arm in ('full', 'capped', 'removed_by_cap')},
    }
    return summary, rows


def input_paths(derived, root=None):
    result = {}
    for year in YEARS:
        directory = Path(root or ROOT) / 'data' / ('trec-dl-' + str(year))
        result[year] = {'qrels': directory / '{}qrels-pass.txt'.format(year),
                        'lexical': {name: directory / 'runs' / (name + '.txt') for name in LEXICAL},
                        'new_source': derived[year]}
    return result


def hash_paths(paths, root=None):
    return {str(Path(path).resolve().relative_to(Path(root or ROOT).resolve())): sha256(path) for path in paths}


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def new_output_directory(path):
    path = Path(path).resolve()
    path.mkdir(parents=True, exist_ok=False)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-manifest', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New immutable evidence directory')
    args = parser.parse_args(argv)
    try:
        manifest_path = repository_file(args.source_manifest)
        protocol_path = repository_file(args.protocol)
        # Hash manifest before its contents are used, then recheck after load.
        selection_path = repository_file('data/cycle02/source-selection.json')
        source_paths = [Path(__file__).resolve(), manifest_path, protocol_path, selection_path]
        start_sources = hash_paths(source_paths)
        source_id, derived = load_source_manifest(manifest_path)
        paths = input_paths(derived)
        data_paths = [path for year in YEARS for path in
                      [paths[year]['qrels'], *paths[year]['lexical'].values(), paths[year]['new_source']]]
        start_inputs = hash_paths(data_paths)
        # Close the window between declared-hash validation and input snapshot.
        load_source_manifest(manifest_path)
        if start_sources != hash_paths(source_paths):
            raise ValueError('source manifest, protocol, or script changed while loading')
        output = new_output_directory(args.output)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    provenance = {
        'status': 'started', 'started_utc': datetime.now(timezone.utc).isoformat(),
        'argv': list(sys.argv) if argv is None else [str(Path(__file__).resolve())] + list(argv),
        'cwd': str(Path.cwd()), 'python_version': platform.python_version(),
        'python_executable': sys.executable,
        'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'git_dirty_status': subprocess.check_output(
            ['git', '--no-optional-locks', 'status', '--short', '--untracked-files=all'], cwd=ROOT, text=True).splitlines(),
        'source_id': source_id, 'source_manifest': str(manifest_path.relative_to(ROOT)),
        'protocol': str(protocol_path.relative_to(ROOT)),
        'source_sha256_start': start_sources, 'input_sha256_start': start_inputs,
        'rank_contract': {'lexical_serialized_origin': 0, 'new_source_serialized_origin': 1,
                          'reported_origin': 1, 'ties': 'preserve serialized order; scores nonincreasing'},
        'analysis_kind': 'descriptive membership and candidate inventory only',
    }
    write_json(output / 'manifest-start.json', provenance)
    try:
        summaries, per_query = {}, {}
        for year in YEARS:
            config = paths[year]
            runs = {name: read_ranked_run(path, 0) for name, path in config['lexical'].items()}
            runs[source_id] = read_ranked_run(config['new_source'], 1)
            summaries[str(year)], per_query[str(year)] = summarize_year(
                year, source_id, runs, read_judged_membership(config['qrels']))
        end_sources, end_inputs = hash_paths(source_paths), hash_paths(data_paths)
        unchanged = start_sources == end_sources and start_inputs == end_inputs
        provenance.update({'source_sha256_end': end_sources, 'input_sha256_end': end_inputs,
                           'sources_and_inputs_unchanged': unchanged})
        if not unchanged:
            raise RuntimeError('sources or inputs changed during the audit')
        result = {
            'analysis_kind': 'descriptive observation feasibility; no relevance outcomes',
            'source_id': source_id, 'years': summaries,
            'definitions': {
                'eligible_queries': 'qrel queries with a nonempty run from every one of the five sources',
                'judged': 'qrel document membership, including explicit grade zero; grades are discarded',
                'full_arm': 'four complete supplied lexical lists plus the selected source top1000',
                'shared_depth_arm': 'all five full-arm lists cropped to Dq=min(200,minimum full-arm source length)',
                'specialist': 'fixed original full-arm owner top10 and absent every other original full-arm top30',
                'support_group': 'tail_supported iff any other original full-arm source rank>30; otherwise isolated',
                'visible_only': 'fixed-cohort members still present in their owning source for the specified arm',
                'outside_candidates': 'new-source documents outside the original lexical full-list union in both arms',
                'pooled_counts': 'query-document counts, not independent document samples or mean per-query fractions',
                'paired_observability': 'intersection of visible-only query eligibility across arms; no effect contrast',
            },
            'limits': [
                'Judgment coverage is potentially nonrandom and cannot establish relevance or comparative retrieval quality.',
                'Query counts and judged fractions alone do not establish precision or sample-size adequacy.',
                'The two depth arms reuse queries and documents and are not independent samples.',
                'These previously explored annual panels are not untouched evaluation data.',
            ],
        }
        write_json(output / 'summary.json', result)
        write_json(output / 'per_query.json', per_query)
    except Exception as error:
        provenance.update({'status': 'invalid', 'finished_utc': datetime.now(timezone.utc).isoformat(),
                           'error': '{}: {}'.format(type(error).__name__, error)})
        for key, tracked in (('source_sha256_end', source_paths), ('input_sha256_end', data_paths)):
            if key not in provenance:
                try:
                    provenance[key] = hash_paths(tracked)
                except OSError as hash_error:
                    provenance[key + '_error'] = str(hash_error)
        provenance['sources_and_inputs_unchanged'] = (
            provenance.get('source_sha256_end') == start_sources and
            provenance.get('input_sha256_end') == start_inputs)
        write_json(output / 'manifest-invalid.json', provenance)
        raise
    provenance.update({'status': 'complete', 'finished_utc': datetime.now(timezone.utc).isoformat(),
                       'output_sha256': {path.name: sha256(path) for path in sorted(output.glob('*.json'))}})
    write_json(output / 'manifest.json', provenance)
    print('Wrote observation inventory:', output, flush=True)


if __name__ == '__main__':
    main()
