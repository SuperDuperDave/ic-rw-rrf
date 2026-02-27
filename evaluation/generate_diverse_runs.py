#!/usr/bin/env python3
"""
Generate diverse TREC run files from MS MARCO top-1000 passage data.
====================================================================

Creates rankers with genuinely different ranking functions, including
both the original lexical rankers AND structurally diverse rankers that
use fundamentally different signals than bag-of-words.

Original lexical rankers (bag-of-words paradigm):
  1. BM25 (k1=1.2, b=0.75) -- standard lexical
  2. BM25-tuned (k1=0.9, b=0.4) -- term-frequency emphasis
  3. TF-IDF -- classic information retrieval
  4. QL-Dirichlet (mu=2000) -- language model approach

NEW structurally diverse rankers (non-bag-of-words signals):
  5. tfidf_bigram -- TF-IDF with (1,2)-grams + cosine similarity
     Captures word-pair co-occurrence absent from unigram models
  6. proximity -- Query term proximity scoring
     Captures positional/structural signal (not bag-of-words at all)
  7. semantic_hash -- Random projection hashing of character n-grams
     Distributional signal via locality-sensitive hashing (subword)

Dependencies: numpy, scipy (for new rankers only)
"""

import math
import os
import re
import sys
import time
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

# numpy/scipy for diverse rankers
try:
    import numpy as np
    from scipy import sparse
    from scipy.sparse.linalg import norm as sparse_norm
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("WARNING: numpy/scipy not found. Only lexical rankers will be generated.")


# ================================================================
# SECTION 1: Data Loading
# ================================================================

def load_top1000(path: str) -> Tuple[Dict, Dict]:
    """
    Load MS MARCO top-1000 TSV file.
    Format: qid \t pid \t query_text \t passage_text
    Returns: {qid: [(pid, passage_text), ...]}, {qid: query_text}
    """
    data = defaultdict(list)
    queries = {}

    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 4:
                continue
            qid, pid, query, passage = parts[0], parts[1], parts[2], parts[3]
            data[qid].append((pid, passage))
            if qid not in queries:
                queries[qid] = query

    return dict(data), queries


# ================================================================
# SECTION 2: Text Processing
# ================================================================

# Simple stopwords (top 50 English)
STOPWORDS = set("""
a an and are as at be but by for from has have he her his how i in is it its
me my no not of on or our she so than that the their them then there these they
this to too us was we were what when where which who will with you your
""".split())


def tokenize(text: str) -> List[str]:
    """Simple whitespace + punctuation tokenizer."""
    tokens = []
    current = []
    for ch in text.lower():
        if ch.isalnum():
            current.append(ch)
        else:
            if current:
                tokens.append(''.join(current))
                current = []
    if current:
        tokens.append(''.join(current))
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def tokenize_raw(text: str) -> List[str]:
    """Tokenize without stopword removal (for proximity scoring)."""
    return re.findall(r'[a-z0-9]+', text.lower())


def char_ngrams(text, n=4):
    """Extract character n-grams from text."""
    text = text.lower()
    grams = []
    for i in range(len(text) - n + 1):
        grams.append(text[i:i+n])
    return grams


# ================================================================
# SECTION 3: Collection Statistics
# ================================================================

def build_collection_stats(data: Dict[str, List[Tuple[str, str]]]) -> dict:
    """Build collection-level statistics for ranking functions."""
    df = Counter()
    cf = Counter()
    total_dl = 0
    N = 0
    seen_docs = set()

    for qid, passages in data.items():
        for pid, text in passages:
            if pid in seen_docs:
                continue
            seen_docs.add(pid)
            tokens = tokenize(text)
            total_dl += len(tokens)
            N += 1
            unique_terms = set(tokens)
            for t in unique_terms:
                df[t] += 1
            for t in tokens:
                cf[t] += 1

    return {
        'avg_dl': total_dl / max(N, 1),
        'N': N,
        'df': df,
        'cf': cf,
        'total_terms': sum(cf.values()),
    }


