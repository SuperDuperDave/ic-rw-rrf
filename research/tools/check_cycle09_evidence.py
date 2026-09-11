#!/usr/bin/env python3
"""Independent local certificate-content audit; no production imports or exec.

The actual two RNGs are reconstructed only by an explicit fixture audit. No
provider calls, response interpretation or other-cycle data access occurs.
"""
import argparse
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/cycle09-2026-09-11/prepared'
DESIGN = '_sessions/cycles/2026-09-10-cycle09-certificate-design.md'
PROTOCOL = '_sessions/cycles/2026-09-11-cycle09-local-protocol.md'
CODE = 'evaluation/cycle09_certificates.py'
CHECKER = '_sessions/tools/check_cycle09_evidence.py'
CHECKS = 0
MAX_MAGNITUDE = 100
SKELETON = '''a = A
b = B
a = a + b
b = a - b
a = a + b
result = (a % 2 == R)
'''


def require(condition, label):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise ValueError('independent cycle09 check failed: ' + label)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(Path(path).read_bytes())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n'


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def reject_nonfinite(_value):
    raise ValueError('nonfinite JSON constant')


def parse_json(text):
    return json.loads(text, object_pairs_hook=unique_pairs, parse_constant=reject_nonfinite)


def read_json(path):
    return parse_json(Path(path).read_text())


def initial_literal(node):
    if isinstance(node, ast.Constant) and type(node.value) is int:
        value = node.value
    elif (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub)
          and isinstance(node.operand, ast.Constant) and type(node.operand.value) is int
          and node.operand.value >= 0):
        value = -node.operand.value
    else:
        raise ValueError('initial state must be a signed integer literal')
    require(-9 <= value <= 9, 'initial literal in -9..9')
    return value


def validate_program(source):
    require(type(source) is str and 0 < len(source.encode()) <= 4096, 'bounded program bytes')
    try:
        tree = ast.parse(source)
        nodes = list(ast.walk(tree))
        statements = [node for node in nodes if isinstance(node, ast.stmt)]
        require(len(nodes) <= 96 and len(tree.body) == len(statements) == 6,
                'exact six assignments and bounded AST')
        require(len([line for line in source.splitlines() if line.strip()]) == 6
                and len({node.lineno for node in statements}) == 6, 'one numbered assignment per line')
        a, b = initial_literal(tree.body[0].value), initial_literal(tree.body[1].value)
        rhs = tree.body[-1].value.comparators[0]
        require(isinstance(rhs, ast.Constant) and type(rhs.value) is int and rhs.value in (0, 1),
                'literal parity comparison')
        erased = deepcopy(tree)
        erased.body[0].value = ast.Name(id='A', ctx=ast.Load())
        erased.body[1].value = ast.Name(id='B', ctx=ast.Load())
        erased.body[-1].value.comparators[0] = ast.Name(id='R', ctx=ast.Load())
        require(ast.dump(erased, include_attributes=False)
                == ast.dump(ast.parse(SKELETON), include_attributes=False), 'entire AST matches exact allowed skeleton')
    except (SyntaxError, AttributeError, IndexError, TypeError, RecursionError) as error:
        raise ValueError('invalid exact certificate program') from error
    return tree, {'A': a, 'B': b, 'R': rhs.value}


def step_state(statement, previous):
    """One independent state transition, preserving all unchanged variables."""
    maximum = 0

    def integer(value):
        nonlocal maximum
        require(type(value) is int and abs(value) <= MAX_MAGNITUDE, 'typed bounded arithmetic value')
        maximum = max(maximum, abs(value))
        return value

    def expression(node):
        if isinstance(node, ast.Constant):
            return integer(node.value)
        if isinstance(node, ast.Name):
            require(node.id in previous, 'initialized scalar read')
            return integer(previous[node.id])
        if isinstance(node, ast.UnaryOp):
            return integer(-expression(node.operand))
        if isinstance(node, ast.BinOp):
            left, right = expression(node.left), expression(node.right)
            if isinstance(node.op, ast.Add):
                return integer(left + right)
            if isinstance(node.op, ast.Sub):
                return integer(left - right)
            return integer(left % right)
        return expression(node.left) == expression(node.comparators[0])

    next_state = dict(previous)
    next_state[statement.targets[0].id] = expression(statement.value)
    return next_state, maximum


