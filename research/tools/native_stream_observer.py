#!/usr/bin/env python3
"""Future native observation adapter for a verified local refusal event shape.

Does not run a provider, alter historical collectors/receipts, or accept a
refused response. It separates known local error records from provider messages
before applying the preserved acceptance/parser gates. Original stream bytes
must still be retained and hashed by any caller.
"""
import json
import run_cycle05_replication as verified


LOCAL_ERROR_USAGE = {
    'output_tokens_details': None,
    'input_tokens': 0, 'output_tokens': 0,
    'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0,
    'server_tool_use': {'web_search_requests': 0, 'web_fetch_requests': 0},
    'service_tier': None,
    'cache_creation': {'ephemeral_1h_input_tokens': 0, 'ephemeral_5m_input_tokens': 0},
    'inference_geo': None, 'iterations': None, 'speed': None,
}


def _zero_usage(value, shape=LOCAL_ERROR_USAGE):
    """Match only the complete, typed local-error usage structure observed."""
    if type(shape) is dict:
        return type(value) is dict and set(value) == set(shape) and all(
            _zero_usage(value[key], child) for key, child in shape.items())
    if shape is None:
        return value is None
    return type(value) is int and value == 0


def _local_message_shape(message):
    if not isinstance(message, dict):
        return False
    content, usage = message.get('content'), message.get('usage')
    return (isinstance(content, list) and len(content) == 1
            and isinstance(content[0], dict) and set(content[0]) == {'type', 'text'}
            and content[0]['type'] == 'text' and type(content[0]['text']) is str
            and _zero_usage(usage))


def inspect_stream(raw, exit_code, expected_session, timed_out=False):
    try:
        events = [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
    except (UnicodeError, ValueError):
        return verified.inspect_stream(raw, exit_code, expected_session, timed_out)
    terminal = [e for e in events if isinstance(e, dict) and e.get('type') == 'result']
    refused_terminal = (len(terminal) == 1 and terminal[0].get('is_error') is True
                        and terminal[0].get('stop_reason') == 'refusal'
                        and terminal[0].get('session_id') == expected_session)
    refusals, local_records, normalized = {}, [], []
    for event in events:
        if not isinstance(event, dict):
            normalized.append(event)
            continue
        known_refusal = (refused_terminal and event.get('type') == 'system'
                        and event.get('subtype') == 'model_refusal_no_fallback'
                        and event.get('session_id') == expected_session
                        and verified.original.canonical_model(event.get('original_model'))
                        and type(event.get('request_id')) is str and bool(event['request_id']))
        if known_refusal:
            refusals[event['request_id']] = {
                'request_id': event['request_id'], 'original_model': event['original_model'],
                'category': ('reasoning_extraction' if event.get('api_refusal_category')
                             == 'reasoning_extraction' else 'unrecognized'),
                'fallback_observed': False}
            # The old generic substring classifier mistakes "no_fallback" for
            # switching models. Preserve the exact event separately below.
            normalized.append(dict(event, subtype='provider_refusal_without_model_switch'))
            continue
        message = event.get('message', {})
        local_error = (refused_terminal and event.get('type') == 'assistant'
                       and event.get('is_api_error_message') is True
                       and event.get('error') == 'invalid_request'
                       and event.get('parent_tool_use_id') is None
                       and event.get('session_id') == expected_session
                       and type(event.get('request_id')) is str and bool(event['request_id'])
                       and event.get('request_id') in refusals
                       and refusals[event['request_id']]['category'] == 'reasoning_extraction'
                       and _local_message_shape(message) and message.get('model') == '<synthetic>'
                       and message.get('role') == 'assistant' and message.get('type') == 'message'
                       and message.get('stop_reason') == 'refusal'
                       and type(message.get('id')) is str and bool(message['id']))
        if local_error:
            local_records.append({'message_id': message['id'], 'request_id': event['request_id'],
                                  'kind': 'native_local_api_error', 'stop_reason': 'refusal'})
            # It is not a provider message_start and must not become the target
            # for the following provider message_delta's cumulative usage.
            continue
        normalized.append(event)
    observed = verified.inspect_stream(
        ('\n'.join(json.dumps(e) for e in normalized)).encode('utf-8'),
        exit_code, expected_session, timed_out)
    observed['provider_refusals'] = list(refusals.values())
    observed['local_error_records'] = local_records
    if refusals:
        observed['issues'] = sorted(set(observed['issues'] + ['provider_refusal']))
        observed['native_acceptable'] = False
        observed['p_positive'] = None
        observed['parse_failure'] = None
    return observed
