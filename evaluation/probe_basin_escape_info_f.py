#!/usr/bin/env python3
"""
PROBE 3: Basin-Escape — Information-Theoretic f(r)  (Basin 2 in session 001's nomenclature)

Session 2026-05-13-002, Probe 3.

Probes 1 (MC4) and 2 (score-aware) both failed: they showed that across rank-only
AND score-aware label-free families, NOTHING beats Vanilla RRF on the cross-
ensemble mean. The realization forming: Vanilla RRF sits near a genuine peak in
the label-free aggregation family. Methods that try to do more by exploiting
agreement / scores / preferences gain on homogeneous regimes but lose more on
heterogeneous, netting to worse cross-ensemble performance.

This probe attacks RRF's central heuristic directly: the decay function f(r) =
1/(60+r). Instead of choosing this functional form, *derive* the empirically
optimal f_r(k) per ranker from data. The information-theoretic-optimal
contribution from a document at rank k in ranker r is the log-odds of
relevance:

    f_r(k) = log( P(rel | rank=k, ranker=r) / P(non-rel | rank=k, ranker=r) )

Compute this from labeled qrels via a held-out training set. Use the empirical
f_r(k) as the per-ranker decay function in linear fusion. Compare to Vanilla RRF.

Two outcomes both informative:
  - If empirical f-fusion BEATS Vanilla -> RRF's specific shape was suboptimal.
    Basin escaped via Basin 2.
  - If empirical f-fusion ties or loses to Vanilla -> RRF's heuristic is
    remarkably close to information-optimal. Close the question.

Cross-validation discipline:
  - 5-fold within-corpus CV (train f_r on 4 folds, test on 1; same corpus)
  - Cross-corpus transfer: train on 2019, test on 2020; and vice versa

If within-corpus works but cross-corpus fails, the optimal f_r is corpus-
specific (consistent with session 001's v7 PQAS finding).

Visualizes the empirical f_r(k) shape vs RRF's 1/(60+k) shape — the shape
comparison itself is publishable signal regardless of fusion performance.
"""
import argparse
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import (
    parse_run_file, parse_qrels, runs_to_ranked_lists,
    fuse_vanilla_rrf, evaluate_ranking, paired_t_test,
)


REL_THRESHOLD = 2   # TREC DL convention: grade >= 2 means relevant


