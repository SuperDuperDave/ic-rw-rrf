#!/usr/bin/env python3
"""Independent cycle06 likelihood, custody, native-stream and direct-loss audit.

Standard library only; no generator, collector, scorer or prior checker imports.
Raw streams are optional and private. No response content or thinking is printed
or included in the public receipt. This command never invokes a provider.
"""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/cycle06-2026-09-10'
BASELINE = ROOT / 'results/cycle04-2026-09-10/exact'
BASELINE_SHA = '83eae092a1dc2ab2bada9631927063095fe265777bd5fbd10d3d03a5686963c5'
MODEL = 'claude-opus-5'
BINARY_SHA = '0399c793ff571d5946ef923d80b4f330d05ac4b6842a6b0775468f5d389403c0'
REFS = ('noisy_bayes', 'blind', 'naive_hint_trust')
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
            raise ValueError('duplicate_key')
        result[key] = value
    return result


def reject_constant(_):
    raise ValueError('nonfinite')


def read_json(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs_object,
                      parse_constant=reject_constant)


def probability(text):
    """Return an exact fraction or the published parse-failure category."""
    if type(text) is not str:
        return None, 'not_text'
    try:
        value = json.loads(text, object_pairs_hook=pairs_object, parse_int=F,
                           parse_float=F, parse_constant=reject_constant)
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        return None, str(error) if str(error) in ('duplicate_key', 'nonfinite') else 'malformed_json'
    if type(value) is not dict:
        return None, 'not_object'
    if set(value) != {'p_positive'}:
        return None, 'keys'
    p = value['p_positive']
    if type(p) is not F:
        return None, 'not_number'
    return (p, None) if 0 <= p <= 1 else (None, 'out_of_range')


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


def analytical_cells():
    """Sum the two truth masses using the original unconditional arm prior."""
    cells = {}
    for s in (F(11, 20), F(17, 20)):
        for g in (-1, 1):
            gp, gm = (F(7, 10), F(3, 10)) if g == 1 else (F(3, 10), F(7, 10))
            sp, sm = (1 - s, s) if g == 1 else (s, 1 - s)
            parts = {'copied': (gp * sp / 6, gm * sm / 6),
                     'independent': (gp ** 3 * sp / 6, gm ** 3 * sm / 6)}
            blind = sum(v[0] for v in parts.values()) / sum(sum(v) for v in parts.values())
            for hint in ('copied', 'independent'):
                positive = sum(v[0] * (F(3, 4) if a == hint else F(1, 4)) for a, v in parts.items())
                negative = sum(v[1] * (F(3, 4) if a == hint else F(1, 4)) for a, v in parts.items())
                q, trust = positive / (positive + negative), parts[hint][0] / sum(parts[hint])
                cells[(str(s), g, hint)] = {'positive': positive, 'mass': positive + negative,
                    'q': q, 'references': dict(zip(REFS, (q, blind, trust)))}
                for flip, expected in ((F(0), trust), (F(1, 2), blind)):
                    bp = sum(v[0] * (1 - flip if a == hint else flip) for a, v in parts.items())
                    bm = sum(v[1] * (1 - flip if a == hint else flip) for a, v in parts.items())
                    require(bp / (bp + bm) == expected, 'zero/half noise boundary')
    expected = {
        '11/20': (F(541, 2500), (F(2443, 3576), F(5187, 6584)), (F(1341, 4328), F(823, 4328))),
        '17/20': (F(181, 1250), (F(2443, 7696), F(1729, 3888)), (F(481, 1448), F(243, 1448))),
    }
    for s, (mass, qs, weights) in expected.items():
        total = sum(c['mass'] for key, c in cells.items() if key[0] == s)
        require(total == mass, 'design diagnostic mass')
        for hint, q, weight in zip(('copied', 'independent'), qs, weights):
            c = cells[(s, 1, hint)]
            require(c['q'] == q and c['mass'] / total == weight, 'design probability/weight')
            require(cells[(s, -1, hint)]['q'] == 1 - q, 'analytical sign symmetry')
    strong = cells[('17/20', 1, 'independent')]['references']
    require(strong['noisy_bayes'] < F(1, 2) and strong['blind'] < F(1, 2)
            and strong['naive_hint_trust'] > F(1, 2), 'class-only inference counterexample')
    return cells


