#!/usr/bin/env python3
"""Independent cycle11 atomic-response, score and native-custody audit.

No producer/scorer/observer imports. Missing private streams are explicitly
unverified. Only permitted metadata and returned decisions enter the receipt.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

import check_cycle07_evidence as native
import check_cycle11_evidence as local


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/cycle11-2026-09-11'
ORDER = local.ORDER
PROMPT_SHA = 'd5406ddd3d64ed6b067e786e72383afff8be2d8d4f91608bde8d85f982da7b2a'
require, same, read_json = local.require, local.same, local.read_json
canonical, file_sha = local.canonical, local.file_sha
RECORD_FIELDS = set('ordinal packet_id session_id started_utc finished_utc payload_sha256 '
    'system_prompt_sha256 scheduled_remaining_native_usd scheduled_timeout_seconds exit_code wall_seconds '
    'timed_out interrupted stdout_path stderr_path stdout_sha256 stderr_sha256 issues native_acceptable '
    'response parse_failure init native_subtype native_is_error native_stop_reason terminal_session_id '
    'terminal_text_sha256 num_turns native_cost_usd usage model_usage messages distinct_observed_message_count '
    'subagent_statistics local_error_records provider_refusals observed_models requesting_status_count recovery_markers'.split())


def parse_response(text, ids):
    if type(text) is not str:
        return None, 'not_text'
    try:
        value = json.loads(text, object_pairs_hook=native.pairs_object, parse_constant=native.reject_constant)
    except (ValueError, UnicodeError, RecursionError) as error:
        return None, str(error) if str(error) in ('duplicate_key', 'nonfinite') else 'invalid_json'
    if type(value) is not dict or set(value) != {'answer', 'validity'}:
        return None, 'wrong_outer_keys'
    if type(value['answer']) is not bool:
        return None, 'answer_not_boolean'
    if type(value['validity']) is not dict or set(value['validity']) != set(ids):
        return None, 'wrong_id_set'
    if any(type(bit) is not bool for bit in value['validity'].values()):
        return None, 'validity_not_boolean'
    return value, None


def reconstruct_score(fixture, records):
    require([r['packet_id'] for r in records] == ORDER[:len(records)] and len(records) <= 4,
            'unique prefix of the four planned packets')
    packets = {p['packet_id']: p for p in fixture['packets']}
    observed_by_id = {r['packet_id']: r for r in records}
    answers, validities, diagnostics, reference_answers, reference_validities = [], [], {}, {}, {}
    accepted = invalid = 0
    for pid in ORDER:
        packet = packets[pid]
        payload = local.parse_json(packet['payload'])
        answer_map, validity_maps = local.reference_maps(payload)
        expected_answer, expected_validity = answer_map['exact_replay'], validity_maps['exact_checker']
        for name, value in answer_map.items():
            reference_answers.setdefault(name, []).append(value)
        for name, decisions in validity_maps.items():
            reference_validities.setdefault(name, []).extend(decisions[sid] for sid in payload['submission_ids'])
        record, response, failure = observed_by_id.get(pid), None, None
        if record is not None:
            if record['native_acceptable'] and record['response'] is not None:
                response, error = parse_response(canonical(record['response']), payload['submission_ids'])
                require(error is None and record['parse_failure'] is None, 'atomic accepted response schema')
                accepted += 1
            else:
                require(record['response'] is None, 'invalid response contributes no salvaged answer or validity bits')
                require(not record['native_acceptable'] or type(record['parse_failure']) is str, 'format failure has a cause')
                failure = ('native:' + ','.join(record['issues']) if not record['native_acceptable']
                           else 'parse:' + record['parse_failure'])
                invalid += 1
        status = 'accepted' if response is not None else 'invalid' if record is not None else 'unsent'
        common = {'packet_id': pid, 'program_id': packet['program_id'], 'regime': pid[-1],
                  'status': status, 'collection_failure': failure}
        answer_correct = response['answer'] is expected_answer if response is not None else None
        answers.append({**common, 'expected_answer': expected_answer,
                        'returned_answer': response['answer'] if response is not None else None, 'correct': answer_correct})
        current, root_decisions, endpoints = [], {}, set()
        for position, (label, report) in enumerate(zip(packet['private_order'], payload['reports'][:4]), 1):
            sid, root = report['report_id'], report['root_id']
            returned = response['validity'][sid] if response is not None else None
            current.append({**common, 'submission_id': sid, 'root_id': root, 'private_type': label, 'position': position,
                'expected_validity': expected_validity[sid], 'returned_validity': returned,
                'correct': returned is expected_validity[sid] if response is not None else None})
            if response is not None:
                root_decisions.setdefault(root, []).append(returned)
                if returned:
                    endpoints.add(report['certificate']['rows'][-1]['state']['result'])
        validities.extend(current)
        diagnostics[pid] = None
        if response is not None:
            diagnostics[pid] = {'answer_correct': answer_correct,
                'all_validities_correct': all(row['correct'] for row in current),
                'accepted_support_endpoints': sorted(endpoints),
                'answer_support_consistent': response['answer'] in endpoints if len(endpoints) == 1 else None,
                'undefined_reason': 'no-accepted-support' if not endpoints else 'conflicting-support' if len(endpoints) > 1 else None,
                'root_copy_disagreements': {root: len(set(bits)) > 1 for root, bits in root_decisions.items()}}
    answer_truth = [row['expected_answer'] for row in answers]
    validity_truth = [row['expected_validity'] for row in validities]
    reference_totals = {
        'answer': {name: {'correct': sum(v is t for v, t in zip(vector, answer_truth)),
            'answered': sum(v is not None for v in vector), 'planned': 4, 'abstained': sum(v is None for v in vector),
            'vector': vector} for name, vector in reference_answers.items()},
        'validity': {name: {'correct': sum(v is t for v, t in zip(vector, validity_truth)),
            'valid': 16, 'planned': 16, 'vector': vector} for name, vector in reference_validities.items()}}
    counts = {name: {'correct': sum(row['correct'] is True for row in rows),
        'accepted': sum(row['status'] == 'accepted' for row in rows), 'planned': len(rows)}
        for name, rows in (('answers', answers), ('validities', validities))}
    return {'schema_version': 1, 'status': 'complete' if accepted == 4 else 'partial',
        'full_primary': counts if accepted == 4 else None, 'observed_counts': counts,
        'answers': answers, 'validities': validities, 'diagnostics': diagnostics,
        'invocations': {'attempted': len(records), 'accepted': accepted, 'invalid': invalid,
                        'unsent': 4 - len(records), 'planned': 4}, 'reference_policy_totals': reference_totals,
        'independent_task_count': None,
        'interpretation': 'Four reused-root packets on two program variants; output decisions and consistency do not identify internal strategy or multiagent benefit.'}

def run(prepared_sha, execution_sha, public_only=False, base=BASE):
    local.CHECKS = local.parent_audit.CHECKS = local.truth.CHECKS = native.CHECKS = 0
    require(local.run(base / 'prepared')['prepared_manifest_sha256'] == prepared_sha, 'pre-observation preparation anchor')
    fixture = read_json(base / 'prepared/fixture.json')
    seal = read_json(base / 'execution/manifest.json')
    require(file_sha(base / 'execution/manifest.json') == execution_sha
            and seal['prepared_manifest_sha256'] == prepared_sha, 'separate sealed execution anchor')
    execution_files = {'system-prompt.txt'} | {pid + '.json' for pid in ORDER}
    require(set(seal['artifact_sha256']) == execution_files, 'exact execution artifact inventory')
    for name, digest in seal['artifact_sha256'].items():
        require(file_sha(base / 'execution' / name) == digest, 'execution bytes ' + name)
    for packet in fixture['packets']:
        require((base / 'execution' / (packet['packet_id'] + '.json')).read_bytes() == packet['payload'].encode(),
                'actual sealed packet equals independent local construction')
    prompt = (base / 'execution/system-prompt.txt').read_text()
    require(local.sha(prompt.encode()) == PROMPT_SHA, 'frozen atomic answer-and-validity instruction')
    require(seal['request_order'] == ORDER and seal['native_budget_usd'] == '1'
            and seal['call_wall_seconds'] == 120 and seal['batch_wall_seconds'] == 300, 'execution limits/order')
    expected_sources = (local.parent_audit.SOURCE_FILES | local.NEW_SOURCES) | {
        '_sessions/tools/run_cycle11_verifier.py', 'evaluation/cycle11_verifier.py',
        '_sessions/tools/tests/test_cycle11_runner.py', '_sessions/tools/score_cycle11_verifier.py',
        '_sessions/cycles/2026-09-11-cycle11-execution-protocol.md',
        '_sessions/evidence/2026-09-11-cycle11-execution-decision.json',
        '_sessions/tools/tests/test_native_stream_observer.py', 'evaluation/cycle09_verifier.py',
        '_sessions/tools/run_cycle09_verifier.py', '_sessions/tools/score_cycle09_verifier.py',
        '_sessions/tools/tests/test_cycle09_runner.py',
        '_sessions/tools/run_cycle05_coordinator.py', '_sessions/tools/run_cycle05_replication.py',
        '_sessions/tools/native_stream_observer.py', 'evaluation/cycle05_coordinator_packets.py',
        str((base / 'prepared/fixture.json').relative_to(ROOT)), str((base / 'prepared/manifest.json').relative_to(ROOT))}
    require(set(seal['source_sha256']) == expected_sources, 'complete execution dependency inventory')
    for name, digest in seal['source_sha256'].items():
        require(file_sha(ROOT / name) == digest, 'sealed execution source ' + name)
    decision = read_json(ROOT / '_sessions/evidence/2026-09-11-cycle11-execution-decision.json')
    require(decision['proceed'] is True and decision['prepared_manifest_sha256'] == prepared_sha
            and decision['maximum_empirical_invocations'] == 4 and decision['empirical_calls_before_decision'] == 0,
            'separate preceding four-call execution decision')
    collection = native.artifact_manifest(base / 'observations')
    scoring = native.artifact_manifest(base / 'scored', source_fields=False)
    require(collection['execution_manifest_sha256'] == execution_sha
            and collection['prepared_manifest_sha256'] == prepared_sha and collection['request_order'] == ORDER,
            'collection execution anchor')
    identities = dict(seal['source_sha256'])
    identities.update({str((base / 'execution' / name).relative_to(ROOT)): file_sha(base / 'execution' / name)
                       for name in execution_files | {'manifest.json'}})
    same(collection['source_sha256_start'], identities, 'complete collection source/execution custody')
    binary_status = native.check_controls(collection, {'system_prompt': prompt})
    require(seal['native_binary_sha256'] == collection['native_binary_sha256'], 'execution/collection binary identity')
    records = read_json(base / 'observations/responses.json')
    require(len(records) == collection['invocations_scheduled'] == collection['invocations_observed'] <= 4
            and [r['packet_id'] for r in records] == ORDER[:len(records)], 'bounded immutable invocation prefix')
    packets = {p['packet_id']: p for p in fixture['packets']}
    raw_checks, sessions, messages, costs, spent = [], set(), set(), [], Decimal(0)
    outputs = {'manifest-start.json', 'responses.json'}
    for ordinal, record in enumerate(records, 1):
        require(set(record) == RECORD_FIELDS and all(set(message) == {'model', 'stop_reason', 'usage'}
                for message in record['messages'].values()), 'public metadata schema excludes provider thought/text')
        pid = record['packet_id']
        attempt_name, record_name = f'{ordinal:02d}-attempt.json', f'{ordinal:02d}-{pid}.json'
        outputs.update((attempt_name, record_name))
        same(read_json(base / 'observations' / record_name), record, 'individual/combined record identity')
        attempt = read_json(base / 'observations' / attempt_name)
        require(record['ordinal'] == ordinal and record['payload_sha256'] == packets[pid]['payload_sha256']
                and record['system_prompt_sha256'] == PROMPT_SHA, 'record payload/prompt identity')
        for key in ('ordinal', 'packet_id', 'session_id', 'started_utc', 'payload_sha256', 'system_prompt_sha256'):
            same(record[key], attempt[key], 'write-ahead attempt ' + key)
        require(Decimal(record['scheduled_remaining_native_usd']) == Decimal(attempt['remaining_native_usd']) == 1 - spent
                and spent < 1 and record['scheduled_timeout_seconds'] == attempt['timeout_seconds']
                and 0 < attempt['timeout_seconds'] <= 120, 'remaining allowance and timeout')
        require(record['session_id'] not in sessions and not messages.intersection(record['messages']), 'fresh session/message IDs')
        sessions.add(record['session_id'])
        messages.update(record['messages'])
        require(record['native_acceptable'] is (not record['issues']), 'strict public native gate consistency')
        if record['native_acceptable']:
            require(record['exit_code'] == 0 and not record['timed_out'] and record['native_subtype'] == 'success'
                    and record['native_is_error'] is False and record['native_stop_reason'] == 'end_turn'
                    and record['terminal_session_id'] == record['session_id'], 'public accepted terminal fields')
            allowed, init = (native.MODEL, native.MODEL + '[1m]'), record['init']
            require(init['model'] in allowed and init['tools'] == [] and init['mcp_servers'] == []
                    and not init['skills'] and not init['plugins'] and record['observed_models']
                    and all(model in allowed for model in record['observed_models']), 'public model and empty context surfaces')
            require(record['distinct_observed_message_count'] == len(record['messages'])
                    and not record['provider_refusals'] and not record['local_error_records'], 'message/refusal/error accounting')
            for message in record['messages'].values():
                output = message['usage'].get('output_tokens')
                require(message['model'] in allowed and (output is None or type(output) is int and 0 <= output <= 500),
                        'per-message model/output bound')
            require(all(stat['field'] in ('subagent_stats', 'subagentStats') and native.typed_shape(stat['counts'], native.ZERO_STATS)
                        for stat in record['subagent_statistics']), 'typed zero-agent telemetry')
            require((record['response'] is None) == (record['parse_failure'] is not None), 'map/parse exclusivity')
        else:
            require(record['response'] is None and record['parse_failure'] is None, 'native failure supplies no parsed judgment')
        if not record['native_acceptable'] or record['response'] is None or record['interrupted']:
            require(ordinal == len(records), 'first collection failure stops scheduling')
        for key in ('stdout_path', 'stderr_path'):
            require(record[key].startswith('_sessions/local/cycle11/')
                    and (ROOT / record[key]).parent == ROOT / collection['private_directory'], 'private stream boundary')
        ids = local.parse_json(packets[pid]['payload'])['submission_ids']
        old_parser = native.boolean_answer
        try:
            native.boolean_answer = lambda text: parse_response(text, ids)
            raw_checks.append(native.check_raw(dict(record, answer=record['response']), public_only))
        finally:
            native.boolean_answer = old_parser
        cost = Decimal(record['native_cost_usd']) if record['native_cost_usd'] is not None else None
        require(cost is None or cost.is_finite() and cost >= 0, 'finite native cost')
        if cost is not None:
            spent += cost
        costs.append(cost)
    require(set(collection['output_sha256']) == outputs, 'complete acquisition output inventory')
    require(Decimal(collection['known_native_cost_usd']) == spent
            and collection['all_observed_costs_known'] is all(cost is not None for cost in costs), 'cost sum/coverage')
    expected = reconstruct_score(fixture, records)
    same(read_json(base / 'scored/scores.json'), expected, 'all four answers, sixteen validity judgments, support diagnostics, references and partial semantics')
    require(scoring['measurement_status'] == expected['status'] and scoring['coverage'] == expected['observed_counts']
            and collection['valid_predictions'] == expected['invocations']['accepted'], 'manifest score/coverage summaries')
    require(set(scoring['output_sha256']) == {'manifest-start.json', 'scores.json'}
            and set(scoring['input_sha256']) == {str((base / 'observations' / name).relative_to(ROOT))
                for name in ('manifest.json', 'responses.json')} | {'_sessions/tools/score_cycle11_verifier.py'}, 'scoring input/output inventory')
    stops = {'all_invocations_finished': expected['invocations']['accepted'] == 4 and not any(r['interrupted'] for r in records),
        'invalid_answer': bool(records) and records[-1]['native_acceptable'] and records[-1]['response'] is None,
        'native_or_configuration_failure': bool(records) and not records[-1]['native_acceptable'],
        'interrupted': bool(records) and records[-1]['interrupted'],
        'native_budget_exhausted': len(records) < 4 and spent >= 1,
        'batch_wall_exhausted': len(records) < 4 and collection['wall_seconds'] >= 300}
    require(collection['stop_reason'] in stops and stops[collection['stop_reason']], 'recorded stopping rule')
    unavailable = sum(row['status'] == 'unavailable' for row in raw_checks)
    usages = [record['usage'] for record in records]
    all_messages = [message for record in records for message in record['messages'].values()]
    return {'schema_version': 1, 'status': 'passed_public_only' if public_only or unavailable else 'passed',
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'checks_passed': local.CHECKS + local.parent_audit.CHECKS + local.truth.CHECKS + native.CHECKS,
        'checker_sha256': file_sha(Path(__file__)), 'independent_helper_sha256': {
            Path(module.__file__).name: file_sha(Path(module.__file__)) for module in (local, local.parent_audit, local.truth, native)},
        'prepared_manifest_sha256': prepared_sha, 'execution_manifest_sha256': execution_sha,
        'collection_manifest_sha256': file_sha(base / 'observations/manifest.json'),
        'scoring_manifest_sha256': file_sha(base / 'scored/manifest.json'),
        'raw_streams_verified': len(records) - unavailable, 'raw_streams_unavailable': unavailable,
        'native_binary_bytes': binary_status, 'raw_checks': raw_checks, 'score_check': expected,
        'accounting': {'native_cost_usd': str(spent), 'all_observed_costs_known': all(c is not None for c in costs),
            'collection_wall_seconds': collection['wall_seconds'], 'provider_message_count': len(all_messages),
            'messages_per_invocation': [len(record['messages']) for record in records],
            'output_tokens': sum(usage.get('output_tokens', 0) for usage in usages),
            'thinking_tokens': sum(usage.get('output_tokens_details', {}).get('thinking_tokens', 0) for usage in usages),
            'missing_thinking_counters': sum('thinking_tokens' not in usage.get('output_tokens_details', {}) for usage in usages),
            'max_observed_message_output_tokens': max((m['usage'].get('output_tokens', 0) for m in all_messages), default=None)},
        'limitations': ['Four packets reuse four roots from two variants of one arithmetic skeleton, not independent acquisitions.',
            'Direct program solving and endpoint agreement can reproduce the exact decisions on this V/F-only panel.',
            'Returned support consistency does not identify an internal sequence of checking and selection.',
            'Copy counts, positions and stochastic outputs do not isolate a causal copying effect.',
            'Raw streams are explicitly unverified when absent or --public-only is used.',
            'Missing usage counters remain unverified; native cost is not subscription billing.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared-manifest-sha256', required=True)
    parser.add_argument('--execution-manifest-sha256', required=True)
    parser.add_argument('--public-only', action='store_true')
    parser.add_argument('--output', type=Path, help='Write a new receipt; never overwrite')
    args = parser.parse_args()
    result = run(args.prepared_manifest_sha256, args.execution_manifest_sha256, args.public_only)
    if args.output:
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write('\n')
    print(json.dumps({key: result[key] for key in ('status', 'checks_passed', 'raw_streams_verified', 'raw_streams_unavailable')}))


if __name__ == '__main__':
    main()
