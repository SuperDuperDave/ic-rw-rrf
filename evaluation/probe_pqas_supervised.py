#!/usr/bin/env python3
"""
PROBE 8: PQAS supervised — minimal logistic regression with leave-one-collection-out CV.

After the label-free combinator failed to win on both collections,
test whether a tiny supervised classifier can extract the per-query
oracle gap (+0.0305 on 2019, +0.0325 on 2020).

No external dependencies. Hand-coded LR with gradient descent + L2.
"""
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import parse_run_file, parse_qrels
from probe_per_query_diagnosis import diagnose_collection


FEATURE_KEYS = [
    'rho',
    'h_cov',
    'frac_specialist_top30',
    'frac_consensus_top30',
    'mean_score_gap',
    'max_score_gap',
    'top1_spread',
    'score_var_mean',
    'mean_rank_dist',
]


def standardize(features_per_query, means=None, stds=None):
    """Z-score each feature column. Return standardized matrix + stats."""
    if means is None:
        means = [statistics.mean([f[k] for f in features_per_query]) for k in FEATURE_KEYS]
        stds = []
        for i, k in enumerate(FEATURE_KEYS):
            vals = [f[k] for f in features_per_query]
            sd = statistics.pstdev(vals)
            stds.append(max(sd, 1e-6))
    X = []
    for f in features_per_query:
        row = []
        for i, k in enumerate(FEATURE_KEYS):
            row.append((f[k] - means[i]) / stds[i])
        X.append(row)
    return X, means, stds


def make_labels(features_per_query):
    """Label = 1 if v5 wins (or ties), 0 if Vanilla wins."""
    return [1 if f['v5_ndcg'] >= f['van_ndcg'] else 0 for f in features_per_query]


def sigmoid(z):
    if z > 30:
        return 1.0
    if z < -30:
        return 0.0
    return 1.0 / (1.0 + math.exp(-z))


def train_lr(X, y, lr=0.05, l2=0.10, epochs=2000, seed=42):
    """Tiny logistic regression via batch gradient descent + L2."""
    random.seed(seed)
    n, d = len(X), len(X[0])
    w = [random.uniform(-0.01, 0.01) for _ in range(d)]
    b = 0.0
    for _ in range(epochs):
        # Gradients
        gw = [0.0] * d
        gb = 0.0
        for i in range(n):
            z = b + sum(w[j] * X[i][j] for j in range(d))
            p = sigmoid(z)
            err = p - y[i]
            for j in range(d):
                gw[j] += err * X[i][j]
            gb += err
        # Update with L2
        for j in range(d):
            w[j] -= lr * (gw[j] / n + l2 * w[j])
        b -= lr * gb / n
    return w, b


def predict(X, w, b):
    return [sigmoid(b + sum(w[j] * x[j] for j in range(len(x)))) for x in X]


def evaluate_classifier_routing(per_query, probs, threshold=0.5):
    """For each query, pick v5 if prob > threshold else Vanilla. Return mean NDCG@10."""
    chosen = []
    for q, p in zip(per_query, probs):
        chosen.append(q['v5_ndcg'] if p > threshold else q['van_ndcg'])
    return statistics.mean(chosen)


def evaluate_classifier_routing_with_stats(per_query, probs, threshold=0.5):
    chosen = []
    n_v5 = 0
    for q, p in zip(per_query, probs):
        if p > threshold:
            chosen.append(q['v5_ndcg'])
            n_v5 += 1
        else:
            chosen.append(q['van_ndcg'])
    return statistics.mean(chosen), n_v5, len(per_query) - n_v5