def independent_oracle(fixture):
    cells, oracle, seen = analytical_cells(), {}, set()
    require(len(fixture['packets']) == 8, 'eight unique packets')
    require(file_sha(BASELINE / 'manifest.json') == fixture['baseline']['manifest_sha256'] == BASELINE_SHA,
            'anchored cycle04 baseline')
    baseline = read_json(BASELINE / 'manifest.json')
    for name in ('summary.json', 'per_world.json'):
        require(file_sha(BASELINE / name) == baseline['output_sha256'][name]
                == fixture['baseline']['output_sha256'][name], 'baseline output ' + name)
    rows = read_json(BASELINE / 'per_world.json')['rows']
    require(len(rows) == 192, 'baseline dimensions')
    selected = {}
    for index, row in enumerate(rows):
        if row['arm'] not in ('copied', 'independent'):
            continue
        values = [r['value'] for r in row['reports']]
        if values[:3] != [-values[3]] * 3:
            continue
        world, s = row['world'], F(row['p_specialist'])
        wp = F(1, 2)
        for name, accuracy in [('g1', F(7, 10)), ('g2', F(7, 10)), ('g3', F(7, 10)), ('s', s)]:
            wp *= accuracy if world[name] == world['y'] else 1 - accuracy
        fraction_equal(row['world_probability'], wp, 'primitive independent world probability')
        selected[index] = (row, wp)
    require(len(selected) == fixture['diagnostic_world_arm_rows'] == 40, 'selected baseline rows')
    fraction_equal(fixture['hint_flip_probability'], F(1, 4), 'fixture channel error')
    for packet in fixture['packets']:
        pid = packet['packet_id']
        payload = json.loads(packet['payload'], object_pairs_hook=pairs_object)
        require(canonical(payload) == packet['payload'], 'canonical provider serialization')
        h = sha(packet['payload'].encode())
        require(h == packet['payload_sha256'] and pid == 'p_' + h[:20], 'payload identity')
        require(set(payload) == {'model_parameters', 'reports', 'noisy_lineage_hint'}, 'input exclusion boundary')
        s, g, hint = packet['p_specialist'], packet['generalist_sign'], packet['noisy_lineage_hint']
        key = (s, g, hint)
        require(key in cells and key not in seen and pid not in oracle, 'unique diagnostic cell')
        seen.add(key)
        require(payload['noisy_lineage_hint'] == hint, 'disclosed hint')
        require(payload['model_parameters'] == {
            'truth_prior_positive': '1/2', 'p_generalist': '7/10', 'p_specialist': s,
            'construction_prior': {'padded': '1/3', 'copied': '1/3', 'independent': '1/3'},
            'hint_flip_probability': '1/4'}, 'full supplied model')
        require(payload['reports'] == [
            {'report_id': rid, 'role': 'generalist' if i < 3 else 'specialist', 'value': g if i < 3 else -g}
            for i, rid in enumerate(('r_94c2', 'r_b170', 'r_28e9', 'r_5a63'))], 'original opaque reports')
        c = cells[key]
        mass = sum(v['mass'] for k, v in cells.items() if k[0] == s)
        for field, value in [('diagnostic_mass', c['mass']), ('truth_positive_mass', c['positive']),
                             ('reference_p_positive', c['q']), ('diagnostic_weight', c['mass'] / mass)]:
            fraction_equal(packet[field], value, 'packet ' + field)
        require(set(packet['references']) == set(REFS), 'reference identities')
        for ref, value in c['references'].items():
            fraction_equal(packet['references'][ref], value, 'reference ' + ref)
        expected_rows = [(index, row, wp / 3 * (F(3, 4) if row['arm'] == hint else F(1, 4)))
                         for index, (row, wp) in selected.items()
                         if row['p_specialist'] == s and row['reports'][0]['value'] == g]
        require([r['source_row_id'] for r in packet['source_row_weights']] == [r[0] for r in expected_rows],
                'augmented source row identity/order')
        for observed, (_, _, weight) in zip(packet['source_row_weights'], expected_rows):
            fraction_equal(observed['augmented_mass'], weight, 'augmented primitive world weight')
        require(sum(r[2] for r in expected_rows) == c['mass']
                and sum(r[2] for r in expected_rows if r[1]['world']['y'] == 1) == c['positive'],
                'enumerated worlds equal closed-form truth masses')
        oracle[pid] = dict(c, packet=packet)
        fraction_equal(fixture['diagnostic_mass_by_p_specialist'][s], mass, 'full diagnostic mass')
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
    if type(value) is not dict:
        return {}
    answer = {k: value[k] for k in ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'thinking_tokens') if k in value}
    if type(value.get('output_tokens_details')) is dict and 'thinking_tokens' in value['output_tokens_details']:
        answer['output_tokens_details'] = {'thinking_tokens': value['output_tokens_details']['thinking_tokens']}
    return answer


