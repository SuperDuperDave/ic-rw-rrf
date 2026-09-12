#!/usr/bin/env python3
"""Acquire the frozen SciFact files once; preserve any failed attempt locally.

No parsing, retrieval, model calls or effectiveness computation. Output must be
a fresh ignored directory. Network/body failures stop the sequence without retry.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / '_sessions/evidence/2026-09-11-cycle14-input-plan.json'
PLAN_SHA256 = '051aed306d99e3431aa0cf60f17b7acdf1341becc20d37259c283155c134d18a'
EVALUATOR_REVISION = 'ba38899cbd4de0fb699b47f39b64ef1c107e4a5c'
CHUNK = 1024 * 1024


class AcquisitionError(ValueError):
    """Safe error containing no remote response text or redirect credentials."""


def sha256_file(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b''):
            value.update(chunk)
    return value.hexdigest()


def load_plan():
    raw = PLAN.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PLAN_SHA256:
        raise AcquisitionError('Frozen input plan identity mismatch')
    plan = json.loads(raw)
    if sum(row['expected_bytes'] for row in plan['inputs']) > plan['raw_input_byte_cap']:
        raise AcquisitionError('Raw input byte cap exceeded before download')
    return plan


def download(item, destination, deadline, *, opener=urlopen, clock=time.monotonic):
    """One request, a bounded body, exact identity where published, no reuse."""
    destination = Path(destination)
    partial = destination.with_name(destination.name + '.partial')
    if destination.exists() or partial.exists():
        raise AcquisitionError('Destination already exists')
    remaining = deadline - clock()
    if remaining <= 0:
        raise AcquisitionError('Download wall limit reached')
    expected = item.get('expected_bytes')
    cap = expected if expected is not None else item['byte_cap']
    if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
        raise AcquisitionError('Invalid byte cap')
    algorithm = item.get('identity_algorithm', 'sha256')
    if algorithm not in ('sha256', 'git-blob-sha1'):
        raise AcquisitionError('Unsupported identity algorithm')
    if algorithm == 'git-blob-sha1' and expected is None:
        raise AcquisitionError('Git blob identity requires a frozen size')
    digest = hashlib.sha256() if algorithm == 'sha256' else hashlib.sha1()
    if algorithm == 'git-blob-sha1':
        digest.update(('blob ' + str(expected) + '\0').encode())
    body_sha = hashlib.sha256()
    request = Request(item['url'], headers={'Accept-Encoding': 'identity',
                                           'User-Agent': 'IC-RW-RRF-cycle15/1'})
    total = 0
    with opener(request, timeout=min(30, remaining)) as response:
        if response.status != 200:
            raise AcquisitionError('Expected HTTP 200')
        length = response.headers.get('Content-Length')
        if length is not None:
            try:
                length = int(length)
            except (TypeError, ValueError) as error:
                raise AcquisitionError('Invalid Content-Length') from error
            if length < 0 or length > cap or (expected is not None and length != expected):
                raise AcquisitionError('Advertised body length violates frozen input')
        with partial.open('xb') as stream:
            while True:
                if clock() >= deadline:
                    raise AcquisitionError('Download wall limit reached')
                chunk = response.read(min(CHUNK, cap - total + 1))
                if not chunk:
                    break
                total += len(chunk)
                if total > cap:
                    raise AcquisitionError('Body exceeds frozen byte cap')
                stream.write(chunk)
                digest.update(chunk)
                body_sha.update(chunk)
            stream.flush()
            os.fsync(stream.fileno())
    if clock() >= deadline:
        raise AcquisitionError('Download wall limit reached')
    if expected is not None and total != expected:
        raise AcquisitionError('Actual body size differs from frozen input')
    if total == 0:
        raise AcquisitionError('Empty body')
    actual = digest.hexdigest()
    if item.get('expected_digest') and actual != item['expected_digest']:
        raise AcquisitionError('Actual body identity differs from frozen input')
    # Exclusive destination creation; preserve partial even if a concurrent path appears.
    os.link(partial, destination)
    partial.unlink()
    return {'role': item['role'], 'path': str(destination), 'bytes': total,
            'sha256': body_sha.hexdigest(), 'identity_algorithm': algorithm,
            'identity_digest': actual, 'published_identity_verified': bool(item.get('expected_digest'))}


def items_from_plan(plan):
    items = [dict(item) for item in plan['inputs']]
    decoder = plan['optional_parquet_decoder']
    if decoder['expected_bytes'] > plan['optional_decoder_byte_cap']:
        raise AcquisitionError('Decoder cap exceeded before download')
    items.append({'role': 'decoder', 'path': decoder['filename'], 'url': decoder['url'],
                  'expected_bytes': decoder['expected_bytes'], 'identity_algorithm': 'sha256',
                  'expected_digest': decoder['expected_sha256']})
    items.append({'role': 'evaluator_source', 'path': 'trec_eval.tar.gz',
                  'url': 'https://codeload.github.com/usnistgov/trec_eval/tar.gz/' + EVALUATOR_REVISION,
                  'byte_cap': plan['official_evaluator_source_byte_cap']})
    return items


def acquire(output, *, opener=urlopen, clock=time.monotonic):
    plan = load_plan()
    items = items_from_plan(plan)
    output = Path(output).resolve()
    try:
        output.relative_to(ROOT / '_sessions/local')
    except ValueError as error:
        raise AcquisitionError('Raw output must be under ignored _sessions/local') from error
    output.mkdir(parents=True, exist_ok=False)
    start = clock()
    manifest = {'status': 'running', 'input_plan_sha256': PLAN_SHA256,
                'acquirer_sha256': sha256_file(__file__), 'inputs': {}, 'files': [],
                'download_wall_cap_seconds': plan['download_wall_cap_seconds'],
                'network_requests_attempted': 0, 'retries': 0}
    current = None
    try:
        for current in items:
            suffix = Path(current['path']).suffix
            if current['role'] == 'decoder':
                filename = current['path']
            elif current['role'] == 'evaluator_source':
                filename = 'evaluator_source.tar.gz'
            else:
                filename = current['role'] + suffix
            manifest['network_requests_attempted'] += 1
            row = download(current, output / filename,
                           start + plan['download_wall_cap_seconds'], opener=opener, clock=clock)
            row['path'] = str(Path(row['path']).relative_to(ROOT))
            manifest['files'].append(row)
            if current['role'] in {item['role'] for item in plan['inputs']}:
                manifest['inputs'][current['role']] = row['path']
            print(json.dumps({'completed_role': current['role'], 'bytes': row['bytes'],
                              'elapsed_seconds': clock() - start}), flush=True)
        manifest['status'] = 'passed'
    except BaseException as error:
        manifest['status'] = 'failed'
        manifest['failed_role'] = current['role'] if current else None
        manifest['error_type'] = type(error).__name__
        manifest['safe_error'] = str(error) if isinstance(error, AcquisitionError) else 'Transport or process failure'
        raise
    finally:
        manifest['wall_seconds'] = clock() - start
        manifest['partial_files'] = [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size}
                                     for p in sorted(output.glob('*.partial'))]
        with (output / 'manifest.json').open('x') as stream:
            json.dump(manifest, stream, indent=2)
            stream.write('\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    # SIGALRM supplies a hard aggregate wall boundary even inside blocking reads.
    def wall_limit(_signum, _frame):
        raise AcquisitionError('Download wall limit reached')
    previous = signal.signal(signal.SIGALRM, wall_limit)
    signal.alarm(load_plan()['download_wall_cap_seconds'])
    try:
        acquire(args.output)
    except (Exception, KeyboardInterrupt) as error:
        print('Acquisition stopped: ' + type(error).__name__, file=sys.stderr)
        return 1
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
