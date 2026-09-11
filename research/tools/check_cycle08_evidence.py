#!/usr/bin/env python3
"""Independent local cycle08 truth, matching, trace, decision and custody audit.

No production imports, Python execution, provider calls or cycle07 source reads.
Actual candidate reconstruction occurs only when verify_panel is explicitly run.
"""
import argparse
import ast
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/cycle08-2026-09-10/prepared'
DESIGN = '_sessions/cycles/2026-09-10-cycle08-loopbound-design.md'
PROTOCOL = '_sessions/cycles/2026-09-10-cycle08-local-protocol.md'
CODE = 'evaluation/cycle08_loopbound.py'
CHECKER = '_sessions/tools/check_cycle08_evidence.py'
CHECKS = 0
MAX_MAGNITUDE, MAX_STEPS = 1_000_000, 512
OPERATOR_PAIRS = (('+', '+'), ('+', '-'), ('-', '+'), ('-', '-'))
SKELETON = '''a = A
b = B
c = C
for i in range(N):
    a = (a * b + c) % 997
    b = (b * c + a) % 997
    if b < c:
        c = (c + b) % 997
    c = (c * a + b) % 997
a = (a + b) % 997
b = (b + c) % 997
result = (a % 3 == R)
'''


def require(condition, label):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise ValueError('independent cycle08 check failed: ' + label)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(Path(path).read_bytes())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def reject_nonfinite(_value):
    raise ValueError('nonfinite JSON constant')


def read_json(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=unique_pairs,
                      parse_constant=reject_nonfinite)


def validate_program(source):
    """Allow exactly the frozen skeleton, with five literals and two signs free."""
    require(type(source) is str and 0 < len(source.encode()) <= 16_384, 'bounded source bytes')
    try:
        tree = ast.parse(source)
        nodes = list(ast.walk(tree))
        require(len(nodes) <= 256, 'bounded AST size')
        statements = [node for node in nodes if isinstance(node, ast.stmt)]
        require(len(statements) == len([line for line in source.splitlines() if line.strip()]) == 12
                and len({node.lineno for node in statements}) == 12, 'twelve distinct executable source lines')
        require(len(tree.body) == 7, 'exact top-level skeleton')
        initial = [tree.body[index].value for index in range(3)]
        loop = tree.body[3]
        n, rhs = loop.iter.args[0], tree.body[-1].value.comparators[0]
        require(all(isinstance(node, ast.Constant) and type(node.value) is int
                    and 1 <= node.value <= 996 for node in initial), 'bounded initial literals')
        require(isinstance(n, ast.Constant) and type(n.value) is int and n.value in (4, 64), 'literal four/64 loop bound')
        require(isinstance(rhs, ast.Constant) and type(rhs.value) is int and rhs.value in (0, 1, 2), 'literal truth predicate')
        operations = [loop.body[index].value.left.op for index in range(2)]
        require(all(type(op) in (ast.Add, ast.Sub) for op in operations), 'two frozen sign choices')
        # Erase only declared intervention/parameter slots. Exact remaining AST
        # equality also rejects dead-code imports, i reads, nesting and resets.
        erased = deepcopy(tree)
        for index, name in enumerate(('A', 'B', 'C')):
            erased.body[index].value = ast.Name(id=name, ctx=ast.Load())
        erased.body[3].iter.args[0] = ast.Name(id='N', ctx=ast.Load())
        erased.body[-1].value.comparators[0] = ast.Name(id='R', ctx=ast.Load())
        for index in range(2):
            erased.body[3].body[index].value.left.op = ast.Add()
        require(ast.dump(erased, include_attributes=False)
                == ast.dump(ast.parse(SKELETON), include_attributes=False), 'whole AST matches exact allowlisted skeleton')
    except (SyntaxError, AttributeError, IndexError, TypeError, RecursionError) as error:
        raise ValueError('invalid exact cycle08 syntax') from error
    require(6 * n.value + 7 <= MAX_STEPS, 'static worst-case step ceiling before interpretation')
    return tree, {'parameters': [node.value for node in initial] + [rhs.value],
                  'operators': ['+' if isinstance(op, ast.Add) else '-' for op in operations], 'n': n.value}


