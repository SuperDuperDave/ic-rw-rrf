#!/usr/bin/env python3
"""Independent cycle10 local audit, reusing only the cycle09 AST interpreter.

No producer imports, program exec, provider calls, or fixture creation on import.
verify_fixture accepts synthetic constants; run enforces the frozen A=2,B=3.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/cycle10-2026-09-11/prepared'
CHECKER = '_sessions/tools/check_cycle10_evidence.py'
SOURCE_FILES = {
    CHECKER, '_sessions/tools/tests/test_cycle10_audit.py',
    'evaluation/cycle10_certificates.py', 'evaluation/tests/test_cycle10_certificates.py',
    '_sessions/cycles/2026-09-11-cycle10-discriminating-design.md',
    '_sessions/cycles/2026-09-11-cycle10-local-protocol.md',
    'evaluation/cycle09_certificates.py', '_sessions/tools/check_cycle09_evidence.py'}
SPEC = importlib.util.spec_from_file_location(
    'cycle10_independent_ast', ROOT / '_sessions/tools/check_cycle09_evidence.py')
truth = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(truth)
canonical, parse_json, read_json = truth.canonical, truth.parse_json, truth.read_json
sha, file_sha = truth.sha, truth.file_sha
ORDERS = {'P1': ['V', 'I', 'F'], 'P2': ['F', 'V', 'I'], 'P3': ['I', 'F', 'V']}
REQUEST_ORDER = ['R0-P1', 'R1-P2', 'R0-P3', 'R1-P1', 'R0-P2', 'R1-P3']
POLICY_COUNTS = {'exact_checker': 18, 'always_valid': 6, 'always_invalid': 12,
                 'position_1': 10, 'position_2': 10, 'position_3': 10,
                 'endpoint_matches_truth': 12, 'endpoint_boolean': 9}
CHECKS = 0


def require(condition, label):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise ValueError('independent cycle10 check failed: ' + label)


def same(actual, expected, label):
    require(canonical(actual) == canonical(expected), label)


def certificate_id(source, certificate):
    payload = canonical({'program': source, 'certificate': certificate}).encode('utf-8')
    return 'r_' + sha(b'cycle10-certificate\n' + payload)[:16]


def packet_policies(payload):
    """Decisions follow submitted states, source truth and position, not labels."""
    source = payload['program']
    answer = truth.evaluate_program(source)['answer']
    reports = payload['reports'][:3]
    validity = {row['report_id']: truth.check_certificate(source, row['certificate'])['valid']
                for row in reports}
    result = {}
    for name in POLICY_COUNTS:
        decisions = {}
        for position, report in enumerate(reports, 1):
            rid = report['report_id']
            endpoint = report['certificate']['rows'][-1]['state']['result']
            if name == 'exact_checker':
                decision = validity[rid]
            elif name in ('always_valid', 'always_invalid'):
                decision = name == 'always_valid'
            elif name.startswith('position_'):
                decision = position == int(name[-1])
            elif name == 'endpoint_matches_truth':
                decision = endpoint is answer
            else:
                decision = endpoint
            decisions[rid] = decision
        result[name] = {'decisions': decisions,
                        'correct': sum(decisions[rid] is validity[rid] for rid in validity),
                        'valid': 3, 'planned': 3}
    return result


def verify_fixture(fixture):
    """Reconstruct exact sources, certificates, ID bytes, permutations and policies."""
    require(type(fixture) is dict and set(fixture) == {
        'schema_version', 'generation', 'programs', 'packets', 'request_order',
        'reference_policies', 'policy_totals', 'audit'}, 'complete fixture schema')
    same(fixture['schema_version'], 1, 'typed schema version')
    parameters = fixture['generation']['parameters']
    require(type(parameters) is dict and set(parameters) == {'A', 'B'}
            and all(type(v) is int and -9 <= v <= 9 for v in parameters.values()),
            'typed bounded synthetic or actual constants')
    a, b = parameters['A'], parameters['B']
    same(fixture['generation'], {'parameters': {'A': a, 'B': b}, 'program_count': 2,
        'root_certificate_count': 6, 'packet_count': 6, 'rng_used': False,
        'candidate_attempts': 1, 'exclusions': []}, 'fixed construction with no draws or search')
    require(type(fixture['programs']) is list and len(fixture['programs']) == 2,
            'two programs, separately from their repeated appearances')
    programs, all_ids, packets, references = [], [], [], {}
    seen_positions, seen_endpoints = {}, {}
    for residue, supplied in enumerate(fixture['programs']):
        program_id = f'R{residue}'
        source = (f'a = {a}\nb = {b}\na = a + b\nb = a - b\na = a + b\n'
                  f'result = (a % 2 == {residue})\n')
        evaluated = truth.evaluate_program(source)
        certificates = truth.reconstruct_certificates(source)
        checks = {label: truth.check_certificate(source, cert)
                  for label, cert in certificates.items()}
        same({label: check['valid'] for label, check in checks.items()},
             {'V': True, 'I': False, 'F': False}, 'whole-certificate validity')
        same({label: check['first_invalid_step'] for label, check in checks.items()},
             {'V': None, 'I': 3, 'F': 6}, 'first invalid rows')
        same({label: [row['step'] for row in check['transitions'] if not row['valid']]
              for label, check in checks.items()}, {'V': [], 'I': [3], 'F': [6]},
             'I propagates the submitted bad row and has only one invalid transition')
        endpoints = {label: cert['rows'][-1]['state'] for label, cert in certificates.items()}
        require(endpoints['V']['a'] == 2 * a + b and endpoints['I']['a'] == 2 * a + b + 2
                and endpoints['V']['result'] is endpoints['I']['result']
                and endpoints['F']['result'] is not endpoints['V']['result'],
                'algebraic endpoint check and parity-preserving corruption')
        ids = {label: certificate_id(source, cert) for label, cert in certificates.items()}
        reports = {label: {'report_id': rid, 'root_id': rid, 'certificate': certificates[label]}
                   for label, rid in ids.items()}
        all_ids.extend(ids.values())
        expected = {'program_id': program_id, 'parameters': {'A': a, 'B': b, 'R': residue},
                    'program': source, 'program_sha256': sha(source.encode()), 'python_truth': evaluated,
                    'certificates': certificates, 'certificate_checks': checks,
                    'certificate_sha256': {label: sha(canonical(cert).encode())
                                           for label, cert in certificates.items()},
                    'report_ids': ids, 'report_sha256': {label: sha(canonical(report).encode())
                                                       for label, report in reports.items()}}
        same(supplied, expected, 'exact program/state/certificate/check/identity record ' + program_id)
        programs.append(expected)
        for order_id, order in ORDERS.items():
            packet_id = program_id + '-' + order_id
            payload = {'program': source, 'original_ids': [ids[label] for label in order],
                       'reports': [reports[label] for label in order] + [None, None]}
            text = canonical(payload)
            packets.append({'packet_id': packet_id, 'program_id': program_id, 'private_order': order,
                            'payload': text, 'payload_sha256': sha(text.encode()),
                            'payload_bytes': len(text.encode())})
            references[packet_id] = packet_policies(payload)
            for position, label in enumerate(order, 1):
                seen_positions.setdefault(ids[label], []).append(position)
                seen_endpoints.setdefault((position, label), []).append(endpoints[label]['result'])
    require(len(all_ids) == len(set(all_ids)) == 6, 'six content-derived IDs without collision or replacement')
    require(all(sorted(positions) == [1, 2, 3] for positions in seen_positions.values()),
            'each root appears once in every original position')
    require(len(seen_endpoints) == 9 and all(sorted(values) == [False, True]
            for values in seen_endpoints.values()), 'both endpoint values for every type and position')
    require(programs[0]['program'].splitlines()[:5] == programs[1]['program'].splitlines()[:5],
            'R alone changes between the two exact sources')
    for label in ('V', 'I', 'F'):
        left, right = [deepcopy(program['certificates'][label]) for program in programs]
        left_answer = left['rows'][-1]['state'].pop('result')
        right_answer = right['rows'][-1]['state'].pop('result')
        same(left, right, 'unchanged integer certificate states across R ' + label)
        require(left_answer is not right_answer, 'complemented endpoint for ' + label)
    same(fixture['packets'], packets, 'exact ordered packet schema, bytes, slots, labels and per-packet hashes')
    same(fixture['request_order'], REQUEST_ORDER, 'prespecified candidate invocation order')
    for packet in fixture['packets']:
        payload = parse_json(packet['payload'])
        require(canonical(payload) == packet['payload'] and set(payload) == {'program', 'original_ids', 'reports'},
                'canonical native payload without private construction or expected-validity metadata')
        require(payload['reports'][3:] == [None, None], 'all trailing slots null, with no copying intervention')
        for rid, report in zip(payload['original_ids'], payload['reports'][:3]):
            require(set(report) == {'report_id', 'root_id', 'certificate'}
                    and report['report_id'] == report['root_id'] == rid, 'exact original-only report schema')
            truth.validate_certificate(report['certificate'])
    same(fixture['reference_policies'], references, 'all eight full reference vectors and per-packet counts')
    vectors = {name: [references[packet['packet_id']][name]['decisions'][rid]
                     for packet in packets for rid in parse_json(packet['payload'])['original_ids']]
               for name in POLICY_COUNTS}
    totals = {name: {'correct': sum(references[p['packet_id']][name]['correct'] for p in packets),
                     'valid': 18, 'planned': 18,
                     'vector_differs_from_exact': vectors[name] != vectors['exact_checker']}
              for name in POLICY_COUNTS}
    same({name: row['correct'] for name, row in totals.items()}, POLICY_COUNTS, 'preregistered policy totals')
    require(all(totals[name]['vector_differs_from_exact'] for name in totals if name != 'exact_checker'),
            'checker differs from every specified heuristic vector')
    same(fixture['policy_totals'], totals, 'retained reference totals and vector distinctions')
    lengths = {packet['packet_id']: packet['payload_bytes'] for packet in packets}
    same(fixture['audit'], {'r_complement_verified': True, 'position_endpoint_balance': True,
        'root_and_report_identity_verified': True, 'heuristic_vectors_distinct_from_exact': True,
        'payload_byte_lengths': lengths}, 'retained local balance and byte-length audit')
    return {'distinct_programs': 2, 'distinct_root_certificates': 6, 'packet_count': 6,
            'planned_original_judgments': 18, 'all_states_transitions_ids_packets_and_policies_match': True,
            'reference_policy_correct': POLICY_COUNTS, 'first_invalid_step': {'V': None, 'I': 3, 'F': 6},
            'payload_byte_lengths': lengths, 'empirical_launch_authorized': False}


def run(prepared=BASE):
    own_start, reused_start = CHECKS, truth.CHECKS
    manifest = read_json(prepared / 'manifest.json')
    sources = manifest['source_sha256_start']
    same(sources, manifest['source_sha256_end'], 'unchanged preparation sources')
    require(set(sources) == SOURCE_FILES and manifest['empirical_launch_authorized'] is False,
            'complete source inventory and local-only boundary')
    for name, digest in sources.items():
        require(file_sha(ROOT / name) == digest, 'pinned source ' + name)
    artifacts = {'fixture.json', 'independent-check.json', 'cases.md'}
    artifacts.update(f'programs/R{r}.py' for r in (0, 1))
    artifacts.update(f'certificates/R{r}-{label}.json' for r in (0, 1) for label in ('V', 'I', 'F'))
    artifacts.update('packets/' + packet + '.json' for packet in REQUEST_ORDER)
    require(set(manifest['artifact_sha256']) == artifacts, 'complete prepared artifact inventory')
    for name, digest in manifest['artifact_sha256'].items():
        require(file_sha(prepared / name) == digest, 'sealed artifact ' + name)
    fixture = read_json(prepared / 'fixture.json')
    same(fixture['generation']['parameters'], {'A': 2, 'B': 3}, 'actual fixed constants, without candidate replacement')
    require((prepared / 'fixture.json').read_bytes() == canonical(fixture).encode(), 'canonical fixture bytes')
    verified = verify_fixture(fixture)
    same(read_json(prepared / 'independent-check.json'), verified, 'retained independent preparation audit')
    for program in fixture['programs']:
        pid = program['program_id']
        require((prepared / 'programs' / (pid + '.py')).read_bytes() == program['program'].encode(), 'program bytes ' + pid)
        for label, cert in program['certificates'].items():
            require((prepared / 'certificates' / (pid + '-' + label + '.json')).read_bytes()
                    == canonical(cert).encode(), 'certificate bytes ' + pid + label)
    for packet in fixture['packets']:
        require((prepared / 'packets' / (packet['packet_id'] + '.json')).read_bytes() == packet['payload'].encode(),
                'actual native packet bytes ' + packet['packet_id'])
    interpreter = Path(manifest['python']['executable'])
    interpreter_status = 'unavailable'
    if interpreter.exists():
        require(file_sha(interpreter) == manifest['python']['executable_sha256'], 'preparation interpreter bytes')
        interpreter_status = 'verified'
    duration = manifest['local_generation_truth_wall_seconds']
    require(type(duration) in (int, float) and math.isfinite(duration) and duration >= 0
            and type(manifest['preparation_argv']) is list and bool(manifest['preparation_argv'])
            and all(type(arg) is str for arg in manifest['preparation_argv']), 'finite wall time and exact command record')
    return {'schema_version': 1, 'status': 'passed', 'checked_utc': datetime.now(timezone.utc).isoformat(),
            'checker_sha256': file_sha(Path(__file__)),
            'checks_passed': CHECKS - own_start + truth.CHECKS - reused_start,
            'prepared_manifest_sha256': file_sha(prepared / 'manifest.json'),
            'truth_python_bytes': interpreter_status, 'fixture_check': verified,
            'independence': 'Reused independent cycle09 AST state interpreter; no producer imports or program exec.',
            'limitations': ['Eighteen judgments on two endpoint variants of one arithmetic skeleton.',
                           'Named response vectors do not identify internal reasoning or exclude unlisted shortcuts.',
                           'No empirical solver outcome, source independence, causal effect or launch is implied.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, default=BASE)
    parser.add_argument('--output', type=Path, help='Write a new receipt; never overwrite')
    args = parser.parse_args()
    result = run(args.prepared)
    if args.output:
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write('\n')
    print(json.dumps({'status': result['status'], 'checks_passed': result['checks_passed'],
                      'reference_policy_correct': result['fixture_check']['reference_policy_correct']}))


if __name__ == '__main__':
    main()
