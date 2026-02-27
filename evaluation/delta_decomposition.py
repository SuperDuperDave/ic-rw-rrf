#!/usr/bin/env python3
"""
Per-document delta decomposition for the 3 failing queries.
Shows exactly which documents moved, which ranker's mass changed,
and how much delta came from Type D vs Type S.

Also includes the Top-1 Protection Check.
"""

import math
import os
import sys
import statistics
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from trec_eval_harness import (
    parse_run_file, parse_qrels, runs_to_ranked_lists,
    fuse_v4x, evaluate_ranking, _rrf_scores, _rank_from_scores,
    _jaccard, _zscore, _clip, _sigmoid
)


def compute_per_doc_masses(lists, confidences, scores_per_ranker, k=60, **variant_cfg):
    """
    Run fusion and return per-document per-ranker contribution masses.
    Returns: {docid: {ranker_idx: {'mass': float, 'mod': float, 'w': float,
                                    'rank': int, 'contrib': float,
                                    'pC': float, 'pD': float, 'pS': float,
                                    'mD': float, 'mS': float, 'zConf': float}}}
    """
    R = len(lists)
    N = 30
    w = [1.0 / R] * R
    c = confidences
    top_sets = [set(L[:N]) for L in lists]

    indep = []
    for r in range(R):
        mean_jac = sum(_jaccard(top_sets[r], top_sets[s])
                       for s in range(R) if s != r) / (R - 1 + 1e-12)
        indep.append(1.0 - mean_jac)

    for _ in range(4):
        fused = _rrf_scores(lists, weights=w, k=k)
        fused_top = set(_rank_from_scores(fused)[:N])
        a = [_jaccard(set(L[:N]), fused_top) for L in lists]
        a_bar, c_bar, i_bar = sum(a)/R, sum(c)/R, sum(indep)/R
        w_new = [w[r] * math.exp(1.2*(a[r]-a_bar) + 0.6*(c[r]-c_bar) + 0.5*(indep[r]-i_bar))
                 for r in range(R)]
        w_new = [_clip(x, 0.05, 0.65) for x in w_new]
        s = sum(w_new) + 1e-12
        w = [x/s for x in w_new]

    Tq = 0.0
    cnt = 0
    for i in range(R):
        for j in range(i+1, R):
            Tq += 1.0 - _jaccard(top_sets[i], top_sets[j])
            cnt += 1
    Tq /= (cnt + 1e-12)

    alpha_eff = 0.5 * (Tq ** 1.5)
    beta_eff = 0.5 * (Tq ** 1.5)

    z_c = _zscore(c)
    z_ind = _zscore(indep)

    use_contrib_space = variant_cfg.get('use_contrib_space', False)
    use_reliability_gate = variant_cfg.get('use_reliability_gate', False)
    use_per_doc_confidence = variant_cfg.get('use_per_doc_confidence', False)
    one_sided_confidence = variant_cfg.get('one_sided_confidence', False)
    one_sided_independence = variant_cfg.get('one_sided_independence', False)
    conf_gated_independence = variant_cfg.get('conf_gated_independence', False)
    conf_gate_type = variant_cfg.get('conf_gate_type', 'sigmoid')

    z_ind_eff = [max(0, z) for z in z_ind] if one_sided_independence else z_ind

    mean_w = 1.0 / R
    reliability = [min(1.0, w[r] / mean_w) for r in range(R)]

    per_doc_conf = {}
    if use_per_doc_confidence and scores_per_ranker:
        for r, score_map in enumerate(scores_per_ranker):
            if not score_map:
                continue
            scores = list(score_map.values())
            if len(scores) < 2:
                continue
            mu = sum(scores) / len(scores)
            var = sum((sv - mu) ** 2 for sv in scores) / len(scores)
            std = max(math.sqrt(var), 1e-3)
            per_doc_conf[r] = {d: (sv - mu) / std for d, sv in score_map.items()}

    m_D_global = [1.0 + alpha_eff * z_c[r] for r in range(R)]
    if use_reliability_gate:
        m_S_global = [1.0 + beta_eff * z_ind_eff[r] * reliability[r] for r in range(R)]
    else:
        m_S_global = [1.0 + beta_eff * z_ind_eff[r] for r in range(R)]

    doc_ranks = defaultdict(dict)
    for r, L in enumerate(lists):
        for idx, d in enumerate(L):
            doc_ranks[d][r] = idx

    result = {}
    doc_scores = defaultdict(float)

    for d, ranks in doc_ranks.items():
        cov = len(ranks) / R
        rank_vals = list(ranks.values())
        if len(rank_vals) >= 2:
            if use_contrib_space:
                contribs_v = [1.0 / (k + rv + 1) for rv in rank_vals]
                mu_c = sum(contribs_v) / len(contribs_v)
                var_c = sum((cv - mu_c) ** 2 for cv in contribs_v) / len(contribs_v)
                disp = math.sqrt(var_c) / (mu_c + 1e-12)
            else:
                mu_r = sum(rank_vals) / len(rank_vals)
                var_r = sum((rv - mu_r) ** 2 for rv in rank_vals) / len(rank_vals)
                disp = math.sqrt(var_r) / (mu_r + k)
        else:
            disp = 0.0

        p_C = cov * (1 - disp)
        p_D = cov * disp
        p_S = 1 - cov
        total = p_C + p_D + p_S + 1e-12

        result[d] = {}
        for r, rank_val in ranks.items():
            z_conf = 0.0
            if per_doc_conf and r in per_doc_conf:
                z_conf = per_doc_conf[r].get(d, 0.0)
                if one_sided_confidence:
                    m_D_r = 1.0 + alpha_eff * max(0, z_conf)
                else:
                    m_D_r = 1.0 + alpha_eff * z_conf
            else:
                m_D_r = m_D_global[r]

            if conf_gated_independence and per_doc_conf:
                if r in per_doc_conf:
                    raw_conf = per_doc_conf[r].get(d, 0.0)
                    if conf_gate_type == 'sigmoid':
                        gate = _sigmoid(raw_conf)
                    elif conf_gate_type == 'relu':
                        gate = max(0, raw_conf)
                    elif conf_gate_type == 'bounded_relu':
                        gate = min(1.0, max(0, raw_conf))
                    else:
                        gate = _sigmoid(raw_conf)
                else:
                    gate = 1.0
                m_S_r = 1.0 + beta_eff * z_ind_eff[r] * gate
            else:
                m_S_r = m_S_global[r]

            mod = (p_C/total) * 1.0 + (p_D/total) * m_D_r + (p_S/total) * m_S_r
            mod = max(0.1, mod)
            contrib = 1.0 / (k + rank_val + 1)
            mass = w[r] * mod * contrib

            result[d][r] = {
                'mass': mass, 'mod': mod, 'w': w[r], 'rank': rank_val,
                'contrib': contrib, 'pC': p_C/total, 'pD': p_D/total,
                'pS': p_S/total, 'mD': m_D_r, 'mS': m_S_r,
                'zConf': z_conf, 'gate': gate if conf_gated_independence else None,
            }
            doc_scores[d] += mass

    return result, doc_scores, {'w': w, 'Tq': Tq, 'indep': indep,
                                 'z_ind': z_ind, 'reliability': reliability,
                                 'alpha_eff': alpha_eff, 'beta_eff': beta_eff}