# ================================================================
# SECTION 4: Original Lexical Ranking Functions
# ================================================================

def score_bm25(query_tokens, doc_tokens, stats, k1=1.2, b=0.75):
    dl = len(doc_tokens)
    avg_dl = stats['avg_dl']
    N = stats['N']
    tf_map = Counter(doc_tokens)
    score = 0.0
    for qt in query_tokens:
        if qt not in tf_map:
            continue
        tf = tf_map[qt]
        df_val = stats['df'].get(qt, 0)
        idf = math.log((N - df_val + 0.5) / (df_val + 0.5) + 1.0)
        tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avg_dl))
        score += idf * tf_norm
    return score


def score_tfidf(query_tokens, doc_tokens, stats):
    dl = len(doc_tokens)
    if dl == 0:
        return 0.0
    N = stats['N']
    tf_map = Counter(doc_tokens)
    score = 0.0
    for qt in query_tokens:
        if qt not in tf_map:
            continue
        tf = tf_map[qt]
        df_val = stats['df'].get(qt, 0)
        tf_norm = 1 + math.log(tf) if tf > 0 else 0
        idf = math.log(N / (df_val + 1))
        score += tf_norm * idf
    score /= math.sqrt(dl)
    return score


def score_ql_dirichlet(query_tokens, doc_tokens, stats, mu=2000):
    dl = len(doc_tokens)
    if dl == 0:
        return -1e10
    total_terms = stats['total_terms']
    tf_map = Counter(doc_tokens)
    score = 0.0
    for qt in query_tokens:
        tf = tf_map.get(qt, 0)
        cf_val = stats['cf'].get(qt, 0)
        p_collection = cf_val / max(total_terms, 1)
        p_doc = (tf + mu * p_collection) / (dl + mu)
        if p_doc > 0:
            score += math.log(p_doc)
    return score


LEXICAL_RANKERS = {
    'bm25': lambda qt, dt, s: score_bm25(qt, dt, s, k1=1.2, b=0.75),
    'bm25_tuned': lambda qt, dt, s: score_bm25(qt, dt, s, k1=0.9, b=0.4),
    'tfidf': lambda qt, dt, s: score_tfidf(qt, dt, s),
    'ql_dirichlet': lambda qt, dt, s: score_ql_dirichlet(qt, dt, s, mu=2000),
}


# ================================================================
# SECTION 5: NEW Diverse Ranking Functions
# ================================================================

