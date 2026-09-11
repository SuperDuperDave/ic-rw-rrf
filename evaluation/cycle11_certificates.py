"""Cycle11 submission selection, preserving the sealed cycle10 parent artifacts."""
import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import re
import sys
import time

if __package__:
    from . import cycle10_certificates as previous
else:
    import cycle10_certificates as previous

ROOT = Path(__file__).resolve().parents[1]
CODE = 'evaluation/cycle11_certificates.py'
TESTS = 'evaluation/tests/test_cycle11_certificates.py'
CHECKER = '_sessions/tools/check_cycle11_evidence.py'
CHECKER_TESTS = '_sessions/tools/tests/test_cycle11_audit.py'
DESIGN = '_sessions/cycles/2026-09-11-cycle11-evidence-selection-design.md'
PROTOCOL = '_sessions/cycles/2026-09-11-cycle11-local-protocol.md'
SOURCE_FILES = previous.SOURCE_FILES + (CODE, TESTS, CHECKER, CHECKER_TESTS, DESIGN, PROTOCOL)
PARENT_DIRECTORY = ROOT / 'results/cycle10-2026-09-11/prepared'
PARENT_MANIFEST_SHA = '6647f0ae806ada137668252ffe03839caeab3e13ae2ccf8127dcc6b67cf203cd'
REQUEST_ORDER = ORDER = ('R0-A', 'R1-B', 'R0-B', 'R1-A')
PLACEMENTS = {'R0-A': ('F', 'V', 'F', 'F'), 'R1-B': ('V', 'V', 'V', 'F'),
              'R0-B': ('V', 'F', 'V', 'V'), 'R1-A': ('F', 'F', 'F', 'V')}
ANSWER_POLICIES = ('exact_replay', 'majority', 'minority', 'position_1', 'position_2',
                   'position_3', 'position_4', 'always_true', 'always_false',
                   'deduplicated_root_vote')
VALIDITY_POLICIES = ('exact_checker', 'endpoint_matches_truth', 'always_valid', 'always_invalid')
ID_DOMAIN = b'cycle11-submission\n'
ID_PATTERN = re.compile(r's_[0-9a-f]{16}\Z')
base = previous.previous
canonical_json = previous.canonical_json
parse_json = previous.parse_json
sha256_bytes = previous.sha256_bytes
_read_json, _file_sha, _python_identity = previous._read_json, previous._file_sha, previous._python_identity


def submission_id(program, root_id, instance_ordinal):
    if not base._valid_id(root_id) or type(instance_ordinal) is not int or not 1 <= instance_ordinal <= 3:
        raise ValueError('invalid submission identity tuple')
    content = canonical_json({'program': program, 'root_id': root_id,
                              'instance_ordinal': instance_ordinal}).encode('utf-8')
    return 's_' + sha256_bytes(ID_DOMAIN + content)[:16]


def validate_payload(payload):
    if type(payload) is not dict or set(payload) != {'program', 'submission_ids', 'reports'}:
        raise ValueError('unexpected packet fields')
    base.validate_program(payload['program'])
    ids, reports = payload['submission_ids'], payload['reports']
    if (type(ids) is not list or len(ids) != 4
            or not all(type(rid) is str and ID_PATTERN.fullmatch(rid) for rid in ids)
            or len(set(ids)) != 4):
        raise ValueError('four distinct submission IDs required')
    if type(reports) is not list or len(reports) != 5 or reports[-1] is not None:
        raise ValueError('four submissions and a trailing empty slot required')
    root_certificates, counts = {}, Counter()
    for rid, report in zip(ids, reports[:4]):
        if type(report) is not dict or set(report) != {'report_id', 'root_id', 'certificate'}:
            raise ValueError('unexpected submission fields')
        if report['report_id'] != rid or not base._valid_id(report['root_id']):
            raise ValueError('submission/root identity mismatch')
        base.validate_certificate(report['certificate'])
        root = report['root_id']
        encoded = canonical_json(report['certificate'])
        if root in root_certificates and root_certificates[root] != encoded:
            raise ValueError('copied root has different certificate bytes')
        root_certificates[root] = encoded
        counts[root] += 1
    if sorted(counts.values()) != [1, 3]:
        raise ValueError('packet must have two roots with 3:1 submission counts')
    return payload


