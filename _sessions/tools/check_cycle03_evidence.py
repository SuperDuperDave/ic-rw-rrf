#!/usr/bin/env python3
"""Independent cycle03 arithmetic checks; no experiment-module imports.

The synthetic-only entry point reads no dataset. The explicit --results entry
point reconstructs effects from frozen cohort IDs and original qrel grades.
Fractions and exhaustive binary completions specify endpoints independently.
"""

import argparse
from fractions import Fraction
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parents[2]


def exact_group(values):
    if not values or any(v is not None and type(v) is not bool for v in values):
        raise ValueError('Expected a nonempty group of binary or missing outcomes')
    relevant = sum(v is True for v in values)
    unknown = sum(v is None for v in values)
    return Fraction(relevant, len(values)), Fraction(relevant + unknown, len(values))


def exact_contrast(supported, isolated):
    sl, su = exact_group(supported)
    il, iu = exact_group(isolated)
    return sl - iu, su - il


def completions(values):
    locations = [i for i, value in enumerate(values) if value is None]
    for fill in product((False, True), repeat=len(locations)):
        completed = list(values)
        for index, value in zip(locations, fill):
            completed[index] = value
        yield Fraction(sum(completed), len(completed))


def synthetic_check():
    groups = [values for size in (1, 2, 3)
              for values in product((False, True, None), repeat=size)]
    cases = assignments = 0
    for supported, isolated in product(groups, repeat=2):
        extrema = [s - i for s, i in product(completions(supported), completions(isolated))]
        lo, hi = exact_contrast(supported, isolated)
        assert (lo, hi) == (min(extrema), max(extrema))
        width = (Fraction(supported.count(None), len(supported))
                 + Fraction(isolated.count(None), len(isolated)))
        assert hi - lo == width
        cases += 1
        assignments += len(extrema)
    assert exact_contrast([None], [None]) == (Fraction(-1), Fraction(1))
    assert exact_contrast([True, False], [False, False]) == (Fraction(1, 2), Fraction(1, 2))
    # Equal query weights differ from pooling nine extra documents in query2.
    first = exact_contrast([True], [False])
    second = exact_contrast([False] * 9, [False] * 9)
    equal_query = tuple((a + b) / 2 for a, b in zip(first, second))
    pooled = exact_contrast([True] + [False] * 9, [False] * 10)
    assert equal_query == (Fraction(1, 2),) * 2
    assert pooled == (Fraction(1, 10),) * 2
    # With missing groups, same-value filling misses the contrast's extrema.
    same_zero = Fraction(0) - Fraction(0)
    same_one = Fraction(1) - Fraction(1)
    assert same_zero == same_one == 0
    return {'status': 'passed', 'group_pair_cases': cases,
            'binary_completion_pairs': assignments,
            'method': 'Exhaustively enumerate missing binary completions, compare Fraction extrema.',
            'equal_query_vs_pooled_example': {'equal_query': 0.5, 'pooled': 0.1},
            'all_missing_interval': [-1, 1],
            'dataset_reads': 0}


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def near(actual, expected):
    assert math.isclose(actual, float(expected), rel_tol=1e-12, abs_tol=1e-12), (actual, expected)


def quantile(values, p):
    ordered = sorted(values)
    x = (len(ordered) - 1) * p
    lo, hi = math.floor(x), math.ceil(x)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (x - lo)