def evaluate_program(source):
    """Traverse AST state transitions without eval, exec or compile."""
    tree, metadata = validate_program(source)
    state, loop_states, counts = {}, [], {'true': 0, 'false': 0}
    steps, maximum, answer = 0, 0, None

    def integer(value):
        nonlocal maximum
        require(type(value) is int and abs(value) <= MAX_MAGNITUDE, 'bounded actual intermediate')
        maximum = max(maximum, abs(value))
        return value

    def expression(node):
        if isinstance(node, ast.Constant):
            return integer(node.value)
        if isinstance(node, ast.Name):
            require(node.id in state, 'initialized state read')
            return integer(state[node.id])
        if isinstance(node, ast.BinOp):
            left, right = expression(node.left), expression(node.right)
            if isinstance(node.op, ast.Add):
                return integer(left + right)
            if isinstance(node.op, ast.Sub):
                return integer(left - right)
            if isinstance(node.op, ast.Mult):
                return integer(left * right)
            return integer(left % right)
        left, right = expression(node.left), expression(node.comparators[0])
        return left < right if isinstance(node.ops[0], ast.Lt) else left == right

    def tick():
        nonlocal steps
        steps += 1
        require(steps <= MAX_STEPS, 'actual statement ceiling')

    def snapshot():
        return {key: state[key] for key in ('a', 'b', 'c')}

    def execute(block):
        nonlocal answer
        for node in block:
            if isinstance(node, ast.For):
                loop_states.append(snapshot())
                for index in range(integer(node.iter.args[0].value)):
                    tick()
                    state['i'] = integer(index)
                    execute(node.body)
                    loop_states.append(snapshot())
                tick()
            else:
                tick()
                if isinstance(node, ast.If):
                    take = expression(node.test)
                    counts['true' if take else 'false'] += 1
                    if take:
                        execute(node.body)
                elif node.targets[0].id == 'result':
                    answer = expression(node.value)
                else:
                    state[node.targets[0].id] = expression(node.value)

    execute(tree.body)
    n = metadata['n']
    require(type(answer) is bool and len(loop_states) == n + 1, 'complete typed state trace')
    require(steps == 5 * n + 7 + counts['true'] and sum(counts.values()) == n, 'independent actual step identity')
    return {'answer': answer, 'final_state': dict(sorted(state.items())), 'loop_states': loop_states,
            'executed_statements': steps, 'worst_case_executed_statements': 6 * n + 7,
            'static_statement_count': 12, 'max_abs_intermediate': maximum, 'branch_counts': counts,
            'ast_dump': ast.dump(tree, include_attributes=False), 'predicate': ast.unparse(tree.body[-1].value)}