def reference_maps(payload):
    reports = payload['reports'][:4]
    truth = base.python_truth(payload['program'])['answer']
    endpoints = [report['certificate']['rows'][-1]['state']['result'] for report in reports]
    correct = {report['report_id']: base.check_certificate(
        payload['program'], report['certificate'])['valid'] for report in reports}
    root_endpoints = {report['root_id']: endpoint for report, endpoint in zip(reports, endpoints)}
    majority = sum(endpoints) > 2
    deduplicated = (None if 2 * sum(root_endpoints.values()) == len(root_endpoints)
                    else 2 * sum(root_endpoints.values()) > len(root_endpoints))
    answers = {'exact_replay': truth, 'majority': majority, 'minority': not majority,
               **{'position_' + str(i + 1): value for i, value in enumerate(endpoints)},
               'always_true': True, 'always_false': False, 'deduplicated_root_vote': deduplicated}
    validity = {'exact_checker': correct,
                'endpoint_matches_truth': {report['report_id']: endpoint is truth
                                           for report, endpoint in zip(reports, endpoints)},
                'always_valid': {rid: True for rid in correct},
                'always_invalid': {rid: False for rid in correct}}
    return {
        'answer': {name: {'answer': answers[name],
                          'correct': int(answers[name] is not None and answers[name] is truth),
                          'answered': int(answers[name] is not None), 'planned': 1,
                          'abstained': int(answers[name] is None)} for name in ANSWER_POLICIES},
        'validity': {name: {'decisions': validity[name],
                            'correct': sum(validity[name][rid] is value for rid, value in correct.items()),
                            'valid': 4, 'planned': 4} for name in VALIDITY_POLICIES}}


def construct_fixture(parent_fixture):
    """Compose submitted copies from exact parent records; never rebuild the parent."""
    previous._load_checker().verify_fixture(parent_fixture)
    programs = copy.deepcopy(parent_fixture['programs'])
    by_program = {program['program_id']: program for program in programs}
    packets, references, tuple_ids, id_tuples, balance = [], {}, {}, {}, Counter()
    for packet_id in REQUEST_ORDER:
        program_id, regime = packet_id.split('-')
        program = by_program[program_id]
        order, occurrences, reports = PLACEMENTS[packet_id], Counter(), []
        for position, label in enumerate(order):
            root = program['report_ids'][label]
            occurrences[root] += 1
            identity = (program['program'], root, occurrences[root])
            rid = submission_id(*identity)
            if rid in id_tuples and id_tuples[rid] != identity:
                raise ValueError('distinct submission tuples collide')
            if identity in tuple_ids and tuple_ids[identity] != rid:
                raise ValueError('same submission tuple changes identity')
            tuple_ids[identity], id_tuples[rid] = rid, identity
            certificate = copy.deepcopy(program['certificates'][label])
            if sha256_bytes(canonical_json(certificate).encode('utf-8')) != program['certificate_sha256'][label]:
                raise ValueError('parent certificate bytes changed')
            reports.append({'report_id': rid, 'root_id': root, 'certificate': certificate})
            balance[(position, program['python_truth']['answer'], label)] += 1
        payload_object = validate_payload({'program': program['program'],
            'submission_ids': [report['report_id'] for report in reports], 'reports': reports + [None]})
        payload = canonical_json(payload_object)
        packets.append({'packet_id': packet_id, 'program_id': program_id, 'private_regime': regime,
                        'private_order': list(order), 'payload': payload,
                        'payload_sha256': sha256_bytes(payload.encode('utf-8')),
                        'payload_bytes': len(payload.encode('utf-8'))})
        references[packet_id] = reference_maps(payload_object)
        expected_valid = 1 if regime == 'A' else 3
        if sum(references[packet_id]['validity']['exact_checker']['decisions'].values()) != expected_valid:
            raise ValueError('regime validity count mismatch')
    if len(tuple_ids) != 12 or len(id_tuples) != 12 or len(balance) != 16 or set(balance.values()) != {1}:
        raise ValueError('instance or position/truth balance mismatch')
    for first, second in (('V', 'F'), ('F', 'V')):
        a, b = by_program['R0'], by_program['R1']
        if (canonical_json(a['certificates'][first]) != canonical_json(b['certificates'][second])
                or a['report_ids'][first] == b['report_ids'][second]):
            raise ValueError('program-conditioned root identity mismatch')
    answer_totals = {name: {
        **{key: sum(references[pid]['answer'][name][key] for pid in REQUEST_ORDER)
           for key in ('correct', 'answered', 'planned', 'abstained')},
        'vector': [references[pid]['answer'][name]['answer'] for pid in REQUEST_ORDER]}
        for name in ANSWER_POLICIES}
    validity_totals = {name: {
        **{key: sum(references[pid]['validity'][name][key] for pid in REQUEST_ORDER)
           for key in ('correct', 'valid', 'planned')},
        'vector': [references[packet['packet_id']]['validity'][name]['decisions'][rid]
                   for packet in packets for rid in parse_json(packet['payload'])['submission_ids']]}
        for name in VALIDITY_POLICIES}
    for name, policy in answer_totals.items():
        target = 4 if name == 'exact_replay' else 0 if name == 'deduplicated_root_vote' else 2
        if (policy['correct'] != target or policy['planned'] != 4
                or policy['answered'] != (0 if name == 'deduplicated_root_vote' else 4)
                or policy['abstained'] != (4 if name == 'deduplicated_root_vote' else 0)):
            raise ValueError('answer reference count discrepancy')
    if ({name: policy['correct'] for name, policy in validity_totals.items()}
            != {'exact_checker': 16, 'endpoint_matches_truth': 16, 'always_valid': 8, 'always_invalid': 8}
            or validity_totals['exact_checker']['vector'] != validity_totals['endpoint_matches_truth']['vector']):
        raise ValueError('validity reference count/vector discrepancy')
    return {
        'schema_version': 1, 'programs': programs, 'packets': packets,
        'request_order': list(REQUEST_ORDER),
        'generation': {'program_count': 2, 'root_certificate_count': 4, 'packet_count': 4,
                       'distinct_submission_id_count': 12, 'submitted_instances': 16,
                       'rng_used': False, 'construction_attempts': 1, 'exclusions': []},
        'parent_custody': {'fixture_sha256': sha256_bytes(canonical_json(parent_fixture).encode('utf-8')),
                           'manifest_sha256': None, 'artifact_sha256': {}},
        'reference_policies': references,
        'policy_totals': {'answer': answer_totals, 'validity': validity_totals},
        'audit': {'source_and_certificate_bytes_preserved': True,
                  'program_conditioned_roots_preserved': True, 'instance_identity_verified': True,
                  'regime_position_truth_balance_verified': True, 'reference_vectors_verified': True,
                  'payload_byte_lengths': {p['packet_id']: p['payload_bytes'] for p in packets}}}


