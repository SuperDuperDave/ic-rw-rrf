#!/usr/bin/env python3
"""
PROBE: Basin-Escape Score-Aware Fusion

Session 2026-05-13-002, Probe 2. First probe in Basin 5 (score-aware Bayesian).

Probe 1 (MC4) revealed that rank-only methods — IC-RRF lineage AND Markov-chain
aggregation — sit inside the same meta-basin: methods that exploit ranker
agreement. They lose to Vanilla RRF when rankers disagree, because rank-only
information cannot distinguish "rankers disagree because the documents are
ambiguous" from "rankers disagree because they have different confidences."

Scores carry that distinction. A ranker that places d at rank 5 with a
score 0.85 (well above the next-doc score 0.40) is making a high-confidence
claim. The same ranker placing d at rank 5 with score 0.41 (just above the
next-doc 0.40) is making a low-confidence claim. RRF treats both identically
(both contribute 1/(60+5)). Score-aware fusion can tell them apart.

This probe tests three ascending forms of score awareness:
  A) CombSUM-MinMax  — per-ranker min-max normalize, then sum
  B) CombSUM-Z       — per-ranker z-score normalize, then sum (missing -> -2)
  C) Bayesian-Logit  — per-ranker sigmoid(z) -> P(rel), log-odds combine

All three are LABEL-FREE. All three preserve graceful degradation (uniform
collapse if scores are all equal).

If any of these beats Vanilla RRF on the cross-ensemble mean (TREC DL 2019,
n=4..7) — that is the structural basin escape session 001 mapped the way to.
"""
import argparse
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import (
    parse_run_file, parse_qrels, runs_to_ranked_lists,
    fuse_vanilla_rrf, fuse_v4x, evaluate_ranking,
    paired_t_test, bootstrap_ci,
)


# ===== Score-aware fusion functions =====

def _per_ranker_minmax(scores_per_ranker):
    """Min-max normalize each ranker's score map to [0, 1]."""
    out = []
    for sm in scores_per_ranker:
        if not sm:
            out.append({})
            continue
        vals = list(sm.values())
        lo, hi = min(vals), max(vals)
        rng = hi - lo
        if rng < 1e-12:
            out.append({d: 0.5 for d in sm})
        else:
            out.append({d: (v - lo) / rng for d, v in sm.items()})
    return out


def _per_ranker_zscore(scores_per_ranker):
    """Z-score normalize each ranker's score map (mean 0, std 1)."""
    out = []
    for sm in scores_per_ranker:
        if not sm:
            out.append({})
            continue
        vals = list(sm.values())
        mu = statistics.mean(vals)
        if len(vals) > 1:
            sigma = statistics.pstdev(vals)
        else:
            sigma = 0.0
        if sigma < 1e-9:
            out.append({d: 0.0 for d in sm})
        else:
            out.append({d: (v - mu) / sigma for d, v in sm.items()})
    return out


def fuse_combsum_minmax(scores_per_ranker, fill=0.0):
    """CombSUM with per-ranker min-max normalization. Missing docs contribute `fill`."""
    norm = _per_ranker_minmax(scores_per_ranker)
    all_docs = set()
    for sm in norm:
        all_docs.update(sm.keys())
    final = {}
    for d in all_docs:
        total = 0.0
        for sm in norm:
            total += sm.get(d, fill)
        final[d] = total
    return sorted(final, key=lambda d: (-final[d], d))


def fuse_combsum_zscore(scores_per_ranker, fill=-2.0):
    """CombSUM with per-ranker z-score normalization. Missing docs get a low-z fill."""
    norm = _per_ranker_zscore(scores_per_ranker)
    all_docs = set()
    for sm in norm:
        all_docs.update(sm.keys())
    final = {}
    for d in all_docs:
        total = 0.0
        for sm in norm:
            total += sm.get(d, fill)
        final[d] = total
    return sorted(final, key=lambda d: (-final[d], d))