def decompose_query(qid, lists, confidences, scores_per_ranker, qrel, ranker_names):
    """Full decomposition for a single query across variants."""
    R = len(lists)

    variants = {
        'v4.0+Ref3': {'use_per_doc_confidence': True},
        'v4.1': {'use_contrib_space': True, 'use_reliability_gate': True, 'use_per_doc_confidence': True},
        'v4.2-sig': {'use_contrib_space': True, 'use_per_doc_confidence': True,
                     'one_sided_confidence': True, 'one_sided_independence': True,
                     'conf_gated_independence': True, 'conf_gate_type': 'sigmoid'},
    }

    print(f"\n{'='*120}")
    print(f"  QUERY {qid}: Per-Document Delta Decomposition")
    print(f"{'='*120}")

    all_masses = {}
    all_scores = {}
    all_meta = {}
    all_rankings = {}
    all_metrics = {}

    for vname, cfg in variants.items():
        masses, scores, meta = compute_per_doc_masses(
            lists, confidences, scores_per_ranker, **cfg)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        rank_list = [d for d, _ in ranked]
        metrics = evaluate_ranking(rank_list, qrel)
        all_masses[vname] = masses
        all_scores[vname] = scores
        all_meta[vname] = meta
        all_rankings[vname] = rank_list
        all_metrics[vname] = metrics

    meta = all_meta['v4.0+Ref3']
    print(f"\n  Tq={meta['Tq']:.3f}  alpha_eff={meta['alpha_eff']:.4f}  beta_eff={meta['beta_eff']:.4f}")
    print(f"  Weights: {['R'+str(r)+'('+ranker_names[r]+')='+format(meta['w'][r],'.4f') for r in range(R)]}")
    print(f"  Indep:   {['R'+str(r)+'='+format(meta['indep'][r],'.3f') for r in range(R)]}")
    print(f"  z(ind):  {['R'+str(r)+'='+format(meta['z_ind'][r],'.3f') for r in range(R)]}")
    print(f"  Reliab:  {['R'+str(r)+'='+format(meta['reliability'][r],'.3f') for r in range(R)]}")

    print(f"\n  Metrics:")
    for vname in variants:
        m = all_metrics[vname]
        print(f"    {vname:<14} NDCG@10={m['NDCG@10']:.4f}  MRR={m['MRR']:.4f}")

    # Show top-10 documents for each variant with decomposition
    for vname in variants:
        print(f"\n  ── {vname} Top-10 ──")
        print(f"  {'Rank':>4} {'DocID':>10} {'Score':>10} {'Rel':>3} | "
              f"{'pC':>5} {'pD':>5} {'pS':>5} | Ranker masses")
        print(f"  {'-'*110}")

        rank_list = all_rankings[vname]
        for pos, d in enumerate(rank_list[:10]):
            rel = qrel.get(d, 0)
            score = all_scores[vname][d]
            masses = all_masses[vname].get(d, {})

            # Type membership (same across rankers for a doc)
            if masses:
                sample = list(masses.values())[0]
                pC, pD, pS = sample['pC'], sample['pD'], sample['pS']
            else:
                pC, pD, pS = 0, 0, 0

            ranker_str = ""
            for r in range(R):
                if r in masses:
                    m = masses[r]
                    ranker_str += f"  R{r}:m={m['mod']:.3f},z={m['zConf']:+.2f}"
                    if m.get('gate') is not None:
                        ranker_str += f",g={m['gate']:.2f}"

            rel_marker = " ***" if rel >= 2 else (" +" if rel > 0 else "")
            print(f"  {pos:>4} {d:>10} {score:>10.6f} {rel:>3}{rel_marker:3} | "
                  f"{pC:>5.3f} {pD:>5.3f} {pS:>5.3f} | {ranker_str}")

    # ── Top-1 Protection Check ──
    print(f"\n  ── Top-1 Protection Check ──")
    for vname in variants:
        rank_list = all_rankings[vname]
        top1_doc = rank_list[0] if rank_list else None
        if top1_doc and top1_doc in all_masses[vname]:
            masses = all_masses[vname][top1_doc]
            min_mod = min(m['mod'] for m in masses.values())
            max_mod = max(m['mod'] for m in masses.values())
            rel = qrel.get(top1_doc, 0)
            neg_mods = sum(1 for m in masses.values() if m['mod'] < 1.0)
            print(f"    {vname:<14} top1={top1_doc} rel={rel} "
                  f"mod_range=[{min_mod:.3f}, {max_mod:.3f}] "
                  f"rankers_with_mod<1: {neg_mods}/{len(masses)}")