def _load_parent():
    return previous.validate_fixture_custody(PARENT_DIRECTORY, PARENT_MANIFEST_SHA)


def build_fixture():
    parent, manifest = _load_parent()
    fixture = construct_fixture(parent)
    fixture['parent_custody'].update(manifest_sha256=PARENT_MANIFEST_SHA,
                                     artifact_sha256=manifest['artifact_sha256'])
    return fixture


def readable_cases(fixture):
    lines = ['# Cycle11 evidence-selection cases', '',
             'Private labels and exact checks below are evaluator metadata.',
             'The sealed packets are candidate solver inputs, not observed responses.', '',
             '| Request | Packet | Private slots | Program answer | Bytes |',
             '| --- | --- | --- | --- | --- |']
    programs = {p['program_id']: p for p in fixture['programs']}
    for index, packet in enumerate(fixture['packets'], 1):
        truth = programs[packet['program_id']]['python_truth']['answer']
        lines.append(f"| {index} | {packet['packet_id']} | {', '.join(packet['private_order'])} | "
                     f"{str(truth).lower()} | {packet['payload_bytes']} |")
    for packet in fixture['packets']:
        lines.extend(['', '## ' + packet['packet_id'], '',
                      '| Slot | Submission ID | Parent root ID | Valid | Endpoint |',
                      '| --- | --- | --- | --- | --- |'])
        for position, report in enumerate(parse_json(packet['payload'])['reports'][:4], 1):
            validity = fixture['reference_policies'][packet['packet_id']]['validity']['exact_checker']['decisions'][report['report_id']]
            endpoint = report['certificate']['rows'][-1]['state']['result']
            lines.append(f"| {position} | {report['report_id']} | {report['root_id']} | "
                         f"{str(validity).lower()} | {str(endpoint).lower()} |")
    lines.extend(['', '## Answer references', '',
                  '| Policy | Correct / answered / planned | Abstentions | Ordered answer vector |',
                  '| --- | --- | --- | --- |'])
    for name in ANSWER_POLICIES:
        policy = fixture['policy_totals']['answer'][name]
        lines.append(f"| {name} | {policy['correct']} / {policy['answered']} / {policy['planned']} | "
                     f"{policy['abstained']} | {canonical_json(policy['vector']).strip()} |")
    lines.extend(['', '## Validity references', '',
                  '| Policy | Correct / valid / planned | Ordered validity vector |',
                  '| --- | --- | --- |'])
    for name in VALIDITY_POLICIES:
        policy = fixture['policy_totals']['validity'][name]
        lines.append(f"| {name} | {policy['correct']} / {policy['valid']} / {policy['planned']} | "
                     f"{canonical_json(policy['vector']).strip()} |")
    lines.extend(['', 'Root deduplication abstains on all four 1:1 ties; it does not make four errors.',
                  'Copies are artifact instances, not independent acquisitions or independent samples.',
                  'The parent programs and all parent certificates remain unchanged.',
                  'A passing local audit does not authorize empirical calls.', ''])
    return '\n'.join(lines)


