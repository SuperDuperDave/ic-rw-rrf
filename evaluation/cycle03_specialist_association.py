#!/usr/bin/env python3
"""Frozen cycle03 specialist association (Python 3.8+, standard library).

The CLI has no source, cohort, threshold, seed, or bootstrap search controls.
Run synthetic tests before authorizing the first actual relevance calculation.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import subprocess
import sys

try:
    from evaluation import cycle02_observation_audit as observation
except ModuleNotFoundError:  # Direct script invocation from repository root.
    import cycle02_observation_audit as observation


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = 'splade_pp_ensemble_distil'
YEARS = (2019, 2020)
GROUPS = ('tail_supported', 'isolated')
OUTCOMES = {'grade_ge_2': 2, 'grade_gt_0': 1}
PRIMARY = 'grade_ge_2'
B = 10000
SEED = 42
DELTA = 0.10
EXPECTED_COUNTS = {2019: (43, 20), 2020: (54, 23)}
PROTOCOL = '_sessions/cycles/2026-09-10-cycle03-specialist-association-protocol.md'
OBSERVATIONS = 'results/cycle02-2026-09-10/observations'
OBS_MANIFEST_SHA256 = '74a41d2e96754cd658c8486b296a7a8e01691c4c6fa894a9f256b05d23da5bea'
SELECTION = 'data/cycle02/source-selection.json'
ACQUIRED = 'data/cycle02/acquired/source-manifest.json'
DRAW_ENCODING = ('UTF-8 bytes of json.dumps(draw_matrix, separators=(",",":"), '
                 'ensure_ascii=True), no trailing newline')


def read_json(path):
    """Reject duplicate JSON keys rather than accept an ambiguous custody record."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)


def read_qrels(path):
    """Strict original grades; explicit zero is known and absent pairs are unknown."""
    result = {}
    with Path(path).open(encoding='utf-8') as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            parts = line.split()
            where = '{}:{}'.format(path, number)
            if len(parts) != 4:
                raise ValueError(where + ': expected four qrel fields')
            qid, _, docid, raw = parts
            try:
                grade = int(raw)
            except ValueError as error:
                raise ValueError(where + ': grade must be an integer in 0..3') from error
            if grade not in (0, 1, 2, 3):
                raise ValueError(where + ': grade outside 0..3')
            query = result.setdefault(qid, {})
            if docid in query:
                raise ValueError(where + ': duplicate qrel document within query')
            query[docid] = grade
    if not result:
        raise ValueError('qrels contain no query rows')
    return result


def group_bounds(documents, grades, threshold):
    if type(threshold) is not int or threshold not in (1, 2):
        raise ValueError('only the frozen thresholds 1 and 2 are supported')
    if any(type(grade) is not int or grade not in (0, 1, 2, 3)
           for grade in grades.values()):
        raise ValueError('grades must be integers in 0..3')
    documents = list(documents)
    if len(set(documents)) != len(documents):
        raise ValueError('duplicate candidate document')
    n = len(documents)
    u = sum(doc not in grades for doc in documents)
    r = sum(grades[doc] >= threshold for doc in documents if doc in grades)
    return {'n': n, 'r': r, 'u': u, 'n_judged': n - u,
            'lower': r / n if n else None, 'upper': (r + u) / n if n else None}


def query_outcome(candidates, grades, threshold):
    seen = set()
    for candidate in candidates:
        doc = candidate['docid']
        if doc in seen or candidate['group'] not in GROUPS:
            raise ValueError('candidates must have unique documents and a frozen group')
        seen.add(doc)
        if type(candidate['judged']) is not bool or candidate['judged'] != (doc in grades):
            raise ValueError('candidate judged membership differs from qrels')
    groups = {group: group_bounds([row['docid'] for row in candidates if row['group'] == group],
                                  grades, threshold) for group in GROUPS}
    supported, isolated = (groups[group] for group in GROUPS)
    contrast = None
    if supported['n'] and isolated['n']:
        lower = supported['lower'] - isolated['upper']
        upper = supported['upper'] - isolated['lower']
        missing = supported['u'] / supported['n'] + isolated['u'] / isolated['n']
        if not math.isclose(upper - lower, missing, abs_tol=1e-12):
            raise AssertionError('missing-width invariant failed')
        contrast = {'lower': lower, 'upper': upper, 'width': upper - lower,
                    'missing_fraction_sum': missing}
    return {'groups': groups, 'contrast': contrast}