def main():
    import argparse
    import glob as globmod

    parser = argparse.ArgumentParser(description="Per-document delta decomposition")
    parser.add_argument('--qrels', type=str, required=True)
    parser.add_argument('--run-dir', type=str, required=True)
    parser.add_argument('--queries', nargs='+', default=['146187', '1112341', '962179'],
                        help='Query IDs to decompose')
    args = parser.parse_args()

    runs = {}
    ranker_names = []
    for path in sorted(globmod.glob(os.path.join(args.run_dir, '*.txt'))):
        name = os.path.splitext(os.path.basename(path))[0]
        runs[name] = parse_run_file(path)
        ranker_names.append(name)

    qrels = parse_qrels(args.qrels)
    print(f"Loaded {len(runs)} runs, {len(qrels)} queries with judgments")
    print(f"Ranker order: {ranker_names}")
    print(f"Decomposing queries: {args.queries}")

    for qid in args.queries:
        lists, confidences, scores_per_ranker = runs_to_ranked_lists(runs, qid)
        if len(lists) < 2:
            print(f"  Skipping {qid}: insufficient rankers")
            continue
        qrel = qrels.get(qid, {})
        decompose_query(qid, lists, confidences, scores_per_ranker, qrel, ranker_names)


if __name__ == "__main__":
    main()