def _source_hashes():
    return {name: _file_sha(ROOT / name) for name in SOURCE_FILES}


def _load_checker():
    spec = importlib.util.spec_from_file_location('cycle11_independent_checker', ROOT / CHECKER)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    return checker


def _artifact_data(fixture, parent_bytes, parent_manifest_bytes, independent):
    artifacts = {'fixture.json': canonical_json(fixture).encode('utf-8'),
                 'independent-check.json': canonical_json(independent).encode('utf-8'),
                 'cases.md': readable_cases(fixture).encode('utf-8'),
                 'parent-fixture.json': parent_bytes, 'parent-manifest.json': parent_manifest_bytes}
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
    parent, parent_manifest = _load_parent()
    parent_bytes = (PARENT_DIRECTORY / 'fixture.json').read_bytes()
    parent_manifest_bytes = (PARENT_DIRECTORY / 'manifest.json').read_bytes()
    if (parent_bytes != canonical_json(parent).encode('utf-8')
            or sha256_bytes(parent_manifest_bytes) != PARENT_MANIFEST_SHA):
        raise ValueError('parent manifest/fixture byte mismatch')
    fixture = construct_fixture(parent)
    fixture['parent_custody'].update(manifest_sha256=PARENT_MANIFEST_SHA,
                                     artifact_sha256=parent_manifest['artifact_sha256'])
    independent = checker.verify_fixture(fixture, parent)
    if sources != _source_hashes() or identity != _python_identity():
        raise ValueError('source/interpreter changed during preparation')
    _load_parent()  # Parent artifact/source custody must also survive preparation.
    artifacts = _artifact_data(fixture, parent_bytes, parent_manifest_bytes, independent)
    manifest = {'schema_version': 1, 'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
                'source_sha256_start': sources, 'source_sha256_end': _source_hashes(),
                'python': identity, 'preparation_argv': list(sys.argv if preparation_argv is None else preparation_argv),
                'local_generation_truth_wall_seconds': time.monotonic() - start,
                'parent_custody': fixture['parent_custody'],
                'parent_source_sha256': parent_manifest['source_sha256_start'],
                'artifact_sha256': {name: sha256_bytes(data) for name, data in artifacts.items()},
                'empirical_launch_authorized': False}
    output.mkdir(parents=True, exist_ok=False)
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
    parent, parent_manifest = _load_parent()
    parent_bytes = (directory / 'parent-fixture.json').read_bytes()
    parent_manifest_bytes = (directory / 'parent-manifest.json').read_bytes()
    if (parent_bytes != canonical_json(parent).encode('utf-8')
            or sha256_bytes(parent_manifest_bytes) != PARENT_MANIFEST_SHA
            or manifest['parent_source_sha256'] != parent_manifest['source_sha256_start']):
        raise ValueError('parent copy/source custody mismatch')
    fixture = _read_json(directory / 'fixture.json')
    custody = {'fixture_sha256': sha256_bytes(parent_bytes), 'manifest_sha256': PARENT_MANIFEST_SHA,
               'artifact_sha256': parent_manifest['artifact_sha256']}
    if fixture['parent_custody'] != custody or manifest['parent_custody'] != custody:
        raise ValueError('parent linkage mismatch')
    _load_checker().verify_fixture(fixture, parent)
    independent = _read_json(directory / 'independent-check.json')
    expected = _artifact_data(fixture, parent_bytes, parent_manifest_bytes, independent)
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
    print(canonical_json({'packets': len(fixture['packets']),
                          'policy_totals': fixture['policy_totals'],
                          'empirical_launch_authorized': False}), end='')


if __name__ == '__main__':
    main()
