#!/usr/bin/env python3
"""Seal and collect one cycle09 two-packet verifier pilot; no retries or repair."""
import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from evaluation import cycle09_certificates as packets
from evaluation import cycle09_verifier as measure
import run_cycle05_coordinator as shared
import native_stream_observer as native

BINARY, BINARY_SHA, MODEL = shared.BINARY, shared.BINARY_SHA, shared.MODEL
OVERRIDES = shared.OVERRIDES
CAP, CALL_SECONDS, BATCH_SECONDS = Decimal('1'), 120, 300
BASE = ROOT / 'results/cycle09-2026-09-11'
PREPARED = BASE / 'prepared'
EXECUTION = BASE / 'execution'
OUTPUT = BASE / 'observations'
PROTOCOL = '_sessions/cycles/2026-09-11-cycle09-execution-protocol.md'
DECISION = '_sessions/evidence/2026-09-11-cycle09-execution-decision.json'
PINNED = {
    '_sessions/tools/run_cycle05_coordinator.py': 'e3b49dce410beab317235445851d73a89fc2a21efff7a56ed74d2d8cfdce25f2',
    '_sessions/tools/run_cycle05_replication.py': '9fe3c83e1e5f157d0d9b3a913dd7006edd4c288ee3f003502421bcf15c3f2706',
    '_sessions/tools/native_stream_observer.py': '56372ade927f2ac98a4e6f593315a38f3060dd7a00f3eeb7f41452ad97ec4992',
    'evaluation/cycle05_coordinator_packets.py': '83845428b0e36bdc2aecb68676a4e899377ff7713725e00b64059da392ebc941',
}
digest, write_json, now = shared.digest, shared.write_json, shared.now
process_environment, command = shared.process_environment, shared.command
native_cost, invoke = shared.native_cost, shared.invoke