def quantile(values, probability):
    if not values or not 0 <= probability <= 1:
        raise ValueError('quantile requires nonempty values and a probability in [0,1]')
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    left = int(math.floor(position))
    right = min(left + 1, len(ordered) - 1)
    return ordered[left] + (position - left) * (ordered[right] - ordered[left])


def bootstrap_indices(qids, replicates=B):
    """One paired query-index matrix reused for endpoints and both outcomes."""
    qids = sorted(qids)
    if not qids or any(not isinstance(qid, str) for qid in qids) or len(set(qids)) != len(qids):
        raise ValueError('bootstrap requires unique nonempty string query IDs')
    if type(replicates) is not int or replicates <= 0:
        raise ValueError('bootstrap replicate count must be positive')
    rng = random.Random(SEED)
    draws = [[rng.randrange(len(qids)) for _ in qids] for _ in range(replicates)]
    encoded = json.dumps(draws, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
    return draws, {'B': replicates, 'seed': SEED, 'n': len(qids), 'sorted_qids': qids,
                   'indices_sha256': hashlib.sha256(encoded).hexdigest(), 'encoding': DRAW_ENCODING,
                   'generator': 'random.Random(42), randrange(n) n times per replicate; reset per year'}


def interpret_envelope(lower, upper):
    if not all(math.isfinite(value) for value in (lower, upper)) or lower > upper:
        raise ValueError('envelope endpoints must be finite and ordered')
    if lower > DELTA:
        return 'material_positive'
    if upper < -DELTA:
        return 'material_negative'
    if lower >= -DELTA and upper <= DELTA and upper - lower <= 0.10:
        return 'small_under_chosen_bound'
    return 'inconclusive'


def branch_decision(primary_interpretations):
    if len(primary_interpretations) != len(YEARS):
        raise ValueError('the branch gate requires both annual primary interpretations')
    if primary_interpretations[0] == primary_interpretations[1] and primary_interpretations[0] in (
            'material_positive', 'material_negative'):
        return 'advance_to_distinct_fusion_contribution_protocol'
    return 'stop_association_branch_and_draft_R5_controlled_known_truth_task'


def summarize_outcome(records, draws, primary):
    n = len(records)
    if not n or any(record is None for record in records):
        raise ValueError('only candidate-paired queries enter the contrast')
    lower = math.fsum(row['lower'] for row in records) / n
    upper = math.fsum(row['upper'] for row in records) / n
    missing = math.fsum(row['missing_fraction_sum'] for row in records) / n
    invariant = math.isclose(upper - lower, missing, abs_tol=1e-12)
    if not invariant:
        raise AssertionError('aggregate missing-width invariant failed')
    lower_samples, upper_samples = [], []
    for indices in draws:
        if len(indices) != n or any(type(index) is not int or not 0 <= index < n for index in indices):
            raise ValueError('each paired bootstrap draw must contain n valid query indices')
        lower_samples.append(math.fsum(records[index]['lower'] for index in indices) / n)
        upper_samples.append(math.fsum(records[index]['upper'] for index in indices) / n)
    lower_quantiles = {str(p): quantile(lower_samples, p) for p in (0.025, 0.975)}
    upper_quantiles = {str(p): quantile(upper_samples, p) for p in (0.025, 0.975)}
    lo, hi = lower_quantiles['0.025'], upper_quantiles['0.975']
    result = {'empirical_sharp_interval': {'lower': lower, 'upper': upper, 'width': upper - lower},
              'missing_width_invariant': {'mean_missing_fraction_sum': missing, 'holds': invariant},
              'bootstrap': {'lower_endpoint_quantiles': lower_quantiles,
                            'upper_endpoint_quantiles': upper_quantiles,
                            'exploratory_uncertainty_envelope': {'lower': lo, 'upper': hi, 'width': hi - lo}}}
    if primary:
        result['interpretation'] = interpret_envelope(lo, hi)
    return result


def analyze_year(candidates_by_query, qrels, replicates=B):
    """All-query outputs; only candidate-paired rows enter equal-query means."""
    rows = {}
    for qid, candidates in sorted(candidates_by_query.items()):
        if qid not in qrels:
            raise ValueError('frozen query absent from qrels: ' + qid)
        missing = [group for group in GROUPS if not any(row['group'] == group for row in candidates)]
        rows[qid] = {'eligible': not missing, 'missing_candidate_groups': missing,
                     'candidates': candidates,
                     'outcomes': {name: query_outcome(candidates, qrels[qid], threshold)
                                  for name, threshold in OUTCOMES.items()}}
    eligible = [qid for qid, row in rows.items() if row['eligible']]
    excluded = [qid for qid, row in rows.items() if not row['eligible']]
    draws, draw_receipt = bootstrap_indices(eligible, replicates)
    outcomes = {name: summarize_outcome([rows[qid]['outcomes'][name]['contrast'] for qid in eligible],
                                        draws, name == PRIMARY) for name in OUTCOMES}
    summary = {'n_queries_all': len(rows), 'all_qids': list(rows), 'eligible_qids': eligible,
               'excluded_qids': excluded, 'n_queries_eligible': len(eligible),
               'exclusions': {qid: {'missing_candidate_groups': rows[qid]['missing_candidate_groups']}
                              for qid in excluded}, 'outcomes': outcomes, 'bootstrap_draws': draw_receipt}
    if not math.isclose(outcomes['grade_ge_2']['empirical_sharp_interval']['width'],
                        outcomes['grade_gt_0']['empirical_sharp_interval']['width'], abs_tol=1e-12):
        raise AssertionError('missing-label width must not depend on relevance threshold')
    return summary, rows


def fixed_paths(root, protocol):
    source_names = ['evaluation/cycle03_specialist_association.py',
                    'evaluation/tests/test_cycle03_specialist_association.py',
                    'evaluation/cycle02_observation_audit.py', str(protocol), SELECTION, ACQUIRED,
                    '_sessions/cycles/2026-09-10-cycle02-observation-protocol.md']
    source_names += [OBSERVATIONS + '/' + name for name in
                     ('manifest.json', 'manifest-start.json', 'summary.json', 'per_query.json')]
    configs = observation.input_paths({year: root / 'data/cycle02/acquired' / ('dl{}.trec'.format(year))
                                      for year in YEARS}, root)
    data = [path for year in YEARS for path in
            [configs[year]['qrels'], *configs[year]['lexical'].values(), configs[year]['new_source']]]
    sources = [observation.repository_file(name, root) for name in source_names]
    data = [observation.repository_file(path, root) for path in data]
    return sources, data, configs


def validate_custody(root, source_hashes, input_hashes):
    """Anchor to the completed, pre-outcome cycle02 observation manifest."""
    manifest_path = root / OBSERVATIONS / 'manifest.json'
    if observation.sha256(manifest_path) != OBS_MANIFEST_SHA256:
        raise ValueError('frozen observation manifest hash mismatch')
    manifest = read_json(manifest_path)
    if manifest.get('status') != 'complete' or manifest.get('sources_and_inputs_unchanged') is not True:
        raise ValueError('cycle02 observation manifest must record complete unchanged inputs')
    for prefix, actual in (('source', source_hashes), ('input', input_hashes)):
        start, end = manifest[prefix + '_sha256_start'], manifest[prefix + '_sha256_end']
        if not start or start != end:
            raise ValueError('cycle02 {} start/end hash mismatch'.format(prefix))
        if any(actual.get(path) != digest for path, digest in start.items()):
            raise ValueError('current files differ from cycle02 {} custody'.format(prefix))
        if prefix == 'input' and set(start) != set(input_hashes):
            raise ValueError('cycle02 input inventory differs from fixed inputs')
    if set(manifest['output_sha256']) != {'manifest-start.json', 'per_query.json', 'summary.json'}:
        raise ValueError('unexpected cycle02 output inventory')
    for name, digest in manifest['output_sha256'].items():
        if source_hashes.get(OBSERVATIONS + '/' + name) != digest:
            raise ValueError('cycle02 observation output hash mismatch: ' + name)
    selection, acquired = read_json(root / SELECTION), read_json(root / ACQUIRED)
    if any(record.get('source_id') != SOURCE_ID for record in (manifest, selection, acquired)):
        raise ValueError('source identity differs from frozen SPLADE source')
    if acquired.get('selection_sha256') != source_hashes[SELECTION]:
        raise ValueError('acquisition selection hash mismatch')
    if any(selection.get(key) != acquired.get(key) for key in ('dataset_id', 'dataset_revision')):
        raise ValueError('acquisition dataset identity mismatch')
    source_id, derived = observation.load_source_manifest(root / ACQUIRED, root)
    for year in YEARS:
        if derived[year] != root / 'data/cycle02/acquired' / ('dl{}.trec'.format(year)):
            raise ValueError('derived run path differs from frozen path')
    frozen, summary = read_json(root / OBSERVATIONS / 'per_query.json'), read_json(root / OBSERVATIONS / 'summary.json')
    if summary.get('source_id') != source_id or set(frozen) != {str(year) for year in YEARS}:
        raise ValueError('frozen observation source or annual inventory mismatch')
    return frozen, summary


def validate_cohort(year, frozen_rows, frozen_summary, runs, qrels):
    names = list(observation.LEXICAL) + [SOURCE_ID]
    qids = sorted(qid for qid in qrels if all(runs[name].get(qid) for name in names))
    if qids != sorted(frozen_rows) or qids != frozen_summary['eligible_qids']:
        raise ValueError('all-query inventory differs from frozen observations')
    candidates = {}
    for qid in qids:
        lists = {name: runs[name][qid][:1000] if name == SOURCE_ID else runs[name][qid] for name in names}
        reconstructed = [row for row in observation.specialist_candidates(lists, lists, qrels[qid])
                         if row['owner_source'] == SOURCE_ID]
        frozen = [row for row in frozen_rows[qid]['arms']['full']['specialist_candidates']
                  if row['owner_source'] == SOURCE_ID]
        if any(type(row.get('judged')) is not bool for row in frozen) or frozen != reconstructed:
            raise ValueError('SPLADE specialist membership, groups, ranks, or judgments changed: ' + qid)
        candidates[qid] = frozen
    expected = frozen_summary['arms']['full']['owners']['fixed_cohort']['new_source']
    if observation.summarize_groups(candidates) != expected:
        raise ValueError('frozen SPLADE denominators or eligibility differ from reconstructed cohort')
    actual_counts = (len(qids), expected['eligibility']['with_both_groups']['n_queries'])
    if actual_counts != EXPECTED_COUNTS[year] or len(qrels) != EXPECTED_COUNTS[year][0]:
        raise ValueError('query counts differ from prespecified annual inventory')
    return candidates


def new_output_directory(path, root):
    path = Path(path).resolve()
    try:
        path.relative_to((root / 'results').resolve())
    except ValueError as error:
        raise ValueError('output must be a fresh directory inside repository results/') from error
    path.mkdir(parents=True, exist_ok=False)
    return path


def git_state(root):
    return {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
            'dirty_status': subprocess.check_output(
                ['git', '--no-optional-locks', 'status', '--short', '--untracked-files=all'],
                cwd=root, text=True).splitlines()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Fresh immutable directory in results/')
    parser.add_argument('--protocol', type=Path, default=Path(PROTOCOL))
    args = parser.parse_args(argv)
    root = ROOT.resolve()
    try:
        protocol = observation.repository_file(args.protocol, root)
        sources, data, configs = fixed_paths(root, protocol)
        source_start = observation.hash_paths(sources, root)
        input_start = observation.hash_paths(data, root)
        output = new_output_directory(args.output, root)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    provenance = {'status': 'started', 'started_utc': datetime.now(timezone.utc).isoformat(),
                  'argv': list(sys.argv) if argv is None else [str(Path(__file__).resolve())] + list(argv),
                  'cwd': str(Path.cwd()), 'python_version': platform.python_version(),
                  'python_executable': sys.executable, 'python_implementation': platform.python_implementation(),
                  'protocol': str(protocol.relative_to(root)), 'source_id': SOURCE_ID,
                  'source_sha256_start': source_start, 'input_sha256_start': input_start,
                  'frozen_observation_manifest_sha256': OBS_MANIFEST_SHA256,
                  'git_state_start': git_state(root)}
    observation.write_json(output / 'manifest-start.json', provenance)
    try:
        frozen, frozen_summary = validate_custody(root, source_start, input_start)
        summaries, per_query = {}, {}
        for year in YEARS:
            config = configs[year]
            runs = {name: observation.read_ranked_run(path, 0) for name, path in config['lexical'].items()}
            runs[SOURCE_ID] = observation.read_ranked_run(config['new_source'], 1)
            qrels = read_qrels(config['qrels'])
            candidates = validate_cohort(year, frozen[str(year)], frozen_summary['years'][str(year)], runs, qrels)
            summaries[str(year)], per_query[str(year)] = analyze_year(candidates, qrels)
            summaries[str(year)]['frozen_observation_inventory'] = {
                'per_query_path': OBSERVATIONS + '/per_query.json',
                'per_query_sha256': source_start[OBSERVATIONS + '/per_query.json'],
                'summary_path': OBSERVATIONS + '/summary.json',
                'summary_sha256': source_start[OBSERVATIONS + '/summary.json'],
                'n_qrel_queries': frozen_summary['years'][str(year)]['n_qrel_queries']}
        result = {'analysis_kind': 'descriptive equal-query specialist relevance association',
                  'comparator': 'SPLADE-owned tail-supported minus SPLADE-owned isolated specialists',
                  'primary_outcome': PRIMARY, 'secondary_outcome': 'grade_gt_0', 'delta': DELTA,
                  'small_envelope_maximum_width': 0.10, 'years': summaries,
                  'branch_decision': branch_decision([summaries[str(year)]['outcomes'][PRIMARY]['interpretation']
                                                       for year in YEARS]),
                  'assumptions_and_limits': [
                      'Fixed full-arm specialist candidates; eligibility uses candidates, not judgment presence.',
                      'Each query has equal weight; documents and annual panels are never pooled as independent samples.',
                      'Observed qrel grades are fixed; every unjudged binary label may independently be zero or one.',
                      'Opposite missing assignments in supported and isolated groups jointly attain the sharp endpoints.',
                      'Empirical sharp bounds describe missing-label uncertainty for this finite eligible-query panel.',
                      'The exploratory bootstrap uncertainty envelope assumes exchangeable queries within each year.',
                      'Bootstrap quantiles linearly interpolate at (B-1)p; no exact coverage or calibrated p-value claim.',
                      'These annual panels were previously used for development and are not untouched evaluation data.',
                      'Support is coupled to lexical candidate access; association does not identify mechanism or fusion value.',
                      'Secondary grade>0 cannot override the primary two-year decision gate.',
                  ]}
        observation.write_json(output / 'summary.json', result)
        observation.write_json(output / 'per_query.json', per_query)
        provenance['source_sha256_end'] = observation.hash_paths(sources, root)
        provenance['input_sha256_end'] = observation.hash_paths(data, root)
        provenance['sources_and_inputs_unchanged'] = (
            source_start == provenance['source_sha256_end'] and input_start == provenance['input_sha256_end'])
        if not provenance['sources_and_inputs_unchanged']:
            raise RuntimeError('sources or inputs changed during cycle03; outputs are invalid')
        provenance['git_state_end'] = git_state(root)
    except Exception as error:
        provenance.update({'status': 'invalid', 'finished_utc': datetime.now(timezone.utc).isoformat(),
                           'error': '{}: {}'.format(type(error).__name__, error)})
        for key, paths in (('source_sha256_end', sources), ('input_sha256_end', data)):
            try:
                provenance[key] = observation.hash_paths(paths, root)
            except (OSError, ValueError) as hash_error:
                provenance[key + '_error'] = str(hash_error)
        provenance['sources_and_inputs_unchanged'] = (
            provenance.get('source_sha256_end') == source_start and provenance.get('input_sha256_end') == input_start)
        provenance['git_state_end'] = git_state(root)
        observation.write_json(output / 'manifest-invalid.json', provenance)
        raise
    provenance.update({'status': 'complete', 'finished_utc': datetime.now(timezone.utc).isoformat(),
                       'output_sha256': {path.name: observation.sha256(path)
                                         for path in sorted(output.glob('*.json'))}})
    observation.write_json(output / 'manifest.json', provenance)
    print('Wrote cycle03 association:', output, flush=True)


if __name__ == '__main__':
    main()
