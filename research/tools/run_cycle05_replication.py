#!/usr/bin/env python3
"""Separately frozen cycle05 replication correcting zero-agent metadata parsing.

Reuse the frozen collector without editing its historical source. This adapter
changes measurement parsing and output custody only; provider controls, payloads,
order, model, effort, and budgets remain the original constants.
"""
import json
from pathlib import Path
import run_cycle05_coordinator as original

ZERO_STATS = {
    'spawned': 0, 'requested': {'background': 0, 'foreground': 0, 'unset': 0},
    'started_in_background': 0, 'max_depth': 0, 'spawned_by_subagents': 0,
    'completed': 0, 'failed': 0, 'killed': {'parent': 0, 'user': 0, 'system': 0},
    'refused': {'depth_limit': 0, 'concurrency_limit': 0, 'budget': 0}, 'by_type': {},
}
_inspect = original.inspect_stream
_sources = original.sources


def exact_zero_stats(value, shape=ZERO_STATS):
    if type(shape) is dict:
        return type(value) is dict and set(value) == set(shape) and all(
            exact_zero_stats(value[key], child) for key, child in shape.items())
    return type(value) is int and value == 0


def inspect_stream(raw, exit_code, expected_session, timed_out=False):
    """Recognize the observed zero-count schema; keep all activity gates."""
    observed, schema_issue = [], False
    try:
        events = [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
        for event in events:
            if isinstance(event, dict) and event.get('type') == 'result':
                for key in ('subagent_stats', 'subagentStats'):
                    if key in event:
                        stats = event[key]
                        observed.append({'field': key, 'counts': stats})
                        if exact_zero_stats(stats):
                            del event[key]
                        else:
                            schema_issue = True
        inspected_bytes = ('\n'.join(json.dumps(e) for e in events)).encode('utf-8')
    except (ValueError, UnicodeError):
        inspected_bytes = raw
    result = _inspect(inspected_bytes, exit_code, expected_session, timed_out)
    # Only the known numeric-count shape is published; unknown content remains
    # in the original private stream with an explicit failure, never copied out.
    result['subagent_statistics'] = [item for item in observed if exact_zero_stats(item['counts'])]
    if schema_issue:
        result['issues'] = sorted(set(result['issues'] + ['subagent_statistics_nonzero_or_unknown']))
        result['native_acceptable'] = False
        result['p_positive'] = None
        result['parse_failure'] = None
    return result


def sources():
    fixture, identities = _sources()
    extra = [Path(__file__), original.ROOT / '_sessions/tools/tests/test_cycle05_replication.py',
             original.ROOT / '_sessions/tools/score_cycle05_replication.py',
             original.ROOT / '_sessions/tools/score_cycle05_coordinator.py',
             original.ROOT / '_sessions/cycles/2026-09-10-cycle05-replication-protocol.md',
             original.ROOT / 'results/cycle05-2026-09-10/observations/manifest.json',
             original.ROOT / 'results/cycle05-2026-09-10/scored/manifest.json']
    identities.update({str(path.relative_to(original.ROOT)): original.digest(path) for path in extra})
    return fixture, identities


def configure():
    original.OUTPUT = original.ROOT / 'results/cycle05-replication-2026-09-10/observations'
    original.inspect_stream = inspect_stream
    original.sources = sources


if __name__ == '__main__':
    configure()
    original.main()
