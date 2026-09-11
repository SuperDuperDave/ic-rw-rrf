"""Cycle10 fixed position/endpoint controls, composed from frozen cycle09 helpers."""
import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import time

if __package__:
    from . import cycle09_certificates as previous
else:
    import cycle09_certificates as previous


ROOT = Path(__file__).resolve().parents[1]
CODE = 'evaluation/cycle10_certificates.py'
TESTS = 'evaluation/tests/test_cycle10_certificates.py'
CHECKER = '_sessions/tools/check_cycle10_evidence.py'
CHECKER_TESTS = '_sessions/tools/tests/test_cycle10_audit.py'
DESIGN = '_sessions/cycles/2026-09-11-cycle10-discriminating-design.md'
PROTOCOL = '_sessions/cycles/2026-09-11-cycle10-local-protocol.md'
SOURCE_FILES = (CODE, TESTS, CHECKER, CHECKER_TESTS, DESIGN, PROTOCOL,
                'evaluation/cycle09_certificates.py', '_sessions/tools/check_cycle09_evidence.py')
LABELS = previous.LABELS
ORDERS = (('P1', ('V', 'I', 'F')), ('P2', ('F', 'V', 'I')), ('P3', ('I', 'F', 'V')))
REQUEST_ORDER = ('R0-P1', 'R1-P2', 'R0-P3', 'R1-P1', 'R0-P2', 'R1-P3')
POLICIES = ('exact_checker', 'always_valid', 'always_invalid', 'position_1',
            'position_2', 'position_3', 'endpoint_matches_truth', 'endpoint_boolean')
EXPECTED_TOTALS = dict(zip(POLICIES, (18, 6, 12, 10, 10, 10, 12, 9)))
ID_DOMAIN = b'cycle10-certificate\n'
canonical_json = previous.canonical_json
parse_json = previous.parse_json
sha256_bytes = previous.sha256_bytes
_read_json = previous._read_json
_file_sha = previous._file_sha
_python_identity = previous._python_identity
validate_payload = previous.validate_payload


def certificate_id(program, certificate):
    content = canonical_json({'program': program, 'certificate': certificate}).encode('utf-8')
    return 'r_' + sha256_bytes(ID_DOMAIN + content)[:16]


def _policies(program, reports):
    correct = {report['report_id']: previous.check_certificate(
        program['program'], report['certificate'])['valid'] for report in reports}
    endpoints = {report['report_id']: report['certificate']['rows'][-1]['state']['result']
                 for report in reports}
    ids = [report['report_id'] for report in reports]
    predictions = {
        'exact_checker': correct, 'always_valid': {rid: True for rid in ids},
        'always_invalid': {rid: False for rid in ids},
        **{'position_' + str(position + 1): {rid: index == position for index, rid in enumerate(ids)}
           for position in range(3)},
        'endpoint_matches_truth': {rid: answer is program['python_truth']['answer']
                                   for rid, answer in endpoints.items()},
        'endpoint_boolean': endpoints}
    return {name: {'decisions': predictions[name],
                   'correct': sum(predictions[name][rid] is correct[rid] for rid in ids),
                   'valid': 3, 'planned': 3} for name in POLICIES}


