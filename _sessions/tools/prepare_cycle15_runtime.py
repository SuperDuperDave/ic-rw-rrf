#!/usr/bin/env python3
"""Unpack verified local support artifacts and build the pinned evaluator.

No network, global installation or SciFact parsing. Keep extracted artifacts
ignored; the small receipt contains only build and identity facts.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from acquire_cycle15_inputs import EVALUATOR_REVISION, PLAN_SHA256, load_plan, sha256_file


def prepare(acquisition, output, receipt_path):
    plan = load_plan()
    acquisition = Path(acquisition).resolve()
    receipt_path = Path(receipt_path).resolve()
    if receipt_path.exists():
        raise ValueError('Build receipt already exists')
    manifest = json.loads(acquisition.read_text())
    if manifest['status'] != 'passed' or manifest['input_plan_sha256'] != PLAN_SHA256:
        raise ValueError('Acquisition is not the completed frozen plan')
    if sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 12):
        raise ValueError('Pinned decoder requires CPython3.12')
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ValueError('Pinned decoder requires Linux x86_64')
    libc, version = platform.libc_ver()
    if libc != 'glibc' or tuple(map(int, version.split('.')[:2])) < (2, 28):
        raise ValueError('Pinned decoder requires glibc2.28+')
    rows = {row['role']: row for row in manifest['files']}
    support = {}
    for role in ('decoder', 'evaluator_source'):
        row = rows[role]
        path = ROOT / row['path']
        if path.stat().st_size != row['bytes'] or sha256_file(path) != row['sha256']:
            raise ValueError('Support artifact differs from acquisition receipt')
        support[role] = path
    decoder = plan['optional_parquet_decoder']
    if (rows['decoder']['sha256'] != decoder['expected_sha256'] or
            rows['decoder']['bytes'] != decoder['expected_bytes']):
        raise ValueError('Decoder differs from the pinned wheel')
    if rows['evaluator_source']['bytes'] > plan['official_evaluator_source_byte_cap']:
        raise ValueError('Evaluator archive exceeds cap')
    output = Path(output).resolve()
    output.relative_to(ROOT / '_sessions/local')
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    receipt = {'status': 'running', 'evaluator_revision': EVALUATOR_REVISION,
               'acquisition_manifest_sha256': sha256_file(acquisition),
               'source_archive_sha256': rows['evaluator_source']['sha256'],
               'decoder_wheel_sha256': rows['decoder']['sha256'],
               'setup_source_sha256': sha256_file(__file__)}
    try:
        decoder_dir = output / 'decoder'
        with zipfile.ZipFile(support['decoder']) as archive:
            members = archive.infolist()
            if sum(item.file_size for item in members) > 500_000_000:
                raise ValueError('Expanded decoder exceeds setup cap')
            for item in members:
                path = PurePosixPath(item.filename)
                if path.is_absolute() or '..' in path.parts or '\\' in item.filename:
                    raise ValueError('Unsupported decoder archive path')
            archive.extractall(decoder_dir)
        with tarfile.open(support['evaluator_source'], 'r:gz') as archive:
            members = archive.getmembers()
            prefix = 'trec_eval-' + EVALUATOR_REVISION
            if sum(item.size for item in members) > 100_000_000:
                raise ValueError('Expanded evaluator exceeds setup cap')
            for item in members:
                path = PurePosixPath(item.name)
                if (not path.parts or path.parts[0] != prefix or '..' in path.parts or
                        not (item.isfile() or item.isdir())):
                    raise ValueError('Unsupported evaluator archive member')
            archive.extractall(output, filter='data')
        source = output / prefix
        pinned = json.loads((ROOT / '_sessions/evidence/2026-09-11-cycle14-metric-sources.json').read_text())
        metric_hash = sha256_file(source / 'm_ndcg_cut.c')
        if metric_hash != pinned['sources']['trec_eval']['source_sha256']:
            raise ValueError('Evaluator metric source differs from pinned source')
        local_metric = sha256_file(ROOT / 'evaluation/trec_eval_harness.py')
        if local_metric != pinned['local_sources']['evaluation/trec_eval_harness.py']:
            raise ValueError('Local metric source changed before fixture')
        command = ['make', '-C', str(source.relative_to(ROOT))]
        build = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=120)
        (output / 'build.stdout').write_bytes(build.stdout)
        (output / 'build.stderr').write_bytes(build.stderr)
        receipt['build_exit_code'] = build.returncode
        if build.returncode:
            raise ValueError('Official evaluator build failed')
        sys.path.insert(0, str(decoder_dir))
        import pyarrow
        if pyarrow.__version__ != decoder['version']:
            raise ValueError('Observed decoder version mismatch')
        binary = source / 'trec_eval'
        receipt.update(status='passed', source_directory=str(source.relative_to(ROOT)),
                       binary_path=str(binary.relative_to(ROOT)), binary_sha256=sha256_file(binary),
                       metric_source_sha256=metric_hash, local_metric_sha256=local_metric,
                       build_command=command, decoder_path=str(decoder_dir.relative_to(ROOT)),
                       observed_decoder_version=pyarrow.__version__,
                       decoder_import_path=str(Path(pyarrow.__file__).relative_to(ROOT)),
                       python_version=sys.version, platform=platform.platform())
    except BaseException as error:
        receipt.update(status='failed', error_type=type(error).__name__)
        raise
    finally:
        receipt['wall_seconds'] = time.monotonic() - start
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        with receipt_path.open('x') as stream:
            json.dump(receipt, stream, indent=2)
            stream.write('\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acquisition', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--receipt', required=True)
    args = parser.parse_args()
    try:
        value = prepare(args.acquisition, args.output, args.receipt)
    except (Exception, KeyboardInterrupt) as error:
        receipt = Path(args.receipt)
        if not receipt.exists():
            receipt.parent.mkdir(parents=True, exist_ok=True)
            with receipt.open('x') as stream:
                json.dump({'status': 'failed_before_runtime_prepare',
                           'error_type': type(error).__name__,
                           'scifact_parsing_or_effectiveness_started': False}, stream, indent=2)
                stream.write('\n')
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__}))
        return 1
    print(json.dumps({'status': value['status'], 'evaluator_revision': EVALUATOR_REVISION,
                      'decoder_version': value['observed_decoder_version']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
