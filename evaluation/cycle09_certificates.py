"""Cycle09 fixed certificate-content construction and local verification.

No providers, prompt runner, outcome search, or RNG draws on import.
"""
import argparse
import ast
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import random
import re
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
CODE = 'evaluation/cycle09_certificates.py'
TESTS = 'evaluation/tests/test_cycle09_certificates.py'
CHECKER = '_sessions/tools/check_cycle09_evidence.py'
CHECKER_TESTS = '_sessions/tools/tests/test_cycle09_audit.py'
DESIGN = '_sessions/cycles/2026-09-10-cycle09-certificate-design.md'
PROTOCOL = '_sessions/cycles/2026-09-11-cycle09-local-protocol.md'
SOURCE_FILES = (CODE, TESTS, CHECKER, CHECKER_TESTS, DESIGN, PROTOCOL)
PARAMETER_SEED = 420009
IDENTITY_SEED = 420010
LABELS = ('V', 'I', 'F')
MAX_MAGNITUDE = 100
ID_PATTERN = re.compile(r'r_[0-9a-f]{16}\Z')


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False) + '\n'


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


def parse_json(text):
    if type(text) is not str:
        raise ValueError('JSON input must be text')
    def reject_constant(_):
        raise ValueError('nonfinite JSON constant')
    try:
        return json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=reject_constant)
    except (TypeError, RecursionError) as error:
        raise ValueError('invalid JSON') from error


def _read_json(path):
    return parse_json(Path(path).read_text(encoding='utf-8'))


def render_program(parameters):
    if type(parameters) is not dict or set(parameters) != {'A', 'B', 'R'}:
        raise ValueError('invalid program parameter keys')
    if any(type(parameters[key]) is not int or not -9 <= parameters[key] <= 9 for key in ('A', 'B')):
        raise ValueError('initial parameters must be integers in -9..9')
    if type(parameters['R']) is not int or parameters['R'] not in (0, 1):
        raise ValueError('predicate residue must be 0 or 1')
    return (f"a = {parameters['A']}\nb = {parameters['B']}\n"
            "a = a + b\nb = a - b\na = a + b\n"
            f"result = (a % 2 == {parameters['R']})\n")


def validate_program(source):
    """Validate the full exact AST, including signed initial literals, before exec."""
    if type(source) is not str or not 0 < len(source.encode('utf-8')) <= 4096:
        raise ValueError('program source size bound')
    try:
        tree = ast.parse(source)
        if len(tree.body) != 6 or len(source.splitlines()) != 6:
            raise ValueError('program must have exactly six assignments')
        def signed_initial(node):
            if isinstance(node, ast.Constant) and type(node.value) is int:
                return node.value
            if (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub)
                    and isinstance(node.operand, ast.Constant) and type(node.operand.value) is int
                    and node.operand.value > 0):
                return -node.operand.value
            raise ValueError('only signed integer literals may initialize state')
        parameters = {'A': signed_initial(tree.body[0].value),
                      'B': signed_initial(tree.body[1].value)}
        rhs = tree.body[5].value.comparators[0]
        if not isinstance(rhs, ast.Constant) or type(rhs.value) is not int:
            raise ValueError('noninteger predicate residue')
        parameters['R'] = rhs.value
        expected = ast.parse(render_program(parameters))
        if ast.dump(tree, include_attributes=False) != ast.dump(expected, include_attributes=False):
            raise ValueError('AST differs from fixed allowlisted program')
    except (SyntaxError, AttributeError, IndexError, KeyError, TypeError, RecursionError) as error:
        raise ValueError('invalid program AST') from error
    return tree, parameters


def _bounded_integer(value):
    if type(value) is not int or abs(value) > MAX_MAGNITUDE:
        raise ValueError('integer magnitude/type bound')
    return value


