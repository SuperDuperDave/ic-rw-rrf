#!/usr/bin/env python3
"""Score the separate replication with the frozen cycle05 scoring rules."""
import score_cycle05_coordinator as original
from evaluation import cycle05_coordinator_packets as packets

_validate = packets.validate_fixture_custody


def validate_shared_preparation(unused_path, manifest_hash):
    # Exact original payloads/references; no copied or regenerated preparation.
    return _validate(original.ROOT / 'results/cycle05-2026-09-10/prepared', manifest_hash)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--score', action='store_true', required=True)
    parser.parse_args()
    original.BASE = original.ROOT / 'results/cycle05-replication-2026-09-10'
    packets.validate_fixture_custody = validate_shared_preparation
    original.score()
