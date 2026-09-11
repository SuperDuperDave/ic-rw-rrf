"""Cycle08 local loop-bound audit. No provider calls or adaptive hardness search.

The actual seed is enumerated only by explicit build_panel/prepare invocation.
Tests can exercise the assembly and interpreter with synthetic candidates.
"""
import argparse
import ast
from collections import Counter
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import platform
import random
import sys
import time

if __package__:
    from .cycle07_program_errors import normalized_template
else:
    from cycle07_program_errors import normalized_template


ROOT = Path(__file__).resolve().parents[1]
CODE = 'evaluation/cycle08_loopbound.py'
TESTS = 'evaluation/tests/test_cycle08_loopbound.py'
CHECKER = '_sessions/tools/check_cycle08_evidence.py'
CHECKER_TESTS = '_sessions/tools/tests/test_cycle08_audit.py'
NORMALIZER = 'evaluation/cycle07_program_errors.py'
DESIGN = '_sessions/cycles/2026-09-10-cycle08-loopbound-design.md'
PROTOCOL = '_sessions/cycles/2026-09-10-cycle08-local-protocol.md'
SOURCE_FILES = (CODE, TESTS, CHECKER, CHECKER_TESTS, NORMALIZER, DESIGN, PROTOCOL)
REVIEW_SOURCES = (CODE, CHECKER, DESIGN, PROTOCOL)
SEED = 420008
MAX_ATTEMPTS = 32
MAX_MAGNITUDE = 1_000_000
MAX_STEPS = 512
BOUNDS = (4, 64)
OPERATOR_PAIRS = (('+', '+'), ('+', '-'), ('-', '+'), ('-', '-'))


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _file_sha(path):
    return sha256_bytes(Path(path).read_bytes())


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _read_json(path):
    def reject_constant(_):
        raise ValueError('nonfinite JSON constant')
    return json.loads(Path(path).read_text(encoding='utf-8'),
                      object_pairs_hook=_unique_pairs, parse_constant=reject_constant)


