#!/usr/bin/env python3
"""Independent cycle11 local custody, copied-evidence and reference-vector audit."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/cycle11-2026-09-11/prepared'
PARENT = ROOT / 'results/cycle10-2026-09-11/prepared'
PARENT_SHA = '6647f0ae806ada137668252ffe03839caeab3e13ae2ccf8127dcc6b67cf203cd'
CHECKER = '_sessions/tools/check_cycle11_evidence.py'
SPEC = importlib.util.spec_from_file_location('cycle11_parent_audit', ROOT / '_sessions/tools/check_cycle10_evidence.py')
parent_audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parent_audit)
truth = parent_audit.truth
canonical, parse_json, read_json = truth.canonical, truth.parse_json, truth.read_json
sha, file_sha = truth.sha, truth.file_sha
ORDER = ['R0-A', 'R1-B', 'R0-B', 'R1-A']
PLACEMENTS = {'R0-A': ['F', 'V', 'F', 'F'], 'R1-B': ['V', 'V', 'V', 'F'],
              'R0-B': ['V', 'F', 'V', 'V'], 'R1-A': ['F', 'F', 'F', 'V']}
NEW_SOURCES = {CHECKER, '_sessions/tools/tests/test_cycle11_audit.py',
    'evaluation/cycle11_certificates.py', 'evaluation/tests/test_cycle11_certificates.py',
    '_sessions/cycles/2026-09-11-cycle11-evidence-selection-design.md',
    '_sessions/cycles/2026-09-11-cycle11-local-protocol.md'}
CHECKS = 0


def require(condition, label):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise ValueError('independent cycle11 check failed: ' + label)


def same(actual, expected, label):
    require(canonical(actual) == canonical(expected), label)


def submission_id(program, root_id, ordinal):
    identity = {'program': program, 'root_id': root_id, 'instance_ordinal': ordinal}
    return 's_' + sha(b'cycle11-submission\n' + canonical(identity).encode())[:16]


def reference_maps(payload):
    """Derive reference choices from supplied program and complete certificate states."""
    answer = truth.evaluate_program(payload['program'])['answer']
    reports = payload['reports'][:4]
    endpoints = [report['certificate']['rows'][-1]['state']['result'] for report in reports]
    validity = {report['report_id']: truth.check_certificate(payload['program'], report['certificate'])['valid']
                for report in reports}
    require(sum(endpoints) in (1, 3), 'literal 3:1 instance vote')
    roots = {report['root_id']: report['certificate']['rows'][-1]['state']['result'] for report in reports}
    require(len(roots) == 2 and set(roots.values()) == {False, True}, 'root votes tie without a selection rule')
    answers = {'exact_replay': answer, 'majority': sum(endpoints) > 2, 'minority': sum(endpoints) < 2,
               **{'position_' + str(i): endpoint for i, endpoint in enumerate(endpoints, 1)},
               'always_true': True, 'always_false': False, 'deduplicated_root_vote': None}
    validities = {'exact_checker': validity,
        'endpoint_matches_truth': {report['report_id']: endpoint is answer for report, endpoint in zip(reports, endpoints)},
        'always_valid': dict.fromkeys(validity, True), 'always_invalid': dict.fromkeys(validity, False)}
    same(validities['endpoint_matches_truth'], validity, 'endpoint agreement equals checking for V/F only')
    return answers, validities


def verify_fixture(fixture, parent):
    """Pure reconstruction from the supplied parent; disk provenance is checked by run."""
    parent_audit.verify_fixture(parent)
    require(type(fixture) is dict and set(fixture) == {'schema_version', 'parent_custody', 'generation',
            'programs', 'packets', 'request_order', 'reference_policies', 'policy_totals', 'audit'}, 'exact fixture schema')
    same(fixture['schema_version'], 1, 'typed schema version')
    same(fixture['programs'], parent['programs'], 'parent program records copied without modification')
    custody = fixture['parent_custody']
    require(type(custody) is dict and set(custody) == {'fixture_sha256', 'manifest_sha256', 'artifact_sha256'},
            'exact parent custody schema')
    require(custody['fixture_sha256'] == sha(canonical(parent).encode()), 'parent fixture canonical identity')
    require((custody['manifest_sha256'] is None and custody['artifact_sha256'] == {})
            or (custody['manifest_sha256'] == PARENT_SHA and type(custody['artifact_sha256']) is dict
                and custody['artifact_sha256'].get('fixture.json') == custody['fixture_sha256']),
            'synthetic parent is explicit; actual parent carries fixed manifest and fixture anchors')
    same(fixture['generation'], {'program_count': 2, 'root_certificate_count': 4, 'packet_count': 4,
        'distinct_submission_id_count': 12, 'submitted_instances': 16, 'rng_used': False,
        'construction_attempts': 1, 'exclusions': []}, 'one fixed copied-evidence construction')
    programs = {row['program_id']: row for row in parent['programs']}
    for program in programs.values():
        for label in ('V', 'F'):
            checked = truth.check_certificate(program['program'], program['certificates'][label])
            require(checked['valid'] is (label == 'V')
                    and checked['first_invalid_step'] == (None if label == 'V' else 6), 'reused V/F truth and first-invalid row')
            same([row['step'] for row in checked['transitions'] if not row['valid']],
                 [] if label == 'V' else [6], 'only the declared final transition differs')
    for left, right in (('V', 'F'), ('F', 'V')):
        same(programs['R0']['certificates'][left], programs['R1']['certificates'][right],
             'identical certificate bytes can have opposite program-conditioned validity')
        require(programs['R0']['report_ids'][left] != programs['R1']['report_ids'][right],
                'program-conditioned roots must not merge equal certificate bytes')
    packets, references, identities = [], {}, {}
    answer_vectors, validity_vectors = {}, {}
    for pid in ORDER:
        program_id, regime = pid.split('-')
        program = programs[program_id]
        order, reports, seen = PLACEMENTS[pid], [], Counter()
        for label in order:
            root_id = program['report_ids'][label]
            seen[root_id] += 1
            ordinal = seen[root_id]
            identity = (program['program'], root_id, ordinal)
            sid = submission_id(*identity)
            require(sid not in identities or identities[sid] == identity, 'distinct identity tuples cannot collide')
            identities[sid] = identity
            reports.append({'report_id': sid, 'root_id': root_id, 'certificate': program['certificates'][label]})
        require(sorted(seen.values()) == [1, 3], 'two original roots under a 3:1 instance count')
        payload = {'program': program['program'], 'submission_ids': [r['report_id'] for r in reports],
                   'reports': reports + [None]}
        text = canonical(payload)
        packets.append({'packet_id': pid, 'program_id': program_id, 'private_regime': regime, 'private_order': order,
                        'payload': text, 'payload_sha256': sha(text.encode()), 'payload_bytes': len(text.encode())})
        answer = truth.evaluate_program(program['program'])['answer']
        answer_maps, validity_maps = reference_maps(payload)
        exact = validity_maps['exact_checker']
        require(sum(exact.values()) == (1 if regime == 'A' else 3), 'declared valid minority/majority crossing')
        references[pid] = {
            'answer': {name: {'answer': value, 'correct': int(value is answer), 'answered': int(value is not None),
                             'planned': 1, 'abstained': int(value is None)} for name, value in answer_maps.items()},
            'validity': {name: {'decisions': decisions, 'correct': sum(decisions[sid] is exact[sid] for sid in exact),
                               'valid': 4, 'planned': 4} for name, decisions in validity_maps.items()}}
        for name, value in answer_maps.items():
            answer_vectors.setdefault(name, []).append(value)
        for name, decisions in validity_maps.items():
            validity_vectors.setdefault(name, []).extend(decisions[sid] for sid in payload['submission_ids'])
    require(len(identities) == 12 and sum(len(parse_json(p['payload'])['submission_ids']) for p in packets) == 16,
            'twelve unique instance tuples reused over sixteen submissions')
    for program_id in programs:
        for first, second in zip(PLACEMENTS[program_id + '-A'], PLACEMENTS[program_id + '-B']):
            require(first != second, 'every slot contains each validity type once per program truth')
    same(fixture['packets'], packets, 'exact copied certificates, left-to-right ordinals, labels and canonical packet bytes')
    same(fixture['request_order'], ORDER, 'frozen four-packet request order')
    for packet in fixture['packets']:
        payload = parse_json(packet['payload'])
        require(canonical(payload) == packet['payload'] and set(payload) == {'program', 'submission_ids', 'reports'}
                and len(payload['reports']) == 5 and payload['reports'][-1] is None
                and len(set(payload['submission_ids'])) == 4, 'native payload schema contains four instances and one null only')
        for sid, report in zip(payload['submission_ids'], payload['reports'][:4]):
            require(set(report) == {'report_id', 'root_id', 'certificate'} and report['report_id'] == sid,
                    'no private type/regime/expected-answer metadata in submission objects')
            truth.validate_certificate(report['certificate'])
    same(fixture['reference_policies'], references, 'every answer/validity reference decision and per-packet denominator')
    totals = {
        'answer': {name: {**{field: sum(references[pid]['answer'][name][field] for pid in ORDER)
                            for field in ('correct', 'answered', 'planned', 'abstained')}, 'vector': vector}
                   for name, vector in answer_vectors.items()},
        'validity': {name: {'correct': sum(references[pid]['validity'][name]['correct'] for pid in ORDER),
                            'valid': 16, 'planned': 16, 'vector': vector} for name, vector in validity_vectors.items()}}
    for name, total in totals['answer'].items():
        correct = 4 if name == 'exact_replay' else 0 if name == 'deduplicated_root_vote' else 2
        require(total['correct'] == correct and total['answered'] == (0 if name == 'deduplicated_root_vote' else 4)
                and total['abstained'] == (4 if name == 'deduplicated_root_vote' else 0), 'prespecified answer reference ' + name)
    require({name: total['correct'] for name, total in totals['validity'].items()}
            == {'exact_checker': 16, 'endpoint_matches_truth': 16, 'always_valid': 8, 'always_invalid': 8},
            'balanced validity reference counts')
    same(fixture['policy_totals'], totals, 'full reference vectors, including four abstentions and zero dedup answers')
    lengths = {p['packet_id']: p['payload_bytes'] for p in packets}
    same(fixture['audit'], {'source_and_certificate_bytes_preserved': True, 'program_conditioned_roots_preserved': True,
        'instance_identity_verified': True, 'regime_position_truth_balance_verified': True,
        'reference_vectors_verified': True, 'payload_byte_lengths': lengths}, 'retained local audit and all input lengths')
    return {'program_count': 2, 'root_certificate_count': 4, 'packet_count': 4,
        'distinct_submission_id_count': 12, 'planned_answers': 4, 'planned_validities': 16,
        'all_parent_states_roots_instances_and_reference_vectors_match': True,
        'answer_policy_correct': {name: row['correct'] for name, row in totals['answer'].items()},
        'validity_policy_correct': {name: row['correct'] for name, row in totals['validity'].items()},
        'deduplicated_root_vote': {'answered': 0, 'abstained': 4, 'planned': 4},
        'payload_byte_lengths': lengths, 'empirical_launch_authorized': False}


def run(prepared=BASE):
    start = CHECKS + parent_audit.CHECKS + truth.CHECKS
    require(file_sha(PARENT / 'manifest.json') == PARENT_SHA, 'immutable cycle10 parent manifest')
    parent_result = parent_audit.run(PARENT)
    require(parent_result['prepared_manifest_sha256'] == PARENT_SHA, 'independent complete parent custody audit')
    parent_manifest, parent = read_json(PARENT / 'manifest.json'), read_json(PARENT / 'fixture.json')
    manifest, fixture = read_json(prepared / 'manifest.json'), read_json(prepared / 'fixture.json')
    sources = manifest['source_sha256_start']
    same(sources, manifest['source_sha256_end'], 'unchanged preparation sources')
    require(set(sources) == parent_audit.SOURCE_FILES | NEW_SOURCES and manifest['empirical_launch_authorized'] is False,
            'complete source inventory and local-only boundary')
    for name, digest in sources.items():
        require(file_sha(ROOT / name) == digest, 'pinned source ' + name)
    same(fixture['parent_custody'], {'fixture_sha256': file_sha(PARENT / 'fixture.json'), 'manifest_sha256': PARENT_SHA,
                                   'artifact_sha256': parent_manifest['artifact_sha256']}, 'exact copied parent provenance')
    same(manifest['parent_custody'], fixture['parent_custody'], 'manifest parent linkage')
    same(manifest['parent_source_sha256'], parent_manifest['source_sha256_start'], 'complete preserved parent sources')
    artifacts = {'fixture.json', 'independent-check.json', 'cases.md', 'parent-fixture.json', 'parent-manifest.json'}
    artifacts.update('packets/' + pid + '.json' for pid in ORDER)
    require(set(manifest['artifact_sha256']) == artifacts, 'complete nine-artifact inventory')
    for name, digest in manifest['artifact_sha256'].items():
        require(file_sha(prepared / name) == digest, 'prepared artifact ' + name)
    require((prepared / 'fixture.json').read_bytes() == canonical(fixture).encode(), 'canonical prepared fixture')
    verified = verify_fixture(fixture, parent)
    same(read_json(prepared / 'independent-check.json'), verified, 'retained independent preparation evidence')
    for name in ('fixture.json', 'manifest.json'):
        require((prepared / ('parent-' + name)).read_bytes() == (PARENT / name).read_bytes(),
                'exact immutable parent artifact copy ' + name)
    for packet in fixture['packets']:
        require((prepared / 'packets' / (packet['packet_id'] + '.json')).read_bytes() == packet['payload'].encode(),
                'sealed solver input bytes ' + packet['packet_id'])
    interpreter = Path(manifest['python']['executable'])
    interpreter_status = 'unavailable'
    if interpreter.exists():
        require(file_sha(interpreter) == manifest['python']['executable_sha256'], 'preparation interpreter bytes')
        interpreter_status = 'verified'
    duration = manifest['local_generation_truth_wall_seconds']
    require(type(duration) in (int, float) and math.isfinite(duration) and duration >= 0
            and type(manifest['preparation_argv']) is list and bool(manifest['preparation_argv'])
            and all(type(arg) is str for arg in manifest['preparation_argv']), 'finite wall time and command provenance')
    return {'schema_version': 1, 'status': 'passed', 'checked_utc': datetime.now(timezone.utc).isoformat(),
        'checks_passed': CHECKS + parent_audit.CHECKS + truth.CHECKS - start,
        'checker_sha256': file_sha(Path(__file__)), 'prepared_manifest_sha256': file_sha(prepared / 'manifest.json'),
        'parent_prepared_manifest_sha256': PARENT_SHA, 'truth_python_bytes': interpreter_status, 'fixture_check': verified,
        'independence': 'Reused independent AST/full-state checker and parent auditor; no producer imports or program exec.',
        'limitations': ['Four packets reuse four roots on two variants of one arithmetic skeleton, not independent acquisitions.',
            'Endpoint agreement and exact certificate checking coincide for the selected V/F roots.',
            'Deduplication alone abstains; a direct solver can produce every correct output.',
            'Local acceptance implies no empirical outcome, internal strategy, causal effect or multiagent benefit.']}


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
    print(json.dumps({key: result[key] for key in ('status', 'checks_passed', 'prepared_manifest_sha256')}))


if __name__ == '__main__':
    main()
