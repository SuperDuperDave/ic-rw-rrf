#!/usr/bin/env python3
"""Score the immutable cycle07 development collection without any provider requests."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from evaluation import cycle07_program_errors as packets

BASE = ROOT / 'results/cycle07-2026-09-10'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


def score():
    observation = BASE / 'observations'
    manifest = json.loads((observation / 'manifest.json').read_text())
    if manifest['status'] != 'complete' or manifest['sources_unchanged'] is not True:
        raise ValueError('collection custody is invalid')
    source_hashes = manifest['source_sha256_start']
    if source_hashes != manifest['source_sha256_end']:
        raise ValueError('collection source hashes disagree')
    for name, value in source_hashes.items():
        if sha(ROOT / name) != value:
            raise ValueError('collection source changed: ' + name)
    for name, value in manifest['output_sha256'].items():
        if sha(observation / name) != value:
            raise ValueError('collection output changed: ' + name)
    fixture, _ = packets.validate_fixture_custody(BASE / 'prepared', manifest['prepared_manifest_sha256'])
    records = json.loads((observation / 'responses.json').read_text())
    if [r['packet_id'] for r in records] != fixture['request_order'][:len(records)]:
        raise ValueError('collection is not a prefix of the frozen order')
    if len(records) != manifest['invocations_observed'] or len(records) != manifest['invocations_scheduled']:
        raise ValueError('attempt/observation coverage mismatch')
    predictions, failures = {}, {}
    by_id = {p['packet_id']: p for p in fixture['packets']}
    for ordinal, record in enumerate(records, 1):
        pid = record['packet_id']
        if (record['ordinal'] != ordinal or record['payload_sha256'] != by_id[pid]['payload_sha256']
                or record['system_prompt_sha256'] != fixture['system_prompt_sha256']):
            raise ValueError('record payload/order custody mismatch')
        individual = observation / f'{ordinal:02d}-{pid}.json'
        if json.loads(individual.read_text()) != record:
            raise ValueError('individual receipt differs from collection')
        if record['native_acceptable']:
            if record['issues']:
                raise ValueError('accepted record has native issues')
            if record['answer'] is not None:
                if record['parse_failure'] is not None:
                    raise ValueError('simultaneous parse failure and prediction')
                if type(record['answer']) is not bool:
                    raise ValueError('stored answer is not Boolean')
                predictions[pid] = record['answer']
            else:
                if ordinal != len(records) or not isinstance(record['parse_failure'], str):
                    raise ValueError('invalid output did not stop collection')
                failures[pid] = 'parse:' + record['parse_failure']
        else:
            if record['answer'] is not None or ordinal != len(records):
                raise ValueError('failed native record yielded prediction or collection continued')
            failures[pid] = 'native:' + ','.join(record['issues'])
    output = BASE / 'scored'
    output.mkdir(exist_ok=False)
    inputs = {str((observation / 'manifest.json').relative_to(ROOT)): sha(observation / 'manifest.json'),
              str((observation / 'responses.json').relative_to(ROOT)): sha(observation / 'responses.json'),
              str(Path(__file__).relative_to(ROOT)): sha(Path(__file__))}
    receipt = {'schema_version': 1, 'status': 'started',
               'started_utc': datetime.now(timezone.utc).isoformat(), 'input_sha256': inputs}
    write(output / 'manifest-start.json', receipt)
    result = packets.score_answers(fixture, predictions, failures)
    write(output / 'scores.json', result)
    if any(sha(ROOT / name) != value for name, value in inputs.items()):
        raise ValueError('scoring inputs changed')
    receipt.update({'status': 'complete', 'finished_utc': datetime.now(timezone.utc).isoformat(),
                    'measurement_status': result['status'], 'coverage': result['coverage'],
                    'output_sha256': {name: sha(output / name) for name in ('manifest-start.json', 'scores.json')}})
    write(output / 'manifest.json', receipt)
    print(json.dumps({'status': result['status'], 'coverage': result['coverage']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--score', action='store_true', required=True)
    parser.parse_args()
    score()
