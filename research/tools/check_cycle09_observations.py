#!/usr/bin/env python3
"""Independent cycle09 empirical audit; no producer/scorer/observer imports.

Reuses previously independent AST and native-frame auditors. Native text stays
private; the only adapted native parser is the strict terminal validity map.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

import check_cycle07_evidence as native_audit
import check_cycle09_evidence as truth_audit


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/cycle09-2026-09-11'
PREPARED_SHA = '0cdb62969bb8a0d365d2b5bd7a225773d938c4a9f66cdc62971d123f62a6d250'
EXECUTION_SHA = '43b5fb9e6bf85b7679a192a48f0f1e66b7091070880c565f0841e1235f96cccc'
PROMPT_SHA = '93c497e29bf96d26eccadb1b1e0f98ae144c29776c3a8fef26aeab1527546ec3'
require, read_json = truth_audit.require, truth_audit.read_json
sha, file_sha, canonical = truth_audit.sha, truth_audit.file_sha, truth_audit.canonical


def parse_map(text, ids):
    if type(text) is not str:
        return None, 'not_text'
    try:
        value = json.loads(text, object_pairs_hook=native_audit.pairs_object,
                           parse_constant=native_audit.reject_constant)
    except (ValueError, UnicodeError, RecursionError) as error:
        return None, str(error) if str(error) in ('duplicate_key', 'nonfinite') else 'invalid_json'
    if type(value) is not dict or set(value) != set(ids):
        return None, 'wrong_id_set'
    if any(type(v) is not bool for v in value.values()):
        return None, 'not_boolean'
    return value, None


def reconstruct_score(fixture, records):
    packets = {row['packet_id']: truth_audit.parse_json(row['payload']) for row in fixture['packets']}
    by_id, rows, per_packet, references = {r['packet_id']: r for r in records}, [], {}, {}
    accepted, invalid = 0, 0
    program_answer = truth_audit.evaluate_program(fixture['program'])['answer']
    for packet_id in ('base', 'repeat'):
        packet, record = packets[packet_id], by_id.get(packet_id)
        ids = packet['original_ids']
        reports = {r['report_id']: r for r in packet['reports'][:3]}
        expected = {rid: truth_audit.check_certificate(packet['program'], reports[rid]['certificate'])['valid'] for rid in ids}
        observed, failure = None, None
        if record is not None:
            if record['native_acceptable'] and record['validity'] is not None:
                observed, error = parse_map(canonical(record['validity']), ids)
                require(error is None and record['parse_failure'] is None, 'strict public decision map')
                accepted += 1
            else:
                require(record['validity'] is None, 'rejected invocation has no imputed validity bits')
                failure = ('native:' + ','.join(record['issues']) if not record['native_acceptable']
                           else 'parse:' + record['parse_failure'])
                invalid += 1
        status = 'accepted' if observed is not None else 'invalid' if record is not None else 'unsent'
        current = [{'packet_id': packet_id, 'original_id': rid, 'expected_validity': expected[rid],
            'returned_validity': observed[rid] if observed is not None else None,
            'correct': observed[rid] is expected[rid] if observed is not None else None,
            'status': status, 'collection_failure': failure} for rid in ids]
        rows.extend(current)
        per_packet[packet_id] = {'correct': sum(row['correct'] is True for row in current),
                                'accepted': 3 if observed is not None else 0, 'planned': 3, 'status': status}
        maps = {'always_valid': dict.fromkeys(ids, True), 'always_invalid': dict.fromkeys(ids, False),
            'exact_checker': expected, 'first_original_only': {rid: rid == ids[0] for rid in ids},
            'final_answer_only': {rid: reports[rid]['certificate']['rows'][-1]['state']['result'] is program_answer for rid in ids}}
        references[packet_id] = {name: {'decisions': decisions,
            'correct': sum(decisions[rid] is expected[rid] for rid in ids), 'valid': 3, 'planned': 3}
            for name, decisions in maps.items()}
    counts = {'correct': sum(row['correct'] is True for row in rows), 'accepted': 3 * accepted, 'planned': 6}
    complete = accepted == 2
    transitions = [{'original_id': base['original_id'], 'base_validity': base['returned_validity'],
        'repeat_validity': repeat['returned_validity'], 'base_correct': base['correct'], 'repeat_correct': repeat['correct']}
        for base, repeat in zip(rows[:3], rows[3:])] if complete else None
    return {'schema_version': 1, 'status': 'complete' if complete else 'partial',
        'full_primary': {'counts': counts, 'transitions': transitions} if complete else None,
        'observed_counts': counts, 'per_packet': per_packet, 'decisions': rows,
        'invocations': {'accepted': accepted, 'invalid': invalid, 'unsent': 2 - len(records), 'planned': 2},
        'reference_policies': references, 'independent_task_count': None,
        'interpretation': 'Six planned judgments repeat three certificates on one program; no population or mechanism inference.'}


def run(public_only=False):
    truth_audit.CHECKS = native_audit.CHECKS = 0
    local = truth_audit.run(BASE / 'prepared')
    require(local['prepared_manifest_sha256'] == PREPARED_SHA, 'original preparation anchor')
    fixture = read_json(BASE / 'prepared/fixture.json')
    seal = read_json(BASE / 'execution/manifest.json')
    require(file_sha(BASE / 'execution/manifest.json') == EXECUTION_SHA
            and seal['prepared_manifest_sha256'] == PREPARED_SHA, 'sealed execution/preparation anchor')
    require(set(seal['artifact_sha256']) == {'system-prompt.txt', 'base.json', 'repeat.json'}, 'execution artifact inventory')
    for name, expected in seal['artifact_sha256'].items():
        require(file_sha(BASE / 'execution' / name) == expected, 'execution artifact bytes ' + name)
    for packet in fixture['packets']:
        require((BASE / 'execution' / (packet['packet_id'] + '.json')).read_bytes() == packet['payload'].encode(),
                'actual sealed packet equals independently verified construction')
    prompt = (BASE / 'execution/system-prompt.txt').read_text()
    require(sha(prompt.encode()) == PROMPT_SHA, 'pre-response exact common prompt')
    require(seal['request_order'] == ['base', 'repeat'] and seal['native_budget_usd'] == '1'
            and seal['call_wall_seconds'] == 120 and seal['batch_wall_seconds'] == 300, 'frozen execution limits/order')
    for name, expected in seal['source_sha256'].items():
        require(file_sha(ROOT / name) == expected, 'sealed source identity ' + name)
    decision = read_json(ROOT / '_sessions/evidence/2026-09-11-cycle09-execution-decision.json')
    require(decision['proceed'] is True and decision['prepared_manifest_sha256'] == PREPARED_SHA
            and decision['maximum_empirical_invocations'] == 2 and decision['empirical_calls_before_decision'] == 0,
            'separate preceding execution decision')
    collection = native_audit.artifact_manifest(BASE / 'observations')
    scoring = native_audit.artifact_manifest(BASE / 'scored', source_fields=False)
    require(collection['execution_manifest_sha256'] == EXECUTION_SHA
            and collection['prepared_manifest_sha256'] == PREPARED_SHA
            and collection['request_order'] == ['base', 'repeat'], 'collection execution anchor')
    expected_sources = dict(seal['source_sha256'])
    expected_sources.update({str((BASE / 'execution' / name).relative_to(ROOT)): file_sha(BASE / 'execution' / name)
                            for name in ('system-prompt.txt', 'base.json', 'repeat.json', 'manifest.json')})
    require(collection['source_sha256_start'] == expected_sources, 'complete collection source and execution custody')
    binary_status = native_audit.check_controls(collection, {'system_prompt': prompt})
    records = read_json(BASE / 'observations/responses.json')
    require(len(records) == collection['invocations_scheduled'] == collection['invocations_observed'] <= 2
            and [r['packet_id'] for r in records] == ['base', 'repeat'][:len(records)], 'bounded immutable invocation prefix')
    packets = {p['packet_id']: p for p in fixture['packets']}
    raw_checks, sessions, messages, costs, spent = [], set(), set(), [], Decimal(0)
    outputs = {'manifest-start.json', 'responses.json'}
    for ordinal, record in enumerate(records, 1):
        pid = record['packet_id']
        names = (f'{ordinal:02d}-attempt.json', f'{ordinal:02d}-{pid}.json')
        outputs.update(names)
        attempt = read_json(BASE / 'observations' / names[0])
        require(read_json(BASE / 'observations' / names[1]) == record, 'individual/combined record identity')
        require(record['ordinal'] == ordinal and record['payload_sha256'] == packets[pid]['payload_sha256']
                and record['system_prompt_sha256'] == PROMPT_SHA, 'record actual payload and prompt custody')
        for key in ('ordinal', 'packet_id', 'session_id', 'started_utc', 'payload_sha256', 'system_prompt_sha256'):
            require(record[key] == attempt[key], 'write-ahead attempt field ' + key)
        require(Decimal(record['scheduled_remaining_native_usd']) == Decimal(attempt['remaining_native_usd']) == 1 - spent
                and spent < 1 and record['scheduled_timeout_seconds'] == attempt['timeout_seconds']
                and 0 < attempt['timeout_seconds'] <= 120, 'remaining native allowance and timeout')
        require(record['session_id'] not in sessions and not messages.intersection(record['messages']), 'fresh session/message identities')
        sessions.add(record['session_id']); messages.update(record['messages'])
        require(record['native_acceptable'] == (not record['issues']), 'public native gate consistency')
        if record['native_acceptable']:
            require(record['exit_code'] == 0 and not record['timed_out'] and record['native_subtype'] == 'success'
                    and record['native_is_error'] is False and record['native_stop_reason'] == 'end_turn'
                    and record['terminal_session_id'] == record['session_id'], 'public accepted terminal fields')
            init = record['init']
            allowed = (native_audit.MODEL, native_audit.MODEL + '[1m]')
            require(init['model'] in allowed and init['tools'] == [] and init['mcp_servers'] == []
                    and not init['skills'] and not init['plugins'] and record['observed_models']
                    and all(model in allowed for model in record['observed_models']), 'public observed model and context surfaces')
            require(record['distinct_observed_message_count'] == len(record['messages'])
                    and not record['provider_refusals'] and not record['local_error_records'], 'public message/refusal accounting')
            for message in record['messages'].values():
                output = message['usage'].get('output_tokens')
                require(message['model'] in allowed and (output is None or type(output) is int and 0 <= output <= 500),
                        'public per-message model/output ceiling')
            require(all(stat['field'] in ('subagent_stats', 'subagentStats')
                        and native_audit.typed_shape(stat['counts'], native_audit.ZERO_STATS)
                        for stat in record['subagent_statistics']), 'public typed zero-agent telemetry')
            require((record['validity'] is None) == (record['parse_failure'] is not None), 'public map/parse exclusivity')
        if not record['native_acceptable'] or record['validity'] is None or record['interrupted']:
            require(ordinal == len(records), 'first collection failure stops later scheduling')
        for key in ('stdout_path', 'stderr_path'):
            require(record[key].startswith('_sessions/local/cycle09/')
                    and (ROOT / record[key]).parent == ROOT / collection['private_directory'], 'private stream boundary')
        ids = truth_audit.parse_json(packets[pid]['payload'])['original_ids']
        # Reuse the independently authored native-frame implementation unchanged
        # on disk. Its acceptance gates are parser-independent. Adapt the record
        # name and terminal parser in memory, then restore the original callable.
        original_parser = native_audit.boolean_answer
        try:
            native_audit.boolean_answer = lambda text: parse_map(text, ids)
            raw_checks.append(native_audit.check_raw(dict(record, answer=record['validity']), public_only))
        finally:
            native_audit.boolean_answer = original_parser
        cost = Decimal(record['native_cost_usd']) if record['native_cost_usd'] is not None else None
        require(cost is None or cost.is_finite() and cost >= 0, 'finite observed native accounting')
        if cost is not None:
            spent += cost
        costs.append(cost)
    require(set(collection['output_sha256']) == outputs, 'complete acquisition output inventory')
    require(Decimal(collection['known_native_cost_usd']) == spent
            and collection['all_observed_costs_known'] == all(cost is not None for cost in costs), 'total cost and coverage')
    expected = reconstruct_score(fixture, records)
    require(canonical(read_json(BASE / 'scored/scores.json')) == canonical(expected), 'all scores, baselines, transitions and denominators')
    require(scoring['measurement_status'] == expected['status'] and scoring['coverage'] == expected['observed_counts']
            and collection['valid_predictions'] == expected['invocations']['accepted'], 'manifest score/coverage summaries')
    stop = collection['stop_reason']
    valid_stops = {'all_invocations_finished': expected['invocations']['accepted'] == 2 and not any(r['interrupted'] for r in records),
        'invalid_answer': bool(records) and records[-1]['native_acceptable'] and records[-1]['validity'] is None,
        'native_or_configuration_failure': bool(records) and not records[-1]['native_acceptable'],
        'interrupted': bool(records) and records[-1]['interrupted'],
        'native_budget_exhausted': len(records) < 2 and spent >= 1,
        'batch_wall_exhausted': len(records) < 2 and collection['wall_seconds'] >= 300}
    require(stop in valid_stops and valid_stops[stop], 'recorded stopping rule')
    unavailable = sum(row['status'] == 'unavailable' for row in raw_checks)
    usages = [record['usage'] for record in records]
    all_messages = [message for record in records for message in record['messages'].values()]
    return {'schema_version': 1, 'status': 'passed_public_only' if unavailable else 'passed',
        'checked_utc': datetime.now(timezone.utc).isoformat(), 'checks_passed': truth_audit.CHECKS + native_audit.CHECKS,
        'checker_sha256': file_sha(Path(__file__)), 'independent_helper_sha256': {
            Path(module.__file__).name: file_sha(Path(module.__file__)) for module in (truth_audit, native_audit)},
        'prepared_manifest_sha256': PREPARED_SHA, 'execution_manifest_sha256': EXECUTION_SHA,
        'collection_manifest_sha256': file_sha(BASE / 'observations/manifest.json'),
        'scoring_manifest_sha256': file_sha(BASE / 'scored/manifest.json'),
        'raw_streams_verified': len(records) - unavailable, 'raw_streams_unavailable': unavailable,
        'native_binary_bytes': binary_status, 'raw_checks': raw_checks, 'score_check': expected,
        'accounting': {'native_cost_usd': str(spent), 'all_observed_costs_known': all(c is not None for c in costs),
            'collection_wall_seconds': collection['wall_seconds'], 'provider_message_count': len(all_messages),
            'messages_per_invocation': [len(record['messages']) for record in records],
            'output_tokens': sum(usage.get('output_tokens', 0) for usage in usages),
            'thinking_tokens': sum(usage.get('output_tokens_details', {}).get('thinking_tokens', 0) for usage in usages),
            'missing_thinking_counters': sum('thinking_tokens' not in usage.get('output_tokens_details', {}) for usage in usages),
            'max_observed_message_output_tokens': max((m['usage'].get('output_tokens', 0) for m in all_messages), default=None)},
        'limitations': ['Six judgments repeat three originals on one all-zero program; not six independent tasks.',
            'First-original-only is also perfect here; correct bits do not identify verification strategy.',
            'F-only copies add text and a provenance cue; this is not a pure copying causal contrast.',
            'Raw streams are explicitly unverified when absent or --public-only is used.',
            'Missing usage counters remain unverified; native cost is not subscription billing.',
            'The raw-frame and AST helpers are independent checkers, not empirical production implementations.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-only', action='store_true')
    parser.add_argument('--output', type=Path, help='Write a new receipt; never overwrite')
    args = parser.parse_args()
    result = run(args.public_only)
    if args.output:
        with args.output.open('x', encoding='utf-8') as handle:
            json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write('\n')
    print(json.dumps({key: result[key] for key in ('status', 'checks_passed', 'raw_streams_verified', 'raw_streams_unavailable')}))


if __name__ == '__main__':
    main()
