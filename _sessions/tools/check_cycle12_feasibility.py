#!/usr/bin/env python3
"""Replay the small cycle12 inventory; no network, provider calls or file writes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / '_sessions/evidence/2026-09-11-cycle12-feasibility.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check(public_only=False):
    receipt = read(RECEIPT)
    for name, digest in receipt['source_sha256'].items():
        require(sha(ROOT / name) == digest, 'source changed: ' + name)
    manifest = read(ROOT / 'data/cycle02/acquired/source-manifest.json')
    sources = manifest['original_inputs']
    inventory = receipt['cache_inventory']
    require(len(sources) == len(inventory) == 2, 'expected two cache inventory entries')
    require([row['year'] for row in sources] == [row['year'] for row in inventory],
            'cache inventory years differ')
    cache_status = []
    for source, expected in zip(sources, inventory):
        path = ROOT / '_sessions/local/cycle02/source-cache' / (source['sha256'] + '-' + source['filename'])
        require((source['year'], source['sha256'], source['bytes']) ==
                (expected['year'], expected['sha256'], expected['bytes']), 'cache provenance mismatch')
        if public_only or not path.exists():
            cache_status.append('unavailable')
            continue
        require(sha(path) == expected['sha256'] and path.stat().st_size == expected['bytes'], 'cache bytes changed')
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        candidates = [candidate for row in rows for candidate in row['candidates']]
        observed = {'query_count': len(rows), 'candidate_appearances': len(candidates)}
        for key, objects in (('row_field_sets', rows), ('query_field_sets', [r['query'] for r in rows]),
                             ('candidate_field_sets', candidates), ('document_field_sets', [c['doc'] for c in candidates])):
            observed[key] = [list(fields) for fields in sorted({tuple(sorted(obj)) for obj in objects})]
        require(all(observed[k] == expected[k] for k in observed), 'cache inventory mismatch')
        cache_status.append('verified')
    case = receipt['operational_case']
    command = case['simple_lookup']['command']
    require(command == ['git', 'grep', '-l', '-F', case['packet_id'], receipt['repository_commit'],
                        '--', '_sessions/evidence'], 'unexpected lookup command')
    matches = subprocess.check_output(command, cwd=ROOT, text=True).splitlines()
    require(matches == case['simple_lookup']['matching_paths'], 'frozen lookup differs')
    original = read(ROOT / case['initial_receipt_path'])
    audit = read(ROOT / case['decisive_audit_path'])
    row = next(r for r in audit['batch']['raw_checks'] if r['packet_id'] == case['packet_id'])
    for key in ('provider_models', 'provider_message_ids', 'local_synthetic_message_ids', 'observed_recovery_markers'):
        require(case[key] == row[key], 'operational metadata mismatch: ' + key)
    raw = ROOT / original['stdout_path']
    raw_status = 'unavailable'
    if not public_only and raw.exists():
        require(sha(raw) == case['raw_sha256'] == original['stdout_sha256'], 'native bytes changed')
        identities = {}
        for line in raw.read_text().splitlines():
            event = json.loads(line)
            message = event.get('message') if event.get('type') == 'assistant' else None
            if event.get('type') == 'stream_event' and event.get('event', {}).get('type') == 'message_start':
                message = event['event']['message']
            if message is not None:
                identities[message['id']] = message['model']
        provider = {mid: model for mid, model in identities.items() if model != '<synthetic>'}
        require(sorted(provider) == sorted(case['provider_message_ids']) and
                sorted(set(provider.values())) == case['provider_models'], 'provider identities differ')
        require(sorted(set(identities) - set(provider)) == sorted(case['local_synthetic_message_ids']),
                'local error identities differ')
        raw_status = 'metadata_verified'
    return {'status': 'passed', 'receipt_sha256': sha(RECEIPT), 'cache_checks': cache_status,
            'native_raw': raw_status, 'frozen_lookup_matches': len(matches),
            'scope': 'Post-inspection replay; no semantic passage or model-policy evaluation.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-only', action='store_true')
    arguments = parser.parse_args()
    print(json.dumps(check(arguments.public_only), sort_keys=True))
