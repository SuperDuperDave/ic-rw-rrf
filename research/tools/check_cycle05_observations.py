#!/usr/bin/env python3
"""Independent cycle05 custody, native-response and exact-loss check.

Uses only the standard library and published artifact schemas. It never imports
the packet generator, collector, adapter or scorer, and never calls a provider.
Private streams are optional; unavailable streams are explicitly unverified.
No model thinking or raw response text is emitted or saved by this checker.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parents[2]
PREPARED = ROOT / 'results/cycle05-2026-09-10/prepared'
PREPARED_SHA = '929fa72b040c97f9ce7908244cab9428eae6a9eb3d656f7dec624e929be2a2b0'
BATCHES = ('cycle05-2026-09-10', 'cycle05-replication-2026-09-10')
MODEL = 'claude-opus-5'
ZERO_STATS = {
    'spawned': 0, 'requested': {'background': 0, 'foreground': 0, 'unset': 0},
    'started_in_background': 0, 'max_depth': 0, 'spawned_by_subagents': 0,
    'completed': 0, 'failed': 0, 'killed': {'parent': 0, 'user': 0, 'system': 0},
    'refused': {'depth_limit': 0, 'concurrency_limit': 0, 'budget': 0}, 'by_type': {},
}
CHECKS = 0


def require(condition, label):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise ValueError('independent check failed: ' + label)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(Path(path).read_bytes())


def pairs_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def reject_constant(_):
    raise ValueError('nonfinite JSON number')


def read_json(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs_object,
                      parse_constant=reject_constant)


def probability(text):
    value = json.loads(text, object_pairs_hook=pairs_object, parse_int=F,
                       parse_float=F, parse_constant=reject_constant)
    require(type(value) is dict and set(value) == {'p_positive'}, 'terminal probability object')
    p = value['p_positive']
    require(type(p) is F and 0 <= p <= 1, 'terminal finite numeric probability')
    return p


def fraction_equal(actual, expected, label):
    require(actual is None if expected is None else actual is not None and F(actual) == expected, label)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def artifact_manifest(directory, source_fields=True):
    manifest = read_json(directory / 'manifest.json')
    start = read_json(directory / 'manifest-start.json')
    require(manifest['status'] == 'complete' and start['status'] == 'started', 'manifest lifecycle')
    require(all(manifest.get(k) == v for k, v in start.items() if k != 'status'), 'start/final custody')
    for name, expected in manifest['output_sha256'].items():
        require(file_sha(directory / name) == expected, 'output hash: ' + name)
    if source_fields:
        require(manifest['sources_unchanged'] is True, 'sources unchanged claim')
        require(manifest['source_sha256_start'] == manifest['source_sha256_end'], 'source start/end equality')
        for name, expected in manifest['source_sha256_start'].items():
            require(file_sha(ROOT / name) == expected, 'source hash: ' + name)
    else:
        for name, expected in manifest['input_sha256'].items():
            require(file_sha(ROOT / name) == expected, 'scoring input hash: ' + name)
    return manifest


def independent_oracle(fixture):
    """Closed-form likelihoods, separately from cycle04 enumerated worlds."""
    require(len(fixture['packets']) == 20 and len(fixture['pairs']) == 12, 'fixture dimensions')
    require(fixture['diagnostic_world_arm_rows'] == 72, 'selected world count')
    require(Counter(p['view'] for p in fixture['packets']) == {'aware': 12, 'blind': 8}, 'unique view counts')
    oracle, payloads = {}, {}
    for packet in fixture['packets']:
        pid, payload = packet['packet_id'], json.loads(packet['payload'])
        payloads[pid] = payload
        require(canonical(payload) == packet['payload'], 'canonical provider serialization')
        h = sha(packet['payload'].encode())
        require(h == packet['payload_sha256'] and pid == 'p_' + h[:20], 'payload identity')
        aware = 'parent_partition' in payload
        require(set(payload) == ({'model_parameters', 'reports', 'parent_partition'} if aware else {'model_parameters', 'reports'}), 'payload exclusion boundary')
        require(aware == (packet['view'] == 'aware'), 'view metadata')
        s = F(packet['p_specialist'])
        require(s in (F(11, 20), F(17, 20)), 'specialist values')
        require(payload['model_parameters'] == {
            'p_generalist': '7/10', 'p_specialist': packet['p_specialist'],
            'truth_prior_positive': '1/2',
            'construction_prior': {'padded': '1/3', 'copied': '1/3', 'independent': '1/3'}}, 'supplied model')
        reports = payload['reports']
        require(len(reports) == 4, 'four report slots')
        for index, (report, rid) in enumerate(zip(reports, ('r_94c2', 'r_b170', 'r_28e9', 'r_5a63'))):
            require(set(report) == {'report_id', 'role', 'value'} and report['report_id'] == rid
                    and report['role'] == ('specialist' if index == 3 else 'generalist'), 'report schema')
        g = reports[0]['value']
        require(type(g) is int and g in (-1, 1) and packet['generalist_sign'] == g, 'generalist sign')
        require(reports[3]['value'] == -g, 'opposed specialist')
        padded = reports[1]['value'] is None
        require([r['value'] for r in reports] == ([g, None, None, -g] if padded else [g, g, g, -g]), 'diagnostic observation')
        if aware:
            partition = payload['parent_partition']
            require(partition in ([0, None, None, 1], [0, 0, 0, 1], [0, 1, 2, 3]), 'canonical lineage')
            require((partition[1] is None) == padded, 'padding lineage')
            powers = [3 if partition == [0, 1, 2, 3] else 1]
        else:
            powers = [1] if padded else [1, 3]
        # Each compatible arm has prior 1/3 and each truth has prior 1/2.
        gp, gm = (F(7, 10), F(3, 10)) if g == 1 else (F(3, 10), F(7, 10))
        sp, sm = (1 - s, s) if g == 1 else (s, 1 - s)
        positive = sum((gp ** n * sp / 6 for n in powers), F(0))
        negative = sum((gm ** n * sm / 6 for n in powers), F(0))
        mass, q = positive + negative, positive / (positive + negative)
        oracle[pid] = {'mass': mass, 'positive': positive, 'q': q, 'packet': packet}
        for field, expected in [('diagnostic_mass', mass), ('truth_positive_mass', positive), ('reference_p_positive', q)]:
            fraction_equal(packet[field], expected, 'closed-form ' + field)
    totals = {}
    for s in ('11/20', '17/20'):
        totals[s] = sum(o['mass'] for o in oracle.values() if o['packet']['p_specialist'] == s and o['packet']['view'] == 'aware')
        fraction_equal(fixture['diagnostic_mass_by_p_specialist'][s], totals[s], 'diagnostic total')
        for view in ('aware', 'blind'):
            relevant = [o for o in oracle.values() if o['packet']['p_specialist'] == s and o['packet']['view'] == view]
            require(sum(o['mass'] for o in relevant) == totals[s], 'matched view mass')
            for o in relevant:
                fraction_equal(o['packet']['diagnostic_weight'], o['mass'] / totals[s], 'normalized packet weight')
    for pair in fixture['pairs']:
        a, b = oracle[pair['aware_packet_id']], oracle[pair['blind_packet_id']]
        pa, pb = payloads[pair['aware_packet_id']], payloads[pair['blind_packet_id']]
        require({k: v for k, v in pa.items() if k != 'parent_partition'} == pb, 'paired only-lineage intervention')
        arm = 'padded' if pa['reports'][1]['value'] is None else ('independent' if pa['parent_partition'] == [0, 1, 2, 3] else 'copied')
        require(pair['arm'] == arm and pair['p_specialist'] == a['packet']['p_specialist'] == b['packet']['p_specialist'], 'pair identity')
        for field, expected in [('diagnostic_mass', a['mass']), ('truth_positive_mass', a['positive']), ('aware_q', a['q']), ('blind_q', b['q']), ('diagnostic_weight', a['mass'] / totals[pair['p_specialist']])]:
            fraction_equal(pair[field], expected, 'pair ' + field)
    order = sorted(oracle)
    random.Random(42).shuffle(order)
    require(fixture['shuffle_seed'] == 42 and fixture['request_order'] == order, 'fixed shuffled order')
    require(sha(fixture['system_prompt'].encode()) == fixture['system_prompt_sha256'], 'prompt identity')
    return oracle


def zero_statistics(value, shape=ZERO_STATS):
    if type(shape) is dict:
        return type(value) is dict and set(value) == set(shape) and all(zero_statistics(value[k], v) for k, v in shape.items())
    return type(value) is int and value == 0


def selected_usage(value):
    answer = {k: value[k] for k in ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'thinking_tokens') if k in value}
    if 'thinking_tokens' in value.get('output_tokens_details', {}):
        answer['output_tokens_details'] = {'thinking_tokens': value['output_tokens_details']['thinking_tokens']}
    return answer


def check_raw(record, original, public_only=False):
    paths = [ROOT / record['stdout_path'], ROOT / record['stderr_path']]
    if public_only or not all(p.exists() for p in paths):
        return {'status': 'unavailable', 'packet_id': record['packet_id'], 'reason': 'public-only mode or private stream absent'}
    for path, field in zip(paths, ('stdout_sha256', 'stderr_sha256')):
        require(file_sha(path) == record[field], 'private stream hash')
    # Parse whole frames privately; only scalar counts/IDs and validated p escape.
    events = [json.loads(line, object_pairs_hook=pairs_object, parse_constant=reject_constant)
              for line in paths[0].read_text().splitlines() if line.strip()]
    require(all(type(e) is dict for e in events), 'native event objects')
    inits = [e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init']
    finals = [e for e in events if e.get('type') == 'result']
    require(len(inits) == len(finals) == 1 and events[-1] is finals[0], 'unique terminal native result')
    init, terminal = inits[0], finals[0]
    require(init.get('model') in (MODEL, MODEL + '[1m]'), 'native init model')
    require(all(init.get(k) == [] for k in ('tools', 'mcp_servers', 'skills', 'plugins')), 'native empty execution surfaces')
    require(init['session_id'] == terminal['session_id'] == record['session_id'], 'native session identity')
    require(record['exit_code'] == 0 and not record['timed_out'] and not record['interrupted'], 'native process success')
    require(terminal.get('subtype') == 'success' and terminal.get('is_error') is False and terminal.get('stop_reason') == 'end_turn', 'native terminal success')
    require(zero_statistics(terminal.get('subagent_stats')), 'native exact zero agent statistics')
    messages, current, requesting, retries, models = {}, None, 0, [], set()
    for event in events:
        require(not event.get('parent_tool_use_id'), 'no native parent tool activity')
        if event.get('type') == 'system':
            subtype = event.get('subtype', '')
            require('hook' not in subtype and 'fallback' not in subtype, 'no hook or fallback activity')
            requesting += subtype == 'status' and event.get('status') == 'requesting'
            if subtype == 'api_retry':
                retries.append('api_retry')
        stream = event.get('event', {}) if event.get('type') == 'stream_event' else {}
        message = event.get('message') if event.get('type') == 'assistant' else None
        if stream.get('type') == 'message_start':
            message = stream['message']
            current = message['id']
        if message is not None:
            mid, model = message['id'], message['model']
            models.add(model)
            require(model in (MODEL, MODEL + '[1m]'), 'message model identity')
            row = messages.setdefault(mid, {'model': model, 'usage': {}, 'stop_reason': None})
            require(row['model'] == model, 'consistent message identity')
            row['usage'].update(selected_usage(message.get('usage', {})))
            if message.get('stop_reason'):
                row['stop_reason'] = message['stop_reason']
            require(all('tool_use' not in block.get('type', '') for block in message.get('content', [])), 'no assistant tool blocks')
        if stream.get('type') == 'content_block_start':
            require('tool_use' not in stream.get('content_block', {}).get('type', ''), 'no streamed tool block')
        if stream.get('type') == 'message_delta':
            require(current in messages, 'message usage has start')
            messages[current]['usage'].update(selected_usage(stream.get('usage', {})))
            if stream.get('delta', {}).get('stop_reason'):
                messages[current]['stop_reason'] = stream['delta']['stop_reason']
    require(messages == record['messages'], 'independent cumulative message reconstruction')
    require(len(messages) == record['distinct_observed_message_count'] and requesting == record['requesting_status_count'], 'message/requesting counts')
    require(retries == record['recovery_markers'], 'observed recovery markers')
    for row in messages.values():
        require(type(row['usage'].get('output_tokens')) is int and 0 <= row['usage']['output_tokens'] <= 500, 'per-message output ceiling')
    for model, usage in terminal['modelUsage'].items():
        models.add(model)
        require(model in (MODEL, MODEL + '[1m]') and usage.get('canonicalModel') == MODEL and usage.get('provider') == 'firstParty', 'native usage identity')
        require(all(usage.get(k) == v for k, v in record['model_usage'][model].items()), 'retained model accounting')
    require(sorted(models) == record['observed_models'], 'observed models')
    require(selected_usage(terminal['usage']) == record['usage'], 'retained aggregate usage')
    cost = Decimal(str(terminal['total_cost_usd']))
    require(cost.is_finite() and cost >= 0 and cost == Decimal(record['native_cost_usd']), 'native cost extraction')
    require(sha(terminal['result'].encode()) == record['terminal_text_sha256'], 'terminal text hash')
    p = probability(terminal['result'])
    if original:
        require(record['native_acceptable'] is False and record['issues'] == ['subagent_activity'] and record['p_positive'] is None, 'historical false positive remains excluded')
    else:
        require(record['native_acceptable'] is True and record['issues'] == [] and F(record['p_positive']) == p, 'strict extraction agrees')
        require(record['subagent_statistics'] == [{'field': 'subagent_stats', 'counts': terminal['subagent_stats']}], 'preserved zero statistics')
    return {'status': 'verified', 'packet_id': record['packet_id'], 'message_count': len(messages),
            'requesting_status_count': requesting, 'observed_recovery_markers': retries,
            'output_tokens': terminal['usage']['output_tokens'],
            'thinking_tokens': terminal['usage'].get('output_tokens_details', {}).get('thinking_tokens'),
            'original_instrument_false_positive': original}


def loss(p, observation):
    """Direct probability-weighted losses for Y=+1 and Y=-1."""
    return observation['positive'] * (1 - p) ** 2 + (observation['mass'] - observation['positive']) * p ** 2


def check_score(scores, fixture, oracle, records):
    predictions = {r['packet_id']: F(r['p_positive']) for r in records if r['p_positive'] is not None}
    failures = {r['packet_id']: ('native:' + ','.join(r['issues']) if not r['native_acceptable'] else 'parse:' + r['parse_failure']) for r in records if r['p_positive'] is None}
    complete = len(predictions) == 20
    require(scores['status'] == ('complete' if complete else 'incomplete'), 'score completeness')
    require(scores['coverage'] == {'planned': 20, 'valid': len(predictions), 'invalid': len(failures), 'missing': 20 - len(records), 'failure_types': dict(Counter(failures.values()))}, 'score coverage')
    require((scores['primary'] is not None) == complete and (scores['valid_subset_diagnostic'] is None) == complete, 'primary gate')
    views = scores['primary'] if complete else scores['valid_subset_diagnostic']['by_p_specialist']
    for s in ('11/20', '17/20'):
        for view in ('aware', 'blind'):
            members = {pid: o for pid, o in oracle.items() if o['packet']['p_specialist'] == s and o['packet']['view'] == view}
            valid = {pid: o for pid, o in members.items() if pid in predictions}
            full, mass = sum(o['mass'] for o in members.values()), sum((o['mass'] for o in valid.values()), F(0))
            observed = views[s][view]
            require(observed['packet_count'] == len(members) and observed['valid_packet_count'] == len(valid), 'view packet denominator')
            actual_loss = sum((loss(predictions[pid], o) for pid, o in valid.items()), F(0))
            ideal_loss = sum((loss(o['q'], o) for o in valid.values()), F(0))
            expected = {'full_diagnostic_mass': full, 'valid_diagnostic_mass': mass, 'diagnostic_mass_coverage': mass / full,
                        'expected_brier': actual_loss / mass if mass else None,
                        'ideal_expected_brier': ideal_loss / mass if mass else None,
                        'conditional_excess_brier': (actual_loss - ideal_loss) / mass if mass else None,
                        'conditional_absolute_posterior_error': sum((o['mass'] * abs(predictions[pid] - o['q']) for pid, o in valid.items()), F(0)) / mass if mass else None}
            for field, value in expected.items():
                fraction_equal(observed[field], value, 'independent view ' + field)
        pairs = [p for p in fixture['pairs'] if p['p_specialist'] == s]
        valid_pairs = [p for p in pairs if p['aware_packet_id'] in predictions and p['blind_packet_id'] in predictions]
        full = sum(oracle[p['aware_packet_id']]['mass'] for p in pairs)
        mass = sum((oracle[p['aware_packet_id']]['mass'] for p in valid_pairs), F(0))
        a_loss = b_loss = a_ideal = b_ideal = regret_delta = squared_gap = F(0)
        for pair in valid_pairs:
            ai, bi = pair['aware_packet_id'], pair['blind_packet_id']
            o, qa, qb, pa, pb = oracle[ai], oracle[ai]['q'], oracle[bi]['q'], predictions[ai], predictions[bi]
            a_loss += loss(pa, o)
            b_loss += loss(pb, o)
            a_ideal += loss(qa, o)
            b_ideal += loss(qb, o)
            regret_delta += o['mass'] * ((pa - qa) ** 2 - (pb - qb) ** 2)
            squared_gap += o['mass'] * (qa - qb) ** 2
        normalize = lambda x: x / mass if mass else None
        expected = {'full_diagnostic_mass': full, 'valid_diagnostic_mass': mass, 'diagnostic_mass_coverage': mass / full,
                    'aware_expected_brier': normalize(a_loss), 'blind_expected_brier': normalize(b_loss),
                    'aware_minus_blind_expected_brier': normalize(a_loss - b_loss),
                    'ideal_information_gap': normalize(a_ideal - b_ideal), 'posterior_squared_gap': normalize(squared_gap),
                    'original_posterior_regret_delta': normalize(regret_delta),
                    'selection_cross_term': normalize((a_loss - b_loss) - (a_ideal - b_ideal) - regret_delta)}
        observed = scores['paired']['by_p_specialist'][s]
        require(observed['pair_count'] == len(pairs) and observed['valid_pair_count'] == len(valid_pairs), 'paired denominator')
        for field, value in expected.items():
            fraction_equal(observed[field], value, 'independent pair ' + field)
    require([p['packet_id'] for p in scores['packets']] == fixture['request_order'], 'score packet order')
    decision = lambda p: 'tie' if p == F(1, 2) else ('positive' if p > F(1, 2) else 'negative')
    for row in scores['packets']:
        pid, o = row['packet_id'], oracle[row['packet_id']]
        p, q = predictions.get(pid), o['q']
        fraction_equal(row['p_positive'], p, 'score probability')
        fraction_equal(row['reference_p_positive'], q, 'score reference')
        fraction_equal(row['absolute_posterior_error'], abs(p - q) if p is not None else None, 'packet absolute error')
        fraction_equal(row['excess_brier'], (loss(p, o) - loss(q, o)) / o['mass'] if p is not None else None, 'packet direct excess loss')
        require(row['failure_type'] == failures.get(pid), 'packet failure type')
        require(row['status'] == ('valid' if p is not None else ('invalid' if pid in failures else 'missing')), 'packet status')
        require(row['sign_decision'] == (decision(p) if p is not None else None) and row['reference_sign_decision'] == decision(q), 'packet sign decision')
        require(row['sign_matches_reference'] == (decision(p) == decision(q) if p is not None else None), 'packet sign comparison')
    contrasts = scores['contrasts']
    require({k: len(v) for k, v in contrasts.items()} == {'sign_symmetry': 10, 'padded_to_copied': 8, 'aware_lineage_contrast': 4}, 'contrast dimensions')
    for row in contrasts['sign_symmetry']:
        a, b = row['positive_generalist_packet_id'], row['negative_generalist_packet_id']
        oa, ob = oracle[a]['packet'], oracle[b]['packet']
        require(oa['view'] == ob['view'] and oa['p_specialist'] == ob['p_specialist'] and oa['generalist_sign'] == 1 and ob['generalist_sign'] == -1, 'symmetry identities')
        fraction_equal(row['probability_sum_minus_one'], predictions[a] + predictions[b] - 1 if a in predictions and b in predictions else None, 'sign symmetry contrast')
    for key, left, right, field, reference in [
            ('padded_to_copied', 'copied_packet_id', 'padded_packet_id', 'copied_minus_padded', 'reference_copied_minus_padded'),
            ('aware_lineage_contrast', 'independent_packet_id', 'copied_packet_id', 'independent_minus_copied', 'reference_independent_minus_copied')]:
        for row in contrasts[key]:
            a, b = row[left], row[right]
            fraction_equal(row[field], predictions[a] - predictions[b] if a in predictions and b in predictions else None, 'probability contrast')
            fraction_equal(row[reference], oracle[a]['q'] - oracle[b]['q'], 'reference contrast')
    return {'measurement_status': scores['status'], 'coverage': scores['coverage'],
            'all_view_pair_packet_and_contrast_numeric_outputs_match': True}


def check_batch(name, fixture, oracle, public_only):
    base = ROOT / 'results' / name
    collection = artifact_manifest(base / 'observations')
    scored = artifact_manifest(base / 'scored', source_fields=False)
    records = read_json(base / 'observations/responses.json')
    require(collection['prepared_manifest_sha256'] == PREPARED_SHA and collection['request_order'] == fixture['request_order'], 'batch preparation identity')
    require(collection['invocations_observed'] == collection['invocations_scheduled'] == len(records), 'collection attempt count')
    require([r['packet_id'] for r in records] == fixture['request_order'][:len(records)], 'collection prefix')
    require(collection['native_budget_usd'] == '4' and collection['call_wall_seconds'] == 120 and collection['batch_wall_seconds'] == 900, 'frozen resource settings')
    require(collection['environment_overrides']['CLAUDE_CODE_MAX_OUTPUT_TOKENS'] == '500' and collection['environment_overrides']['CLAUDE_CODE_EFFORT_LEVEL'] == 'high', 'frozen output/effort controls')
    spent, raw_checks, session_ids, message_ids = F(0), [], set(), set()
    for ordinal, record in enumerate(records, 1):
        pid = record['packet_id']
        require(record['ordinal'] == ordinal and record['payload_sha256'] == oracle[pid]['packet']['payload_sha256'] and record['system_prompt_sha256'] == fixture['system_prompt_sha256'], 'record payload custody')
        require(read_json(base / 'observations' / f'{ordinal:02d}-{pid}.json') == record, 'individual receipt equality')
        attempt = read_json(base / 'observations' / f'{ordinal:02d}-attempt.json')
        require(attempt['ordinal'] == ordinal and attempt['packet_id'] == pid and attempt['session_id'] == record['session_id'], 'attempt identity')
        fraction_equal(attempt['remaining_native_usd'], 4 - spent, 'attempt budget')
        fraction_equal(record['scheduled_remaining_native_usd'], 4 - spent, 'sequential remaining budget')
        require(spent < 4 and 0 < record['scheduled_timeout_seconds'] <= 120, 'scheduling boundary')
        require(record['session_id'] not in session_ids, 'fresh sessions within batch')
        session_ids.add(record['session_id'])
        require(not message_ids.intersection(record['messages']), 'distinct invocation messages')
        message_ids.update(record['messages'])
        spent += F(record['native_cost_usd'])
        raw_checks.append(check_raw(record, name == BATCHES[0], public_only))
    fraction_equal(collection['known_native_cost_usd'], spent, 'batch cost sum')
    require(collection['all_observed_costs_known'] is True, 'complete cost observation')
    require(collection['valid_predictions'] == sum(r['p_positive'] is not None for r in records), 'collection prediction count')
    if name == BATCHES[0]:
        require(len(records) == 1 and collection['valid_predictions'] == 0 and collection['stop_reason'] == 'native_or_configuration_failure', 'original stopped outcome')
    else:
        require(len(records) == 20 and collection['valid_predictions'] == 20 and collection['stop_reason'] == 'all_invocations_finished', 'replication completed outcome')
    score_check = check_score(read_json(base / 'scored/scores.json'), fixture, oracle, records)
    require(scored['measurement_status'] == score_check['measurement_status'] and scored['coverage'] == score_check['coverage'], 'scoring receipt')
    return {'batch': name, 'collection_manifest_sha256': file_sha(base / 'observations/manifest.json'),
            'scoring_manifest_sha256': file_sha(base / 'scored/manifest.json'),
            'native_cost_usd': str(Decimal(collection['known_native_cost_usd'])),
            'invocations': len(records), 'raw_streams_verified': sum(r['status'] == 'verified' for r in raw_checks),
            'raw_streams_unavailable': sum(r['status'] == 'unavailable' for r in raw_checks),
            'raw_checks': raw_checks, 'score_check': score_check}, session_ids, message_ids


def run(public_only=False):
    require(file_sha(PREPARED / 'manifest.json') == PREPARED_SHA, 'anchored prepared manifest')
    prepared = artifact_manifest(PREPARED)
    fixture = read_json(PREPARED / 'fixture.json')
    require(prepared['system_prompt_sha256'] == fixture['system_prompt_sha256'], 'prepared prompt identity')
    oracle = independent_oracle(fixture)
    results, all_sessions, all_messages = [], set(), set()
    for name in BATCHES:
        result, sessions, messages = check_batch(name, fixture, oracle, public_only)
        require(not sessions.intersection(all_sessions) and not messages.intersection(all_messages), 'no cross-batch session/message reuse')
        all_sessions.update(sessions)
        all_messages.update(messages)
        results.append(result)
    unavailable = sum(r['raw_streams_unavailable'] for r in results)
    return {'schema_version': 1, 'status': 'passed_public_only' if unavailable else 'passed',
            'checked_utc': datetime.now(timezone.utc).isoformat(),
            'checker_sha256': file_sha(Path(__file__)), 'checks_passed': CHECKS,
            'independence': 'standard library only; no production imports; closed-form likelihoods and direct truth-weighted losses',
            'prepared_manifest_sha256': PREPARED_SHA,
            'prepared_oracle': {'unique_packets': 20, 'pairs': 12, 'selected_world_rows': 72, 'all_closed_form_posteriors_masses_weights_match': True},
            'batches': results,
            'total_native_cost_usd': str(sum((Decimal(r['native_cost_usd']) for r in results), Decimal(0))),
            'limitations': ['Native observations do not enumerate hidden transport attempts.',
                            'Native aggregate reasoning counters can substitute zero; message detail availability is retained.',
                            'Private stream checks are explicitly unavailable when raw files are absent or public-only mode is requested.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-only', action='store_true', help='Verify public custody/arithmetic and mark all raw streams unavailable')
    parser.add_argument('--output', type=Path, help='Write a new receipt; existing files are never overwritten')
    args = parser.parse_args()
    result = run(args.public_only)
    if args.output:
        with args.output.open('x') as handle:
            json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write('\n')
    print(json.dumps({'status': result['status'], 'checks_passed': result['checks_passed'],
                      'raw_streams_verified': sum(r['raw_streams_verified'] for r in result['batches']),
                      'total_native_cost_usd': result['total_native_cost_usd']}))


if __name__ == '__main__':
    main()
