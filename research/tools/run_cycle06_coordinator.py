#!/usr/bin/env python3
"""Run the frozen eight-input cycle06 batch with the audited native driver."""
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import argparse
import json
import sys

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]
sys.path.insert(0, str(ROOT))
import run_cycle05_coordinator as driver
import run_cycle05_replication as telemetry
from evaluation import cycle05_coordinator_packets as strict
from evaluation import cycle06_noisy_lineage as experiment

BASE = ROOT / 'results/cycle06-2026-09-10'
PREPARED = BASE / 'prepared'
PREPARED_SHA = 'dc3d6ac723ac0551e46b3f1e6a12a56d727b8010961ec764d0c8dc80fe89d5f4'
SHARED = {
    '_sessions/tools/run_cycle05_coordinator.py': 'e3b49dce410beab317235445851d73a89fc2a21efff7a56ed74d2d8cfdce25f2',
    '_sessions/tools/run_cycle05_replication.py': '9fe3c83e1e5f157d0d9b3a913dd7006edd4c288ee3f003502421bcf15c3f2706',
}


def sources():
    fixture, manifest = experiment.validate_fixture_custody(PREPARED, PREPARED_SHA)
    if len(fixture['request_order']) != 8 or len(set(fixture['request_order'])) != 8:
        raise ValueError('cycle06 must contain exactly eight unique inputs')
    paths = [Path(__file__), TOOLS / 'tests/test_cycle06_runner.py',
             TOOLS / 'score_cycle06_coordinator.py',
             TOOLS / 'score_cycle05_coordinator.py',
             ROOT / '_sessions/cycles/2026-09-10-cycle05-native-controls.md',
             ROOT / '_sessions/cycles/2026-09-10-cycle06-execution-protocol.md',
             ROOT / '_sessions/tools/tests/test_cycle05_runner.py',
             ROOT / '_sessions/tools/tests/test_cycle05_replication.py',
             ROOT / 'evaluation/cycle05_coordinator_packets.py',
             PREPARED / 'fixture.json', PREPARED / 'manifest.json']
    identities = dict(manifest['source_sha256_start'])
    identities.update({str(path.relative_to(ROOT)): driver.digest(path) for path in paths})
    for path, expected in SHARED.items():
        observed = driver.digest(ROOT / path)
        if observed != expected:
            raise ValueError('preserved native implementation changed: ' + path)
        identities[path] = observed
    return fixture, identities


@contextmanager
def configured_driver():
    """Scope the new experiment settings; do not mutate historical source files."""
    changes = {
        'OUTPUT': BASE / 'observations', 'PREPARED': PREPARED,
        'PREPARED_SHA': PREPARED_SHA, 'CAP': Decimal('1'),
        'CALL_SECONDS': 120, 'BATCH_SECONDS': 300, 'sources': sources,
        'inspect_stream': telemetry.inspect_stream,
        'packets': SimpleNamespace(validate_payload=experiment.validate_payload,
                                  parse_probability=strict.parse_probability,
                                  ProbabilityParseError=strict.ProbabilityParseError),
    }
    saved = {key: getattr(driver, key) for key in changes}
    try:
        for key, value in changes.items():
            setattr(driver, key, value)
        yield driver
    finally:
        for key, value in saved.items():
            setattr(driver, key, value)


def collect():
    with configured_driver() as collector:
        return collector.collect()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collect', action='store_true', required=True,
                        help='Run one frozen provider batch; no overwrite or resume')
    parser.parse_args()
    result = collect()
    print(json.dumps({k: result[k] for k in ('status', 'stop_reason', 'invocations_observed',
                                           'valid_predictions', 'known_native_cost_usd')}))