def evaluate_program(source):
    tree, _ = validate_program(source)
    rows, state, maximum = [], {}, 0
    for index, statement in enumerate(tree.body, 1):
        state, step_max = step_state(statement, state)
        maximum = max(maximum, step_max)
        rows.append({'step': index, 'state': dict(state)})
    require(type(state['result']) is bool, 'typed final predicate')
    return {'rows': rows, 'answer': state['result'], 'final_state': dict(sorted(state.items())),
            'ast_dump': ast.dump(tree, include_attributes=False), 'max_abs_intermediate': maximum,
            'executed_statements': 6}


def validate_certificate(certificate):
    require(type(certificate) is dict and set(certificate) == {'rows'}, 'certificate has rows only')
    rows = certificate['rows']
    require(type(rows) is list and len(rows) == 6, 'six ordered certificate rows')
    for step, row in enumerate(rows, 1):
        require(type(row) is dict and set(row) == {'step', 'state'} and type(row['step']) is int
                and row['step'] == step, 'exact typed row schema and index')
        expected_keys = {'a'} if step == 1 else {'a', 'b'} if step < 6 else {'a', 'b', 'result'}
        require(type(row['state']) is dict and set(row['state']) == expected_keys, 'complete defined-variable state')
        for name, value in row['state'].items():
            require(type(value) is bool if name == 'result' else type(value) is int and abs(value) <= MAX_MAGNITUDE,
                    'strict scalar type and magnitude')
    return certificate


def check_certificate(source, certificate):
    tree, _ = validate_program(source)
    validate_certificate(certificate)
    previous, transitions = {}, []
    for statement, row in zip(tree.body, certificate['rows']):
        expected, _ = step_state(statement, previous)
        submitted = row['state']
        valid = canonical(expected) == canonical(submitted)
        transitions.append({'step': row['step'], 'valid': valid,
                            'expected_state': expected, 'submitted_state': dict(submitted)})
        previous = submitted
    invalid = [row['step'] for row in transitions if not row['valid']]
    return {'valid': not invalid, 'first_invalid_step': invalid[0] if invalid else None,
            'transitions': transitions}


def reconstruct_certificates(source):
    tree, _ = validate_program(source)
    reference = evaluate_program(source)
    valid = {'rows': reference['rows']}
    altered, state = [], {}
    for step, statement in enumerate(tree.body, 1):
        state, _ = step_state(statement, state)
        if step == 3:
            state['a'] += 1
        altered.append({'step': step, 'state': dict(state)})
    final_wrong = deepcopy(valid)
    final_wrong['rows'][-1]['state']['result'] = not reference['answer']
    certificates = {'V': valid, 'I': {'rows': altered}, 'F': final_wrong}
    for certificate in certificates.values():
        validate_certificate(certificate)
    return certificates


def reference_policies(original_ids, certificates_by_id, source):
    truth = {rid: check_certificate(source, certificates_by_id[rid])['valid'] for rid in original_ids}
    policies = {}
    for name in ('always_valid', 'always_invalid', 'exact_checker'):
        decisions = {rid: truth[rid] if name == 'exact_checker' else name == 'always_valid' for rid in original_ids}
        policies[name] = {'decisions': decisions, 'correct': sum(decisions[rid] is truth[rid] for rid in original_ids),
                          'valid': 3, 'planned': 3}
    return policies


