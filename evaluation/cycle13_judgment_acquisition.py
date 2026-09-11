"""Cycle13 exact partial-judgment bounds and per-query acquisition plans.

Uses the frozen floating canonical RRF ordering. Only metric arithmetic is exact.
No labels, provider answers, stochastic samples, or alternative designs are acquired.
"""
import argparse
from datetime import datetime, timezone
from fractions import Fraction
import json
from pathlib import Path
import platform
import sys
import time

if __package__:
    from .fusion_contract import canonical_rrf
    from .cycle02_observation_audit import LEXICAL, read_ranked_run, sha256, repository_file
    from .cycle03_specialist_association import read_qrels
else:
    from fusion_contract import canonical_rrf
    from cycle02_observation_audit import LEXICAL, read_ranked_run, sha256, repository_file
    from cycle03_specialist_association import read_qrels


ROOT = Path(__file__).resolve().parents[1]
CODE = 'evaluation/cycle13_judgment_acquisition.py'
TESTS = 'evaluation/tests/test_cycle13_judgment_acquisition.py'
PROTOCOL = '_sessions/cycles/2026-09-11-cycle13-judgment-protocol.md'
SOURCE_FILES = (CODE, TESTS, PROTOCOL, 'evaluation/fusion_contract.py',
                'evaluation/cycle02_observation_audit.py', 'evaluation/cycle03_specialist_association.py')
YEARS = (2019, 2020)
EXPECTED_QUERY_COUNTS = {2019: 43, 2020: 54}
SOURCE_ID = 'splade_pp_ensemble_distil'
SOURCES = LEXICAL + (SOURCE_ID,)
DEPTHS = {name: 30 for name in LEXICAL}
DEPTHS[SOURCE_ID] = 1000
PERSISTENCE = Fraction(4, 5)
CUTOFF = 10
BUDGETS = (0, 1, 3)
POLICIES = ('absolute_influence', 'pooled_head', 'uniform')
STATUSES = ('b_better', 'a_better', 'tie', 'unresolved')