def _run_validated_statement(statement, previous):
    """Internal execution primitive; callers first validate the entire source AST."""
    maximum = 0
    def bound(value):
        nonlocal maximum
        _bounded_integer(value)
        maximum = max(maximum, abs(value))
        return value
    for key, value in previous.items():
        if key == 'result':
            if type(value) is not bool:
                raise ValueError('result must be Boolean')
        else:
            bound(value)

    class Instrument(ast.NodeTransformer):
        def wrap(self, node):
            self.generic_visit(node)
            return ast.copy_location(ast.Call(func=ast.Name(id='_bound', ctx=ast.Load()),
                                              args=[node], keywords=[]), node)
        visit_BinOp = wrap
        visit_UnaryOp = wrap

        def visit_Constant(self, node):
            return ast.copy_location(ast.Call(func=ast.Name(id='_bound', ctx=ast.Load()),
                                              args=[node], keywords=[]), node)

    tree = ast.fix_missing_locations(Instrument().visit(ast.Module(
        body=[copy.deepcopy(statement)], type_ignores=[])))
    state = dict(previous)
    exec(compile(tree, '<cycle09-bounded-step>', 'exec'), {'__builtins__': {}, '_bound': bound}, state)
    for key, value in state.items():
        if key == 'result':
            if type(value) is not bool:
                raise ValueError('result must be Boolean')
        else:
            bound(value)
    return state, maximum


def python_truth(source):
    tree, _ = validate_program(source)
    state, rows, maximum = {}, [], 0
    for step, statement in enumerate(tree.body, 1):
        state, observed_max = _run_validated_statement(statement, state)
        rows.append({'step': step, 'state': dict(state)})
        maximum = max(maximum, observed_max)
    original = {}
    exec(compile(tree, '<cycle09-validated>', 'exec'), {'__builtins__': {}}, original)
    if original != state or type(state.get('result')) is not bool:
        raise RuntimeError('instrumented/original truth discrepancy')
    return {'rows': rows, 'answer': state['result'], 'final_state': state,
            'ast_dump': ast.dump(tree, include_attributes=False),
            'max_abs_intermediate': maximum, 'executed_statements': 6}


def validate_certificate(certificate):
    if type(certificate) is not dict or set(certificate) != {'rows'}:
        raise ValueError('certificate must contain exactly rows')
    rows = certificate['rows']
    if type(rows) is not list or len(rows) != 6:
        raise ValueError('certificate must contain six rows')
    for step, row in enumerate(rows, 1):
        if type(row) is not dict or set(row) != {'step', 'state'}:
            raise ValueError('invalid certificate row keys')
        if type(row['step']) is not int or row['step'] != step:
            raise ValueError('certificate steps must be integers 1..6 in order')
        state = row['state']
        expected_keys = {'a'} if step == 1 else {'a', 'b', 'result'} if step == 6 else {'a', 'b'}
        if type(state) is not dict or set(state) != expected_keys:
            raise ValueError('certificate must record the entire defined state')
        for key, value in state.items():
            if key == 'result':
                if type(value) is not bool:
                    raise ValueError('recorded result must be Boolean')
            else:
                _bounded_integer(value)
    return certificate


def parse_certificate(text):
    return validate_certificate(parse_json(text))


def check_certificate(source, certificate):
    tree, _ = validate_program(source)
    validate_certificate(certificate)
    previous, transitions, first = {}, [], None
    for step, (statement, row) in enumerate(zip(tree.body, certificate['rows']), 1):
        expected, _ = _run_validated_statement(statement, previous)
        valid = expected == row['state']
        if not valid and first is None:
            first = step
        transitions.append({'step': step, 'valid': valid, 'expected_state': expected,
                            'submitted_state': copy.deepcopy(row['state'])})
        # Local transition consistency follows the submitted certificate's state.
        previous = row['state']
    return {'valid': first is None, 'first_invalid_step': first, 'transitions': transitions}


def _certificate_variants(source, truth):
    tree, _ = validate_program(source)
    valid = {'rows': copy.deepcopy(truth['rows'])}
    propagated = {'rows': copy.deepcopy(truth['rows'][:3])}
    state = propagated['rows'][2]['state']
    state['a'] = _bounded_integer(state['a'] + 1)
    for step, statement in enumerate(tree.body[3:], 4):
        state, _ = _run_validated_statement(statement, state)
        propagated['rows'].append({'step': step, 'state': dict(state)})
    flipped = copy.deepcopy(valid)
    flipped['rows'][-1]['state']['result'] = not flipped['rows'][-1]['state']['result']
    return {'V': valid, 'I': propagated, 'F': flipped}