def construct_fixture(A, B):
    """Explicit synthetic parameters; no RNG or alternative-parameter search."""
    programs, packets, policies, roots = [], [], {}, set()
    position_endpoints = Counter()
    for residue in (0, 1):
        parameters = {'A': A, 'B': B, 'R': residue}
        source = previous.render_program(parameters)
        truth = previous.python_truth(source)
        certificates = previous._certificate_variants(source, truth)
        checks = {label: previous.check_certificate(source, cert) for label, cert in certificates.items()}
        if ({label: c['valid'] for label, c in checks.items()} != {'V': True, 'I': False, 'F': False}
                or {label: c['first_invalid_step'] for label, c in checks.items()} != {'V': None, 'I': 3, 'F': 6}
                or [row['valid'] for row in checks['I']['transitions']] != [True, True, False, True, True, True]
                or certificates['I']['rows'][-1]['state']['a'] - truth['final_state']['a'] != 2
                or certificates['I']['rows'][-1]['state']['result'] is not truth['answer']
                or certificates['F']['rows'][-1]['state']['result'] is truth['answer']):
            raise ValueError('certificate negative-control discrepancy')
        ids = {label: certificate_id(source, certificate) for label, certificate in certificates.items()}
        if len(set(ids.values())) != 3 or roots.intersection(ids.values()):
            raise ValueError('root ID collision; construction stops')
        roots.update(ids.values())
        reports = {label: {'report_id': ids[label], 'root_id': ids[label],
                           'certificate': certificates[label]} for label in LABELS}
        program = {'program_id': 'R' + str(residue), 'parameters': parameters, 'program': source,
                   'program_sha256': sha256_bytes(source.encode('utf-8')), 'python_truth': truth,
                   'certificates': certificates, 'certificate_checks': checks, 'report_ids': ids,
                   'certificate_sha256': {label: sha256_bytes(canonical_json(cert).encode('utf-8'))
                                          for label, cert in certificates.items()},
                   'report_sha256': {label: sha256_bytes(canonical_json(report).encode('utf-8'))
                                     for label, report in reports.items()}}
        programs.append(program)
        for permutation, order in ORDERS:
            ordered_reports = [copy.deepcopy(reports[label]) for label in order]
            for position, label in enumerate(order):
                position_endpoints[(label, position, certificates[label]['rows'][-1]['state']['result'])] += 1
            packet_id = program['program_id'] + '-' + permutation
            payload = canonical_json(validate_payload({
                'program': source, 'original_ids': [ids[label] for label in order],
                'reports': ordered_reports + [None, None]}))
            packets.append({'packet_id': packet_id, 'program_id': program['program_id'],
                            'private_order': list(order), 'payload': payload,
                            'payload_sha256': sha256_bytes(payload.encode('utf-8')),
                            'payload_bytes': len(payload.encode('utf-8'))})
            policies[packet_id] = _policies(program, ordered_reports)
    if programs[0]['program'].replace('== 0)', '== 1)', 1) != programs[1]['program']:
        raise ValueError('programs differ beyond R')
    for label in LABELS:
        first = copy.deepcopy(programs[0]['certificates'][label])
        first['rows'][-1]['state']['result'] = not first['rows'][-1]['state']['result']
        if first != programs[1]['certificates'][label]:
            raise ValueError('R does not complement exactly the certificate endpoint')
    if (len(position_endpoints) != 18 or set(position_endpoints.values()) != {1}
            or len(roots) != 6):
        raise ValueError('position/endpoint or distinct-root balance discrepancy')
    by_id = {packet['packet_id']: previous.parse_json(packet['payload']) for packet in packets}
    vectors = {name: [policies[packet_id][name]['decisions'][rid]
                      for packet_id in REQUEST_ORDER for rid in by_id[packet_id]['original_ids']]
               for name in POLICIES}
    totals = {name: {'correct': sum(policies[packet_id][name]['correct'] for packet_id in REQUEST_ORDER),
                     'valid': 18, 'planned': 18,
                     'vector_differs_from_exact': vectors[name] != vectors['exact_checker']}
              for name in POLICIES}
    if ({name: total['correct'] for name, total in totals.items()} != EXPECTED_TOTALS
            or not all(totals[name]['vector_differs_from_exact'] for name in POLICIES[1:])):
        raise ValueError('reference policy score or vector discrepancy')
    return {'schema_version': 1,
            'generation': {'parameters': {'A': A, 'B': B}, 'program_count': 2,
                           'root_certificate_count': 6, 'packet_count': 6, 'rng_used': False,
                           'candidate_attempts': 1, 'exclusions': []},
            'programs': programs, 'packets': packets, 'request_order': list(REQUEST_ORDER),
            'reference_policies': policies, 'policy_totals': totals,
            'audit': {'r_complement_verified': True, 'position_endpoint_balance': True,
                      'root_and_report_identity_verified': True,
                      'heuristic_vectors_distinct_from_exact': True,
                      'payload_byte_lengths': {p['packet_id']: p['payload_bytes'] for p in packets}}}


def build_fixture():
    """Render the actual prespecified panel only on coordinator invocation."""
    return construct_fixture(2, 3)