def compute_empirical_log_odds(runs_one_ranker, qrels, train_qids, K=100,
                                smoothing=1.0, bin_size=1):
    """
    For one ranker, compute empirical P(rel | rank=k) over the training queries,
    then return log-odds smoothed with Laplace correction.

    runs_one_ranker: {qid: [(docid, rank, score), ...]}
    qrels:           {qid: {docid: grade}}
    train_qids:      iterable of qids to use for the estimate
    K:               number of rank positions to estimate (0..K-1)
    smoothing:       Laplace smoothing pseudo-count
    bin_size:        bin consecutive ranks together to reduce noise (1 = no binning)

    Returns: list of length K with f_r(k) = log_odds. For unobserved positions
    (no queries had a doc at rank k from this ranker), returns log-odds at
    the marginal prevalence.
    """
    # rel_count[k] = # times the document at rank k from this ranker was relevant
    # tot_count[k] = # times the ranker had a doc at rank k
    rel_count = [0] * K
    tot_count = [0] * K

    for qid in train_qids:
        if qid not in runs_one_ranker:
            continue
        if qid not in qrels:
            continue
        qrel = qrels[qid]
        for docid, rank, _score in runs_one_ranker[qid]:
            if rank >= K:
                continue
            tot_count[rank] += 1
            if qrel.get(docid, 0) >= REL_THRESHOLD:
                rel_count[rank] += 1

    # Bin
    if bin_size > 1:
        binned_rel = [0] * K
        binned_tot = [0] * K
        for k in range(K):
            bin_start = (k // bin_size) * bin_size
            bin_end = min(bin_start + bin_size, K)
            br = sum(rel_count[bin_start:bin_end])
            bt = sum(tot_count[bin_start:bin_end])
            for kk in range(bin_start, bin_end):
                binned_rel[kk] = br
                binned_tot[kk] = bt
        rel_count = binned_rel
        tot_count = binned_tot

    # Compute marginal relevance rate over the training set
    total_rel = sum(rel_count)
    total_tot = sum(tot_count)
    marginal_p = (total_rel + smoothing) / (total_tot + 2 * smoothing) if total_tot > 0 else 0.05
    marginal_log_odds = math.log(marginal_p / (1.0 - marginal_p))

    f_r = []
    for k in range(K):
        # Laplace-smoothed estimate
        p = (rel_count[k] + smoothing) / (tot_count[k] + 2 * smoothing)
        if tot_count[k] == 0:
            f_r.append(marginal_log_odds)
        else:
            f_r.append(math.log(p / (1.0 - p)))

    return f_r, marginal_log_odds


def fuse_empirical_f(lists, f_per_ranker, marginal_log_odds_per_ranker, K=100,
                      missing_strategy='marginal'):
    """
    Linear fusion with per-ranker empirical decay functions.

    score(d) = sum_r f_r(rank_r(d))    for r where d is in r's top-K
              + (missing contribution per missing ranker)

    missing_strategy:
      'marginal' -> use the ranker's marginal log-odds as the contribution from absences
      'zero'     -> absences contribute 0
      'tail'     -> use f_r(K-1) (the deepest learned position) for absences
    """
    R = len(lists)
    all_docs = set()
    for L in lists:
        all_docs.update(L[:K])

    rank_of = []
    for L in lists:
        rank_of.append({d: i for i, d in enumerate(L[:K])})

    final = {}
    for d in all_docs:
        s = 0.0
        for r in range(R):
            rk = rank_of[r].get(d)
            if rk is not None:
                s += f_per_ranker[r][rk]
            else:
                if missing_strategy == 'marginal':
                    s += marginal_log_odds_per_ranker[r]
                elif missing_strategy == 'tail':
                    s += f_per_ranker[r][K - 1]
                # 'zero' contributes nothing
        final[d] = s
    return sorted(final, key=lambda d: (-final[d], d))


def fuse_van_call(lists):
    return fuse_vanilla_rrf(lists, k=60)


def eval_per_query(qids, runs, qrels, fusion_fn, fusion_kind='lists', **kwargs):
    out = {'NDCG@10': [], 'MRR': []}
    for qid in qids:
        if qid not in qrels:
            continue
        lists, confs, sprs = runs_to_ranked_lists(runs, qid)
        if len(lists) < 2:
            continue
        if fusion_kind == 'lists':
            ranked = fusion_fn(lists, **kwargs)
        elif fusion_kind == 'rich':
            ranked = fusion_fn(lists, confs, sprs, **kwargs)
        m = evaluate_ranking(ranked, qrels[qid])
        out['NDCG@10'].append(m['NDCG@10'])
        out['MRR'].append(m['MRR'])
    return out


def kfold_split(qids, k=5, seed=42):
    """Deterministic k-fold split by query id."""
    import random
    rng = random.Random(seed)
    shuffled = list(qids)
    rng.shuffle(shuffled)
    folds = [[] for _ in range(k)]
    for i, q in enumerate(shuffled):
        folds[i % k].append(q)
    return folds


def run_within_corpus(label, runs, qrels, ens_files, K=100, n_folds=5, smoothing=1.0, bin_size=5):
    """Within-corpus k-fold CV: train empirical f on (k-1) folds, eval on the 1 held-out fold."""
    ens_runs = {f: runs[f] for f in ens_files if f in runs}
    ranker_names = list(ens_runs.keys())
    qids_all = sorted(qrels.keys())
    folds = kfold_split(qids_all, k=n_folds)

    all_emp = []
    all_van = []
    for fi in range(n_folds):
        test_qids = set(folds[fi])
        train_qids = [q for q in qids_all if q not in test_qids]

        f_per_ranker = []
        marg_per_ranker = []
        for rn in ranker_names:
            f_r, marg = compute_empirical_log_odds(
                ens_runs[rn], qrels, train_qids, K=K,
                smoothing=smoothing, bin_size=bin_size,
            )
            f_per_ranker.append(f_r)
            marg_per_ranker.append(marg)

        emp_metrics = eval_per_query(
            sorted(test_qids), ens_runs, qrels,
            lambda L: fuse_empirical_f(L, f_per_ranker, marg_per_ranker, K=K,
                                        missing_strategy='marginal'),
            'lists',
        )
        van_metrics = eval_per_query(sorted(test_qids), ens_runs, qrels, fuse_van_call, 'lists')

        all_emp.extend(emp_metrics['NDCG@10'])
        all_van.extend(van_metrics['NDCG@10'])

    emp_mean = statistics.mean(all_emp)
    van_mean = statistics.mean(all_van)
    _t, p = paired_t_test(all_emp, all_van)
    print(f"  {label:<40}  Emp-f: {emp_mean:.4f}  Vanilla: {van_mean:.4f}  delta: {emp_mean-van_mean:+.4f}  p={p:.3f}")
    return emp_mean, van_mean, p


def run_cross_corpus(label, runs_train, qrels_train, runs_test, qrels_test, ens_files,
                      K=100, smoothing=1.0, bin_size=5):
    """Train empirical f on full train corpus, test on full test corpus."""
    ens_runs_train = {f: runs_train[f] for f in ens_files if f in runs_train}
    ens_runs_test  = {f: runs_test[f]  for f in ens_files if f in runs_test}
    ranker_names = list(ens_runs_train.keys())

    train_qids = sorted(qrels_train.keys())
    test_qids = sorted(qrels_test.keys())

    f_per_ranker = []
    marg_per_ranker = []
    for rn in ranker_names:
        f_r, marg = compute_empirical_log_odds(
            ens_runs_train[rn], qrels_train, train_qids, K=K,
            smoothing=smoothing, bin_size=bin_size,
        )
        f_per_ranker.append(f_r)
        marg_per_ranker.append(marg)

    emp_metrics = eval_per_query(
        test_qids, ens_runs_test, qrels_test,
        lambda L: fuse_empirical_f(L, f_per_ranker, marg_per_ranker, K=K,
                                    missing_strategy='marginal'),
        'lists',
    )
    van_metrics = eval_per_query(test_qids, ens_runs_test, qrels_test, fuse_van_call, 'lists')

    emp_mean = statistics.mean(emp_metrics['NDCG@10'])
    van_mean = statistics.mean(van_metrics['NDCG@10'])
    _t, p = paired_t_test(emp_metrics['NDCG@10'], van_metrics['NDCG@10'])
    print(f"  {label:<40}  Emp-f: {emp_mean:.4f}  Vanilla: {van_mean:.4f}  delta: {emp_mean-van_mean:+.4f}  p={p:.3f}")
    return emp_mean, van_mean, p, f_per_ranker, ranker_names


def visualize_f_shapes(f_per_ranker, ranker_names, K=100, sample_positions=(0, 1, 2, 5, 10, 20, 50, 99)):
    """Print the empirical f_r(k) at sample positions vs RRF's 1/(60+k) for shape comparison."""
    print("\n  Shape comparison — empirical f_r(k) vs RRF 1/(60+k)")
    print("  " + "-" * 80)
    header = "  rank k    RRF 1/(60+k)  " + "  ".join(f"{rn[:14]:>14}" for rn in ranker_names)
    print(header)
    # Normalize each f_r to have same range as RRF for shape comparison
    rrf_at = [1.0 / (60 + k) for k in sample_positions]
    for i, k in enumerate(sample_positions):
        row = f"  {k:>5}        {rrf_at[i]:>10.4f}    "
        for fr in f_per_ranker:
            row += f"  {fr[k]:>14.3f}"
        print(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-2019', default='data/trec-dl-2019')
    parser.add_argument('--data-2020', default='data/trec-dl-2020')
    parser.add_argument('--K', type=int, default=100)
    parser.add_argument('--smoothing', type=float, default=1.0)
    parser.add_argument('--bin-size', type=int, default=5)
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
    print("PROBE 3: BASIN-ESCAPE — INFORMATION-THEORETIC f(r)")
    print("=" * 72)
    print(f"K={args.K}  smoothing={args.smoothing}  bin_size={args.bin_size}  rel_threshold={REL_THRESHOLD}")
    print(f"Loaded {len(runs_2019)} runs / {len(qrels_2019)} queries (TREC DL 2019)")
    print(f"Loaded {len(runs_2020)} runs / {len(qrels_2020)} queries (TREC DL 2020)")

    base4 = ['bm25.txt', 'bm25_tuned.txt', 'ql_dirichlet.txt', 'tfidf.txt']
    ens_19 = [
        ('n=4 (lexical core)', base4),
        ('n=5 (+proximity)', base4 + ['proximity.txt']),
        ('n=6 (+tfidf_bigram)', base4 + ['proximity.txt', 'tfidf_bigram.txt']),
        ('n=7 (+semantic_hash)', base4 + ['proximity.txt', 'tfidf_bigram.txt', 'semantic_hash.txt']),
    ]
    ens_20 = [('n=4 (lexical core)', base4)]

    print("\n" + "=" * 72)
    print("WITHIN-CORPUS 5-FOLD CV — TREC DL 2019")
    print("=" * 72)
    rows_19 = []
    for name, files in ens_19:
        e, v, p = run_within_corpus(f"2019 {name}", runs_2019, qrels_2019, files,
                                     K=args.K, n_folds=5, smoothing=args.smoothing, bin_size=args.bin_size)
        rows_19.append((name, e, v, p))

    print("\n" + "=" * 72)
    print("WITHIN-CORPUS 5-FOLD CV — TREC DL 2020")
    print("=" * 72)
    rows_20 = []
    for name, files in ens_20:
        e, v, p = run_within_corpus(f"2020 {name}", runs_2020, qrels_2020, files,
                                     K=args.K, n_folds=5, smoothing=args.smoothing, bin_size=args.bin_size)
        rows_20.append((name, e, v, p))

    print("\n" + "=" * 72)
    print("CROSS-CORPUS TRANSFER (only ensembles available in both corpora)")
    print("=" * 72)
    # Only n=4 is available in both
    for tname, files in [('n=4 (lexical core)', base4)]:
        e, v, p, f_per, names = run_cross_corpus(
            f"train 2020 -> test 2019 {tname}",
            runs_2020, qrels_2020, runs_2019, qrels_2019, files,
            K=args.K, smoothing=args.smoothing, bin_size=args.bin_size,
        )
        e, v, p, f_per, names = run_cross_corpus(
            f"train 2019 -> test 2020 {tname}",
            runs_2019, qrels_2019, runs_2020, qrels_2020, files,
            K=args.K, smoothing=args.smoothing, bin_size=args.bin_size,
        )
        # For the n=4 case, show shape comparison
        visualize_f_shapes(f_per, names, K=args.K)

    # Cross-ensemble mean (within-corpus 5-fold)
    print("\n" + "=" * 72)
    print("CROSS-ENSEMBLE MEAN — TREC DL 2019 (within-corpus 5-fold)")
    print("=" * 72)
    e_mean = statistics.mean([r[1] for r in rows_19])
    v_mean = statistics.mean([r[2] for r in rows_19])
    print(f"  Vanilla RRF: {v_mean:.4f}")
    print(f"  Emp-f:       {e_mean:.4f}   vs Vanilla = {e_mean - v_mean:+.4f}")


if __name__ == '__main__':
    main()