def verify_fixture(fixture):
    """Reconstruct one candidate and the fixed identity shuffle, explicitly only."""
    rng = random.Random(420009)
    parameters = {'A': rng.randint(-9, 9), 'B': rng.randint(-9, 9), 'R': rng.randrange(2)}
    identity_rng = random.Random(420010)
    private_order = ['V', 'I', 'F']
    identity_rng.shuffle(private_order)
    report_ids = [f'r_{identity_rng.getrandbits(64):016x}' for _ in range(5)]
    require(len(set(report_ids)) == 5, 'identifier collision stops without replacement')
    generation = {'parameter_seed': 420009, 'identity_seed': 420010, 'parameters': parameters,
                  'private_order': private_order, 'report_ids': report_ids, 'candidate_attempts': 1, 'exclusions': []}
    require(canonical(fixture['generation']) == canonical(generation), 'exact parameter and identity RNG sequences')
    source = (f"a = {parameters['A']}\nb = {parameters['B']}\n"
              'a = a + b\nb = a - b\na = a + b\n'
              f"result = (a % 2 == {parameters['R']})\n")
    require(fixture['schema_version'] == 1 and fixture['program'] == source
            and fixture['program_sha256'] == sha(source.encode()), 'program grammar and exact source custody')
    reference = evaluate_program(source)
    require(canonical(fixture['python_truth']) == canonical(reference), 'independent Python truth/AST/state/count agreement')
    certificates = reconstruct_certificates(source)
    require(canonical(fixture['certificates']) == canonical(certificates), 'exact V/I/F construction without adaptive repair')
    checks = {label: check_certificate(source, certificate) for label, certificate in certificates.items()}
    require(canonical(fixture['certificate_checks']) == canonical(checks), 'every complete submitted-state transition')
    hashes = {label: sha(canonical(certificate).encode()) for label, certificate in certificates.items()}
    require(fixture['certificate_sha256'] == hashes, 'canonical certificate payload hashes')
    first = {label: checked['first_invalid_step'] for label, checked in checks.items()}
    require(first == {'V': None, 'I': 3, 'F': 6}, 'prespecified first-invalid rows')
    require({label: [row['step'] for row in checked['transitions'] if not row['valid']]
             for label, checked in checks.items()} == {'V': [], 'I': [3], 'F': [6]},
            'exactly one local invalid transition per corrupted certificate')
    final_answers = {label: certificate['rows'][-1]['state']['result'] for label, certificate in certificates.items()}
    delta = certificates['I']['rows'][-1]['state']['a'] - certificates['V']['rows'][-1]['state']['a']
    require(delta == 2 and final_answers['I'] is final_answers['V'] and final_answers['F'] is not final_answers['V'],
            'parity-preserving invalid trace and flipped-final negative controls')
    control = {'whole_certificate_validity': {label: checked['valid'] for label, checked in checks.items()},
        'first_invalid_step': first, 'final_answers': final_answers, 'I_final_a_delta': delta,
        'I_parity_preserved': True, 'F_answer_flipped': True}
    require(canonical(fixture['negative_control']) == canonical(control), 'negative-control record')
    originals = [{'report_id': rid, 'root_id': rid, 'certificate': certificates[label]}
                 for rid, label in zip(report_ids[:3], private_order)]
    f_root = report_ids[private_order.index('F')]
    copies = [{'report_id': rid, 'root_id': f_root, 'certificate': certificates['F']} for rid in report_ids[3:]]
    packets = []
    for packet_id, tail in (('base', [None, None]), ('repeat', copies)):
        payload = {'program': source, 'original_ids': report_ids[:3], 'reports': originals + tail}
        text = canonical(payload)
        packets.append({'packet_id': packet_id, 'payload': text, 'payload_sha256': sha(text.encode())})
    require(canonical(fixture['packets']) == canonical(packets), 'exact original/copy/empty-slot information boundary')
    for packet in fixture['packets']:
        payload = parse_json(packet['payload'])
        require(canonical(payload) == packet['payload'], 'actual packet JSON canonical bytes and newline')
        require(set(payload) == {'program', 'original_ids', 'reports'} and len(payload['reports']) == 5,
                'packets expose no construction metadata or checker verdict')
        for report in payload['reports']:
            if report is not None:
                require(set(report) == {'report_id', 'root_id', 'certificate'}, 'report instance schema')
                validate_certificate(report['certificate'])
    base, repeat = [parse_json(packet['payload']) for packet in fixture['packets']]
    require(canonical(base['reports'][:3]) == canonical(repeat['reports'][:3]), 'original report bytes unchanged between packets')
    for copy in repeat['reports'][3:]:
        require(canonical(copy['certificate']) == canonical(certificates['F']) and copy['root_id'] == f_root,
                'copied boundary is the entire F certificate, excluding instance IDs')
    by_id = {row['report_id']: row['certificate'] for row in originals}
    policies = reference_policies(report_ids[:3], by_id, source)
    require(canonical(fixture['reference_policies']) == canonical({packet_id: policies for packet_id in ('base', 'repeat')}),
            'all simple policy decisions and named correctness denominators')
    return {'candidate_attempts': 1, 'distinct_original_certificates': 3, 'packet_count': 2,
            'all_truths_full_state_transitions_and_copy_bytes_match': True,
            'information_boundary_and_both_RNG_sequences_verified': True,
            'negative_control': control,
            'reference_policy_correct_per_packet': {name: policy['correct'] for name, policy in policies.items()},
            'reference_policy_correct_across_two_packets': {name: 2 * policy['correct'] for name, policy in policies.items()},
            'validity_judgments_per_packet': 3, 'repeated_judgments_across_packets': 6,
            'empirical_launch_authorized': False}