def exact_json(value):
    """Fractions serialize as canonical rational strings; never rounded weights."""
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {str(key): exact_json(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(child) for child in value]
    return value


def canonical_json(value):
    return json.dumps(exact_json(value), sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False) + '\n'


def _ranking(value):
    if not isinstance(value, (list, tuple)):
        raise ValueError('ranking must be a list or tuple of document IDs')
    if any(type(doc) is not str or not doc for doc in value) or len(set(value)) != len(value):
        raise ValueError('ranking IDs must be distinct nonempty strings')
    return list(value)


def rank_weights(ranking):
    ranking = _ranking(ranking)
    return {doc: (1 - PERSISTENCE) * PERSISTENCE ** index
            for index, doc in enumerate(ranking[:CUTOFF])}


def classify_interval(lower, upper):
    if lower > upper:
        raise ValueError('interval endpoints are reversed')
    if lower > 0:
        return 'b_better'
    if upper < 0:
        return 'a_better'
    if lower == upper == 0:
        return 'tie'
    return 'unresolved'


def analyze_query(ranking_a, ranking_b, grades):
    """Sharp B-minus-A metric interval and plans, sharing identity before bounds."""
    a, b = _ranking(ranking_a)[:CUTOFF], _ranking(ranking_b)[:CUTOFF]
    if (type(grades) is not dict or any(type(doc) is not str or not doc
            or type(grade) is not int or grade not in (0, 1, 2, 3) for doc, grade in grades.items())):
        raise ValueError('grades must map document IDs to exact integers 0..3')
    weights_a, weights_b = rank_weights(a), rank_weights(b)
    ranks_a, ranks_b = ({doc: index for index, doc in enumerate(ranking, 1)} for ranking in (a, b))
    documents = []
    for doc in sorted(set(a) | set(b)):
        wa, wb = weights_a.get(doc, Fraction()), weights_b.get(doc, Fraction())
        known = doc in grades
        documents.append({'docid': doc, 'rank_a': ranks_a.get(doc), 'rank_b': ranks_b.get(doc),
                          'weight_a': wa, 'weight_b': wb, 'coefficient': wb - wa,
                          'absolute_influence': abs(wb - wa), 'known': known,
                          'grade': grades.get(doc), 'gain': Fraction(grades[doc], 3) if known else None})
    known = sum((doc['coefficient'] * doc['gain'] for doc in documents if doc['known']), Fraction())
    unknown = [doc for doc in documents if not doc['known']]
    lower = known + sum((min(doc['coefficient'], 0) for doc in unknown), Fraction())
    upper = known + sum((max(doc['coefficient'], 0) for doc in unknown), Fraction())
    width = sum((doc['absolute_influence'] for doc in unknown), Fraction())
    if upper - lower != width:
        raise AssertionError('sharp interval width identity failed')
    influence = sorted(unknown, key=lambda doc: (-doc['absolute_influence'], doc['docid']))
    # Missing ranks are beyond both retained heads. No float rank arithmetic is needed.
    head = sorted(unknown, key=lambda doc: (min(doc['rank_a'] or CUTOFF + 1,
                                                doc['rank_b'] or CUTOFF + 1), doc['docid']))
    plans = {}
    for budget in BUDGETS:
        realized = min(budget, len(unknown))
        selected_i, selected_h = influence[:realized], head[:realized]
        policy_records = {}
        for name, selected in (('absolute_influence', selected_i), ('pooled_head', selected_h)):
            reduction = sum((doc['absolute_influence'] for doc in selected), Fraction())
            policy_records[name] = {'selected_docids': [doc['docid'] for doc in selected],
                                    'projected_width': width - reduction, 'width_reduction': reduction}
        uniform_width = width * Fraction(len(unknown) - realized, len(unknown)) if unknown else Fraction()
        policy_records['uniform'] = {'selected_docids': None, 'expected_projected_width': uniform_width,
                                     'expected_width_reduction': width - uniform_width}
        ids_i = {doc['docid'] for doc in selected_i}
        ids_h = {doc['docid'] for doc in selected_h}
        plans[str(budget)] = {'requested_budget': budget, 'realized_budget': realized,
                             'pool_size': len(unknown), **policy_records,
                             'overlap': {'equal_selected_sets': ids_i == ids_h,
                                         'intersection_size': len(ids_i & ids_h)}}
        if not (Fraction() <= policy_records['absolute_influence']['projected_width']
                <= policy_records['pooled_head']['projected_width'] <= width
                and policy_records['absolute_influence']['projected_width'] <= uniform_width <= width):
            raise AssertionError('acquisition width bounds failed')
    return {'top10_a': a, 'top10_b': b, 'documents': documents,
            'counts': {'union': len(documents), 'known': len(documents) - len(unknown),
                       'unknown': len(unknown),
                       'unknown_nonzero_coefficient': sum(doc['coefficient'] != 0 for doc in unknown),
                       'unknown_zero_coefficient': sum(doc['coefficient'] == 0 for doc in unknown)},
            'known_contribution': known, 'lower': lower, 'upper': upper, 'width': width,
            'status': classify_interval(lower, upper), 'acquisition': plans}


def validate_runs(runs, expected_count):
    if type(expected_count) is not int or expected_count <= 0:
        raise ValueError('expected query count must be positive')
    if type(runs) is not dict or set(runs) != set(SOURCES):
        raise ValueError('exactly the four lexical sources and SPLADE are required')
    query_sets = []
    for name in SOURCES:
        if type(runs[name]) is not dict or any(type(qid) is not str or not qid for qid in runs[name]):
            raise ValueError('source queries must have nonempty string IDs')
        query_sets.append(set(runs[name]))
        for qid, ranking in runs[name].items():
            if len(_ranking(ranking)) != DEPTHS[name]:
                raise ValueError('retained depth mismatch: ' + name + '/' + qid)
    if any(qids != query_sets[0] for qids in query_sets[1:]):
        raise ValueError('source query sets differ; no queries may be dropped')
    if len(query_sets[0]) != expected_count:
        raise ValueError('source query count differs from the prespecified cohort')
    return sorted(query_sets[0])


def summarize_queries(records, year):
    if not records:
        raise ValueError('annual query panel cannot be empty')
    rows = list(records.values())
    n = len(rows)
    mean = lambda values: sum(values, Fraction()) / n
    lower, upper, width = (mean(row[key] for row in rows) for key in ('lower', 'upper', 'width'))
    status_counts = {status: sum(row['status'] == status for row in rows) for status in STATUSES}
    acquisitions = {}
    for budget in BUDGETS:
        plans = [row['acquisition'][str(budget)] for row in rows]
        projected, reduction = {}, {}
        for policy in POLICIES:
            prefix = 'expected_' if policy == 'uniform' else ''
            projected[policy] = mean(plan[policy][prefix + 'projected_width'] for plan in plans)
            reduction[policy] = mean(plan[policy][prefix + 'width_reduction'] for plan in plans)
        acquisitions[str(budget)] = {
            'requested_budget_per_query': budget,
            'realized_labels_total': sum(plan['realized_budget'] for plan in plans),
            'nonempty_pool_query_count': sum(plan['pool_size'] > 0 for plan in plans),
            'mean_projected_width': projected, 'mean_width_reduction': reduction,
            'selected_set_overlap': {
                'identical_set_query_count': sum(plan['overlap']['equal_selected_sets'] for plan in plans),
                'nonempty_pool_query_count': sum(plan['pool_size'] > 0 for plan in plans),
                'intersection_size_sum': sum(plan['overlap']['intersection_size'] for plan in plans),
                'both_selections_empty_query_count': sum(plan['realized_budget'] == 0 for plan in plans)}}
    return {'year': year, 'query_count': n, 'query_ids': sorted(records),
            'mean_lower': lower, 'mean_upper': upper, 'mean_width': width,
            'annual_mean_status': classify_interval(lower, upper), 'query_status_counts': status_counts,
            'query_counts': {'zero_width': sum(row['width'] == 0 for row in rows),
                             'nonempty_unknown_pool': sum(row['counts']['unknown'] > 0 for row in rows)},
            'document_pair_counts': {key: sum(row['counts'][key] for row in rows)
                                    for key in ('union', 'known', 'unknown', 'unknown_nonzero_coefficient',
                                                'unknown_zero_coefficient')},
            'acquisition': acquisitions}


def analyze_year(runs, qrels, year, expected_count=None):
    if type(year) is not int or year not in YEARS:
        raise ValueError('only 2019 and 2020 are prespecified')
    qids = validate_runs(runs, EXPECTED_QUERY_COUNTS[year] if expected_count is None else expected_count)
    if type(qrels) is not dict or any(type(qid) is not str or not qid or type(grades) is not dict
                                    for qid, grades in qrels.items()):
        raise ValueError('qrels must map query IDs to grade dictionaries')
    if any(type(doc) is not str or not doc or type(grade) is not int or grade not in (0, 1, 2, 3)
           for grades in qrels.values() for doc, grade in grades.items()):
        raise ValueError('qrels contain an invalid document ID or grade')
    records = {}
    for qid in qids:
        lexical_lists = [runs[name][qid] for name in LEXICAL]
        # Preserve every retained source list and the canonical floating tie contract.
        a = canonical_rrf(lexical_lists, k=60)
        b = canonical_rrf(lexical_lists + [runs[SOURCE_ID][qid]], k=60)
        records[qid] = analyze_query(a, b, qrels.get(qid, {}))
    summary = summarize_queries(records, year)
    summary['source_depths'] = dict(DEPTHS)
    return summary, records


def fixed_inputs(root=ROOT):
    root = Path(root)
    result = {}
    for year in YEARS:
        directory = Path('data') / ('trec-dl-' + str(year))
        relative = {'qrels': directory / (str(year) + 'qrels-pass.txt'),
                    **{name: directory / 'runs' / (name + '.txt') for name in LEXICAL},
                    SOURCE_ID: Path('data/cycle02/acquired') / ('dl' + str(year) + '.trec')}
        result[year] = {name: repository_file(str(path), root) for name, path in relative.items()}
    return result


def _source_hashes():
    return {relative: sha256(ROOT / relative) for relative in SOURCE_FILES}


def _input_hashes(paths, root):
    return {str(path.relative_to(Path(root).resolve())): sha256(path)
            for config in paths.values() for path in config.values()}


def _python_identity():
    executable = Path(sys.executable).resolve()
    return {'executable': str(executable), 'executable_sha256': sha256(executable),
            'version': sys.version, 'implementation': platform.python_implementation()}


def run_audit(output_directory, root=ROOT, command_argv=None):
    """Dataset entry point; tests may supply an isolated synthetic temporary root."""
    output = Path(output_directory)
    if output.exists():
        raise FileExistsError(output)
    start = time.monotonic()
    root = Path(root).resolve()
    sources, identity = _source_hashes(), _python_identity()
    paths = fixed_inputs(root)
    inputs = _input_hashes(paths, root)
    summaries, per_query = {}, {}
    for year in YEARS:
        config = paths[year]
        runs = {name: read_ranked_run(config[name], 0 if name in LEXICAL else 1) for name in SOURCES}
        qrels = read_qrels(config['qrels'])
        summaries[str(year)], per_query[str(year)] = analyze_year(runs, qrels, year)
    if sources != _source_hashes() or inputs != _input_hashes(paths, root) or identity != _python_identity():
        raise ValueError('input/source/interpreter changed during audit')
    summary = {'schema_version': 1,
               'comparison': {'a': list(LEXICAL), 'b': list(SOURCES), 'rrf_k': 60,
                              'fusion_ordering': 'canonical_rrf floating contributions; string-ID computed-score ties'},
               'metric': {'name': 'top10_rbp_contribution', 'persistence': PERSISTENCE,
                          'cutoff': CUTOFF, 'gain': 'grade/3', 'tail_inference': False,
                          'renormalized': False, 'delta': 'B-minus-A'},
               'allocation': {'budgets_per_query': list(BUDGETS), 'cost_per_exact_label': 1,
                              'uniform': 'analytic expectation without replacement; no sampled runs'},
               'years': summaries,
               'interpretation': 'Finite-panel bounds and per-query acquisition plans. No new labels consumed; '
                                 'projected widths do not determine future centers or signs.'}
    artifacts = {'per_query.json': canonical_json(per_query), 'summary.json': canonical_json(summary)}
    manifest = {'schema_version': 1, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'source_sha256_start': sources, 'source_sha256_end': _source_hashes(),
                'input_sha256_start': inputs, 'input_sha256_end': _input_hashes(paths, root),
                'python': identity, 'expected_query_counts': EXPECTED_QUERY_COUNTS,
                'command_argv': list(sys.argv if command_argv is None else command_argv),
                'local_wall_seconds': time.monotonic() - start,
                'new_labels_acquired': 0}
    output.mkdir(parents=True, exist_ok=False)
    for name, text in artifacts.items():
        with (output / name).open('x', encoding='utf-8') as stream:
            stream.write(text)
    manifest['artifact_sha256'] = {name: sha256(output / name) for name in artifacts}
    with (output / 'manifest.json').open('x', encoding='utf-8') as stream:
        stream.write(canonical_json(manifest))
    return per_query, summary, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    _, summary, _ = run_audit(args.output)
    print(canonical_json({'output': args.output, 'years': summary['years']}), end='')


if __name__ == '__main__':
    main()