def generate_tfidf_bigram_run(data, queries, stats):
    """
    TF-IDF with unigram + bigram features, cosine similarity.
    Captures word-pair co-occurrence patterns that pure unigram models miss.
    """
    print("\n  Scoring with tfidf_bigram...")
    results = {}
    n_queries = len(data)

    for qi, qid in enumerate(sorted(data.keys())):
        if (qi + 1) % 20 == 0 or qi == 0:
            print(f"    Query {qi+1}/{n_queries} (qid={qid})")

        query = queries[qid]
        entries = data[qid]

        def get_features(text):
            tokens = tokenize(text)
            features = list(tokens)
            for i in range(len(tokens) - 1):
                features.append(f"{tokens[i]}_{tokens[i+1]}")
            return features

        # Build per-query vocabulary from passages + query
        all_texts = [query] + [p for _, p in entries]
        all_features = [get_features(t) for t in all_texts]

        # Document frequency within this query's candidate set
        df_local = Counter()
        for feats in all_features:
            for f in set(feats):
                df_local[f] += 1

        n_docs = len(all_texts)
        vocab = {}
        for feat, count in df_local.items():
            if count >= 2 and count < n_docs * 0.95:
                vocab[feat] = len(vocab)

        if not vocab:
            for feats in all_features:
                for f in feats:
                    if f not in vocab:
                        vocab[f] = len(vocab)

        V = len(vocab)
        if V == 0:
            results[qid] = [(pid, 0.0) for pid, _ in entries]
            continue

        def to_tfidf_vector(features):
            tf = Counter(features)
            rows, cols, vals = [], [], []
            for feat, count in tf.items():
                if feat in vocab:
                    col = vocab[feat]
                    idf = math.log(n_docs / (df_local.get(feat, 1) + 1))
                    tf_val = 1 + math.log(count) if count > 0 else 0
                    rows.append(0)
                    cols.append(col)
                    vals.append(tf_val * idf)
            if not vals:
                return sparse.csr_matrix((1, V))
            return sparse.csr_matrix((vals, (rows, cols)), shape=(1, V))

        q_vec = to_tfidf_vector(all_features[0])
        q_norm = sparse_norm(q_vec)

        if q_norm < 1e-12:
            results[qid] = [(pid, 0.0) for pid, _ in entries]
            continue

        scored = []
        for i, (pid, passage) in enumerate(entries):
            p_vec = to_tfidf_vector(all_features[i + 1])
            p_norm = sparse_norm(p_vec)
            if p_norm < 1e-12:
                scored.append((pid, 0.0))
                continue
            sim = float(q_vec.dot(p_vec.T).toarray()[0, 0]) / (q_norm * p_norm)
            scored.append((pid, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        results[qid] = scored

    return results


def generate_proximity_run(data, queries):
    """
    Query term proximity scoring.
    Ranks passages by how close query terms appear to each other.
    This captures positional/structural signal completely orthogonal
    to bag-of-words models.
    """
    print("\n  Scoring with proximity...")
    results = {}
    n_queries = len(data)

    for qi, qid in enumerate(sorted(data.keys())):
        if (qi + 1) % 20 == 0 or qi == 0:
            print(f"    Query {qi+1}/{n_queries} (qid={qid})")

        query = queries[qid]
        q_terms = list(set(tokenize_raw(query)))

        if len(q_terms) < 1:
            results[qid] = [(pid, 0.0) for pid, _ in data[qid]]
            continue

        scored = []
        for pid, passage in data[qid]:
            p_tokens = tokenize_raw(passage)

            if not p_tokens:
                scored.append((pid, 0.0))
                continue

            # Build position index
            positions = defaultdict(list)
            for i, tok in enumerate(p_tokens):
                positions[tok].append(i)

            # Coverage: fraction of query terms found
            found = sum(1 for qt in q_terms if qt in positions)
            coverage = found / len(q_terms)

            # Proximity: for each pair of query terms, minimum span
            proximity_score = 0.0
            n_pairs = 0

            if len(q_terms) >= 2:
                for i in range(len(q_terms)):
                    for j in range(i + 1, len(q_terms)):
                        t1, t2 = q_terms[i], q_terms[j]
                        if t1 in positions and t2 in positions:
                            # Use sorted merge for efficiency
                            p1_list = positions[t1]
                            p2_list = positions[t2]
                            min_dist = float('inf')
                            # Two-pointer minimum distance
                            pi, pj = 0, 0
                            while pi < len(p1_list) and pj < len(p2_list):
                                d = abs(p1_list[pi] - p2_list[pj])
                                if d < min_dist:
                                    min_dist = d
                                if p1_list[pi] < p2_list[pj]:
                                    pi += 1
                                else:
                                    pj += 1
                            if min_dist < float('inf'):
                                proximity_score += 1.0 / (1.0 + min_dist)
                        n_pairs += 1

                if n_pairs > 0:
                    proximity_score /= n_pairs

            # Early position bonus
            early_bonus = 0.0
            for qt in q_terms:
                if qt in positions:
                    earliest = min(positions[qt])
                    early_bonus += 1.0 / (1.0 + earliest)
            if q_terms:
                early_bonus /= len(q_terms)

            # Exact phrase match bonus
            phrase_bonus = 0.0
            if len(q_terms) >= 2:
                passage_lower = passage.lower()
                query_lower = query.lower()
                if query_lower in passage_lower:
                    phrase_bonus = 1.0
                else:
                    # Check for partial phrase matches (consecutive bigrams)
                    for i in range(len(q_terms) - 1):
                        bigram = f"{q_terms[i]} {q_terms[i+1]}"
                        if bigram in passage_lower:
                            phrase_bonus += 0.3

            # Combined score - weight proximity and phrase as they're the unique signals
            score = (0.20 * coverage +
                     0.40 * proximity_score +
                     0.15 * early_bonus +
                     0.25 * min(phrase_bonus, 1.0))
            scored.append((pid, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        results[qid] = scored

    return results


def generate_semantic_hash_run(data, queries, n_components=256, char_n=4, seed=42):
    """
    Random projection hashing of character n-gram features.
    Fundamentally different signal than word-level models:
    - Operates on character 4-grams (subword signal)
    - Uses random projections (locality-sensitive hashing)
    - Captures morphological similarity, partial matches, typos
    """
    print("\n  Scoring with semantic_hash...")

    rng = np.random.RandomState(seed)
    HASH_SPACE = 2**14  # 16384 hash buckets

    # Random sign matrix for projection
    print("    Building random projection matrix...")
    signs = rng.choice([-1, 1], size=(n_components, HASH_SPACE)).astype(np.float32)

    results = {}
    n_queries = len(data)

    for qi, qid in enumerate(sorted(data.keys())):
        if (qi + 1) % 20 == 0 or qi == 0:
            print(f"    Query {qi+1}/{n_queries} (qid={qid})")

        query = queries[qid]
        entries = data[qid]

        # Hash query to character n-gram space
        def text_to_hash_vector(text):
            grams = char_ngrams(text, n=char_n)
            counts = np.zeros(HASH_SPACE, dtype=np.float32)
            for g in grams:
                h = hash(g) % HASH_SPACE
                counts[h] += 1
            # Sublinear TF
            counts = np.log1p(counts)
            return counts

        q_counts = text_to_hash_vector(query)
        q_proj = signs @ q_counts
        q_norm = np.linalg.norm(q_proj)

        if q_norm < 1e-12:
            results[qid] = [(pid, 0.0) for pid, _ in entries]
            continue

        scored = []
        for pid, passage in entries:
            p_counts = text_to_hash_vector(passage)
            p_proj = signs @ p_counts
            p_norm = np.linalg.norm(p_proj)

            if p_norm < 1e-12:
                scored.append((pid, 0.0))
                continue

            sim = float(np.dot(q_proj, p_proj) / (q_norm * p_norm))
            scored.append((pid, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        results[qid] = scored

    return results


# ================================================================
# SECTION 6: Run File I/O
# ================================================================

def generate_lexical_run(data, queries, stats, scorer_fn, run_name, top_k=200):
    """Generate a TREC format run file for a lexical ranker."""
    lines = []
    for qid in sorted(data.keys()):
        query_tokens = tokenize(queries[qid])
        if not query_tokens:
            continue
        scored = []
        for pid, passage_text in data[qid]:
            doc_tokens = tokenize(passage_text)
            score = scorer_fn(query_tokens, doc_tokens, stats)
            scored.append((pid, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        for rank, (pid, score) in enumerate(scored[:top_k]):
            lines.append(f"{qid} Q0 {pid} {rank} {score:.6f} {run_name}")
    return lines


def write_run_file(lines, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        for line in lines:
            f.write(line + '\n')
    print(f"  Written {len(lines)} entries to {path}")


def write_diverse_run(results, path, run_name, top_k=200):
    """Write results dict to TREC run file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    total = 0
    with open(path, 'w') as f:
        for qid in sorted(results.keys(), key=lambda x: int(x) if x.isdigit() else x):
            for rank, (pid, score) in enumerate(results[qid][:top_k]):
                f.write(f"{qid} Q0 {pid} {rank} {score:.6f} {run_name}\n")
                total += 1
    print(f"  Written {total} entries to {path}")


# ================================================================
# SECTION 7: Diversity Analysis
# ================================================================

def analyze_diversity(run_files, qrels_path, top_n=30):
    """Analyze diversity across generated run files."""
    runs = {}
    for name, path in run_files.items():
        runs[name] = defaultdict(list)
        with open(path) as f:
            for line in f:
                parts = line.strip().split()
                qid, pid = parts[0], parts[2]
                runs[name][qid].append(pid)

    qrels = defaultdict(dict)
    with open(qrels_path) as f:
        for line in f:
            parts = line.strip().split()
            qid, pid, rel = parts[0], parts[2], int(parts[3])
            qrels[qid][pid] = rel

    common_qids = set(qrels.keys())
    for name in runs:
        common_qids &= set(runs[name].keys())

    names = list(runs.keys())
    print(f"\n  Diversity Analysis ({len(common_qids)} queries, {len(names)} rankers)")

    # Pairwise Jaccard on top-N
    print(f"\n  Pairwise Jaccard@{top_n}:")
    # Header
    print(f"  {'':20}", end="")
    for n in names:
        print(f" {n[:12]:>12}", end="")
    print()

    for i, n1 in enumerate(names):
        print(f"  {n1[:20]:<20}", end="")
        for j, n2 in enumerate(names):
            jaccards = []
            for qid in common_qids:
                s1 = set(runs[n1][qid][:top_n])
                s2 = set(runs[n2][qid][:top_n])
                union = s1 | s2
                if union:
                    jaccards.append(len(s1 & s2) / len(union))
            mean_j = sum(jaccards) / len(jaccards) if jaccards else 0
            print(f" {mean_j:>12.3f}", end="")
        print()

    # Per-ranker relevance at top 10
    print(f"\n  Mean relevant@10 (grade >= 2):")
    for name in names:
        rels = []
        for qid in common_qids:
            top10 = runs[name][qid][:10]
            rel_count = sum(1 for pid in top10 if qrels.get(qid, {}).get(pid, 0) >= 2)
            rels.append(rel_count)
        mean_rel = sum(rels) / len(rels) if rels else 0
        print(f"    {name:<20} {mean_rel:.2f}")

    # Unique documents per ranker
    print(f"\n  Unique docs per ranker (top-{top_n}, not in any other ranker's top-{top_n}):")
    for name in names:
        unique_counts = []
        for qid in common_qids:
            this_set = set(runs[name][qid][:top_n])
            other_sets = set()
            for other_name in names:
                if other_name != name:
                    other_sets |= set(runs[other_name][qid][:top_n])
            unique = this_set - other_sets
            unique_counts.append(len(unique))
        mean_unique = sum(unique_counts) / len(unique_counts) if unique_counts else 0
        print(f"    {name:<20} {mean_unique:.1f} avg unique docs")


# ================================================================
# SECTION 8: Main
# ================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate diverse TREC run files")
    parser.add_argument('--top1000', type=str,
                        default='data/trec-dl-2019/msmarco-passagetest2019-top1000.tsv',
                        help='Path to MS MARCO top-1000 TSV')
    parser.add_argument('--qrels', type=str,
                        default='data/trec-dl-2019/2019qrels-pass.txt',
                        help='Path to TREC DL 2019 qrels')
    parser.add_argument('--output-dir', type=str,
                        default='data/trec-dl-2019/runs',
                        help='Output directory for run files')
    parser.add_argument('--top-k', type=int, default=200,
                        help='Top-K results per ranker (default: 200)')
    parser.add_argument('--diverse-only', action='store_true',
                        help='Only generate diverse (non-lexical) rankers')
    parser.add_argument('--analyze-only', action='store_true',
                        help='Only run diversity analysis on existing runs')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    if args.analyze_only:
        run_files = {}
        for f in os.listdir(args.output_dir):
            if f.endswith('.txt'):
                name = f[:-4]
                run_files[name] = os.path.join(args.output_dir, f)
        if run_files:
            analyze_diversity(run_files, args.qrels)
        return

    print("Loading top-1000 data...")
    data, queries = load_top1000(args.top1000)
    print(f"  {len(data)} queries, {sum(len(v) for v in data.values())} total passages")

    # Filter to judged queries only
    judged_qids = set()
    with open(args.qrels) as f:
        for line in f:
            judged_qids.add(line.strip().split()[0])
    data = {qid: v for qid, v in data.items() if qid in judged_qids}
    queries = {qid: v for qid, v in queries.items() if qid in judged_qids}
    print(f"  Filtered to {len(data)} judged queries")

    run_files = {}

    # --- Lexical rankers ---
    if not args.diverse_only:
        print("\nBuilding collection statistics...")
        stats = build_collection_stats(data)
        print(f"  Unique docs: {stats['N']}")
        print(f"  Avg doc length: {stats['avg_dl']:.1f} tokens")
        print(f"  Vocabulary size: {len(stats['df'])}")

        print(f"\nGenerating {len(LEXICAL_RANKERS)} lexical run files...")
        for name, scorer_fn in LEXICAL_RANKERS.items():
            print(f"\n  Scoring with {name}...")
            lines = generate_lexical_run(data, queries, stats, scorer_fn, name, top_k=args.top_k)
            path = os.path.join(args.output_dir, f'{name}.txt')
            write_run_file(lines, path)
            run_files[name] = path
    else:
        # Load existing lexical runs
        for name in LEXICAL_RANKERS:
            path = os.path.join(args.output_dir, f'{name}.txt')
            if os.path.exists(path):
                run_files[name] = path
                print(f"  Using existing {name} run")

    # --- Diverse rankers ---
    if not HAS_NUMPY:
        print("\nERROR: numpy/scipy required for diverse rankers. Skipping.")
    else:
        # Need stats for bigram ranker
        if 'stats' not in locals():
            print("\nBuilding collection statistics...")
            stats = build_collection_stats(data)

        print(f"\nGenerating diverse (non-lexical) run files...")

        # 1. TF-IDF Bigram
        t0 = time.time()
        bigram_results = generate_tfidf_bigram_run(data, queries, stats)
        path = os.path.join(args.output_dir, 'tfidf_bigram.txt')
        write_diverse_run(bigram_results, path, 'tfidf_bigram', top_k=args.top_k)
        run_files['tfidf_bigram'] = path
        print(f"    ({time.time()-t0:.1f}s)")

        # 2. Proximity
        t0 = time.time()
        proximity_results = generate_proximity_run(data, queries)
        path = os.path.join(args.output_dir, 'proximity.txt')
        write_diverse_run(proximity_results, path, 'proximity', top_k=args.top_k)
        run_files['proximity'] = path
        print(f"    ({time.time()-t0:.1f}s)")

        # 3. Semantic Hash
        t0 = time.time()
        hash_results = generate_semantic_hash_run(data, queries, n_components=256)
        path = os.path.join(args.output_dir, 'semantic_hash.txt')
        write_diverse_run(hash_results, path, 'semantic_hash', top_k=args.top_k)
        run_files['semantic_hash'] = path
        print(f"    ({time.time()-t0:.1f}s)")

    # --- Analysis ---
    print("\n" + "=" * 70)
    analyze_diversity(run_files, args.qrels)

    print(f"\n{'=' * 70}")
    print("Run files generated. Evaluate with:")
    print(f"  python3 evaluation/trec_eval_harness.py \\")
    print(f"    --qrels {args.qrels} \\")
    print(f"    --run-dir {args.output_dir}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