def _sigmoid(x):
    if x >= 0:
        e = math.exp(-x)
        return 1.0 / (1.0 + e)
    e = math.exp(x)
    return e / (1.0 + e)


def fuse_combsum_zscore_fill0(scores_per_ranker):
    """CombSUM-Z but fill=0 for absences (no penalty). Tests whether absence-penalty was the bug."""
    return fuse_combsum_zscore(scores_per_ranker, fill=0.0)


def fuse_combsum_rectz(scores_per_ranker):
    """CombSUM with rectified z-scores: only positive z contributes (max(0, z)). Absences contribute 0.
    Captures the Manmatha-style intuition that the score distribution is bimodal —
    above-mean scores are evidence of relevance; below-mean scores are non-evidence noise."""
    norm = _per_ranker_zscore(scores_per_ranker)
    all_docs = set()
    for sm in norm:
        all_docs.update(sm.keys())
    final = {}
    for d in all_docs:
        total = 0.0
        for sm in norm:
            z = sm.get(d, 0.0)
            if z > 0:
                total += z
        final[d] = total
    return sorted(final, key=lambda d: (-final[d], d))


def fuse_combanz(scores_per_ranker):
    """CombANZ: average z-score over present rankers only. Coverage-neutral."""
    norm = _per_ranker_zscore(scores_per_ranker)
    all_docs = set()
    for sm in norm:
        all_docs.update(sm.keys())
    final = {}
    for d in all_docs:
        total = 0.0; cnt = 0
        for sm in norm:
            if d in sm:
                total += sm[d]
                cnt += 1
        final[d] = total / cnt if cnt > 0 else 0.0
    return sorted(final, key=lambda d: (-final[d], d))


def fuse_bayesian_logit(scores_per_ranker, fill_z=-2.0, slope=1.0, eps=1e-6):
    """
    Bayesian-Logit fusion (label-free).
    For each ranker r:
      z_r(d) = z-normalized score
      p_r(d) = sigmoid(slope * z_r(d))           # P(relevant | this ranker)
      For docs not in r's list: p_r(d) = sigmoid(slope * fill_z)
    Combine via log-odds (assuming ranker independence):
      logit(d) = sum_r log( p_r(d) / (1 - p_r(d)) )
    Rank by logit descending.

    Algebraically log-odds = slope * z_r(d), so logit(d) = slope * sum_r z_r(d).
    This is mathematically equivalent to fuse_combsum_zscore when fill is set
    consistently — kept as a separate function for the explicit Bayesian framing
    AND because the algebra changes if slope is per-ranker-varied or fill differs.
    """
    norm = _per_ranker_zscore(scores_per_ranker)
    all_docs = set()
    for sm in norm:
        all_docs.update(sm.keys())
    final = {}
    for d in all_docs:
        logit_total = 0.0
        for sm in norm:
            z = sm.get(d, fill_z)
            p = _sigmoid(slope * z)
            p = max(min(p, 1.0 - eps), eps)
            logit_total += math.log(p / (1.0 - p))
        final[d] = logit_total
    return sorted(final, key=lambda d: (-final[d], d))


# ===== Probe runner =====

def evaluate_fusion(qids, runs, qrels, fusion_fn, fusion_input_kind='scores'):
    """
    fusion_input_kind:
      'scores'  -> fusion_fn(scores_per_ranker) -> ranked list
      'lists'   -> fusion_fn(lists) -> ranked list
      'rich'    -> fusion_fn(lists, confidences, scores_per_ranker) -> ranked list
    """
    out = {'NDCG@10': [], 'NDCG@20': [], 'MAP@100': [], 'MRR': []}
    for qid in qids:
        if qid not in qrels:
            continue
        lists, confs, sprs = runs_to_ranked_lists(runs, qid)
        if len(lists) < 2:
            continue
        if fusion_input_kind == 'scores':
            ranked = fusion_fn(sprs)
        elif fusion_input_kind == 'lists':
            ranked = fusion_fn(lists)
        elif fusion_input_kind == 'rich':
            ranked = fusion_fn(lists, confs, sprs)
        m = evaluate_ranking(ranked, qrels[qid])
        for k in out:
            out[k].append(m[k])
    return out