def results_check(directory):
    """Run ONLY after synthetic verification and coordinator dataset authorization."""
    directory = Path(directory).resolve()
    actual = json.loads((directory / 'summary.json').read_text())
    actual_rows = json.loads((directory / 'per_query.json').read_text())
    original_path = ROOT / 'results/cycle02-2026-09-10/observations/per_query.json'
    custody_paths = [directory / 'summary.json', directory / 'per_query.json', original_path]
    custody_paths += [ROOT / f'data/trec-dl-{year}/{year}qrels-pass.txt' for year in ('2019', '2020')]
    before = {str(p.relative_to(ROOT)): file_sha(p) for p in custody_paths}
    original = json.loads(original_path.read_text())
    source_id = 'splade_pp_ensemble_distil'
    report = {}
    checked_rows = 0
    for year in ('2019', '2020'):
        grades = {}
        qrel_path = ROOT / f'data/trec-dl-{year}/{year}qrels-pass.txt'
        for line in qrel_path.read_text().splitlines():
            qid, unused, doc, raw = line.split()
            key = (qid, doc)
            assert key not in grades and raw in ('0', '1', '2', '3')
            grades[key] = int(raw)
        cohorts = {}
        for qid, row in original[year].items():
            cohorts[qid] = {g: [] for g in ('tail_supported', 'isolated')}
            for candidate in row['arms']['full']['specialist_candidates']:
                if candidate['owner_source'] == source_id:
                    cohorts[qid][candidate['group']].append(candidate['docid'])
        qids = sorted(q for q, g in cohorts.items() if all(g.values()))
        annual = actual['years'][year]
        assert annual['eligible_qids'] == qids
        assert annual['all_qids'] == sorted(cohorts)
        assert annual['excluded_qids'] == sorted(set(cohorts) - set(qids))
        assert annual['n_queries_eligible'] == len(qids)
        rng = random.Random(42)
        draws = [[rng.randrange(len(qids)) for _ in qids] for _ in range(10000)]
        draw_bytes = json.dumps(draws, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
        draw_hash = hashlib.sha256(draw_bytes).hexdigest()
        assert annual['bootstrap_draws']['indices_sha256'] == draw_hash
        annual_report = {'n_queries': len(qids), 'indices_sha256': draw_hash, 'outcomes': {}}
        for threshold, name in ((2, 'grade_ge_2'), (1, 'grade_gt_0')):
            endpoints = {}
            for qid, groups in cohorts.items():
                vals = {g: [None if (qid, doc) not in grades else grades[qid, doc] >= threshold
                            for doc in docs] for g, docs in groups.items()}
                a = actual_rows[year][qid]['outcomes'][name]
                for group, values in vals.items():
                    saved = a['groups'][group]
                    assert (saved['n'], saved['r'], saved['u'], saved['n_judged']) == (
                        len(values), values.count(True), values.count(None), len(values) - values.count(None))
                    if values:
                        lo, hi = exact_group(values)
                        near(saved['lower'], lo)
                        near(saved['upper'], hi)
                if qid in qids:
                    lo, hi = exact_contrast(vals['tail_supported'], vals['isolated'])
                    endpoints[qid] = lo, hi
                    near(a['contrast']['lower'], lo)
                    near(a['contrast']['upper'], hi)
                    near(a['contrast']['width'], hi - lo)
                    near(a['contrast']['missing_fraction_sum'], hi - lo)
                else:
                    assert a['contrast'] is None
                checked_rows += 1
            lo = sum(v[0] for v in endpoints.values()) / len(qids)
            hi = sum(v[1] for v in endpoints.values()) / len(qids)
            measured = annual['outcomes'][name]
            interval = measured['empirical_sharp_interval']
            for key, value in (('lower', lo), ('upper', hi), ('width', hi - lo)):
                near(interval[key], value)
            near(measured['missing_width_invariant']['mean_missing_fraction_sum'], hi - lo)
            # Multiplicity-weighted resampling is an independent computation of
            # the paired query bootstrap, using exact endpoints converted once.
            values = [(float(endpoints[q][0]), float(endpoints[q][1])) for q in qids]
            distributions = [[], []]
            for draw in draws:
                frequency = [draw.count(i) for i in range(len(qids))]
                for end in (0, 1):
                    distributions[end].append(math.fsum(f * value[end] for f, value in zip(frequency, values)) / len(qids))
            quantiles = [{str(p): quantile(v, p) for p in (0.025, 0.975)} for v in distributions]
            bs = measured['bootstrap']
            for end, field in enumerate(('lower_endpoint_quantiles', 'upper_endpoint_quantiles')):
                for p, value in quantiles[end].items():
                    near(bs[field][p], value)
            elo, ehi = quantiles[0]['0.025'], quantiles[1]['0.975']
            for key, value in (('lower', elo), ('upper', ehi), ('width', ehi - elo)):
                near(bs['exploratory_uncertainty_envelope'][key], value)
            label = ('material_positive' if elo > 0.10 else
                     'material_negative' if ehi < -0.10 else
                     'small_under_chosen_bound' if elo >= -0.10 and ehi <= 0.10 and ehi - elo <= 0.10 else
                     'inconclusive')
            if name == 'grade_ge_2':
                assert measured['interpretation'] == label
            annual_report['outcomes'][name] = {'sharp_interval': [float(lo), float(hi)],
                                               'bootstrap_envelope': [elo, ehi],
                                               'independently_classified': label}
        report[year] = annual_report
    labels = [report[y]['outcomes']['grade_ge_2']['independently_classified'] for y in ('2019', '2020')]
    gate = ('advance_to_distinct_fusion_contribution_protocol'
            if labels[0] == labels[1] and labels[0] in ('material_positive', 'material_negative')
            else 'stop_association_branch_and_draft_R5_controlled_known_truth_task')
    assert actual['branch_decision'] == gate
    assert before == {str(p.relative_to(ROOT)): file_sha(p) for p in custody_paths}
    return {'status': 'verified', 'query_outcome_rows_checked': checked_rows,
            'input_artifact_sha256': before, 'input_artifacts_unchanged_during_check': True,
            'independent_branch_decision': gate,
            'years': report, 'source_cohort_sha256': file_sha(original_path),
            'summary_sha256': file_sha(directory / 'summary.json'),
            'per_query_sha256': file_sha(directory / 'per_query.json'),
            'method': 'Original qrel/cohort reconstruction with Fraction endpoints and multiplicity-weighted bootstrap; no production imports.',
            'scope': 'All query-group counts, paired eligibility, endpoint widths, draw hashes, bootstrap quantiles/envelopes, primary labels, and branch decision.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--synthetic-only', action='store_true')
    mode.add_argument('--results', type=Path, help='Completed cycle03 evidence directory')
    parser.add_argument('--receipt', type=Path, help='Optional fresh receipt path')
    args = parser.parse_args()
    result = synthetic_check() if args.synthetic_only else results_check(args.results)
    result['checker_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    protocol = ROOT / '_sessions/cycles/2026-09-10-cycle03-specialist-association-protocol.md'
    result['protocol_sha256'] = hashlib.sha256(protocol.read_bytes()).hexdigest()
    if args.receipt:
        with args.receipt.open('x') as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write('\n')
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