def readable_cases(fixture):
    lines = ['# Cycle10 position and endpoint controls', '',
             'Local labels and checks below are evaluator metadata. Only sealed packet files',
             'are candidate solver inputs. There are two programs and six root certificates.', '']
    for program in fixture['programs']:
        lines.extend(['## ' + program['program_id'], '', '~~~python', program['program'].rstrip(),
                      '~~~', '', '| Step | V complete state | I complete state | F complete state |',
                      '| --- | --- | --- | --- |'])
        for index in range(6):
            states = [canonical_json(program['certificates'][label]['rows'][index]['state']).strip()
                      for label in LABELS]
            lines.append('| ' + str(index + 1) + ' | ' + ' | '.join(states) + ' |')
        lines.extend(['', '| Certificate | Root ID | Valid | First invalid step |',
                      '| --- | --- | --- | --- |'])
        for label in LABELS:
            checked = program['certificate_checks'][label]
            lines.append(f"| {label} | {program['report_ids'][label]} | {str(checked['valid']).lower()} | "
                         f"{checked['first_invalid_step']} |")
        lines.append('')
    lines.extend(['## Packet order and exact UTF-8 bytes', '',
                  '| Request | Packet | Private slot order | Bytes | Difference from R0-P1 |',
                  '| --- | --- | --- | --- | --- |'])
    packets = {packet['packet_id']: packet for packet in fixture['packets']}
    baseline = packets['R0-P1']['payload_bytes']
    for index, packet_id in enumerate(fixture['request_order'], 1):
        packet = packets[packet_id]
        lines.append(f"| {index} | {packet_id} | {', '.join(packet['private_order'])} | "
                     f"{packet['payload_bytes']} | {packet['payload_bytes'] - baseline:+d} |")
    lines.extend(['', 'Equal slots or byte lengths do not establish equal native token exposure.', '',
                  '## Reference judgments', '',
                  '| Policy | Correct / valid / planned | Vector differs from exact checker |',
                  '| --- | --- | --- |'])
    for name in POLICIES:
        policy = fixture['policy_totals'][name]
        lines.append(f"| {name} | {policy['correct']} / {policy['valid']} / {policy['planned']} | "
                     f"{str(policy['vector_differs_from_exact']).lower()} |")
    lines.extend(['', 'These 18 planned judgments reuse six roots on two endpoint variants of one',
                  'arithmetic skeleton. They are not 18 independent cases or solver outcomes.',
                  'Any empirical phase requires its own execution freeze.', ''])
    return '\n'.join(lines)


def _source_hashes():
    return {name: _file_sha(ROOT / name) for name in SOURCE_FILES}


def _load_checker():
    spec = importlib.util.spec_from_file_location('cycle10_independent_checker', ROOT / CHECKER)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    return checker


def _artifact_data(fixture, independent):
    artifacts = {'fixture.json': canonical_json(fixture).encode('utf-8'),
                 'independent-check.json': canonical_json(independent).encode('utf-8'),
                 'cases.md': readable_cases(fixture).encode('utf-8')}
    for program in fixture['programs']:
        artifacts['programs/' + program['program_id'] + '.py'] = program['program'].encode('utf-8')
        for label, certificate in program['certificates'].items():
            artifacts['certificates/' + program['program_id'] + '-' + label + '.json'] = canonical_json(certificate).encode('utf-8')
    artifacts.update({'packets/' + packet['packet_id'] + '.json': packet['payload'].encode('utf-8')
                      for packet in fixture['packets']})
    return artifacts


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
    artifacts = _artifact_data(fixture, independent)
    manifest = {'schema_version': 1, 'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
                'source_sha256_start': sources, 'source_sha256_end': _source_hashes(),
                'python': identity, 'preparation_argv': list(sys.argv if preparation_argv is None else preparation_argv),
                'local_generation_truth_wall_seconds': time.monotonic() - start,
                'artifact_sha256': {name: sha256_bytes(data) for name, data in artifacts.items()},
                'empirical_launch_authorized': False}
    output.mkdir(parents=True, exist_ok=False)
    for subdirectory in ('programs', 'certificates', 'packets'):
        (output / subdirectory).mkdir()
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
    fixture = _read_json(directory / 'fixture.json')
    independent = _read_json(directory / 'independent-check.json')
    _load_checker().verify_fixture(fixture)
    expected = _artifact_data(fixture, independent)
    if set(manifest['artifact_sha256']) != set(expected):
        raise ValueError('artifact inventory mismatch')
    for name, data in expected.items():
        if (_file_sha(directory / name) != manifest['artifact_sha256'][name]
                or (directory / name).read_bytes() != data):
            raise ValueError('artifact hash/byte mismatch')
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
    print(canonical_json({'programs': len(fixture['programs']), 'packets': len(fixture['packets']),
                          'policy_totals': fixture['policy_totals'],
                          'empirical_launch_authorized': False}), end='')


if __name__ == '__main__':
    main()