def check_raw(record, public_only=False):
    paths = [ROOT / record['stdout_path'], ROOT / record['stderr_path']]
    if public_only or not all(p.exists() for p in paths):
        return {'status': 'unavailable', 'packet_id': record['packet_id'],
                'reason': 'public-only mode or private stream absent'}
    for path, field in zip(paths, ('stdout_sha256', 'stderr_sha256')):
        require(file_sha(path) == record[field], 'private stream hash')
    # All complete frames are parsed privately. Only IDs, counts and validated
    # probability comparisons leave this function; never serialize content.
    events, issues = [], set()
    try:
        for line in paths[0].read_text().splitlines():
            if line.strip():
                event = json.loads(line, object_pairs_hook=pairs_object, parse_constant=reject_constant)
                if type(event) is not dict:
                    raise ValueError('non-object event')
                events.append(event)
    except (ValueError, UnicodeError):
        issues.add('malformed_native_stream')
    inits = [e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init']
    finals = [e for e in events if e.get('type') == 'result']
    if len(inits) != 1:
        issues.add('init_count')
    else:
        init = inits[0]
        for valid, label in [
            (init.get('model') in (MODEL, MODEL + '[1m]'), 'init_model'),
            (init.get('tools') == [] and init.get('mcp_servers') == [], 'enabled_tools_or_mcp'),
            (not init.get('skills') and not init.get('plugins'), 'enabled_plugins_or_skills'),
            (init.get('session_id') == record['session_id'], 'init_session')]:
            if not valid:
                issues.add(label)
        require({k: init.get(k) for k in ('model', 'tools', 'mcp_servers', 'skills', 'plugins', 'permissionMode')}
                == record['init'], 'retained initialization fields')
    terminal = finals[0] if len(finals) == 1 else {}
    if len(finals) == 1:
        require(events[-1] is terminal, 'result is final native frame')
    for valid, label in [
        (len(finals) == 1, 'terminal_result_count'), (record['exit_code'] == 0, 'native_exit'),
        (not record['timed_out'], 'timeout'),
        (terminal.get('subtype') == 'success' and terminal.get('is_error') is False, 'native_result_error'),
        (terminal.get('stop_reason') == 'end_turn', 'terminal_stop'),
        (terminal.get('session_id') == record['session_id'], 'result_session')]:
        if not valid:
            issues.add(label)
    messages, published_messages = {}, {}
    current, requesting, retries, models, refusals = None, 0, [], set(), []
    local_error_ids = set()
    for event in events:
        if event.get('parent_tool_use_id'):
            issues.add('subagent_activity')
        if event.get('type') == 'system':
            subtype = event.get('subtype', '')
            requesting += subtype == 'status' and event.get('status') == 'requesting'
            if subtype == 'api_retry':
                retries.append('api_retry')
            if 'hook' in subtype:
                issues.add('hook_activity')
            if 'fallback' in subtype:
                issues.add('model_fallback')
                retries.append(subtype)
            if subtype == 'model_refusal_no_fallback':
                refusals.append({k: event.get(k) for k in
                                 ('subtype', 'original_model', 'api_refusal_category', 'request_id')})
        stream = event.get('event', {}) if event.get('type') == 'stream_event' else {}
        message = event.get('message') if event.get('type') == 'assistant' else None
        if stream.get('type') == 'message_start':
            message = stream['message']
            current = message.get('id')
        if type(message) is dict:
            mid, model = message.get('id'), message.get('model')
            if (event.get('type') == 'assistant' and model == '<synthetic>'
                    and event.get('is_api_error_message') is True
                    and event.get('error') == 'invalid_request'
                    and event.get('parent_tool_use_id') is None
                    and message.get('role') == 'assistant' and message.get('type') == 'message'
                    and message.get('stop_reason') == 'refusal'
                    and any(r['request_id'] == event.get('request_id') and r['original_model'] == MODEL
                            for r in refusals)):
                local_error_ids.add(mid)
            if model:
                models.add(model)
            if mid:
                row = messages.setdefault(mid, {'model': model, 'usage': {}, 'stop_reason': None})
                require(row['model'] == model, 'consistent native message model')
                row['usage'].update(selected_usage(message.get('usage')))
                retained = published_messages.setdefault(mid, {'model': model, 'usage': {}, 'stop_reason': None})
                retained['usage'].update(selected_usage(message.get('usage')))
                if message.get('stop_reason'):
                    row['stop_reason'] = message['stop_reason']
                    retained['stop_reason'] = message['stop_reason']
            if any('tool_use' in b.get('type', '') for b in message.get('content', [])):
                issues.add('tool_activity')
        if stream.get('type') == 'content_block_start' and 'tool_use' in stream.get('content_block', {}).get('type', ''):
            issues.add('tool_activity')
        if stream.get('type') == 'message_delta':
            require(current in messages, 'message delta has preceding start')
            messages[current]['usage'].update(selected_usage(stream.get('usage')))
            # Preserve the collector's historical last-inserted-message rule
            # separately from stream message_start attribution. A local error
            # assistant can intervene and make these assignments differ.
            retained = published_messages[next(reversed(published_messages))]
            retained['usage'].update(selected_usage(stream.get('usage')))
            if stream.get('delta', {}).get('stop_reason'):
                messages[current]['stop_reason'] = stream['delta']['stop_reason']
                retained['stop_reason'] = stream['delta']['stop_reason']
    require(published_messages == record['messages'], 'preserved collector message extraction replay')
    discrepancies = [{'message_id': mid, 'stream_attribution': message,
                      'frozen_collector_attribution': record['messages'][mid]}
                     for mid, message in messages.items() if message != record['messages'][mid]]
    require(len(messages) == record['distinct_observed_message_count']
            and requesting == record['requesting_status_count'], 'native message/request counts')
    require(retries == record['recovery_markers'], 'native recovery markers')
    missing_output = 0
    for row in messages.values():
        output = row['usage'].get('output_tokens')
        if output is None:
            missing_output += 1
        elif type(output) is not int or not 0 <= output <= 500:
            issues.add('message_output_ceiling')
    model_usage = terminal.get('modelUsage', {})
    for model, usage in model_usage.items():
        models.add(model)
        if 'canonicalModel' in usage and usage['canonicalModel'] != MODEL:
            issues.add('usage_canonical_model')
        if 'provider' in usage and usage['provider'] != 'firstParty':
            issues.add('usage_provider')
        require({k: v for k, v in usage.items() if k in (
            'inputTokens', 'outputTokens', 'cacheReadInputTokens', 'cacheCreationInputTokens',
            'thinkingTokens', 'costUSD', 'contextWindow', 'maxOutputTokens', 'canonicalModel', 'provider')}
                == record['model_usage'][model], 'retained model usage')
    if not models or any(m not in (MODEL, MODEL + '[1m]') for m in models):
        issues.add('observed_model')
    require(sorted(models) == record['observed_models'], 'observed model set')
    require(set(model_usage) == set(record['model_usage']), 'model accounting keys')
    retained_stats = []
    for final in finals:
        for field in ('subagent_stats', 'subagentStats'):
            if field in final:
                if zero_statistics(final[field]):
                    retained_stats.append({'field': field, 'counts': final[field]})
                else:
                    issues.add('subagent_statistics_nonzero_or_unknown')
                    if len(finals) == 1 and final[field]:
                        issues.add('subagent_activity')
    require(retained_stats == record['subagent_statistics'], 'exact typed zero-agent telemetry')
    try:
        value = terminal.get('total_cost_usd')
        cost = Decimal(str(value)) if type(value) in (str, int, float) else None
        if cost is None or not cost.is_finite() or cost < 0:
            cost = None
    except ArithmeticError:
        cost = None
    if cost is None:
        issues.add('unknown_cost')
    require((record['native_cost_usd'] is None) == (cost is None), 'cost availability')
    if cost is not None:
        require(Decimal(record['native_cost_usd']) == cost, 'native cost extraction')
    require(selected_usage(terminal.get('usage')) == record['usage'], 'aggregate usage extraction')
    for field, key in [('native_subtype', 'subtype'), ('native_is_error', 'is_error'),
                       ('native_stop_reason', 'stop_reason'), ('num_turns', 'num_turns'),
                       ('terminal_session_id', 'session_id')]:
        require(record[field] == terminal.get(key), 'terminal ' + key)
    text = terminal.get('result')
    require(record['terminal_text_sha256'] == (sha(text.encode()) if type(text) is str else None), 'terminal text hash')
    require(sorted(issues) == record['issues'] and record['native_acceptable'] == (not issues), 'native gate reconstruction')
    p, failure = probability(text) if not issues else (None, None)
    fraction_equal(record['p_positive'], p, 'strict terminal-only probability')
    require(record['parse_failure'] == failure, 'strict terminal parse failure')
    return {'status': 'verified', 'packet_id': record['packet_id'], 'message_count': len(messages),
            'provider_message_ids': [mid for mid in messages if mid not in local_error_ids],
            'local_synthetic_message_ids': sorted(local_error_ids),
            'provider_models': sorted({message['model'] for mid, message in messages.items() if mid not in local_error_ids}),
            'collector_message_attribution_matches_stream': not discrepancies,
            'collector_message_attribution_discrepancies': discrepancies,
            'refusal_without_fallback_events': refusals,
            'frozen_label_caveats': (['The model_fallback issue is triggered by the substring in model_refusal_no_fallback; this event reports no fallback.'] if refusals else [])
                + (['The observed_model issue includes a local <synthetic> assistant error record, which is not a provider model identity.']
                   if local_error_ids else []),
            'requesting_status_count': requesting, 'observed_recovery_markers': retries,
            'messages_without_output_usage': missing_output,
            'zero_agent_statistics_observed': bool(retained_stats),
            'output_tokens': terminal.get('usage', {}).get('output_tokens'),
            'thinking_tokens': terminal.get('usage', {}).get('output_tokens_details', {}).get('thinking_tokens'),
            'terminal_is_error': terminal.get('is_error'), 'terminal_stop_reason': terminal.get('stop_reason'),
            'native_acceptable': not issues, 'valid_terminal_probability': p is not None}


def loss(p, cell):
    """Directly average loss at both possible truth values, without regret identity."""
    return cell['positive'] * (1 - p) ** 2 + (cell['mass'] - cell['positive']) * p ** 2


def check_score(scores, fixture, oracle, records):
    predictions = {r['packet_id']: F(r['p_positive']) for r in records if r['p_positive'] is not None}
    failures = {r['packet_id']: ('native:' + ','.join(r['issues']) if not r['native_acceptable']
                else 'parse:' + r['parse_failure']) for r in records if r['p_positive'] is None}
    complete = len(predictions) == 8
    require(scores['status'] == ('complete' if complete else 'incomplete'), 'score completeness')
    require(scores['coverage'] == {'planned': 8, 'valid': len(predictions), 'invalid': len(failures),
            'missing': 8 - len(records), 'failure_types': dict(Counter(failures.values()))}, 'score coverage')
    require((scores['primary'] is not None) == complete
            and (scores['valid_subset_diagnostic'] is None) == complete, 'full primary gate')
    summaries = scores['primary'] if complete else scores['valid_subset_diagnostic']['by_p_specialist']
    for s in ('11/20', '17/20'):
        members = {pid: c for pid, c in oracle.items() if c['packet']['p_specialist'] == s}
        valid = {pid: c for pid, c in members.items() if pid in predictions}
        full, mass = sum(c['mass'] for c in members.values()), sum((c['mass'] for c in valid.values()), F(0))
        actual = sum((loss(predictions[pid], c) for pid, c in valid.items()), F(0))
        ideal = sum((loss(c['q'], c) for c in valid.values()), F(0))
        norm = lambda value: value / mass if mass else None
        observed = summaries[s]
        require(observed['packet_count'] == len(members) and observed['valid_packet_count'] == len(valid), 'summary counts')
        expected = {'full_diagnostic_mass': full, 'valid_diagnostic_mass': mass,
            'diagnostic_mass_coverage': mass / full, 'expected_brier': norm(actual),
            'ideal_expected_brier': norm(ideal), 'conditional_excess_brier': norm(actual - ideal),
            'conditional_absolute_posterior_error': norm(sum((c['mass'] * abs(predictions[pid] - c['q'])
                                                            for pid, c in valid.items()), F(0)))}
        for field, value in expected.items():
            fraction_equal(observed[field], value, 'direct-loss summary ' + field)
        require(set(observed['comparators']) == set(REFS), 'aggregate comparator identities')
        for ref in REFS:
            risk = sum((loss(c['references'][ref], c) for c in valid.values()), F(0))
            expected = {'expected_brier': norm(risk), 'conditional_excess_brier': norm(risk - ideal),
                'model_minus_expected_brier': norm(actual - risk),
                'model_squared_distance': norm(sum((c['mass'] * (predictions[pid] - c['references'][ref]) ** 2
                                                   for pid, c in valid.items()), F(0))),
                'model_absolute_distance': norm(sum((c['mass'] * abs(predictions[pid] - c['references'][ref])
                                                    for pid, c in valid.items()), F(0)))}
            for field, value in expected.items():
                fraction_equal(observed['comparators'][ref][field], value, 'direct-loss comparator ' + ref + ' ' + field)
    require([p['packet_id'] for p in scores['packets']] == fixture['request_order'], 'score packet order')
    decision = lambda p: 'tie' if p == F(1, 2) else ('positive' if p > F(1, 2) else 'negative')
    for row in scores['packets']:
        pid, c = row['packet_id'], oracle[row['packet_id']]
        p, q = predictions.get(pid), c['q']
        for field in ('p_specialist', 'generalist_sign', 'noisy_lineage_hint'):
            require(row[field] == c['packet'][field], 'score packet identity ' + field)
        for field, value in [('p_positive', p), ('reference_p_positive', q),
            ('absolute_posterior_error', abs(p - q) if p is not None else None),
            ('excess_brier', (loss(p, c) - loss(q, c)) / c['mass'] if p is not None else None)]:
            fraction_equal(row[field], value, 'direct packet ' + field)
        require(row['failure_type'] == failures.get(pid), 'packet failure type')
        require(row['status'] == ('valid' if p is not None else ('invalid' if pid in failures else 'missing')), 'packet status')
        require(row['sign_decision'] == (decision(p) if p is not None else None)
                and row['reference_sign_decision'] == decision(q), 'packet sign decisions')
        require(row['sign_matches_reference'] == (decision(p) == decision(q) if p is not None else None), 'packet sign comparison')
        require(set(row['comparators']) == set(REFS), 'packet comparator identities')
        for ref, value in c['references'].items():
            compared = row['comparators'][ref]
            fraction_equal(compared['p_positive'], value, 'packet comparator probability')
            fraction_equal(compared['model_minus_reference'], p - value if p is not None else None, 'packet comparator difference')
            require(compared['sign_decision'] == decision(value), 'packet comparator sign')
    contrasts = scores['contrasts']
    require({k: len(v) for k, v in contrasts.items()} == {'sign_symmetry': 4, 'hint_contrast': 4}, 'contrast dimensions')
    seen = set()
    for row in contrasts['sign_symmetry']:
        a, b = row['positive_generalist_packet_id'], row['negative_generalist_packet_id']
        pa, pb = oracle[a]['packet'], oracle[b]['packet']
        key = (row['p_specialist'], row['noisy_lineage_hint'])
        require(key not in seen and key == (pa['p_specialist'], pa['noisy_lineage_hint'])
                == (pb['p_specialist'], pb['noisy_lineage_hint'])
                and pa['generalist_sign'] == 1 and pb['generalist_sign'] == -1, 'symmetry identities')
        seen.add(key)
        fraction_equal(row['probability_sum_minus_one'], predictions[a] + predictions[b] - 1
                       if a in predictions and b in predictions else None, 'sign symmetry')
        for ref in REFS:
            fraction_equal(row['reference_sum_minus_one'][ref], oracle[a]['references'][ref]
                           + oracle[b]['references'][ref] - 1, 'reference symmetry')
    seen = set()
    for row in contrasts['hint_contrast']:
        a, b = row['hint_independent_packet_id'], row['hint_copied_packet_id']
        pa, pb = oracle[a]['packet'], oracle[b]['packet']
        key = (row['p_specialist'], row['generalist_sign'])
        require(key not in seen and key == (pa['p_specialist'], pa['generalist_sign'])
                == (pb['p_specialist'], pb['generalist_sign'])
                and pa['noisy_lineage_hint'] == 'independent' and pb['noisy_lineage_hint'] == 'copied', 'hint contrast identities')
        seen.add(key)
        fraction_equal(row['hint_independent_minus_copied'], predictions[a] - predictions[b]
                       if a in predictions and b in predictions else None, 'model hint contrast')
        for ref in REFS:
            fraction_equal(row['reference_hint_independent_minus_copied'][ref],
                           oracle[a]['references'][ref] - oracle[b]['references'][ref], 'reference hint contrast')
    return {'measurement_status': scores['status'], 'coverage': scores['coverage'],
            'all_aggregate_comparator_packet_and_contrast_numeric_outputs_match': True}


def check_controls(collection, fixture):
    require(collection['native_binary_sha256'] == BINARY_SHA
            and Path(collection['native_binary']).name == '2.1.267', 'pinned native executable identity')
    expected = {
        'CLAUDE_CODE_MAX_OUTPUT_TOKENS': '500', 'CLAUDE_CODE_EFFORT_LEVEL': 'high',
        'CLAUDE_CODE_MAX_RETRIES': '0', 'CLAUDE_CODE_RETRY_WATCHDOG': '0',
        'CLAUDE_CODE_NO_MODEL_FALLBACK': '1', 'CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK': '1',
        'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1', 'CLAUDE_CODE_DISABLE_FAST_MODE': '1',
        'CLAUDE_CODE_DISABLE_WORKFLOWS': '1', 'CLAUDE_CODE_AUTO_CONNECT_IDE': '0', 'DISABLE_AUTO_COMPACT': '1',
    }
    require(collection['environment_overrides'] == expected, 'frozen environment controls')
    require(collection['native_budget_usd'] == '1' and collection['call_wall_seconds'] == 120
            and collection['batch_wall_seconds'] == 300, 'prospective resource controls')
    argv = [collection['native_binary'], '--print', '--safe-mode', '--setting-sources', '',
        '--settings', '{"disableAllHooks":true,"autoMemoryEnabled":false}',
        '--tools', '', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
        '--disable-slash-commands', '--no-chrome', '--permission-mode', 'dontAsk',
        '--permission-prompts', 'none', '--no-session-persistence', '--model', MODEL,
        '--effort', 'high', '--max-turns', '1', '--max-budget-usd', '<remaining-native-usd>',
        '--system-prompt', fixture['system_prompt'], '--output-format', 'stream-json', '--verbose',
        '--include-partial-messages', '--include-hook-events', '--prompt-suggestions', 'false',
        '--session-id', '<fresh-uuid>']
    require(collection['argv_template'] == argv, 'frozen native argv')
    require(collection['wire_attempt_count'] is None, 'hidden wire attempts remain unclaimed')
    binary = Path(collection['native_binary'])
    if binary.exists():
        require(file_sha(binary) == BINARY_SHA, 'installed binary bytes')
    return 'verified' if binary.exists() else 'unavailable'


def check_batch(fixture, oracle, public_only):
    observation = BASE / 'observations'
    collection = artifact_manifest(observation)
    scored = artifact_manifest(BASE / 'scored', source_fields=False)
    records = read_json(observation / 'responses.json')
    require(collection['prepared_manifest_sha256'] == file_sha(BASE / 'prepared/manifest.json')
            and collection['request_order'] == fixture['request_order'], 'collection preparation anchor')
    binary_status = check_controls(collection, fixture)
    require(collection['invocations_observed'] == collection['invocations_scheduled'] == len(records) <= 8,
            'bounded attempts and observations')
    require([r['packet_id'] for r in records] == fixture['request_order'][:len(records)], 'immutable request prefix')
    outputs = {'manifest-start.json', 'responses.json'}
    spent, raw_checks, session_ids, message_ids = Decimal(0), [], set(), set()
    for ordinal, record in enumerate(records, 1):
        pid = record['packet_id']
        individual, attempt_name = f'{ordinal:02d}-{pid}.json', f'{ordinal:02d}-attempt.json'
        outputs.update((individual, attempt_name))
        require(record['ordinal'] == ordinal and record['payload_sha256'] == oracle[pid]['packet']['payload_sha256']
                and record['system_prompt_sha256'] == fixture['system_prompt_sha256'], 'record payload custody')
        require(read_json(observation / individual) == record, 'individual receipt equality')
        attempt = read_json(observation / attempt_name)
        for field in ('ordinal', 'packet_id', 'session_id', 'started_utc', 'payload_sha256', 'system_prompt_sha256'):
            require(attempt[field] == record[field], 'attempt ' + field)
        require(Decimal(attempt['remaining_native_usd']) == Decimal(record['scheduled_remaining_native_usd'])
                == 1 - spent, 'sequential remaining native budget')
        require(spent < 1 and 0 < record['scheduled_timeout_seconds'] <= 120
                and record['scheduled_timeout_seconds'] == attempt['timeout_seconds'], 'bounded invocation scheduling')
        require(record['session_id'] not in session_ids, 'fresh sessions')
        session_ids.add(record['session_id'])
        require(not message_ids.intersection(record['messages']), 'fresh native messages')
        message_ids.update(record['messages'])
        require(record['native_acceptable'] == (not record['issues']), 'public native gate consistency')
        if record['native_acceptable']:
            require(record['exit_code'] == 0 and not record['timed_out']
                    and record['native_subtype'] == 'success' and record['native_is_error'] is False
                    and record['native_stop_reason'] == 'end_turn'
                    and record['terminal_session_id'] == record['session_id'], 'public native success fields')
            require(record['init']['model'] in (MODEL, MODEL + '[1m]')
                    and record['init']['tools'] == [] and record['init']['mcp_servers'] == []
                    and not record['init']['skills'] and not record['init']['plugins'], 'public native execution surfaces')
            require(bool(record['observed_models']) and all(m in (MODEL, MODEL + '[1m]')
                    for m in record['observed_models']), 'public observed models')
            require(record['distinct_observed_message_count'] == len(record['messages']), 'public message count')
            for message in record['messages'].values():
                require(message['model'] in (MODEL, MODEL + '[1m]'), 'public message model')
                output = message['usage'].get('output_tokens')
                require(output is None or type(output) is int and 0 <= output <= 500, 'public per-message output ceiling')
            for item in record['subagent_statistics']:
                require(item['field'] in ('subagent_stats', 'subagentStats')
                        and zero_statistics(item['counts']), 'public exact zero agent statistics')
            require((record['p_positive'] is None) == (record['parse_failure'] is not None), 'exclusive parse/prediction')
            if record['p_positive'] is not None:
                require(0 <= F(record['p_positive']) <= 1, 'public finite probability')
        else:
            require(ordinal == len(records) and record['p_positive'] is None
                    and record['parse_failure'] is None, 'native failure stops and remains excluded')
        if record['native_cost_usd'] is not None:
            cost = Decimal(record['native_cost_usd'])
            require(cost.is_finite() and cost >= 0, 'finite public cost')
            spent += cost
        for field in ('stdout_path', 'stderr_path'):
            require((ROOT / record[field]).parent == ROOT / collection['private_directory']
                    and record[field].startswith('_sessions/local/'), 'private stream custody boundary')
        raw_checks.append(check_raw(record, public_only))
    require(set(collection['output_sha256']) == outputs, 'complete collection output manifest')
    require(Decimal(collection['known_native_cost_usd']) == spent, 'cumulative native accounting')
    require(collection['all_observed_costs_known'] == all(r['native_cost_usd'] is not None for r in records), 'cost coverage')
    require(collection['valid_predictions'] == sum(r['p_positive'] is not None for r in records), 'prediction coverage')
    stop = collection['stop_reason']
    if stop == 'all_invocations_finished':
        require(len(records) == 8 and all(r['native_acceptable'] and not r['interrupted'] for r in records), 'complete scheduling')
    elif stop == 'native_or_configuration_failure':
        require(bool(records) and not records[-1]['native_acceptable'], 'native stop evidence')
    elif stop == 'interrupted':
        require(bool(records) and records[-1]['interrupted'], 'interruption evidence')
    elif stop == 'native_budget_exhausted':
        require(len(records) < 8 and spent >= 1, 'native budget stop evidence')
    elif stop == 'batch_wall_exhausted':
        require(len(records) < 8 and collection['wall_seconds'] >= 300, 'batch wall stop evidence')
    else:
        require(False, 'recognized collection stop')
    score_check = check_score(read_json(BASE / 'scored/scores.json'), fixture, oracle, records)
    require(scored['measurement_status'] == score_check['measurement_status']
            and scored['coverage'] == score_check['coverage'], 'scoring manifest summary')
    return {'collection_manifest_sha256': file_sha(observation / 'manifest.json'),
            'scoring_manifest_sha256': file_sha(BASE / 'scored/manifest.json'),
            'native_binary_bytes': binary_status, 'native_cost_usd': str(spent),
            'stop_reason': stop, 'invocations': len(records),
            'raw_streams_verified': sum(r['status'] == 'verified' for r in raw_checks),
            'raw_streams_unavailable': sum(r['status'] == 'unavailable' for r in raw_checks),
            'invocations_with_message_attribution_discrepancies': sum(bool(r.get('collector_message_attribution_discrepancies')) for r in raw_checks),
            'raw_checks': raw_checks, 'score_check': score_check}


def run(public_only=False, prepared_only=False):
    prepared = artifact_manifest(BASE / 'prepared')
    fixture = read_json(BASE / 'prepared/fixture.json')
    require(prepared['system_prompt_sha256'] == fixture['system_prompt_sha256'], 'prepared prompt identity')
    require(prepared['provider_payload_sha256'] == {p['packet_id']: p['payload_sha256'] for p in fixture['packets']},
            'prepared payload identities')
    require(prepared['shuffle_seed'] == 42 and prepared['request_order_sha256']
            == sha(canonical(fixture['request_order']).encode()), 'prepared order identity')
    require(file_sha(ROOT / prepared['protocol']) == prepared['protocol_sha256'], 'frozen execution protocol')
    # Read the launcher's literal anchor without importing or executing it.
    tree = ast.parse((ROOT / '_sessions/tools/run_cycle06_coordinator.py').read_text())
    anchors = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == 'PREPARED_SHA' for target in node.targets)]
    require(anchors == [file_sha(BASE / 'prepared/manifest.json')], 'literal launcher preparation anchor')
    oracle = independent_oracle(fixture)
    batch = None if prepared_only else check_batch(fixture, oracle, public_only)
    unavailable = bool(batch and batch['raw_streams_unavailable'])
    status = ('passed_prepared_only' if prepared_only else 'passed_public_only' if unavailable
              else 'passed_with_documented_instrument_discrepancies'
              if batch['invocations_with_message_attribution_discrepancies'] else 'passed')
    return {'schema_version': 1, 'status': status,
            'checked_utc': datetime.now(timezone.utc).isoformat(), 'checker_sha256': file_sha(Path(__file__)),
            'checks_passed': CHECKS, 'prepared_manifest_sha256': file_sha(BASE / 'prepared/manifest.json'),
            'independence': 'standard library only; no production imports; primitive world products, closed-form channel likelihoods, direct truth-weighted losses',
            'prepared_oracle': {'unique_packets': 8, 'selected_world_rows': 40,
                'all_posteriors_masses_weights_and_source_rows_match': True,
                'zero_and_half_noise_boundaries_match': True,
                'class_decisions_do_not_identify_hint_use': True},
            'batch': batch,
            'limitations': ['Eight selected inputs do not estimate model-repeat uncertainty or general ability.',
                'Native observations do not enumerate hidden transport attempts.',
                'Missing per-message output usage is unverified; native aggregate reasoning counters can substitute zero.',
                'Private streams and installed native binary are explicitly unavailable when absent.',
                'Frozen collector labels and message attribution remain unchanged; independent event interpretation records any discrepancies separately.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared-only', action='store_true', help='Check frozen preparation without reading cycle06 outcomes')
    parser.add_argument('--public-only', action='store_true', help='Skip private streams and explicitly mark them unavailable')
    parser.add_argument('--output', type=Path, help='Write a new receipt; never overwrite an existing file')
    args = parser.parse_args()
    result = run(args.public_only, args.prepared_only)
    if args.output:
        with args.output.open('x') as handle:
            json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write('\n')
    print(json.dumps({'status': result['status'], 'checks_passed': result['checks_passed'],
                      'raw_streams_verified': result['batch']['raw_streams_verified'] if result['batch'] else None}))


if __name__ == '__main__':
    main()