def _valid_id(value):
    return type(value) is str and ID_PATTERN.fullmatch(value) is not None


def validate_payload(payload):
    if type(payload) is not dict or set(payload) != {'program', 'original_ids', 'reports'}:
        raise ValueError('payload has unexpected fields')
    validate_program(payload['program'])
    originals, reports = payload['original_ids'], payload['reports']
    if (type(originals) is not list or len(originals) != 3
            or not all(_valid_id(value) for value in originals) or len(set(originals)) != 3):
        raise ValueError('invalid original report IDs')
    if type(reports) is not list or len(reports) != 5:
        raise ValueError('payload must contain five report slots')
    seen = set()
    for index, report in enumerate(reports):
        if report is None:
            if index < 3:
                raise ValueError('original report cannot be empty')
            continue
        if type(report) is not dict or set(report) != {'report_id', 'root_id', 'certificate'}:
            raise ValueError('report has unexpected fields')
        if not _valid_id(report['report_id']) or not _valid_id(report['root_id']) or report['report_id'] in seen:
            raise ValueError('invalid/colliding report identity')
        seen.add(report['report_id'])
        validate_certificate(report['certificate'])
        if index < 3 and not (report['report_id'] == report['root_id'] == originals[index]):
            raise ValueError('original report/root identity mismatch')
    if (reports[3] is None) != (reports[4] is None):
        raise ValueError('empty slots must occur as a pair')
    if reports[3] is not None:
        roots = {r['root_id']: r for r in reports[:3]}
        if reports[3]['root_id'] != reports[4]['root_id']:
            raise ValueError('repeat slots must copy the same root')
        for report in reports[3:]:
            if (report['root_id'] not in roots or canonical_json(report['certificate'])
                    != canonical_json(roots[report['root_id']]['certificate'])):
                raise ValueError('copied certificate payload differs from its root')
    return payload


def _reference_policies(order, ids):
    truth = {report_id: label == 'V' for label, report_id in zip(order, ids)}
    policies = {}
    for name, decisions in (
            ('always_valid', {key: True for key in truth}),
            ('always_invalid', {key: False for key in truth}),
            ('exact_checker', dict(truth))):
        policies[name] = {'decisions': decisions,
                          'correct': sum(decisions[key] is value for key, value in truth.items()),
                          'valid': 3, 'planned': 3}
    return policies