def fuse_v5_call(lists, confs, sprs):
    ranked, _, _, _ = fuse_v4x(lists, confs, sprs, k=60,
                                use_contrib_space=False,
                                use_reliability_gate=False,
                                use_per_doc_confidence=True)
    return ranked


def fuse_van_call(lists):
    return fuse_vanilla_rrf(lists, k=60)


def run_sweep(runs_2019, qrels_2019, runs_2020, qrels_2020):
    base4 = ['bm25.txt', 'bm25_tuned.txt', 'ql_dirichlet.txt', 'tfidf.txt']
    ensembles_2019 = [
        ('n=4 (lexical core)',  base4),
        ('n=5 (+proximity)',     base4 + ['proximity.txt']),
        ('n=6 (+tfidf_bigram)',  base4 + ['proximity.txt', 'tfidf_bigram.txt']),
        ('n=7 (+semantic_hash)', base4 + ['proximity.txt', 'tfidf_bigram.txt', 'semantic_hash.txt']),
    ]
    ensembles_2020 = [('n=4 (lexical core)', base4)]

    all_results = []
    for collection, runs_all, qrels, ensembles in [
        ('TREC DL 2019', runs_2019, qrels_2019, ensembles_2019),
        ('TREC DL 2020', runs_2020, qrels_2020, ensembles_2020),
    ]:
        for ens_name, ens_files in ensembles:
            runs_sub = {f: runs_all[f] for f in ens_files if f in runs_all}
            if len(runs_sub) != len(ens_files):
                print(f"WARN: missing for {collection} {ens_name}")
                continue
            qids = sorted(qrels.keys())

            van  = evaluate_fusion(qids, runs_sub, qrels, fuse_van_call,            'lists')
            v5   = evaluate_fusion(qids, runs_sub, qrels, fuse_v5_call,             'rich')
            csmm = evaluate_fusion(qids, runs_sub, qrels, fuse_combsum_minmax,      'scores')
            cszs = evaluate_fusion(qids, runs_sub, qrels, fuse_combsum_zscore,      'scores')
            csz0 = evaluate_fusion(qids, runs_sub, qrels, fuse_combsum_zscore_fill0,'scores')
            rctz = evaluate_fusion(qids, runs_sub, qrels, fuse_combsum_rectz,       'scores')
            canz = evaluate_fusion(qids, runs_sub, qrels, fuse_combanz,             'scores')
            blog = evaluate_fusion(qids, runs_sub, qrels, fuse_bayesian_logit,      'scores')

            def m(d, k='NDCG@10'):
                return statistics.mean(d[k]) if d[k] else 0.0

            row = {
                'collection': collection, 'ensemble': ens_name,
                'n': len(van['NDCG@10']),
                'van_n10': m(van),  'v5_n10': m(v5),
                'csmm_n10': m(csmm), 'cszs_n10': m(cszs), 'csz0_n10': m(csz0),
                'rctz_n10': m(rctz), 'canz_n10': m(canz), 'blog_n10': m(blog),
                'van_mrr': m(van, 'MRR'), 'v5_mrr': m(v5, 'MRR'),
                'csmm_mrr': m(csmm, 'MRR'), 'cszs_mrr': m(cszs, 'MRR'),
                'csz0_mrr': m(csz0, 'MRR'), 'rctz_mrr': m(rctz, 'MRR'),
                'canz_mrr': m(canz, 'MRR'), 'blog_mrr': m(blog, 'MRR'),
                'pq': {'van': van, 'v5': v5, 'csmm': csmm, 'cszs': cszs,
                       'csz0': csz0, 'rctz': rctz, 'canz': canz, 'blog': blog},
            }
            all_results.append(row)

            print(f"\n{collection} | {ens_name}  (n_queries = {row['n']})")
            print(f"  {'Variant':<22}  {'NDCG@10':>8}  {'MRR':>8}  {'vs Vanilla':>14}  {'p':>7}")
            for tag, n10_key, mrr_key in [
                ('Vanilla RRF',          'van_n10',  'van_mrr'),
                ('v5.0',                 'v5_n10',   'v5_mrr'),
                ('CombSUM-MinMax',       'csmm_n10', 'csmm_mrr'),
                ('CombSUM-Z (fill=-2)',  'cszs_n10', 'cszs_mrr'),
                ('CombSUM-Z (fill=0)',   'csz0_n10', 'csz0_mrr'),
                ('CombSUM-RectZ',        'rctz_n10', 'rctz_mrr'),
                ('CombANZ (avg z)',      'canz_n10', 'canz_mrr'),
                ('Bayesian-Logit',       'blog_n10', 'blog_mrr'),
            ]:
                n10 = row[n10_key]; mrr = row[mrr_key]
                delta = n10 - row['van_n10']
                if tag != 'Vanilla RRF':
                    pq_a = row['pq'][n10_key.replace('_n10', '')]['NDCG@10']
                    pq_b = row['pq']['van']['NDCG@10']
                    _, p = paired_t_test(pq_a, pq_b)
                    p_str = f"{p:.3f}"
                else:
                    p_str = "—"
                print(f"  {tag:<22}  {n10:>8.4f}  {mrr:>8.4f}  {delta:>+14.4f}  {p_str:>7}")

    # Cross-ensemble means
    rows_19 = [r for r in all_results if r['collection'] == 'TREC DL 2019']
    if rows_19:
        print("\n" + "=" * 72)
        print("CROSS-ENSEMBLE MEAN — TREC DL 2019 (n=4,5,6,7)")
        print("=" * 72)
        for tag, key in [
            ('Vanilla RRF',          'van_n10'),
            ('v5.0',                 'v5_n10'),
            ('CombSUM-MinMax',       'csmm_n10'),
            ('CombSUM-Z (fill=-2)',  'cszs_n10'),
            ('CombSUM-Z (fill=0)',   'csz0_n10'),
            ('CombSUM-RectZ',        'rctz_n10'),
            ('CombANZ (avg z)',      'canz_n10'),
            ('Bayesian-Logit',       'blog_n10'),
        ]:
            mean = statistics.mean([r[key] for r in rows_19])
            van_mean = statistics.mean([r['van_n10'] for r in rows_19])
            delta = mean - van_mean
            print(f"  {tag:<22}  NDCG@10 = {mean:.4f}    vs Vanilla = {delta:+.4f}")

    return all_results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-2019', default='data/trec-dl-2019')
    parser.add_argument('--data-2020', default='data/trec-dl-2020')
    args = parser.parse_args()

    runs_2019 = {}
    for p in sorted((Path(args.data_2019) / 'runs').glob('*.txt')):
        runs_2019[p.name] = parse_run_file(str(p))
    qrels_2019 = parse_qrels(str(Path(args.data_2019) / '2019qrels-pass.txt'))

    runs_2020 = {}
    for p in sorted((Path(args.data_2020) / 'runs').glob('*.txt')):
        runs_2020[p.name] = parse_run_file(str(p))
    qrels_2020 = parse_qrels(str(Path(args.data_2020) / '2020qrels-pass.txt'))

    print("=" * 72)
    print("PROBE 2: BASIN-ESCAPE SCORE-AWARE FUSION")
    print("=" * 72)
    print(f"Loaded {len(runs_2019)} runs / {len(qrels_2019)} queries (TREC DL 2019)")
    print(f"Loaded {len(runs_2020)} runs / {len(qrels_2020)} queries (TREC DL 2020)")

    run_sweep(runs_2019, qrels_2019, runs_2020, qrels_2020)


if __name__ == '__main__':
    main()