def run(prepared=BASE):
    manifest = read_json(prepared / 'manifest.json')
    sources = manifest['source_sha256_start']
    require(sources == manifest['source_sha256_end'] and manifest['empirical_launch_authorized'] is False,
            'unchanged local source and launch boundary')
    expected_sources = {CODE, CHECKER, DESIGN, PROTOCOL, 'evaluation/tests/test_cycle09_certificates.py',
                        '_sessions/tools/tests/test_cycle09_audit.py'}
    require(set(sources) == expected_sources, 'complete source/test/protocol inventory')
    for name, expected in sources.items():
        require(file_sha(ROOT / name) == expected, 'pinned source ' + name)
    expected_artifacts = {'fixture.json', 'independent-check.json', 'cases.md', 'program.py',
        'certificates/V.json', 'certificates/I.json', 'certificates/F.json', 'packets/base.json', 'packets/repeat.json'}
    require(set(manifest['artifact_sha256']) == expected_artifacts, 'complete output artifact inventory')
    for name, expected in manifest['artifact_sha256'].items():
        require(file_sha(prepared / name) == expected, 'prepared artifact ' + name)
    fixture = read_json(prepared / 'fixture.json')
    require((prepared / 'fixture.json').read_bytes() == canonical(fixture).encode(), 'canonical fixture bytes')
    require((prepared / 'program.py').read_bytes() == fixture['program'].encode(), 'prepared source bytes')
    for label, certificate in fixture['certificates'].items():
        require((prepared / 'certificates' / (label + '.json')).read_bytes() == canonical(certificate).encode(),
                'prepared certificate bytes ' + label)
    for packet in fixture['packets']:
        require((prepared / 'packets' / (packet['packet_id'] + '.json')).read_bytes() == packet['payload'].encode(),
                'prepared actual packet bytes ' + packet['packet_id'])
    verified = verify_fixture(fixture)
    require(canonical(read_json(prepared / 'independent-check.json')) == canonical(verified), 'retained preparation audit')
    interpreter = Path(manifest['python']['executable'])
    interpreter_status = 'unavailable'
    if interpreter.exists():
        require(file_sha(interpreter) == manifest['python']['executable_sha256'], 'truth Python interpreter bytes')
        interpreter_status = 'verified'
    require(type(manifest['preparation_argv']) is list and bool(manifest['preparation_argv'])
            and type(manifest['local_generation_truth_wall_seconds']) in (int, float)
            and manifest['local_generation_truth_wall_seconds'] >= 0, 'command and measured preparation wall time')
    return {'schema_version': 1, 'status': 'passed', 'checked_utc': datetime.now(timezone.utc).isoformat(),
            'checker_sha256': file_sha(Path(__file__)), 'checks_passed': CHECKS,
            'prepared_manifest_sha256': file_sha(prepared / 'manifest.json'),
            'truth_python_bytes': interpreter_status, 'fixture_check': verified,
            'independence': 'Independent standard-library AST state interpreter; no production imports or program execution.',
            'limitations': [
                'This is one program construction with three original certificates, not six independent cases.',
                'No empirical solver outcome or launch is implied by successful local construction.',
                'Correct validity bits alone cannot identify an internal verification strategy.',
                'Only F is copied; rejecting repeated roots is an alternative way to identify F in the repeat packet.',
                'Repeats replace empty slots and add text, so the contrast does not isolate a pure copying mechanism.',
                'Distinct artifact roots do not establish independent authors or errors.',
                'Machine checking is a practical correctness baseline; no multiagent advantage is measured.']}


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
                      'first_invalid_step': result['fixture_check']['negative_control']['first_invalid_step']}))


if __name__ == '__main__':
    main()