def construct_fixture(parameters, private_order, report_ids):
    """Synthetic-testable assembly. No random draws and no replacement search."""
    if type(private_order) is not list or sorted(private_order) != sorted(LABELS):
        raise ValueError('invalid private certificate order')
    if (type(report_ids) is not list or len(report_ids) != 5
            or not all(_valid_id(value) for value in report_ids)):
        raise ValueError('invalid report ID draws')
    if len(set(report_ids)) != 5:
        raise ValueError('report ID collision; no replacement draw')
    program = render_program(parameters)
    truth = python_truth(program)
    certificates = _certificate_variants(program, truth)
    checks = {label: check_certificate(program, cert) for label, cert in certificates.items()}
    answers = {label: cert['rows'][-1]['state']['result'] for label, cert in certificates.items()}
    negative = {
        'whole_certificate_validity': {label: check['valid'] for label, check in checks.items()},
        'first_invalid_step': {label: check['first_invalid_step'] for label, check in checks.items()},
        'final_answers': answers,
        'I_final_a_delta': certificates['I']['rows'][-1]['state']['a'] - truth['final_state']['a'],
        'I_parity_preserved': answers['I'] is answers['V'],
        'F_answer_flipped': answers['F'] is not answers['V']}
    if (negative['whole_certificate_validity'] != {'V': True, 'I': False, 'F': False}
            or negative['first_invalid_step'] != {'V': None, 'I': 3, 'F': 6}
            or negative['I_final_a_delta'] != 2 or not negative['I_parity_preserved']
            or not negative['F_answer_flipped']
            or [t['valid'] for t in checks['I']['transitions']] != [True, True, False, True, True, True]):
        raise RuntimeError('fixed certificate negative-control audit failed')
    originals = [{'report_id': report_ids[index], 'root_id': report_ids[index],
                  'certificate': copy.deepcopy(certificates[label])}
                 for index, label in enumerate(private_order)]
    false_root = report_ids[private_order.index('F')]
    packets = []
    for packet_id in ('base', 'repeat'):
        reports = copy.deepcopy(originals)
        reports.extend([None, None] if packet_id == 'base' else [
            {'report_id': report_id, 'root_id': false_root,
             'certificate': copy.deepcopy(certificates['F'])} for report_id in report_ids[3:]])
        payload = canonical_json(validate_payload({
            'program': program, 'original_ids': report_ids[:3], 'reports': reports}))
        packets.append({'packet_id': packet_id, 'payload': payload,
                        'payload_sha256': sha256_bytes(payload.encode('utf-8'))})
    return {'schema_version': 1, 'program': program,
            'program_sha256': sha256_bytes(program.encode('utf-8')),
            'generation': {'parameter_seed': PARAMETER_SEED, 'identity_seed': IDENTITY_SEED,
                           'parameters': dict(parameters), 'private_order': list(private_order),
                           'report_ids': list(report_ids), 'candidate_attempts': 1, 'exclusions': []},
            'python_truth': truth, 'certificates': certificates, 'certificate_checks': checks,
            'certificate_sha256': {label: sha256_bytes(canonical_json(cert).encode('utf-8'))
                                   for label, cert in certificates.items()},
            'packets': packets, 'negative_control': negative,
            'reference_policies': {name: _reference_policies(private_order, report_ids[:3])
                                   for name in ('base', 'repeat')}}


def build_fixture():
    """The sole actual seeded draw; only explicit preparation calls this."""
    parameters_rng = random.Random(PARAMETER_SEED)
    parameters = {'A': parameters_rng.randint(-9, 9), 'B': parameters_rng.randint(-9, 9),
                  'R': parameters_rng.randrange(2)}
    identity_rng = random.Random(IDENTITY_SEED)
    order = list(LABELS)
    identity_rng.shuffle(order)
    ids = ['r_' + format(identity_rng.getrandbits(64), '016x') for _ in range(5)]
    return construct_fixture(parameters, order, ids)


def readable_cases(fixture):
    lines = ['# Cycle09 certificate cases', '',
             'Local construction labels and checker verdicts below are evaluator metadata.',
             'Only the separately serialized packet files are candidate solver inputs.', '',
             '## Program', '', '~~~python', fixture['program'].rstrip(), '~~~', '']
    for label in LABELS:
        check = fixture['certificate_checks'][label]
        lines.extend([f'## Certificate {label}', '',
                      '| Step | Recorded complete state | Locally valid transition |',
                      '| --- | --- | --- |'])
        for row, transition in zip(fixture['certificates'][label]['rows'], check['transitions']):
            lines.append(f"| {row['step']} | {canonical_json(row['state']).strip()} | "
                         f"{str(transition['valid']).lower()} |")
        lines.extend(['', f"Whole-certificate validity: {str(check['valid']).lower()}. "
                      f"First invalid step: {check['first_invalid_step']}.", ''])
    lines.extend(['## Fixed reference policies', '',
                  '| Packet | Policy | Correct / valid / planned original judgments |',
                  '| --- | --- | --- |'])
    for packet in ('base', 'repeat'):
        for name in ('always_valid', 'always_invalid', 'exact_checker'):
            policy = fixture['reference_policies'][packet][name]
            lines.append(f"| {packet} | {name} | {policy['correct']} / {policy['valid']} / {policy['planned']} |")
    lines.extend(['', 'These are six diagnostic judgments from one program construction.',
                  'No empirical solver outcome or provider launch is implied.', ''])
    return '\n'.join(lines)


def _source_hashes():
    return {name: _file_sha(ROOT / name) for name in SOURCE_FILES}


def _python_identity():
    executable = Path(sys.executable).resolve()
    return {'executable': str(executable), 'executable_sha256': _file_sha(executable),
            'version': sys.version, 'implementation': platform.python_implementation()}