def loocv_experiment(pq_a, pq_b, label_a, label_b):
    """Train on pq_a, test on pq_b. Report both directions."""
    print(f"\n  Train on {label_a} ({len(pq_a)} q), test on {label_b} ({len(pq_b)} q):")

    X_train, means, stds = standardize(pq_a)
    y_train = make_labels(pq_a)
    X_test, _, _ = standardize(pq_b, means, stds)

    # Sweep L2 strength to find well-regularized solution
    best = None
    for l2 in [0.001, 0.01, 0.05, 0.10, 0.30, 1.0]:
        w, b = train_lr(X_train, y_train, lr=0.05, l2=l2, epochs=2000)
        probs_test = predict(X_test, w, b)
        # Test multiple thresholds for routing
        thresh_results = []
        for t in [0.30, 0.40, 0.50, 0.60, 0.70]:
            ndcg, n_v5, n_van = evaluate_classifier_routing_with_stats(pq_b, probs_test, t)
            thresh_results.append((t, ndcg, n_v5, n_van))

        # Best threshold
        best_t, best_ndcg, best_v5, best_van = max(thresh_results, key=lambda x: x[1])

        # In-sample sanity check
        probs_train = predict(X_train, w, b)
        train_ndcg, _, _ = evaluate_classifier_routing_with_stats(pq_a, probs_train, best_t)

        if best is None or best_ndcg > best[1][1]:
            best = (l2, (best_t, best_ndcg, best_v5, best_van), train_ndcg, w[:])

        print(f"    l2={l2:>6.3f}  test_NDCG@10={best_ndcg:.4f} "
              f"(threshold={best_t}, picks v5/van={best_v5}/{best_van})  "
              f"train_NDCG={train_ndcg:.4f}")

    # Print learned weights for best l2
    l2_best, (t_best, ndcg_best, _, _), train_best, w_best = best
    print(f"\n    BEST l2={l2_best}: test NDCG@10={ndcg_best:.4f}, train NDCG@10={train_best:.4f}")
    print(f"    Weights (after z-score normalization):")
    for k, wj in zip(FEATURE_KEYS, w_best):
        print(f"      {k:<28} {wj:+.3f}")
    return ndcg_best


def main():
    qrels_2019 = parse_qrels('data/trec-dl-2019/2019qrels-pass.txt')
    runs_2019 = {}
    for rf in sorted(Path('data/trec-dl-2019/runs').glob('*.txt')):
        runs_2019[rf.stem] = parse_run_file(str(rf))
    qrels_2020 = parse_qrels('data/trec-dl-2020/2020qrels-pass.txt')
    runs_2020 = {}
    for rf in sorted(Path('data/trec-dl-2020/runs').glob('*.txt')):
        runs_2020[rf.stem] = parse_run_file(str(rf))

    subset = ['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet']
    pq_2019, _ = diagnose_collection(qrels_2019, runs_2019, subset, '2019')
    pq_2020, _ = diagnose_collection(qrels_2020, runs_2020, subset, '2020')

    # Reference points
    print("\n\n" + "="*80)
    print("  REFERENCE POINTS (per-query mean NDCG@10)")
    print("="*80)
    for label, pq in [('2019 n=4', pq_2019), ('2020 n=4', pq_2020)]:
        van = statistics.mean([q['van_ndcg'] for q in pq])
        v5 = statistics.mean([q['v5_ndcg'] for q in pq])
        ora = statistics.mean([max(q['v5_ndcg'], q['van_ndcg']) for q in pq])
        print(f"  {label}: Vanilla={van:.4f}  v5={v5:.4f}  ORACLE={ora:.4f}  "
              f"headroom={ora-max(van,v5):+.4f}")

    print("\n\n" + "="*80)
    print("  LEAVE-ONE-COLLECTION-OUT CROSS-VALIDATION")
    print("="*80)
    ndcg_19_to_20 = loocv_experiment(pq_2019, pq_2020, "2019", "2020")
    ndcg_20_to_19 = loocv_experiment(pq_2020, pq_2019, "2020", "2019")

    # Final summary
    print("\n\n" + "="*80)
    print("  SUMMARY")
    print("="*80)
    print(f"  Train on 2019, test on 2020: {ndcg_19_to_20:.4f}  (vs Vanilla 0.4483, v5 0.4373, oracle 0.4808)")
    print(f"  Train on 2020, test on 2019: {ndcg_20_to_19:.4f}  (vs Vanilla 0.3645, v5 0.3800, oracle 0.4106)")

    # Compare to v6.0 REF
    print(f"\n  v6.0 REF on 2019 n=4: 0.3832")
    print(f"  v6.0 REF on 2020 n=4: 0.4393")
    print(f"  PQAS-supervised on 2019 (test from 2020-trained model): {ndcg_20_to_19:.4f}")
    print(f"  PQAS-supervised on 2020 (test from 2019-trained model): {ndcg_19_to_20:.4f}")


if __name__ == '__main__':
    main()
