#!/usr/bin/env python3
"""One frozen native coordinator batch; raw provider streams remain private."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from evaluation import cycle05_coordinator_packets as packets

BINARY = Path('/home/david-wsl/.local/share/claude/versions/2.1.267')
BINARY_SHA = '0399c793ff571d5946ef923d80b4f330d05ac4b6842a6b0775468f5d389403c0'
PREPARED = ROOT / 'results/cycle05-2026-09-10/prepared'
PREPARED_SHA = '929fa72b040c97f9ce7908244cab9428eae6a9eb3d656f7dec624e929be2a2b0'
OUTPUT = ROOT / 'results/cycle05-2026-09-10/observations'
MODEL = 'claude-opus-5'
CAP = Decimal('4')
CALL_SECONDS = 120
BATCH_SECONDS = 900
OVERRIDES = {
    'CLAUDE_CODE_MAX_OUTPUT_TOKENS': '500', 'CLAUDE_CODE_EFFORT_LEVEL': 'high',
    'CLAUDE_CODE_MAX_RETRIES': '0', 'CLAUDE_CODE_RETRY_WATCHDOG': '0',
    'CLAUDE_CODE_NO_MODEL_FALLBACK': '1',
    'CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK': '1',
    'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
    'CLAUDE_CODE_DISABLE_FAST_MODE': '1', 'CLAUDE_CODE_DISABLE_WORKFLOWS': '1',
    'CLAUDE_CODE_AUTO_CONNECT_IDE': '0', 'DISABLE_AUTO_COMPACT': '1',
}


def digest(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical_model(value):
    # Context-window accounting suffix is not a different model. No aliases.
    return value in (MODEL, MODEL + '[1m]')


def process_environment(inherited):
    blocked = [key for key in inherited if key.startswith(
        ('ANTHROPIC_', 'CLAUDE_', 'AWS_', 'GOOGLE_', 'CLOUD_ML_', 'VERTEX_', 'BEDROCK_'))
        or key in ('MAX_THINKING_TOKENS', 'DISABLE_AUTO_COMPACT')]
    if blocked:
        raise ValueError('inherited provider/behavioral overrides: ' + ', '.join(sorted(blocked)))
    return dict(inherited, **OVERRIDES)


def command(system_prompt, session_id, remaining):
    return [str(BINARY), '--print', '--safe-mode', '--setting-sources', '',
            '--settings', '{"disableAllHooks":true,"autoMemoryEnabled":false}',
            '--tools', '', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
            '--disable-slash-commands', '--no-chrome', '--permission-mode', 'dontAsk',
            '--permission-prompts', 'none', '--no-session-persistence',
            '--model', MODEL, '--effort', 'high', '--max-turns', '1',
            '--max-budget-usd', str(remaining), '--system-prompt', system_prompt,
            '--output-format', 'stream-json', '--verbose', '--include-partial-messages',
            '--include-hook-events', '--prompt-suggestions', 'false',
            '--session-id', session_id]


def native_cost(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        cost = Decimal(str(value))
    except InvalidOperation:
        return None
    return cost if cost.is_finite() and cost >= 0 else None


def usage_fields(usage):
    if not isinstance(usage, dict):
        return {}
    selected = {key: usage[key] for key in (
        'input_tokens', 'output_tokens', 'cache_creation_input_tokens',
        'cache_read_input_tokens', 'thinking_tokens') if key in usage}
    details = usage.get('output_tokens_details')
    if isinstance(details, dict) and 'thinking_tokens' in details:
        selected['output_tokens_details'] = {'thinking_tokens': details['thinking_tokens']}
    return selected


def inspect_stream(raw, exit_code, expected_session, timed_out=False):
    """Extract only measurements; never copy thought text into public records."""
    issues, events = [], []
    try:
        for line in raw.decode('utf-8').splitlines():
            if line.strip():
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError('non-object event')
                events.append(event)
    except (UnicodeError, ValueError):
        issues.append('malformed_native_stream')
    inits = [e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init']
    results = [e for e in events if e.get('type') == 'result']
    messages, models, markers = {}, set(), []
    requesting = 0
    for event in events:
        subtype = event.get('subtype', '')
        if event.get('parent_tool_use_id'):
            issues.append('subagent_activity')
        if event.get('type') == 'system':
            if subtype == 'status' and event.get('status') == 'requesting':
                requesting += 1
            if subtype == 'api_retry':
                markers.append('api_retry')
            if 'hook' in subtype:
                issues.append('hook_activity')
            if 'fallback' in subtype:
                issues.append('model_fallback')
                markers.append(subtype)
        message = event.get('message') if event.get('type') == 'assistant' else None
        stream = event.get('event', {}) if event.get('type') == 'stream_event' else {}
        if stream.get('type') == 'message_start':
            message = stream.get('message', {})
        if isinstance(message, dict):
            model, mid = message.get('model'), message.get('id')
            if model:
                models.add(model)
            if mid:
                row = messages.setdefault(mid, {'model': model, 'usage': {}, 'stop_reason': None})
                row['usage'].update(usage_fields(message.get('usage')))
                if message.get('stop_reason'):
                    row['stop_reason'] = message['stop_reason']
            if any('tool_use' in block.get('type', '') for block in message.get('content', [])):
                issues.append('tool_activity')
        if stream.get('type') == 'content_block_start' and 'tool_use' in stream.get('content_block', {}).get('type', ''):
            issues.append('tool_activity')
        if stream.get('type') == 'message_delta':
            # Main-context stream events are ordered; each message_start selects
            # the subsequent delta target. Parallel tool contexts are forbidden.
            if messages:
                row = messages[next(reversed(messages))]
                row['usage'].update(usage_fields(stream.get('usage')))
                if stream.get('delta', {}).get('stop_reason'):
                    row['stop_reason'] = stream['delta']['stop_reason']
    if len(inits) != 1:
        issues.append('init_count')
    else:
        init = inits[0]
        if not canonical_model(init.get('model')):
            issues.append('init_model')
        if init.get('tools') != [] or init.get('mcp_servers') != []:
            issues.append('enabled_tools_or_mcp')
        if any(init.get(key) for key in ('plugins', 'skills')):
            issues.append('enabled_plugins_or_skills')
        if init.get('session_id') != expected_session:
            issues.append('init_session')
    result = results[0] if len(results) == 1 else {}
    if len(results) != 1:
        issues.append('terminal_result_count')
    if exit_code != 0:
        issues.append('native_exit')
    if timed_out:
        issues.append('timeout')
    if result.get('subtype') != 'success' or result.get('is_error') is not False:
        issues.append('native_result_error')
    if result.get('stop_reason') != 'end_turn':
        issues.append('terminal_stop')
    if result.get('session_id') != expected_session:
        issues.append('result_session')
    model_usage = result.get('modelUsage', {})
    models.update(model_usage)
    for values in model_usage.values():
        if 'canonicalModel' in values and values['canonicalModel'] != MODEL:
            issues.append('usage_canonical_model')
        if 'provider' in values and values['provider'] != 'firstParty':
            issues.append('usage_provider')
    if not models or any(not canonical_model(model) for model in models):
        issues.append('observed_model')
    if any(result.get(key) for key in ('subagentStats', 'subagent_stats')):
        issues.append('subagent_activity')
    for row in messages.values():
        output = row['usage'].get('output_tokens')
        if output is not None and (type(output) is not int or output < 0 or output > 500):
            issues.append('message_output_ceiling')
    cost = native_cost(result.get('total_cost_usd'))
    if cost is None:
        issues.append('unknown_cost')
    probability, parse_failure = None, None
    terminal_text = result.get('result')
    if not issues:
        try:
            probability = str(packets.parse_probability(terminal_text))
        except packets.ProbabilityParseError as error:
            parse_failure = error.code
    safe_model_usage = {model: {k: v for k, v in values.items() if k in (
        'inputTokens', 'outputTokens', 'cacheReadInputTokens', 'cacheCreationInputTokens',
        'thinkingTokens', 'costUSD', 'contextWindow', 'maxOutputTokens', 'canonicalModel', 'provider')}
        for model, values in model_usage.items()}
    return {
        'native_acceptable': not issues, 'issues': sorted(set(issues)),
        'p_positive': probability, 'parse_failure': parse_failure,
        'native_cost_usd': str(cost) if cost is not None else None,
        'observed_models': sorted(models), 'messages': messages,
        'distinct_observed_message_count': len(messages), 'requesting_status_count': requesting,
        'recovery_markers': markers, 'usage': usage_fields(result.get('usage')),
        'model_usage': safe_model_usage, 'native_subtype': result.get('subtype'),
        'native_is_error': result.get('is_error'), 'native_stop_reason': result.get('stop_reason'),
        'num_turns': result.get('num_turns'), 'terminal_session_id': result.get('session_id'),
        'terminal_text_sha256': hashlib.sha256(terminal_text.encode()).hexdigest() if isinstance(terminal_text, str) else None,
        'init': {k: inits[0].get(k) for k in ('model', 'tools', 'mcp_servers', 'skills', 'plugins', 'permissionMode')} if len(inits) == 1 else None,
    }


def stop_group(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)


def invoke(argv, payload, environment, timeout, stdout_path, stderr_path):
    started, timed_out, interrupted = time.monotonic(), False, False
    with tempfile.TemporaryDirectory(prefix='coordinator-context-') as cwd:
        with stdout_path.open('xb') as stdout, stderr_path.open('xb') as stderr:
            process = subprocess.Popen(argv, cwd=cwd, env=environment, stdin=subprocess.PIPE,
                                       stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                process.communicate(input=payload, timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                stop_group(process)
            except KeyboardInterrupt:
                interrupted = True
                stop_group(process)
            finally:
                stop_group(process)
                if process.stdin:
                    process.stdin.close()
    return {'exit_code': process.returncode, 'timed_out': timed_out,
            'interrupted': interrupted, 'wall_seconds': time.monotonic() - started}


def sources():
    paths = [Path(__file__), ROOT / '_sessions/tools/tests/test_cycle05_runner.py',
             ROOT / '_sessions/cycles/2026-09-10-cycle05-native-controls.md',
             ROOT / '_sessions/cycles/2026-09-10-cycle05-preflight-addendum.md',
             PREPARED / 'manifest.json', PREPARED / 'fixture.json']
    fixture, manifest = packets.validate_fixture_custody(PREPARED, PREPARED_SHA)
    return fixture, dict(manifest['source_sha256_start'], **{
        str(path.relative_to(ROOT)): digest(path) for path in paths})


def collect():
    fixture, before = sources()
    environment = process_environment(os.environ)
    if digest(BINARY) != BINARY_SHA:
        raise ValueError('native binary identity changed')
    OUTPUT.mkdir(parents=True, exist_ok=False)
    batch_id = str(uuid.uuid4())
    private = ROOT / '_sessions/local/cycle05' / batch_id
    private.mkdir(parents=True, exist_ok=False)
    manifest = {'schema_version': 1, 'status': 'started', 'started_utc': now(),
        'batch_id': batch_id, 'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'python_version': sys.version, 'source_sha256_start': before,
        'native_binary': str(BINARY), 'native_binary_sha256': BINARY_SHA,
        'prepared_manifest_sha256': PREPARED_SHA, 'environment_overrides': OVERRIDES,
        'argv_template': command(fixture['system_prompt'], '<fresh-uuid>', '<remaining-native-usd>'),
        'request_order': fixture['request_order'], 'native_budget_usd': str(CAP),
        'call_wall_seconds': CALL_SECONDS, 'batch_wall_seconds': BATCH_SECONDS,
        'wire_attempt_count': None, 'private_directory': str(private.relative_to(ROOT))}
    write_json(OUTPUT / 'manifest-start.json', manifest)
    started, spent, records, attempts, stop = time.monotonic(), Decimal(0), [], [], 'all_invocations_finished'
    by_id = {p['packet_id']: p for p in fixture['packets']}
    try:
        for ordinal, packet_id in enumerate(fixture['request_order'], 1):
            left = BATCH_SECONDS - (time.monotonic() - started)
            if spent >= CAP or left <= 0:
                stop = 'native_budget_exhausted' if spent >= CAP else 'batch_wall_exhausted'
                break
            packet = by_id[packet_id]
            payload = packet['payload'].encode('utf-8')
            packets.validate_payload(json.loads(payload))
            if hashlib.sha256(payload).hexdigest() != packet['payload_sha256']:
                raise ValueError('submission payload custody mismatch')
            session_id = str(uuid.uuid4())
            stdout_path, stderr_path = private / f'{ordinal:02d}.jsonl', private / f'{ordinal:02d}.stderr'
            call_started = now()
            attempt = {'ordinal': ordinal, 'packet_id': packet_id, 'session_id': session_id,
                       'started_utc': call_started, 'payload_sha256': packet['payload_sha256'],
                       'system_prompt_sha256': fixture['system_prompt_sha256'],
                       'remaining_native_usd': str(CAP - spent), 'timeout_seconds': min(CALL_SECONDS, left)}
            write_json(OUTPUT / f'{ordinal:02d}-attempt.json', attempt)
            attempts.append(attempt)
            execution = invoke(command(fixture['system_prompt'], session_id, CAP - spent),
                               payload, environment, min(CALL_SECONDS, left), stdout_path, stderr_path)
            record = {'ordinal': ordinal, 'packet_id': packet_id, 'session_id': session_id,
                'started_utc': call_started, 'finished_utc': now(),
                'payload_sha256': packet['payload_sha256'], 'system_prompt_sha256': fixture['system_prompt_sha256'],
                'scheduled_remaining_native_usd': str(CAP - spent),
                'scheduled_timeout_seconds': min(CALL_SECONDS, left), **execution,
                'stdout_path': str(stdout_path.relative_to(ROOT)), 'stderr_path': str(stderr_path.relative_to(ROOT)),
                'stdout_sha256': digest(stdout_path), 'stderr_sha256': digest(stderr_path),
                **inspect_stream(stdout_path.read_bytes(), execution['exit_code'], session_id, execution['timed_out'])}
            records.append(record)
            write_json(OUTPUT / f'{ordinal:02d}-{packet_id}.json', record)
            cost = native_cost(record['native_cost_usd'])
            if cost is not None:
                spent += cost
            print(json.dumps({'ordinal': ordinal, 'native_acceptable': record['native_acceptable'],
                              'valid_probability': record['p_positive'] is not None,
                              'known_native_usd': str(spent), 'issues': record['issues']}), flush=True)
            if not record['native_acceptable'] or execution['interrupted']:
                stop = 'native_or_configuration_failure' if not execution['interrupted'] else 'interrupted'
                break
    except BaseException as error:
        # Preserve an unscorable collection without leaking arbitrary exception text.
        manifest['exception_type'] = type(error).__name__
        stop = 'collection_exception'
        raise
    finally:
        manifest.update({'finished_utc': now(), 'wall_seconds': time.monotonic() - started,
            'stop_reason': stop, 'invocations_observed': len(records),
            'invocations_scheduled': len(attempts),
            'valid_predictions': sum(r['p_positive'] is not None for r in records),
            'known_native_cost_usd': str(spent),
            'all_observed_costs_known': len(attempts) == len(records) and all(r['native_cost_usd'] is not None for r in records)})
        try:
            _, after = sources()
            unchanged = after == before and digest(BINARY) == BINARY_SHA
        except (ValueError, OSError):
            after, unchanged = {}, False
        manifest.update({'source_sha256_end': after, 'sources_unchanged': unchanged,
                         'status': 'complete' if unchanged and stop != 'collection_exception' else 'invalid'})
        write_json(OUTPUT / 'responses.json', records)
        manifest['output_sha256'] = {p.name: digest(p) for p in sorted(OUTPUT.glob('*.json'))}
        write_json(OUTPUT / ('manifest.json' if manifest['status'] == 'complete' else 'manifest-invalid.json'), manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collect', action='store_true', help='Run the one frozen batch; never overwrite or resume')
    args = parser.parse_args()
    if not args.collect:
        parser.error('--collect is required; this command makes provider requests')
    manifest = collect()
    print(json.dumps({k: manifest[k] for k in ('status', 'stop_reason', 'invocations_observed', 'valid_predictions', 'known_native_cost_usd')}))


if __name__ == '__main__':
    main()