def normalized_template(source):
    tree = ast.parse(source)
    tree.body.pop()
    names = {}

    class Normalize(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id == 'range':
                return node
            label = names.setdefault(node.id, 'v' + str(len(names)))
            return ast.copy_location(ast.Name(id=label, ctx=node.ctx), node)

        def visit_Constant(self, node):
            return ast.copy_location(ast.Constant(value=0), node)

        def visit_UnaryOp(self, node):
            if isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
                return ast.copy_location(ast.Constant(value=0), node)
            return self.generic_visit(node)

    return ast.dump(Normalize().visit(tree), include_attributes=False)


def first_cycle(states):
    seen = {}
    for index, state in enumerate(states):
        key = tuple(state[name] for name in ('a', 'b', 'c'))
        if key in seen:
            return {'entry': seen[key], 'period': index - seen[key], 'repeat_at': index}
        seen[key] = index
    return None


def matched_audit(short_source, long_source):
    short, long = evaluate_program(short_source), evaluate_program(long_source)
    short_tree, short_metadata = validate_program(short_source)
    long_tree, long_metadata = validate_program(long_source)
    require(short_metadata['n'] == 4 and long_metadata['n'] == 64, 'both prespecified bounds')
    short_tree.body[3].iter.args[0].value = 64
    require(ast.dump(short_tree, include_attributes=False) == ast.dump(long_tree, include_attributes=False),
            'only N differs in actual matched ASTs')
    require(short_source.replace('range(4)', 'range(64)', 1) == long_source,
            'only N differs in actual matched source bytes')
    require(short['loop_states'] == long['loop_states'][:5], 'identical first four transitions')
    rhs = long_metadata['parameters'][3]
    prefix = []
    for index, state in enumerate(long['loop_states']):
        final = {'a': (state['a'] + state['b']) % 997,
                 'b': (state['b'] + state['c']) % 997, 'c': state['c']}
        prefix.append({'iterations': index, 'final_state': final, 'answer': final['a'] % 3 == rhs})
    for n, interpreted in ((4, short), (64, long)):
        require(prefix[n]['final_state'] == {name: interpreted['final_state'][name] for name in ('a', 'b', 'c')}
                and prefix[n]['answer'] is interpreted['answer'], 'prefix-tail result agrees with AST execution')
    return {'prefix_results': prefix, 'first_cycle': first_cycle(long['loop_states']),
            'same_final_state': prefix[4]['final_state'] == prefix[64]['final_state'],
            'only_n_changes': True, 'constant_prefix_answer': len({row['answer'] for row in prefix}) == 1,
            'endpoint_answers_equal': prefix[4]['answer'] is prefix[64]['answer']}


def valid_hash(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def verify_source_review(review, source_hashes=None):
    require(type(review) is dict and set(review) == {'schema_version', 'reviewer', 'source_sha256', 'reviews'}
            and review['schema_version'] == 1, 'source-review schema')
    require(type(review['reviewer']) is str and bool(review['reviewer'].strip()), 'named independent source reviewer')
    require(set(review['source_sha256']) == {CODE, CHECKER, DESIGN, PROTOCOL}
            and all(valid_hash(value) for value in review['source_sha256'].values()), 'source review pins four inputs')
    if source_hashes is not None:
        require(review['source_sha256'] == {name: source_hashes[name] for name in (CODE, CHECKER, DESIGN, PROTOCOL)},
                'source review matches exact code and protocols')
    require(type(review['reviews']) is list and len(review['reviews']) == 4, 'all four source operator cases reviewed')
    for row, operators in zip(review['reviews'], OPERATOR_PAIRS):
        require(type(row) is dict and set(row) == {'operators', 'demonstrated_bound_irrelevance',
                'proof', 'reduction_finding'}, 'operator review schema')
        require(row['operators'] == list(operators) and type(row['demonstrated_bound_irrelevance']) is bool,
                'operator review identity and typed verdict')
        require(type(row['proof']) is str and type(row['reduction_finding']) is str
                and bool(row['reduction_finding'].strip()), 'source findings are explicit')
        require(bool(row['proof'].strip()) if row['demonstrated_bound_irrelevance'] else row['proof'] == '',
                'claimed irrelevance requires an explicit proof')


def independent_decision(templates, items, source_review):
    reasons = []
    if len(templates) != 4:
        reasons.append({'code': 'insufficient_distinct_templates'})
    if len(items) == 8 and len({item['python_truth']['answer'] for item in items}) == 1:
        reasons.append({'code': 'all_eight_answers_equal'})
    for template in templates:
        if template['audit']['same_final_state']:
            reasons.append({'code': 'identical_final_triples', 'template_id': template['template_id']})
        if template['audit']['first_cycle'] is not None:
            reasons.append({'code': 'repeated_transition_state', 'template_id': template['template_id']})
    if source_review is not None:
        verify_source_review(source_review)
        demonstrated = {tuple(row['operators']) for row in source_review['reviews']
                        if row['demonstrated_bound_irrelevance']}
        for template in templates:
            if tuple(template['operators']) in demonstrated:
                reasons.append({'code': 'demonstrated_bound_irrelevance', 'template_id': template['template_id']})
    return {'status': 'parked' if reasons else 'pending_source_review' if source_review is None
            else 'consider_execution_freeze', 'park_reasons': reasons, 'empirical_launch_authorized': False}


def verify_panel(panel):
    """Explicit actual-seed reconstruction; never called at import or by default."""
    require(panel['schema_version'] == 1, 'panel schema version')
    old_hashes = panel['old_template_hashes']
    require(type(old_hashes) is list and len(old_hashes) == 24 and old_hashes == sorted(set(old_hashes))
            and all(valid_hash(value) for value in old_hashes), '24 old structural hashes only')
    require(panel['bounds'] == {'loop_bounds': [4, 64], 'max_abs_integer': MAX_MAGNITUDE,
            'max_executed_statements': MAX_STEPS, 'source_lines': 12}, 'frozen numerical and grammar bounds')
    generation = panel['generation']
    candidates = generation['candidates']
    require(generation['seed'] == 420008 and generation['max_attempts'] == 32
            and generation['attempt_count'] == len(candidates) and 4 <= len(candidates) <= 32,
            'fixed candidate seed and finite attempt ceiling')
    rng = random.Random(420008)
    accepted, templates, items, exclusions = set(), [], [], Counter()
    for attempt, candidate in enumerate(candidates):
        parameters = {name: rng.randint(1, 996) for name in ('A', 'B', 'C')}
        parameters['R'] = rng.randint(0, 2)
        operators = list(OPERATOR_PAIRS[attempt % 4])
        require(candidate['attempt'] == attempt and candidate['parameters'] == parameters
                and candidate['operators'] == operators, 'first-order parameter draws and structural order')
        sources = {}
        for n in (4, 64):
            lines = [f"a = {parameters['A']}", f"b = {parameters['B']}", f"c = {parameters['C']}",
                f'for i in range({n}):', f'    a = (a * b {operators[0]} c) % 997',
                f'    b = (b * c {operators[1]} a) % 997', '    if b < c:',
                '        c = (c + b) % 997', '    c = (c * a + b) % 997',
                'a = (a + b) % 997', 'b = (b + c) % 997', f"result = (a % 3 == {parameters['R']})"]
            sources[str(n)] = '\n'.join(lines) + '\n'
        require(candidate['programs'] == sources, 'exact candidate program bytes')
        hashes = {n: sha(source.encode()) for n, source in sources.items()}
        require(candidate['program_sha256'] == hashes, 'candidate program hashes')
        for source in sources.values():
            validate_program(source)
        normalized = [normalized_template(sources[str(n)]) for n in (4, 64)]
        require(normalized[0] == normalized[1], 'matched bounds share one structural identity')
        digest = sha(normalized[0].encode())
        require(candidate['template_hash'] == digest, 'independent normalized template digest')
        reason = ('previous_cycle_template' if digest in old_hashes else
                  'duplicate_accepted_template' if digest in accepted else None)
        require(candidate['reason'] == reason and candidate['status'] == ('excluded' if reason else 'accepted'),
                'acceptance uses novelty and bounds, never trace/truth findings')
        if reason:
            exclusions[reason] += 1
            continue
        truth = {n: evaluate_program(source) for n, source in sources.items()}
        require(canonical(candidate['checks']) == canonical({n: {key: row[key] for key in
                ('answer', 'executed_statements', 'max_abs_intermediate')} for n, row in truth.items()}),
                'candidate truth/count/magnitude checks')
        tid = 't_' + digest[:20]
        new_items = [{'item_id': 'i_' + hashes[str(n)][:20], 'template_id': tid, 'n': n,
                      'program': sources[str(n)], 'program_sha256': hashes[str(n)], 'python_truth': truth[str(n)]}
                     for n in (4, 64)]
        templates.append({'template_id': tid, 'template_hash': digest, 'parameters': parameters,
            'operators': operators, 'item_ids': [row['item_id'] for row in new_items],
            'audit': matched_audit(sources['4'], sources['64'])})
        items.extend(new_items)
        accepted.add(digest)
        require(len(templates) <= 4 and (len(templates) != 4 or attempt == len(candidates) - 1),
                'stop immediately at four accepted structures')
    require(len(templates) == 4 or len(candidates) == 32, 'four-structure completion or finite search stop')
    require(canonical(panel['items']) == canonical(items), 'all Python truths, states, traces, ASTs, branches and bounds')
    require(canonical(panel['templates']) == canonical(templates), 'all template matching, prefix-tail and cycle diagnostics')
    require(len({item['item_id'] for item in items}) == len(items), 'distinct item IDs')
    source_review = panel['source_review']
    if source_review is not None:
        verify_source_review(source_review, {name: file_sha(ROOT / name) for name in (CODE, CHECKER, DESIGN, PROTOCOL)})
    decision = independent_decision(templates, items, source_review)
    require(canonical(panel['decision']) == canonical(decision), 'all and only prespecified local parking criteria')
    return {'template_count': len(templates), 'program_count': len(items),
            'candidate_attempts': len(candidates), 'exclusion_counts': dict(exclusions),
            'all_python_truths_final_states_and_traces_match': True,
            'all_prefix_tail_answers_and_cycle_diagnostics_match': True,
            'all_counts_magnitudes_ASTs_and_source_only_n_contrasts_match': True,
            'old_hash_and_new_structure_deduplication_verified': True,
            'source_review_present': source_review is not None, 'decision': decision,
            'templates': [{'template_id': t['template_id'], 'operators': t['operators'],
                'first_cycle': t['audit']['first_cycle'], 'same_final_state': t['audit']['same_final_state'],
                'constant_prefix_answer': t['audit']['constant_prefix_answer'],
                'endpoint_answers_equal': t['audit']['endpoint_answers_equal'],
                'answers_by_n': {str(i['n']): i['python_truth']['answer'] for i in items
                                 if i['template_id'] == t['template_id']}} for t in templates]}


def run(prepared=BASE):
    manifest = read_json(prepared / 'manifest.json')
    sources = manifest['source_sha256_start']
    require(sources == manifest['source_sha256_end'] and manifest['empirical_launch_authorized'] is False,
            'closed local preparation source and authorization boundary')
    required_sources = {CODE, CHECKER, DESIGN, PROTOCOL, 'evaluation/tests/test_cycle08_loopbound.py',
                        '_sessions/tools/tests/test_cycle08_audit.py', 'evaluation/cycle07_program_errors.py'}
    require(set(sources) == required_sources, 'complete source/checker/test/protocol inventory')
    for name, expected in sources.items():
        require(file_sha(ROOT / name) == expected, 'unchanged source ' + name)
    required = {'panel.json', 'independent-check.json', 'cases.md', 'old-template-hashes.json', 'source-review.json'}
    require(set(manifest['artifact_sha256']) == required, 'complete prepared artifact inventory')
    for name, expected in manifest['artifact_sha256'].items():
        require(file_sha(prepared / name) == expected, 'prepared artifact custody ' + name)
    require(set(manifest['input_sha256']) == {'old-template-hashes.json', 'source-review.json'}, 'frozen input inventory')
    for name, expected in manifest['input_sha256'].items():
        require(expected == manifest['artifact_sha256'][name], 'input/prepared exact byte custody')
    old = read_json(prepared / 'old-template-hashes.json')
    require(set(old) == {'schema_version', 'source_fixture_sha256', 'template_hashes'}
            and old['schema_version'] == 1 and valid_hash(old['source_fixture_sha256']), 'old hash export schema')
    # Scope is deliberately restricted to digest and template_hash metadata.
    # No reserved source, truth or response is inspected or used for this panel.
    old_path = ROOT / 'results/cycle07-2026-09-10/prepared/fixture.json'
    require(file_sha(old_path) == old['source_fixture_sha256'], 'old hash export original fixture anchor')
    old_template_hashes = sorted(item['template_hash'] for item in read_json(old_path)['items'])
    require(old['template_hashes'] == old_template_hashes, 'independently extracted 24 old structural hashes')
    panel = read_json(prepared / 'panel.json')
    review = read_json(prepared / 'source-review.json')
    verify_source_review(review, sources)
    require(panel['old_template_hashes'] == old['template_hashes'] and panel['source_review'] == review,
            'panel input custody')
    verified = verify_panel(panel)
    require(canonical(read_json(prepared / 'independent-check.json')) == canonical(verified),
            'retained preparation audit reconstruction')
    python_path = Path(manifest['python']['executable'])
    python_status = 'unavailable'
    if python_path.exists():
        require(file_sha(python_path) == manifest['python']['executable_sha256'], 'truth Python interpreter bytes')
        python_status = 'verified'
    require(type(manifest['preparation_argv']) is list and bool(manifest['preparation_argv'])
            and type(manifest['local_generation_truth_wall_seconds']) in (int, float)
            and manifest['local_generation_truth_wall_seconds'] >= 0, 'preparation command and measured wall time')
    return {'schema_version': 1, 'status': 'passed', 'checked_utc': datetime.now(timezone.utc).isoformat(),
            'checker_sha256': file_sha(Path(__file__)), 'checks_passed': CHECKS,
            'prepared_manifest_sha256': file_sha(prepared / 'manifest.json'),
            'truth_python_bytes': python_status, 'panel_check': verified,
            'independence': 'Independent standard-library AST state interpreter; no production imports or Python program execution.',
            'limitations': [
                'No empirical solver responses or new provider calls are part of this local audit.',
                'Different sequential execution lengths do not prove different reasoning difficulty.',
                'Constant prefix answers and equal endpoint Booleans are descriptive, not additional parking criteria.',
                'The source review found last-step algebraic reductions, not proof that the bound is irrelevant.',
                'Absence of a discovered shortcut is not proof that no short solution exists.',
                'Within-pair manipulation of N does not isolate all differences between cycle07 and cycle08.',
                'Old fixture access is restricted to its digest and stored structural hashes.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, default=BASE)
    parser.add_argument('--output', type=Path, help='Write a new receipt; never overwrite')
    args = parser.parse_args()
    result = run(args.prepared)
    if args.output:
        with args.output.open('x', encoding='utf-8') as handle:
            json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write('\n')
    print(json.dumps({'status': result['status'], 'checks_passed': result['checks_passed'],
                      'decision': result['panel_check']['decision']}))


if __name__ == '__main__':
    main()