def _load_checker():
    spec = importlib.util.spec_from_file_location('cycle09_independent_checker', ROOT / CHECKER)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    return checker


def prepare_fixture(output_directory, preparation_argv=None):
    output = Path(output_directory)
    if output.exists():
        raise FileExistsError(output)
    start = time.monotonic()
    sources, identity = _source_hashes(), _python_identity()
    checker = _load_checker()
    if not callable(getattr(checker, 'verify_fixture', None)):
        raise ValueError('independent fixture checker unavailable')
    fixture = build_fixture()
    independent = checker.verify_fixture(fixture)
    if sources != _source_hashes() or identity != _python_identity():
        raise ValueError('source/interpreter changed during preparation')
    artifacts = {'fixture.json': canonical_json(fixture).encode('utf-8'),
                 'independent-check.json': canonical_json(independent).encode('utf-8'),
                 'cases.md': readable_cases(fixture).encode('utf-8'),
                 'program.py': fixture['program'].encode('utf-8')}
    artifacts.update({'certificates/' + label + '.json': canonical_json(cert).encode('utf-8')
                      for label, cert in fixture['certificates'].items()})
    artifacts.update({'packets/' + packet['packet_id'] + '.json': packet['payload'].encode('utf-8')
                      for packet in fixture['packets']})
    manifest = {'schema_version': 1, 'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
                'source_sha256_start': sources, 'source_sha256_end': _source_hashes(),
                'python': identity, 'preparation_argv': list(sys.argv if preparation_argv is None else preparation_argv),
                'local_generation_truth_wall_seconds': time.monotonic() - start,
                'artifact_sha256': {name: sha256_bytes(data) for name, data in artifacts.items()},
                'empirical_launch_authorized': False}
    output.mkdir(parents=True, exist_ok=False)
    (output / 'certificates').mkdir()
    (output / 'packets').mkdir()
    for name, data in artifacts.items():
        with (output / name).open('xb') as stream:
            stream.write(data)
    with (output / 'manifest.json').open('x', encoding='utf-8') as stream:
        stream.write(canonical_json(manifest))
    return fixture, manifest


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
    required = {'fixture.json', 'independent-check.json', 'cases.md', 'program.py',
                'certificates/V.json', 'certificates/I.json', 'certificates/F.json',
                'packets/base.json', 'packets/repeat.json'}
    if set(manifest['artifact_sha256']) != required:
        raise ValueError('artifact inventory mismatch')
    for name, digest in manifest['artifact_sha256'].items():
        if _file_sha(directory / name) != digest:
            raise ValueError('artifact hash mismatch')
    fixture = _read_json(directory / 'fixture.json')
    if ((directory / 'program.py').read_bytes() != fixture['program'].encode('utf-8')
            or (directory / 'cases.md').read_bytes() != readable_cases(fixture).encode('utf-8')):
        raise ValueError('readable program/cases custody mismatch')
    for label, certificate in fixture['certificates'].items():
        if (directory / 'certificates' / (label + '.json')).read_bytes() != canonical_json(certificate).encode('utf-8'):
            raise ValueError('certificate bytes mismatch')
    for packet in fixture['packets']:
        if (directory / 'packets' / (packet['packet_id'] + '.json')).read_bytes() != packet['payload'].encode('utf-8'):
            raise ValueError('packet bytes mismatch')
    _load_checker().verify_fixture(fixture)
    return fixture, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prepare = sub.add_parser('prepare')
    prepare.add_argument('--output', required=True)
    validate = sub.add_parser('validate')
    validate.add_argument('--prepared', required=True)
    validate.add_argument('--manifest-sha256')
    args = parser.parse_args(argv)
    if args.command == 'prepare':
        fixture, _ = prepare_fixture(args.output)
    else:
        fixture, _ = validate_fixture_custody(args.prepared, args.manifest_sha256)
    print(canonical_json({'packets': len(fixture['packets']),
                          'negative_control': fixture['negative_control'],
                          'empirical_launch_authorized': False}), end='')


if __name__ == '__main__':
    main()
