"""Cycle13 metadata correction: preserve exactly the inventoried retained inputs."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys
import time

if __package__:
    from . import cycle13_judgment_acquisition as frozen
    from .cycle03_specialist_association import read_json
else:
    import cycle13_judgment_acquisition as frozen
    from cycle03_specialist_association import read_json


ROOT = frozen.ROOT
CODE = 'evaluation/cycle13_retained_inputs.py'
TESTS = 'evaluation/tests/test_cycle13_retained_inputs.py'
CORRECTION = '_sessions/cycles/2026-09-11-cycle13-retained-input-correction.md'
INVENTORY = '_sessions/evidence/2026-09-11-cycle13-retained-inputs.json'
SOURCE_FILES = frozen.SOURCE_FILES + (CODE, TESTS, CORRECTION, INVENTORY)
canonical_rrf = frozen.canonical_rrf
analyze_query = frozen.analyze_query
summarize_queries = frozen.summarize_queries
canonical_json = frozen.canonical_json


def source_depths(runs):
    return {name: {'query_depths': {qid: len(ranking) for qid, ranking in sorted(runs[name].items())},
                   'depth_histogram': {str(depth): count for depth, count in
                                       sorted(Counter(map(len, runs[name].values())).items())}}
            for name in frozen.SOURCES}


def validate_retained_runs(runs, inventory_year, expected_count):
    """Check exact metadata and shared cohort, retaining every list in file order."""
    if type(runs) is not dict or set(runs) != set(frozen.SOURCES):
        raise ValueError('retained run source set mismatch')
    if type(inventory_year) is not dict or set(inventory_year) != set(frozen.SOURCES):
        raise ValueError('inventory source set mismatch')
    qids = None
    for name in frozen.SOURCES:
        if type(runs[name]) is not dict or any(type(q) is not str or not q for q in runs[name]):
            raise ValueError('invalid retained query IDs')
        current = set(runs[name])
        if qids is None:
            qids = current
        if current != qids or len(current) != expected_count:
            raise ValueError('retained sources do not share the complete prescribed cohort')
        for ranking in runs[name].values():
            if not frozen._ranking(ranking):
                raise ValueError('retained source list cannot be empty')
        entry = inventory_year[name]
        if type(entry) is not dict or set(entry) != {'path', 'query_depths', 'depth_histogram'}:
            raise ValueError('invalid retained inventory entry')
        if (type(entry['query_depths']) is not dict
                or any(type(q) is not str or not q or type(n) is not int or n <= 0
                       for q, n in entry['query_depths'].items())
                or type(entry['depth_histogram']) is not dict
                or any(type(n) is not int or n <= 0 for n in entry['depth_histogram'].values())):
            raise ValueError('invalid retained inventory depths')
    depths = source_depths(runs)
    for name in frozen.SOURCES:
        if (depths[name]['query_depths'] != inventory_year[name]['query_depths']
                or depths[name]['depth_histogram'] != inventory_year[name]['depth_histogram']):
            raise ValueError('exact retained depth inventory mismatch: ' + name)
    return sorted(qids), depths


def load_validated_inputs(root, inventory):
    """Finish all file/hash/depth checks across both years before returning data."""
    root = Path(root).resolve()
    paths = frozen.fixed_inputs(root)
    if (type(inventory) is not dict or inventory.get('preserve_full_retained_lists') is not True
            or type(inventory.get('years')) is not dict
            or set(inventory['years']) != {str(y) for y in frozen.YEARS}):
        raise ValueError('invalid retained input inventory')
    hashes = frozen._input_hashes(paths, root)
    if hashes != inventory.get('input_sha256') or len(hashes) != 12:
        raise ValueError('retained input hash identity mismatch')
    years, metadata = {}, {}
    for year in frozen.YEARS:
        config, entries = paths[year], inventory['years'][str(year)]
        if type(entries) is not dict or set(entries) != set(frozen.SOURCES):
            raise ValueError('retained inventory source set mismatch')
        for name in frozen.SOURCES:
            if type(entries[name]) is not dict or entries[name].get('path') != str(config[name].relative_to(root)):
                raise ValueError('retained source path mismatch')
        runs = {name: frozen.read_ranked_run(config[name], 0 if name in frozen.LEXICAL else 1)
                for name in frozen.SOURCES}
        metadata[year] = validate_retained_runs(runs, entries, frozen.EXPECTED_QUERY_COUNTS[year])
        years[year] = runs
    qrels = {year: frozen.read_qrels(paths[year]['qrels']) for year in frozen.YEARS}
    if hashes != frozen._input_hashes(paths, root):
        raise ValueError('retained inputs changed before scoring')
    return paths, hashes, years, qrels, metadata


def _source_hashes(inventory_path):
    return {name: frozen.sha256(inventory_path if name == INVENTORY else ROOT / name) for name in SOURCE_FILES}


def run_audit(output_directory, root=ROOT, command_argv=None):
    output = Path(output_directory)
    if output.exists():
        raise FileExistsError(output)
    start = time.monotonic()
    root = Path(root).resolve()
    inventory_path = frozen.repository_file(INVENTORY, root)
    sources, identity = _source_hashes(inventory_path), frozen._python_identity()
    inventory = read_json(inventory_path)
    paths, inputs, all_runs, qrels, metadata = load_validated_inputs(root, inventory)
    per_query, summaries = {}, {}
    for year in frozen.YEARS:
        runs, (qids, depths) = all_runs[year], metadata[year]
        records = {}
        for qid in qids:
            lexical = [runs[name][qid] for name in frozen.LEXICAL]
            a = canonical_rrf(lexical, k=60)
            b = canonical_rrf(lexical + [runs[frozen.SOURCE_ID][qid]], k=60)
            records[qid] = analyze_query(a, b, qrels[year].get(qid, {}))
        summary = summarize_queries(records, year)
        summary['source_depths'] = depths
        per_query[str(year)], summaries[str(year)] = records, summary
    if (sources != _source_hashes(inventory_path) or inputs != frozen._input_hashes(paths, root)
            or identity != frozen._python_identity()):
        raise ValueError('input/source/interpreter changed during corrected audit')
    summary = {
        'schema_version': 1,
        'comparison': {'a': list(frozen.LEXICAL), 'b': list(frozen.SOURCES), 'rrf_k': 60,
                       'fusion_ordering': 'canonical_rrf floating contributions; string-ID computed-score ties'},
        'metric': {'name': 'top10_rbp_contribution', 'persistence': frozen.PERSISTENCE,
                   'cutoff': frozen.CUTOFF, 'gain': 'grade/3', 'tail_inference': False,
                   'renormalized': False, 'delta': 'B-minus-A'},
        'allocation': {'budgets_per_query': list(frozen.BUDGETS), 'cost_per_exact_label': 1,
                       'uniform': 'analytic expectation without replacement; no sampled runs'},
        'years': summaries,
        'interpretation': 'Finite-panel bounds and per-query acquisition plans. No new labels consumed; '
                          'projected widths do not determine future centers or signs.'}
    manifest = {
        'schema_version': 1, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_sha256_start': sources, 'source_sha256_end': _source_hashes(inventory_path),
        'input_sha256_start': inputs, 'input_sha256_end': frozen._input_hashes(paths, root),
        'python': identity, 'expected_query_counts': frozen.EXPECTED_QUERY_COUNTS,
        'command_argv': list(sys.argv if command_argv is None else command_argv),
        'local_wall_seconds': time.monotonic() - start, 'new_labels_acquired': 0,
        'retained_input_correction': CORRECTION, 'retained_input_inventory': INVENTORY}
    output.mkdir(parents=True, exist_ok=False)
    for name, value in (('per_query.json', per_query), ('summary.json', summary)):
        with (output / name).open('x', encoding='utf-8') as stream:
            stream.write(canonical_json(value))
    manifest['artifact_sha256'] = {name: frozen.sha256(output / name) for name in ('per_query.json', 'summary.json')}
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
