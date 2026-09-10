#!/usr/bin/env python3
"""Cycle 01: comparable k selection and repeated-evidence interventions.

Development evidence only. This runner preserves historical implementations.
All means and resampling retain query identity; repeated folds/ensembles are
not additional independent queries. Bootstrap intervals condition on the saved
out-of-fold predictions; they do not measure the full uncertainty of selection.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys

from fusion_contract import canonical_rrf, coverage_limit, asymptotic_rrf, duplicate_quotient
from trec_eval_harness import parse_run_file, parse_qrels, runs_to_ranked_lists, ndcg_at_k, fuse_vanilla_rrf, fuse_v21

ROOT = Path(__file__).resolve().parents[1]
GRID = [1, 5, 10, 30, 60, 100, 200, 500]
SEEDS = [42, 123, 7, 99, 2026]
BASE = ['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet']
CONFIGS = [(2019, BASE), (2019, BASE + ['proximity']),
           (2019, BASE + ['proximity', 'tfidf_bigram']),
           (2019, BASE + ['proximity', 'tfidf_bigram', 'semantic_hash']), (2020, BASE)]


def mean(values):
    return statistics.mean(values)


def paired_summary(deltas, n_boot=4000, seed=1847):
    """Descriptive paired query bootstrap of fixed observed/predicted scores."""
    values = list(deltas)
    if not values:
        raise ValueError('no paired queries')
    rng = random.Random(seed)
    samples = sorted(mean(rng.choices(values, k=len(values))) for _ in range(n_boot))
    return {'n_queries': len(values), 'mean_delta': mean(values),
            'conditional_query_bootstrap_95': [samples[int(.025*n_boot)], samples[int(.975*n_boot)]],
            'wins': sum(d > 1e-12 for d in values), 'losses': sum(d < -1e-12 for d in values),
            'ties': sum(abs(d) <= 1e-12 for d in values)}


def cv_predictions(score_by_qid, seed, grid=GRID):
    """Train selection only; all test labels are accessed after selecting k."""
    qids = sorted(score_by_qid)
    shuffled = list(qids)
    random.Random(seed).shuffle(shuffled)
    folds = [shuffled[i::5] for i in range(5)]
    predictions = {}
    details = []
    for fold, held_out in enumerate(folds):
        held = set(held_out)
        train = [q for q in qids if q not in held]
        best = max(grid, key=lambda k: mean(score_by_qid[q][k] for q in train))
        details.append({'seed': seed, 'fold': fold, 'selected_k': best,
                        'train_qids': train, 'test_qids': held_out})
        for q in held_out:
            predictions[q] = {'k': best, 'ndcg10': score_by_qid[q][best]}
    return predictions, details


def load_inputs():
    inputs, hashes = {}, {}
    for year in (2019, 2020):
        directory = ROOT / 'data' / ('trec-dl-' + str(year))
        qrel_path = directory / ('{}qrels-pass.txt'.format(year))
        qrels = parse_qrels(str(qrel_path))
        runs = {}
        for path in sorted((directory / 'runs').glob('*.txt')):
            runs[path.stem] = parse_run_file(str(path))
            hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[str(qrel_path.relative_to(ROOT))] = hashlib.sha256(qrel_path.read_bytes()).hexdigest()
        inputs[year] = (runs, qrels)
    return inputs, hashes


def evaluate_configuration(year, names, runs, qrels):
    selected = {n: runs[n] for n in names}
    qids = sorted(q for q in qrels if any(v > 0 for v in qrels[q].values())
                  and all(q in selected[n] for n in names))
    rows, cache = {}, {}
    for q in qids:
        lists, _, _ = runs_to_ranked_lists(selected, q)
        rankings = {'k{}'.format(k): canonical_rrf(lists, k=k) for k in GRID}
        rankings.update(legacy_k60=fuse_vanilla_rrf(lists),
                        coverage_proxy=coverage_limit(lists), asymptotic=asymptotic_rrf(lists),
                        quotient_k60=canonical_rrf(duplicate_quotient(lists), k=60))
        scores = {method: ndcg_at_k(rank, qrels[q], 10) for method, rank in rankings.items()}
        cache[q] = {k: scores['k{}'.format(k)] for k in GRID}
        rows[q] = {'scores': scores,
                   'unique_sources': len(duplicate_quotient(lists)),
                   'n_sources': len(lists),
                   'top10_equal_asymptotic': {str(k): rankings['k{}'.format(k)][:10] == rankings['asymptotic'][:10] for k in GRID}}
    folds = []
    for seed in SEEDS:
        predictions, detail = cv_predictions(cache, seed)
        folds.extend(detail)
        for q in qids:
            rows[q].setdefault('cv', {})[str(seed)] = predictions[q]
    for q in qids:
        rows[q]['scores']['selected_k'] = mean(rows[q]['cv'][str(seed)]['ndcg10'] for seed in SEEDS)
    methods = list(rows[qids[0]]['scores'])
    summary = {'year': year, 'rankers': names, 'n_queries': len(qids),
               'means': {m: mean(rows[q]['scores'][m] for q in qids) for m in methods},
               'comparisons_to_k60': {m: paired_summary(rows[q]['scores'][m] - rows[q]['scores']['k60'] for q in qids)
                                      for m in ['selected_k', 'k200', 'coverage_proxy', 'asymptotic', 'quotient_k60']},
               'selected_k_counts': dict(sorted(Counter(f['selected_k'] for f in folds).items())),
               'cv_seed_means': {str(seed): mean(rows[q]['cv'][str(seed)]['ndcg10'] for q in qids) for seed in SEEDS},
               'top10_equal_asymptotic_fraction': {str(k): mean(int(rows[q]['top10_equal_asymptotic'][str(k)]) for q in qids) for k in GRID}}
    return summary, rows, folds, cache


def duplicate_interventions(year, names, runs, qrels):
    selected = {n:runs[n] for n in names}
    output = []
    for q in sorted(qrels):
        if not all(q in selected[n] for n in names):
            continue
        lists, _, _ = runs_to_ranked_lists(selected, q)
        for k in [60, 200]:
            original = canonical_rrf(lists,k=k)
            quotient = canonical_rrf(duplicate_quotient(lists),k=k)
            for index, source in enumerate(names):
                for copies in [1, 3]:
                    altered = lists + [list(lists[index]) for _ in range(copies)]
                    ranked = canonical_rrf(altered,k=k)
                    corrected = canonical_rrf(duplicate_quotient(altered),k=k)
                    output.append({'year':year,'qid':q,'source':source,'k':k,'added_copies':copies,
                                   'top10_changed':ranked[:10] != original[:10],
                                   'ndcg_delta':ndcg_at_k(ranked,qrels[q],10)-ndcg_at_k(original,qrels[q],10),
                                   'quotient_ranking_unchanged':corrected == quotient})
    summaries=[]
    for k in [60,200]:
        for copies in [1,3]:
            group=[r for r in output if r['k']==k and r['added_copies']==copies]
            per_q=defaultdict(list)
            for row in group:per_q[row['qid']].append(row['ndcg_delta'])
            summaries.append({'year':year,'k':k,'added_copies':copies,'source_interventions':len(group),
                              'top10_changed_fraction':mean(int(r['top10_changed']) for r in group),
                              'mean_absolute_ndcg_change':mean(abs(r['ndcg_delta']) for r in group),
                              'paired_by_query_averaged_sources':paired_summary(mean(v) for v in per_q.values()),
                              'quotient_invariant_all':all(r['quotient_ranking_unchanged'] for r in group)})
    return summaries,output


def identifiability_fixture():
    """Same rank/confidence observations, incompatible relevance worlds."""
    docs=['d{:02d}'.format(i) for i in range(60)]
    majority=docs[:]
    specialist=docs[30:]+docs[:30]
    lists=[majority,majority[:],specialist]
    worlds={'majority_correct':{d:3 for d in majority[:10]},
            'specialist_correct':{d:3 for d in specialist[:10]}}
    rankers={'rrf60':canonical_rrf(lists),'quotient60':canonical_rrf(duplicate_quotient(lists)),
             'v21_equal_confidence':fuse_v21(lists,[.5,.5,.5])[0]}
    return {'observations':{'lists':lists,'confidences':[.5,.5,.5]},'world_qrels':worlds,
            'rankings_top10':{m:r[:10] for m,r in rankers.items()},
            'ndcg10':{world:{m:ndcg_at_k(r,qrels,10) for m,r in rankers.items()} for world,qrels in worlds.items()},
            'interpretation':'Identical rank-only inputs cannot reveal which relevance world holds. An additional signal must carry information about correctness, not merely repeat disagreement.'}


def full_coverage_counterexample():
    """Copying a source reverses x/y at every finite k despite full coverage.

    Base x ranks (1,5,5), y ranks (5,1,1): y wins by
    1/(k+1)-1/(k+5)>0. Adding two exact copies of the first source
    reverses that difference. Every document is present in every source.
    """
    a=['x','a','b','c','y']
    b=['y','a','b','c','x']
    base=[a,b,b[:]]
    copied=base+[a[:],a[:]]
    outcomes={}
    for k in GRID:
        original=canonical_rrf(base,k=k);altered=canonical_rrf(copied,k=k)
        outcomes[str(k)]={'base_y_above_x':original.index('y')<original.index('x'),
                          'copied_x_above_y':altered.index('x')<altered.index('y')}
    return {'base':base,'copied':copied,'every_source_has_same_candidate_set':True,
            'grid_results':outcomes,'asymptotic_base':asymptotic_rrf(base),
            'asymptotic_copied':asymptotic_rrf(copied),
            'scope':'Constructive failure of exact-source-duplication invariance for every finite k>=0; no general claim that empirical displacement is monotone in k.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('output directory is not empty; choose a new evidence directory')
    args.output.mkdir(parents=True,exist_ok=True)
    sources=['evaluation/cycle01_rank_geometry.py','evaluation/fusion_contract.py','evaluation/trec_eval_harness.py','_sessions/cycles/2026-09-10-cycle01-protocol.md']
    source_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}
    inputs,hashes=load_inputs()
    provenance={'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'git_dirty_status':subprocess.check_output(['git','--no-optional-locks','status','--short','--untracked-files=all'],cwd=ROOT,text=True).splitlines(),
                'argv':sys.argv,'cwd':str(Path.cwd()),'python_version':platform.python_version(),
                'python_executable':sys.executable,'bootstrap':{'resamples':4000,'seed':1847},
                'input_sha256':hashes,'source_sha256':source_hashes}
    # Write launch provenance before work, then verify custody at completion.
    (args.output/'manifest-start.json').write_text(json.dumps(provenance,indent=2,sort_keys=True)+'\n')
    summaries,allrows,folds,caches=[],{}, {},{}
    for year,names in CONFIGS:
        label='{}-n{}'.format(year,len(names))
        summary,rows,details,cache=evaluate_configuration(year,names,*inputs[year])
        summaries.append(summary);allrows[label]=rows;folds[label]=details;caches[label]=cache
        print(label, json.dumps(summary['means']),flush=True)
    # Average each query across its repeated ensembles first, then resample queries.
    qids=sorted(allrows['2019-n4'])
    aggregate={m:paired_summary(mean(allrows['2019-n{}'.format(n)][q]['scores'][m]-allrows['2019-n{}'.format(n)][q]['scores']['k60'] for n in [4,5,6,7]) for q in qids) for m in ['selected_k','k200','coverage_proxy','asymptotic']}
    transfers=[]
    for train_year,test_year in [(2019,2020),(2020,2019)]:
        train=caches['{}-n4'.format(train_year)];test=caches['{}-n4'.format(test_year)]
        chosen=max(GRID,key=lambda k:mean(row[k] for row in train.values()))
        transfers.append({'train_year':train_year,'test_year':test_year,'selected_k':chosen,
                          'baseline_mean':mean(row[60] for row in test.values()),'selected_mean':mean(row[chosen] for row in test.values()),
                          'paired':paired_summary(row[chosen]-row[60] for row in test.values())})
    dup_summaries,dup_rows=[],[]
    for year in [2019,2020]:
        summary,rows=duplicate_interventions(year,BASE,*inputs[year])
        dup_summaries.extend(summary);dup_rows.extend(rows)
    result={'protocol':'_sessions/cycles/2026-09-10-cycle01-protocol.md','k_grid':GRID,'cv_seeds':SEEDS,'summaries':summaries,
            '2019_ensemble_mean_by_query':aggregate,'cross_annual_transfer':transfers,'duplicate_interventions':dup_summaries,
            'identifiability_fixture':identifiability_fixture(),'full_coverage_counterexample':full_coverage_counterexample(),
            'limits':['Development data after extensive search','Intervals conditional on saved predictions; not full training-selection uncertainty','Exact duplicate quotient proves invariance, not general source-quality inference','No novelty or independent-domain generalization claim']}
    for name,value in [('summary',result),('per_query',allrows),('folds',folds),('duplication_per_query',dup_rows)]:
        (args.output/(name+'.json')).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    for path,digest in {**hashes,**source_hashes}.items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('input/source changed during experiment: '+path)
    provenance['output_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.output.glob('*.json')) if p.name!='manifest.json'}
    (args.output/'manifest.json').write_text(json.dumps(provenance,indent=2,sort_keys=True)+'\n')
    print('Wrote',args.output,flush=True)


if __name__=='__main__':
    main()