def inspect_stream(raw, exit_code, expected_session, expected_ids, timed_out=False):
    """Native acceptance precedes strict terminal-only parsing of all three bits."""
    observed = native.inspect_stream(raw, exit_code, expected_session, timed_out)
    observed.pop('p_positive')
    observed.update(validity=None, parse_failure=None)
    if observed['native_acceptable']:
        events = [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
        terminal = [e for e in events if e.get('type') == 'result']
        try:
            observed['validity'] = measure.parse_validity(terminal[0].get('result'), expected_ids)
        except measure.MapParseError as error:
            observed['parse_failure'] = str(error)
    return observed


def current_sources(prepared_manifest):
    extra = [Path(__file__), ROOT / 'evaluation/cycle09_verifier.py',
             ROOT / '_sessions/tools/tests/test_cycle09_runner.py',
             ROOT / '_sessions/tools/score_cycle09_verifier.py',
             ROOT / PROTOCOL, ROOT / DECISION,
             ROOT / '_sessions/tools/tests/test_native_stream_observer.py',
             PREPARED / 'fixture.json', PREPARED / 'manifest.json']
    identities = dict(prepared_manifest['source_sha256_start'])
    identities.update({str(p.relative_to(ROOT)): digest(p) for p in extra})
    for path, expected in PINNED.items():
        if digest(ROOT / path) != expected:
            raise ValueError('preserved native implementation changed: ' + path)
        identities[path] = expected
    return identities


def prepare_execution(prepared_sha):
    if EXECUTION.exists():
        raise FileExistsError(EXECUTION)
    fixture, prepared = packets.validate_fixture_custody(PREPARED, prepared_sha)
    decision = packets.parse_json((ROOT / DECISION).read_text())
    if decision.get('proceed') is not True or decision.get('prepared_manifest_sha256') != prepared_sha:
        raise ValueError('no matching separate execution decision')
    process_environment(os.environ)
    if digest(BINARY) != BINARY_SHA:
        raise ValueError('native binary identity changed')
    sources = current_sources(prepared)
    by_id = {row['packet_id']: row for row in fixture['packets']}
    if set(by_id) != set(measure.ORDER):
        raise ValueError('expected base and repeat only')
    artifacts = {'system-prompt.txt': measure.SYSTEM_PROMPT.encode('utf-8')}
    for pid in measure.ORDER:
        payload = by_id[pid]['payload'].encode('utf-8')
        packets.validate_payload(packets.parse_json(payload.decode()))
        if hashlib.sha256(payload).hexdigest() != by_id[pid]['payload_sha256']:
            raise ValueError('local packet identity mismatch')
        artifacts[pid + '.json'] = payload
    seal = {'schema_version': 1, 'prepared_manifest_sha256': prepared_sha,
            'request_order': list(measure.ORDER), 'source_sha256': sources,
            'native_binary_sha256': BINARY_SHA, 'native_budget_usd': str(CAP),
            'call_wall_seconds': CALL_SECONDS, 'batch_wall_seconds': BATCH_SECONDS,
            'sealed_utc': now(), 'artifact_sha256': {
                name: hashlib.sha256(data).hexdigest() for name, data in artifacts.items()}}
    if sources != current_sources(prepared):
        raise ValueError('execution sources changed during sealing')
    EXECUTION.mkdir(parents=True, exist_ok=False)
    for name, data in artifacts.items():
        with (EXECUTION / name).open('xb') as stream:
            stream.write(data)
    write_json(EXECUTION / 'manifest.json', seal)
    return digest(EXECUTION / 'manifest.json')


def sources(execution_sha):
    if digest(EXECUTION / 'manifest.json') != execution_sha:
        raise ValueError('execution manifest hash mismatch')
    seal = packets.parse_json((EXECUTION / 'manifest.json').read_text())
    fixture, prepared = packets.validate_fixture_custody(PREPARED, seal['prepared_manifest_sha256'])
    if (seal['source_sha256'] != current_sources(prepared)
            or seal['request_order'] != list(measure.ORDER)
            or seal['native_binary_sha256'] != BINARY_SHA
            or seal['native_budget_usd'] != str(CAP)
            or seal['call_wall_seconds'] != CALL_SECONDS
            or seal['batch_wall_seconds'] != BATCH_SECONDS):
        raise ValueError('execution source/control custody mismatch')
    expected_names = {'system-prompt.txt', 'base.json', 'repeat.json'}
    if set(seal['artifact_sha256']) != expected_names:
        raise ValueError('execution artifact inventory mismatch')
    for name, value in seal['artifact_sha256'].items():
        if digest(EXECUTION / name) != value:
            raise ValueError('execution payload custody mismatch')
    if (EXECUTION / 'system-prompt.txt').read_bytes() != measure.SYSTEM_PROMPT.encode():
        raise ValueError('system prompt differs from frozen text')
    for row in fixture['packets']:
        if (EXECUTION / (row['packet_id'] + '.json')).read_bytes() != row['payload'].encode():
            raise ValueError('execution packet differs from local fixture')
    fixture.update(system_prompt=measure.SYSTEM_PROMPT,
                   system_prompt_sha256=seal['artifact_sha256']['system-prompt.txt'],
                   request_order=list(measure.ORDER), prepared_manifest_sha256=seal['prepared_manifest_sha256'])
    identities = dict(seal['source_sha256'])
    identities.update({str((EXECUTION / name).relative_to(ROOT)): digest(EXECUTION / name)
                       for name in expected_names | {'manifest.json'}})
    return fixture, identities


def collect(execution_sha):
    fixture, before = sources(execution_sha)
    environment = process_environment(os.environ)
    if digest(BINARY) != BINARY_SHA:
        raise ValueError('native binary identity changed')
    OUTPUT.mkdir(parents=True, exist_ok=False)
    batch_id = str(uuid.uuid4())
    private = ROOT / '_sessions/local/cycle09' / batch_id
    private.mkdir(parents=True, exist_ok=False)
    manifest = {'schema_version': 1, 'status': 'started', 'started_utc': now(),
        'batch_id': batch_id, 'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'python_version': sys.version, 'source_sha256_start': before,
        'native_binary': str(BINARY), 'native_binary_sha256': BINARY_SHA,
        'prepared_manifest_sha256': fixture['prepared_manifest_sha256'],
        'execution_manifest_sha256': execution_sha, 'environment_overrides': OVERRIDES,
        'argv_template': command(fixture['system_prompt'], '<fresh-uuid>', '<remaining-native-usd>'),
        'request_order': fixture['request_order'], 'native_budget_usd': str(CAP),
        'call_wall_seconds': CALL_SECONDS, 'batch_wall_seconds': BATCH_SECONDS,
        'wire_attempt_count': None, 'private_directory': str(private.relative_to(ROOT))}
    write_json(OUTPUT / 'manifest-start.json', manifest)
    started, spent, records, attempts, stop = time.monotonic(), Decimal(0), [], [], 'all_invocations_finished'
    by_id = {p['packet_id']: p for p in fixture['packets']}
    try:
        for ordinal, packet_id in enumerate(fixture['request_order'], 1):
            left = BATCH_SECONDS - (time.monotonic() - started)
            if spent >= CAP or left <= 0:
                stop = 'native_budget_exhausted' if spent >= CAP else 'batch_wall_exhausted'
                break
            packet = by_id[packet_id]
            payload = packet['payload'].encode('utf-8')
            packets.validate_payload(json.loads(payload))
            if hashlib.sha256(payload).hexdigest() != packet['payload_sha256']:
                raise ValueError('submission payload custody mismatch')
            session_id = str(uuid.uuid4())
            stdout_path, stderr_path = private / f'{ordinal:02d}.jsonl', private / f'{ordinal:02d}.stderr'
            call_started = now()
            attempt = {'ordinal': ordinal, 'packet_id': packet_id, 'session_id': session_id,
                       'started_utc': call_started, 'payload_sha256': packet['payload_sha256'],
                       'system_prompt_sha256': fixture['system_prompt_sha256'],
                       'remaining_native_usd': str(CAP - spent), 'timeout_seconds': min(CALL_SECONDS, left)}
            write_json(OUTPUT / f'{ordinal:02d}-attempt.json', attempt)
            attempts.append(attempt)
            execution = invoke(command(fixture['system_prompt'], session_id, CAP - spent),
                               payload, environment, min(CALL_SECONDS, left), stdout_path, stderr_path)
            record = {'ordinal': ordinal, 'packet_id': packet_id, 'session_id': session_id,
                'started_utc': call_started, 'finished_utc': now(),
                'payload_sha256': packet['payload_sha256'], 'system_prompt_sha256': fixture['system_prompt_sha256'],
                'scheduled_remaining_native_usd': str(CAP - spent),
                'scheduled_timeout_seconds': min(CALL_SECONDS, left), **execution,
                'stdout_path': str(stdout_path.relative_to(ROOT)), 'stderr_path': str(stderr_path.relative_to(ROOT)),
                'stdout_sha256': digest(stdout_path), 'stderr_sha256': digest(stderr_path),
                **inspect_stream(stdout_path.read_bytes(), execution['exit_code'], session_id,
                    packets.parse_json(packet['payload'])['original_ids'], execution['timed_out'])}
            records.append(record)
            write_json(OUTPUT / f'{ordinal:02d}-{packet_id}.json', record)
            cost = native_cost(record['native_cost_usd'])
            if cost is not None:
                spent += cost
            print(json.dumps({'ordinal': ordinal, 'native_acceptable': record['native_acceptable'],
                              'valid_answer': record['validity'] is not None,
                              'known_native_usd': str(spent), 'issues': record['issues']}), flush=True)
            if not record['native_acceptable'] or record['validity'] is None or execution['interrupted']:
                stop = ('interrupted' if execution['interrupted'] else
                        'native_or_configuration_failure' if not record['native_acceptable'] else 'invalid_answer')
                break
    except BaseException as error:
        # Preserve an unscorable collection without leaking arbitrary exception text.
        manifest['exception_type'] = type(error).__name__
        stop = 'collection_exception'
        raise
    finally:
        manifest.update({'finished_utc': now(), 'wall_seconds': time.monotonic() - started,
            'stop_reason': stop, 'invocations_observed': len(records),
            'invocations_scheduled': len(attempts),
            'valid_predictions': sum(r['validity'] is not None for r in records),
            'known_native_cost_usd': str(spent),
            'all_observed_costs_known': len(attempts) == len(records) and all(r['native_cost_usd'] is not None for r in records)})
        try:
            _, after = sources(execution_sha)
            unchanged = after == before and digest(BINARY) == BINARY_SHA
        except (ValueError, OSError):
            after, unchanged = {}, False
        manifest.update({'source_sha256_end': after, 'sources_unchanged': unchanged,
                         'status': 'complete' if unchanged and stop != 'collection_exception' else 'invalid'})
        write_json(OUTPUT / 'responses.json', records)
        manifest['output_sha256'] = {p.name: digest(p) for p in sorted(OUTPUT.glob('*.json'))}
        write_json(OUTPUT / ('manifest.json' if manifest['status'] == 'complete' else 'manifest-invalid.json'), manifest)
    return manifest



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    prepare = sub.add_parser('prepare')
    prepare.add_argument('--prepared-manifest-sha256', required=True)
    run = sub.add_parser('collect')
    run.add_argument('--execution-manifest-sha256', required=True)
    args = parser.parse_args()
    if args.action == 'prepare':
        print(json.dumps({'execution_manifest_sha256': prepare_execution(args.prepared_manifest_sha256)}))
    else:
        manifest = collect(args.execution_manifest_sha256)
        print(json.dumps({k: manifest[k] for k in ('status', 'stop_reason', 'invocations_observed',
                                                  'valid_predictions', 'known_native_cost_usd')}))