def _valid_hash(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def validate_old_hash_export(value):
    if type(value) is not dict or set(value) != {
            'schema_version', 'source_fixture_sha256', 'template_hashes'} or value['schema_version'] != 1:
        raise ValueError('invalid old-template hash export schema')
    hashes = value['template_hashes']
    if (not _valid_hash(value['source_fixture_sha256']) or type(hashes) is not list
            or len(hashes) != 24 or not all(_valid_hash(v) for v in hashes)
            or hashes != sorted(set(hashes))):
        raise ValueError('old-template export must contain 24 sorted distinct hashes')
    return value


def validate_source_review(review, source_hashes=None):
    if type(review) is not dict or set(review) != {
            'schema_version', 'reviewer', 'source_sha256', 'reviews'} or review['schema_version'] != 1:
        raise ValueError('invalid source-review schema')
    if type(review['reviewer']) is not str or not review['reviewer'].strip():
        raise ValueError('source review needs a reviewer')
    hashes = review['source_sha256']
    if (type(hashes) is not dict or set(hashes) != set(REVIEW_SOURCES)
            or not all(_valid_hash(value) for value in hashes.values())):
        raise ValueError('source review must pin code/checker/design/protocol')
    if source_hashes is not None and hashes != {p: source_hashes[p] for p in REVIEW_SOURCES}:
        raise ValueError('source review hash mismatch')
    if type(review['reviews']) is not list or len(review['reviews']) != 4:
        raise ValueError('source review must cover four ordered operator tuples')
    for record, operators in zip(review['reviews'], OPERATOR_PAIRS):
        if type(record) is not dict or set(record) != {
                'operators', 'demonstrated_bound_irrelevance', 'proof', 'reduction_finding'}:
            raise ValueError('invalid operator-review schema')
        if record['operators'] != list(operators) or type(record['demonstrated_bound_irrelevance']) is not bool:
            raise ValueError('invalid operator review identity or decision')
        if type(record['proof']) is not str or type(record['reduction_finding']) is not str or not record['reduction_finding'].strip():
            raise ValueError('operator review must record its source finding')
        if record['demonstrated_bound_irrelevance'] and not record['proof'].strip():
            raise ValueError('demonstrated shortcut requires a proof')
        if not record['demonstrated_bound_irrelevance'] and record['proof']:
            raise ValueError('non-demonstrated shortcut must have an empty proof')
    return review


def render_program(parameters, operators, n):
    if type(parameters) is not dict or set(parameters) != {'A', 'B', 'C', 'R'}:
        raise ValueError('invalid parameter keys')
    if any(type(parameters[k]) is not int or not 1 <= parameters[k] <= 996 for k in ('A', 'B', 'C')):
        raise ValueError('initial state must contain integers in 1..996')
    if type(parameters['R']) is not int or parameters['R'] not in (0, 1, 2):
        raise ValueError('predicate residue must be 0, 1, or 2')
    if type(n) is not int or n not in BOUNDS or tuple(operators) not in OPERATOR_PAIRS:
        raise ValueError('invalid frozen operators or loop bound')
    op1, op2 = operators
    return (
        f"a = {parameters['A']}\nb = {parameters['B']}\nc = {parameters['C']}\n"
        f"for i in range({n}):\n"
        f"    a = (a * b {op1} c) % 997\n"
        f"    b = (b * c {op2} a) % 997\n"
        "    if b < c:\n        c = (c + b) % 997\n"
        "    c = (c * a + b) % 997\n"
        "a = (a + b) % 997\nb = (b + c) % 997\n"
        f"result = (a % 3 == {parameters['R']})\n")


def validate_program(source):
    """Prove membership in the exact bounded skeleton before any execution."""
    if type(source) is not str or not 0 < len(source.encode('utf-8')) <= 16_384:
        raise ValueError('source size bound')
    try:
        tree = ast.parse(source)
        if len(list(ast.walk(tree))) > 512 or len(source.splitlines()) != 12:
            raise ValueError('source/AST size bound')
        constants = [tree.body[i].value for i in range(3)]
        loop = tree.body[3]
        rhs = tree.body[-1].value.comparators[0]
        n_node = loop.iter.args[0]
        if not all(isinstance(node, ast.Constant) and type(node.value) is int
                   for node in constants + [rhs, n_node]):
            raise ValueError('nonliteral frozen parameters')
        parameters = dict(zip(('A', 'B', 'C'), (node.value for node in constants)))
        parameters['R'] = rhs.value
        operator_types = (type(loop.body[0].value.left.op), type(loop.body[1].value.left.op))
        if any(kind not in (ast.Add, ast.Sub) for kind in operator_types):
            raise ValueError('nonallowlisted structural operator')
        operators = tuple('+' if kind is ast.Add else '-' for kind in operator_types)
        expected = ast.parse(render_program(parameters, operators, n_node.value))
        if ast.dump(tree, include_attributes=False) != ast.dump(expected, include_attributes=False):
            raise ValueError('AST differs from the exact frozen skeleton')
    except (SyntaxError, AttributeError, IndexError, KeyError, TypeError, RecursionError) as error:
        raise ValueError('invalid frozen program AST') from error
    worst = 6 * n_node.value + 7
    if worst > MAX_STEPS:
        raise ValueError('static termination bound')
    return tree, {'parameters': parameters, 'operators': list(operators), 'n': n_node.value,
                  'static_statement_count': 12, 'worst_case_executed_statements': worst}


def python_truth(source):
    """Python controls all state transitions; instrumentation checks every integer.

    The original validated AST executes only after the instrumented run passes.
    Neither Python execution accepts arbitrary unvalidated payloads.
    """
    tree, metadata = validate_program(source)
    steps, maximum = 0, 0
    states, branches = [], Counter({'true': 0, 'false': 0})

    def bounded(value):
        nonlocal maximum
        if type(value) is not int or abs(value) > MAX_MAGNITUDE:
            raise ValueError('intermediate integer magnitude bound')
        maximum = max(maximum, abs(value))
        return value

    def tick():
        nonlocal steps
        steps += 1
        if steps > MAX_STEPS:
            raise ValueError('executed statement bound')

    def snapshot(a, b, c):
        states.append({name: bounded(value) for name, value in zip(('a', 'b', 'c'), (a, b, c))})

    def branch(value):
        if type(value) is not bool:
            raise ValueError('nonboolean branch')
        branches[str(value).lower()] += 1
        return value

    class Instrument(ast.NodeTransformer):
        def wrap_integer(self, node):
            self.generic_visit(node)
            return ast.copy_location(ast.Call(func=ast.Name(id='_bound', ctx=ast.Load()),
                                              args=[node], keywords=[]), node)
        visit_BinOp = wrap_integer

        def visit_Constant(self, node):
            return ast.copy_location(ast.Call(func=ast.Name(id='_bound', ctx=ast.Load()),
                                              args=[node], keywords=[]), node)

        def call_statement(self, node, name, args=()):
            return ast.copy_location(ast.Expr(value=ast.Call(
                func=ast.Name(id=name, ctx=ast.Load()), args=list(args), keywords=[])), node)

        def visit_Assign(self, node):
            self.generic_visit(node)
            return [self.call_statement(node, '_tick'), node]

        def visit_If(self, node):
            self.generic_visit(node)
            node.test = ast.Call(func=ast.Name(id='_branch', ctx=ast.Load()),
                                 args=[node.test], keywords=[])
            return [self.call_statement(node, '_tick'), node]

        def visit_For(self, node):
            self.generic_visit(node)
            args = [ast.Name(id=name, ctx=ast.Load()) for name in ('a', 'b', 'c')]
            node.body.insert(0, self.call_statement(node, '_tick'))
            node.body.append(self.call_statement(node, '_snapshot', args))
            return [self.call_statement(node, '_snapshot', copy.deepcopy(args)),
                    self.call_statement(node, '_tick'), node]

    transformed = ast.fix_missing_locations(Instrument().visit(copy.deepcopy(tree)))
    state = {}
    exec(compile(transformed, '<cycle08-bounded>', 'exec'),
         {'__builtins__': {}, 'range': range, '_bound': bounded, '_tick': tick,
          '_snapshot': snapshot, '_branch': branch}, state)
    original_state = {}
    exec(compile(tree, '<cycle08-validated>', 'exec'),
         {'__builtins__': {}, 'range': range}, original_state)
    if original_state != state or type(state['result']) is not bool:
        raise RuntimeError('instrumented/original Python discrepancy')
    if len(states) != metadata['n'] + 1 or steps > metadata['worst_case_executed_statements']:
        raise RuntimeError('trace or static step discrepancy')
    return {'answer': state.pop('result'), 'final_state': dict(sorted(state.items())),
            'loop_states': states, 'executed_statements': steps,
            'worst_case_executed_statements': metadata['worst_case_executed_statements'],
            'static_statement_count': 12, 'max_abs_intermediate': maximum,
            'branch_counts': dict(branches), 'ast_dump': ast.dump(tree, include_attributes=False),
            'predicate': ast.unparse(tree.body[-1].value)}


def prefix_results(loop_states, rhs):
    """Apply the unchanged two-assignment tail to every verified loop state."""
    result = []
    for iterations, state in enumerate(loop_states):
        a, b, c = state['a'], state['b'], state['c']
        if any(type(v) is not int or not 0 <= v <= 996 for v in (a, b, c)):
            raise ValueError('invalid prefix state')
        # These sums cannot exceed 1992, well within the declared bound.
        a, b = (a + b) % 997, (b + c) % 997
        result.append({'iterations': iterations, 'final_state': {'a': a, 'b': b, 'c': c},
                       'answer': a % 3 == rhs})
    return result


def first_cycle(loop_states):
    seen = {}
    for index, state in enumerate(loop_states):
        key = tuple(state[name] for name in ('a', 'b', 'c'))
        if key in seen:
            return {'entry': seen[key], 'period': index - seen[key], 'repeat_at': index}
        seen[key] = index
    return None


def audit_template(items, rhs):
    by_n = {item['n']: item for item in items}
    low, high = [by_n[n]['python_truth'] for n in BOUNDS]
    if low['loop_states'] != high['loop_states'][:5]:
        raise ValueError('matched prefix state discrepancy')
    prefixes = prefix_results(high['loop_states'], rhs)
    for n in BOUNDS:
        truth = by_n[n]['python_truth']
        if (prefixes[n]['answer'] != truth['answer'] or prefixes[n]['final_state']
                != {name: truth['final_state'][name] for name in ('a', 'b', 'c')}):
            raise ValueError('prefix tail/Python result discrepancy')
    only_n = by_n[4]['program'].replace('range(4)', 'range(64)', 1) == by_n[64]['program']
    if not only_n:
        raise ValueError('matched programs differ beyond N')
    return {'prefix_results': prefixes, 'first_cycle': first_cycle(high['loop_states']),
            'same_final_state': prefixes[4]['final_state'] == prefixes[64]['final_state'],
            'only_n_changes': only_n,
            'constant_prefix_answer': len({p['answer'] for p in prefixes}) == 1,
            'endpoint_answers_equal': low['answer'] is high['answer']}


def panel_decision(templates, items, source_review=None):
    reasons = []
    if len(templates) != 4:
        reasons.append({'code': 'insufficient_distinct_templates'})
    if len(items) == 8 and len({item['python_truth']['answer'] for item in items}) == 1:
        reasons.append({'code': 'all_eight_answers_equal'})
    for template in templates:
        for key, code in (('same_final_state', 'identical_final_triples'),
                          ('first_cycle', 'repeated_transition_state')):
            if template['audit'][key]:
                reasons.append({'code': code, 'template_id': template['template_id']})
    if source_review is not None:
        validate_source_review(source_review)
        by_ops = {tuple(review['operators']): review for review in source_review['reviews']}
        for template in templates:
            if by_ops[tuple(template['operators'])]['demonstrated_bound_irrelevance']:
                reasons.append({'code': 'demonstrated_bound_irrelevance',
                                'template_id': template['template_id']})
    status = 'parked' if reasons else 'pending_source_review' if source_review is None else 'consider_execution_freeze'
    return {'status': status, 'park_reasons': reasons, 'empirical_launch_authorized': False}


def _candidate_stream():
    rng = random.Random(SEED)
    for attempt in range(MAX_ATTEMPTS):
        parameters = {name: rng.randint(1, 996) for name in ('A', 'B', 'C')}
        parameters['R'] = rng.randint(0, 2)
        yield {'attempt': attempt, 'parameters': parameters,
               'operators': list(OPERATOR_PAIRS[attempt % 4])}


def _assemble_panel(candidates, old_template_hashes, source_review=None):
    """Accept by syntax/bounds/novelty only. Audits never request replacements."""
    hashes = list(old_template_hashes)
    if len(hashes) != 24 or hashes != sorted(set(hashes)) or not all(_valid_hash(h) for h in hashes):
        raise ValueError('expected 24 sorted previous structural hashes')
    accepted_hashes = set()
    templates, items, attempted = [], [], []
    for candidate in itertools.islice(candidates, MAX_ATTEMPTS):
        record = copy.deepcopy(candidate)
        if record['attempt'] != len(attempted):
            raise ValueError('candidate attempt order mismatch')
        try:
            sources = {str(n): render_program(record['parameters'], record['operators'], n) for n in BOUNDS}
            record['programs'] = sources
            record['program_sha256'] = {n: sha256_bytes(source.encode()) for n, source in sources.items()}
            for source in sources.values():
                validate_program(source)
            normalized = [normalized_template(sources[str(n)]) for n in BOUNDS]
            if normalized[0] != normalized[1]:
                raise ValueError('bound variants normalize differently')
            digest = sha256_bytes(normalized[0].encode())
            record['template_hash'] = digest
            if digest in hashes:
                raise ValueError('previous_cycle_template')
            if digest in accepted_hashes:
                raise ValueError('duplicate_accepted_template')
            truths = {str(n): python_truth(sources[str(n)]) for n in BOUNDS}
        except ValueError as error:
            record.update(status='excluded', reason=str(error))
            attempted.append(record)
            continue
        record.update(status='accepted', reason=None, checks={
            n: {key: truth[key] for key in ('answer', 'executed_statements', 'max_abs_intermediate')}
            for n, truth in truths.items()})
        attempted.append(record)
        template_id = 't_' + digest[:20]
        new_items = [{'item_id': 'i_' + record['program_sha256'][str(n)][:20],
                      'template_id': template_id, 'n': n, 'program': sources[str(n)],
                      'program_sha256': record['program_sha256'][str(n)], 'python_truth': truths[str(n)]}
                     for n in BOUNDS]
        template = {'template_id': template_id, 'template_hash': digest,
                    'parameters': record['parameters'], 'operators': record['operators'],
                    'item_ids': [item['item_id'] for item in new_items],
                    'audit': audit_template(new_items, record['parameters']['R'])}
        accepted_hashes.add(digest)
        templates.append(template)
        items.extend(new_items)
        if len(templates) == 4:
            break
    return {'schema_version': 1, 'old_template_hashes': hashes,
            'generation': {'seed': SEED, 'max_attempts': MAX_ATTEMPTS,
                           'attempt_count': len(attempted), 'candidates': attempted},
            'bounds': {'loop_bounds': list(BOUNDS), 'max_abs_integer': MAX_MAGNITUDE,
                       'max_executed_statements': MAX_STEPS, 'source_lines': 12},
            'templates': templates, 'items': items, 'source_review': source_review,
            'decision': panel_decision(templates, items, source_review)}


def build_panel(old_template_hashes, source_review=None):
    """Explicitly enumerate the actual frozen seed; never called on import."""
    return _assemble_panel(_candidate_stream(), old_template_hashes, source_review)


def readable_cases(panel):
    lines = ['# Cycle08 source cases', '',
             'Local synthetic truth audit; no provider responses or empirical launch.', '']
    for template in panel['templates']:
        lines.extend([f"## {template['template_id']}", '',
                      'Operators: ' + ' / '.join(template['operators']) + '.', ''])
        for item in [item for item in panel['items'] if item['template_id'] == template['template_id']]:
            lines.extend([f"### N = {item['n']}", '', '~~~python', item['program'].rstrip(),
                          '~~~', '', 'Verified answer: ' + str(item['python_truth']['answer']).lower() + '.',
                          f"Executed statements: {item['python_truth']['executed_statements']}.", ''])
    lines.extend(['Decision: ' + panel['decision']['status'] + '.',
                  'Any empirical experiment requires its own execution freeze.', ''])
    return '\n'.join(lines)


def _source_hashes():
    return {name: _file_sha(ROOT / name) for name in SOURCE_FILES}


def _python_identity():
    executable = Path(sys.executable).resolve()
    return {'executable': str(executable), 'executable_sha256': _file_sha(executable),
            'version': sys.version, 'implementation': platform.python_implementation()}


def _load_checker():
    spec = importlib.util.spec_from_file_location('cycle08_independent_checker', ROOT / CHECKER)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    return checker


def prepare_fixture(output_directory, old_hash_file, source_review_file, preparation_argv=None):
    output = Path(output_directory)
    if output.exists():
        raise FileExistsError(output)
    start = time.monotonic()
    sources = _source_hashes()  # Missing source/checker files fail before enumeration.
    old_export = validate_old_hash_export(_read_json(old_hash_file))
    review = validate_source_review(_read_json(source_review_file), sources)
    input_sha = {'old-template-hashes.json': _file_sha(old_hash_file),
                 'source-review.json': _file_sha(source_review_file)}
    panel = build_panel(old_export['template_hashes'], review)
    independent = _load_checker().verify_panel(panel)
    if sources != _source_hashes() or input_sha != {
            'old-template-hashes.json': _file_sha(old_hash_file),
            'source-review.json': _file_sha(source_review_file)}:
        raise ValueError('source/input changed during preparation')
    artifacts = {'panel.json': (canonical_json(panel) + '\n').encode(),
                 'independent-check.json': (canonical_json(independent) + '\n').encode(),
                 'cases.md': readable_cases(panel).encode(),
                 'old-template-hashes.json': Path(old_hash_file).read_bytes(),
                 'source-review.json': Path(source_review_file).read_bytes()}
    manifest = {'schema_version': 1, 'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
                'source_sha256_start': sources, 'source_sha256_end': _source_hashes(),
                'python': _python_identity(), 'input_sha256': input_sha,
                'preparation_argv': list(sys.argv if preparation_argv is None else preparation_argv),
                'local_generation_truth_wall_seconds': time.monotonic() - start,
                'artifact_sha256': {name: sha256_bytes(data) for name, data in artifacts.items()},
                'empirical_launch_authorized': False}
    output.mkdir(parents=True, exist_ok=False)
    for name, data in artifacts.items():
        with (output / name).open('xb') as stream:
            stream.write(data)
    with (output / 'manifest.json').open('x', encoding='utf-8') as stream:
        stream.write(canonical_json(manifest) + '\n')
    return panel, manifest


def validate_fixture_custody(directory, expected_manifest_sha=None):
    directory = Path(directory)
    if expected_manifest_sha is not None and _file_sha(directory / 'manifest.json') != expected_manifest_sha:
        raise ValueError('manifest hash mismatch')
    manifest = _read_json(directory / 'manifest.json')
    if (manifest['source_sha256_start'] != manifest['source_sha256_end']
            or manifest['source_sha256_start'] != _source_hashes()
            or manifest['python'] != _python_identity()
            or manifest['empirical_launch_authorized'] is not False):
        raise ValueError('source/interpreter custody mismatch')
    required = {'panel.json', 'independent-check.json', 'cases.md',
                'old-template-hashes.json', 'source-review.json'}
    if set(manifest['artifact_sha256']) != required:
        raise ValueError('artifact inventory mismatch')
    for name, digest in manifest['artifact_sha256'].items():
        if _file_sha(directory / name) != digest:
            raise ValueError('artifact hash mismatch')
    old_export = validate_old_hash_export(_read_json(directory / 'old-template-hashes.json'))
    review = validate_source_review(_read_json(directory / 'source-review.json'),
                                    manifest['source_sha256_start'])
    for name in ('old-template-hashes.json', 'source-review.json'):
        if manifest['input_sha256'][name] != manifest['artifact_sha256'][name]:
            raise ValueError('input artifact identity mismatch')
    panel = _read_json(directory / 'panel.json')
    if panel['old_template_hashes'] != old_export['template_hashes'] or panel['source_review'] != review:
        raise ValueError('panel input custody mismatch')
    if readable_cases(panel).encode() != (directory / 'cases.md').read_bytes():
        raise ValueError('readable source cases mismatch')
    # Independent reconstruction verifies order, traces, truth and decision.
    _load_checker().verify_panel(panel)
    return panel, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prepare = sub.add_parser('prepare')
    prepare.add_argument('--output', required=True)
    prepare.add_argument('--old-template-hashes', required=True)
    prepare.add_argument('--source-review', required=True)
    validate = sub.add_parser('validate')
    validate.add_argument('--prepared', required=True)
    validate.add_argument('--manifest-sha256')
    args = parser.parse_args(argv)
    if args.command == 'prepare':
        panel, _ = prepare_fixture(args.output, args.old_template_hashes, args.source_review)
    else:
        panel, _ = validate_fixture_custody(args.prepared, args.manifest_sha256)
    print(canonical_json({'templates': len(panel['templates']), 'items': len(panel['items']),
                          'decision': panel['decision']}))


if __name__ == '__main__':
    main()
