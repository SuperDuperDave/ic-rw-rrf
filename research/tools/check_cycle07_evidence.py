#!/usr/bin/env python3
"""Independent cycle07 bounded-program, split, score and native custody audit.

Standard library only. No production generator, evaluator, scorer or collector
imports; no provider calls. Raw native text and thinking never enter receipts.
"""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/cycle07-2026-09-10'
MODEL = 'claude-opus-5'
MAX_MAGNITUDE = 1_000_000
MAX_STEPS = 128
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


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def pairs_object(pairs):
    value = {}
    for key, child in pairs:
        if key in value:
            raise ValueError('duplicate_key')
        value[key] = child
    return value


def reject_constant(_):
    raise ValueError('nonfinite')


def read_json(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs_object,
                      parse_constant=reject_constant)


def boolean_answer(text):
    if type(text) is not str:
        return None, 'not_text'
    try:
        value = json.loads(text, object_pairs_hook=pairs_object,
                           parse_constant=reject_constant)
    except (ValueError, TypeError, RecursionError) as error:
        return None, str(error) if str(error) in ('duplicate_key', 'nonfinite') else 'malformed_json'
    if type(value) is not dict:
        return None, 'not_object'
    if set(value) != {'answer'}:
        return None, 'keys'
    if type(value['answer']) is not bool:
        return None, 'not_boolean'
    return value['answer'], None


def evaluate_program(source):
    """Interpret every state transition independently, after whole-tree validation.

    There is no eval/exec/compile call. Even unreachable branches are checked.
    An assignment or if costs one step; range headers cost n+1 visits. The
    Boolean result is separated from scalar final_state.
    """
    require(type(source) is str and 0 < len(source.encode('utf-8')) <= 16_384, 'bounded source bytes')
    try:
        tree = ast.parse(source)
    except (SyntaxError, RecursionError) as error:
        raise ValueError('invalid program syntax') from error
    nodes = list(ast.walk(tree))
    require(len(nodes) <= 512, 'bounded AST nodes')
    statement_count = sum(isinstance(node, ast.stmt) for node in nodes)
    require(8 <= statement_count <= 14, '8-14 executable source statements')
    require(len([line for line in source.splitlines() if line.strip()]) == statement_count
            and len({node.lineno for node in nodes if isinstance(node, ast.stmt)}) == statement_count,
            'one executable statement per nonblank source line')
    require(tree.body and isinstance(tree.body[-1], ast.Assign), 'final predicate assignment')
    last = tree.body[-1]
    require(len(last.targets) == 1 and isinstance(last.targets[0], ast.Name)
            and last.targets[0].id == 'result' and isinstance(last.value, ast.Compare),
            'explicit final Boolean result')
    require(isinstance(last.value.left, ast.BinOp) and isinstance(last.value.left.op, ast.Mod)
            and isinstance(last.value.left.left, ast.Name) and last.value.left.left.id == 'a'
            and isinstance(last.value.left.right, ast.Constant) and type(last.value.left.right.value) is int
            and last.value.left.right.value == 3 and len(last.value.ops) == 1
            and isinstance(last.value.ops[0], ast.Eq) and len(last.value.comparators) == 1
            and isinstance(last.value.comparators[0], ast.Constant)
            and type(last.value.comparators[0].value) is int
            and last.value.comparators[0].value in (0, 1, 2), 'frozen modulo-three predicate family')
    for_count = sum(isinstance(node, ast.For) for node in nodes)
    if_count = sum(isinstance(node, ast.If) for node in nodes)
    require(for_count <= 1 and if_count <= (1 if for_count else 2), 'control-flow count bounds')
    integer_ops = {ast.Add, ast.Sub, ast.Mult, ast.Mod}
    comparison_ops = {ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE}

    def identifier(node):
        require(isinstance(node, ast.Name) and node.id in ('a', 'b', 'c', 'i'), 'scalar variable identifier')

    def integer_expression(node):
        if isinstance(node, ast.Constant):
            require(type(node.value) is int and abs(node.value) <= MAX_MAGNITUDE, 'bounded integer literal')
        elif isinstance(node, ast.Name):
            identifier(node)
        elif isinstance(node, ast.UnaryOp):
            require(isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant), 'signed integer literal')
            integer_expression(node.operand)
        elif isinstance(node, ast.BinOp):
            require(type(node.op) in integer_ops, 'allowlisted integer operator')
            if isinstance(node.op, ast.Mod):
                require(isinstance(node.right, ast.Constant) and type(node.right.value) is int
                        and node.right.value > 0, 'positive literal modulus')
            integer_expression(node.left)
            integer_expression(node.right)
        else:
            raise ValueError('nonallowlisted integer expression: ' + type(node).__name__)

    def predicate(node):
        require(isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1
                and type(node.ops[0]) in comparison_ops, 'single allowlisted comparison')
        integer_expression(node.left)
        integer_expression(node.comparators[0])

    def validate(block, inside_loop=False, inside_if=False):
        for node in block:
            if isinstance(node, ast.Assign):
                require(len(node.targets) == 1 and isinstance(node.targets[0], ast.Name), 'single scalar assignment')
                if node is last:
                    predicate(node.value)
                else:
                    identifier(node.targets[0])
                    integer_expression(node.value)
            elif isinstance(node, ast.If):
                require(not for_count or inside_loop, 'loop conditional inside loop')
                require(not node.orelse and not inside_if, 'nonnested conditional without else')
                predicate(node.test)
                validate(node.body, inside_loop, True)
            elif isinstance(node, ast.For):
                require(not inside_loop and not inside_if and not node.orelse, 'one nonnested loop without else')
                identifier(node.target)
                call = node.iter
                require(isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                        and call.func.id == 'range' and not call.keywords and len(call.args) == 1
                        and isinstance(call.args[0], ast.Constant) and type(call.args[0].value) is int
                        and 3 <= call.args[0].value <= 6, 'literal bounded range')
                validate(node.body, True)
            else:
                raise ValueError('nonallowlisted statement: ' + type(node).__name__)

    validate(tree.body)

    def worst_steps(block):
        total = 0
        for node in block:
            if isinstance(node, ast.For):
                n = node.iter.args[0].value
                total += n + 1 + n * worst_steps(node.body)
            else:
                total += 1 + (worst_steps(node.body) if isinstance(node, ast.If) else 0)
        return total

    worst = worst_steps(tree.body)
    require(worst <= MAX_STEPS, 'static worst-case statement ceiling')
    state, steps, maximum = {}, 0, 0

    def bounded(value):
        nonlocal maximum
        require(type(value) is int and abs(value) <= MAX_MAGNITUDE, 'bounded intermediate integer')
        maximum = max(maximum, abs(value))
        return value

    def value(node):
        if isinstance(node, ast.Constant):
            return bounded(node.value)
        if isinstance(node, ast.Name):
            require(node.id in state, 'read initialized scalar')
            return bounded(state[node.id])
        if isinstance(node, ast.UnaryOp):
            return bounded(-value(node.operand))
        a, b = value(node.left), value(node.right)
        if isinstance(node.op, ast.Add):
            return bounded(a + b)
        if isinstance(node.op, ast.Sub):
            return bounded(a - b)
        if isinstance(node.op, ast.Mult):
            return bounded(a * b)
        return bounded(a % b)

    def test(node):
        a, b = value(node.left), value(node.comparators[0])
        op = type(node.ops[0])
        return {ast.Eq: a == b, ast.NotEq: a != b, ast.Lt: a < b,
                ast.LtE: a <= b, ast.Gt: a > b, ast.GtE: a >= b}[op]

    def tick():
        nonlocal steps
        steps += 1
        require(steps <= MAX_STEPS, 'executed step ceiling')

    answer = None

    def execute(block):
        nonlocal answer
        for node in block:
            if isinstance(node, ast.For):
                for index in range(bounded(node.iter.args[0].value)):
                    tick()
                    state[node.target.id] = bounded(index)
                    execute(node.body)
                tick()
            else:
                tick()
                if isinstance(node, ast.If):
                    execute(node.body if test(node.test) else node.orelse)
                elif node is last:
                    answer = test(node.value)
                else:
                    state[node.targets[0].id] = value(node.value)

    execute(tree.body)
    require(type(answer) is bool, 'Boolean interpretation result')
    return {'answer': answer, 'final_state': dict(sorted(state.items())),
            'executed_statements': steps, 'ast_dump': ast.dump(tree, include_attributes=False),
            'predicate': ast.unparse(last.value), 'max_abs_intermediate': maximum,
            'static_statement_count': statement_count,
            'worst_case_executed_statements': worst,
            'stratum': 'bounded_loop' if for_count else 'sequential'}


def normalized_template(source):
    """Exclude the answer predicate; alpha-rename and erase literal parameters.

    This deliberately conservative structure fingerprint does not claim full
    semantic equivalence. Predicate changes cannot manufacture split novelty.
    """
    tree = ast.parse(source)
    tree.body.pop()
    names = {}

    class Normalize(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id == 'range':
                return node
            label = names.setdefault(node.id, 'v' + str(len(names)))
            return ast.copy_location(ast.Name(id=label, ctx=node.ctx), node)

        def visit_Constant(self, node):
            return ast.copy_location(ast.Constant(value=0), node)

        def visit_UnaryOp(self, node):
            if isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
                return ast.copy_location(ast.Constant(value=0), node)
            return self.generic_visit(node)

    return ast.dump(Normalize().visit(tree), include_attributes=False)


def verify_fixture(fixture):
    """Reconstruct candidate order, all truths, splits and actual provider bytes."""
    require(fixture['candidate_seed'] == 420007 and fixture['shuffle_seed'] == 42, 'frozen generator and split seeds')
    require(fixture['bounds'] == {'max_attempts': 1000, 'max_abs_integer': MAX_MAGNITUDE,
            'max_executed_statements': MAX_STEPS, 'source_lines': [8, 14]}, 'frozen grammar bounds')
    cells = [(stratum, truth) for stratum in ('sequential', 'bounded_loop') for truth in (False, True)]
    candidates = fixture['generation']['candidates']
    require(24 <= len(candidates) <= 1000 and fixture['generation']['attempt_count'] == len(candidates),
            'bounded candidate attempt count')
    rng, cell_counts, structures, accepted, exclusions = random.Random(420007), Counter(), set(), {}, Counter()
    for attempt, candidate in enumerate(candidates):
        index = (attempt // 2) % 81
        op1, op2 = ('+', '-', '*')[index // 27], ('+', '-', '*')[(index // 9) % 3]
        tail, compare = (index // 3) % 3, ('<', '>', '==')[index % 3]
        parameters = [rng.randint(low, high) for low, high in
                      ((1, 9), (2, 7), (1, 6), (5, 11), (3, 6), (7, 13), (0, 2))]
        a, b, c, modulus, iterations, q, rhs = parameters
        stratum = 'sequential' if attempt % 2 == 0 else 'bounded_loop'
        lines = [f'a = {a}', f'b = {b}', f'c = {c}']
        if stratum == 'sequential':
            lines += [f'a = a {op1} b', f'b = (a + c) % {modulus}', f'if b {compare} c:',
                      f'    a = a {op2} c', 'c = c + b', 'if a % 2 == 0:', '    b = b + a']
        else:
            lines += [f'for i in range({iterations}):', f'    a = a {op1} b',
                      f'    b = (b + i) % {modulus}', f'    if b {compare} c:',
                      f'        a = a {op2} i', f'    c = (c + a) % {q}', 'b = b + c']
        tail_source = ('(a + b) + c', '(a - b) + c', '(a + b) - c')[tail]
        lines += [f'a = {tail_source}', f'result = (a % 3 == {rhs})']
        source = '\n'.join(lines) + '\n'
        require(candidate['attempt'] == attempt and candidate['stratum'] == stratum
                and candidate['structural_index'] == index and candidate['structure'] == [op1, op2, tail, compare]
                and candidate['parameters'] == parameters and candidate['program'] == source,
                'candidate enumeration and exact source bytes')
        require(candidate['program_sha256'] == sha(source.encode()), 'candidate source hash')
        try:
            truth = evaluate_program(source)
        except ValueError:
            require(candidate['status'] == 'excluded' and type(candidate['reason']) is str
                    and bool(candidate['reason']), 'bounded evaluator excludes invalid candidate')
            exclusions[candidate['reason']] += 1
            continue
        template = normalized_template(source)
        digest = sha(template.encode())
        require(candidate['template_hash'] == digest and type(candidate['truth']) is bool
                and candidate['truth'] is truth['answer'], 'candidate independent structure and truth')
        cell = stratum, truth['answer']
        reason = ('duplicate_accepted_template' if digest in structures else
                  'cell_full' if cell_counts[cell] >= 6 else None)
        require(candidate['reason'] == reason and candidate['status'] == ('excluded' if reason else 'accepted'),
                'first-valid-candidate acceptance rule')
        if reason:
            exclusions[reason] += 1
        else:
            cell_counts[cell] += 1
            structures.add(digest)
            accepted[attempt] = (candidate, truth, template)
        require(not all(cell_counts[cell] == 6 for cell in cells) or attempt == len(candidates) - 1,
                'stop enumeration immediately once cells fill')
    require(all(cell_counts[cell] == 6 for cell in cells) and len(accepted) == len(structures) == 24,
            '24 unique structures and six per truth/stratum cell')
    require(dict(exclusions) == fixture['generation']['exclusion_counts'], 'candidate exclusion totals')
    items = fixture['items']
    require(len(items) == 24 and len({item['item_id'] for item in items}) == 24
            and len({item['template_id'] for item in items}) == 24, 'distinct item/template IDs')
    require([item['item_id'] for item in items] == sorted(item['item_id'] for item in items), 'canonical item order')
    truth_fields = ('answer', 'final_state', 'executed_statements', 'ast_dump', 'predicate',
                    'max_abs_intermediate', 'static_statement_count', 'stratum', 'worst_case_executed_statements')
    for item in items:
        require(item['attempt'] in accepted, 'accepted candidate backs item')
        candidate, truth, template = accepted[item['attempt']]
        for field in ('program', 'program_sha256', 'template_hash', 'stratum', 'truth'):
            require(item[field] == candidate[field], 'item candidate ' + field)
        require(item['item_id'] == 'i_' + candidate['program_sha256'][:20]
                and item['template_id'] == 't_' + candidate['template_hash'][:20]
                and item['normalized_template'] == template, 'item source/structural identities')
        for field in truth_fields:
            require(item['python_truth'][field] == truth[field], 'independent state/AST/predicate ' + field)
        require(type(item['truth']) is bool and item['truth'] is truth['answer'], 'item typed Boolean truth')
    require({item['attempt'] for item in items} == set(accepted), 'every accepted candidate retained once')
    by_template = {item['template_id']: item for item in items}
    shuffle, split_cells = random.Random(42), []
    for stratum, truth in cells:
        order = sorted(item['template_id'] for item in items if (item['stratum'], item['truth']) == (stratum, truth))
        shuffle.shuffle(order)
        split_cells.append({'stratum': stratum, 'truth': truth, 'template_order': order})
        for index, template_id in enumerate(order):
            item = by_template[template_id]
            require(item['split'] == ('development' if index < 2 else 'reserved')
                    and item['first_role'] == (('G', 'S')[index] if index < 2 else None),
                    'seeded split and counterbalanced first role')
    require(fixture['split_cells'] == split_cells, 'reconstructed cell shuffle order')
    order = sorted(item['item_id'] for item in items if item['split'] == 'development')
    random.Random(42).shuffle(order)
    require(fixture['item_order'] == order and len(order) == 8, 'independent development item order')
    instructions = {
        'G': 'Evaluate the supplied program and answer the final Boolean question.',
        'S': 'Check sequential updates, loop bounds and branch conditions when evaluating the supplied program, then answer the final Boolean question.',
    }
    require(len(fixture['packets']) == 16 and len(set(fixture['request_order'])) == 16, '16 distinct development calls')
    by_item = {item['item_id']: item for item in items}
    for index, item_id in enumerate(order):
        item = by_item[item_id]
        roles = (item['first_role'], 'S' if item['first_role'] == 'G' else 'G')
        for offset, role in enumerate(roles):
            packet = fixture['packets'][index * 2 + offset]
            require(packet['item_id'] == item_id and packet['role'] == role, 'adjacent counterbalanced role calls')
            payload = json.loads(packet['payload'], object_pairs_hook=pairs_object, parse_constant=reject_constant)
            require(payload == {'program': item['program'], 'role_instruction': instructions[role]},
                    'only development source and role instruction enter request')
            require(canonical(payload) == packet['payload'], 'canonical actual provider payload bytes')
            digest = sha(packet['payload'].encode())
            require(packet['payload_sha256'] == digest and packet['packet_id'] == 'p_' + digest[:20], 'payload identity')
    require(fixture['request_order'] == [packet['packet_id'] for packet in fixture['packets']], 'complete frozen request order')
    expected_prompt = '''The input contains a complete Python program and a role instruction.
Follow the role instruction and determine the Boolean value assigned to result
by the final line after executing the program. Python integer arithmetic and
range semantics apply. Return only a JSON object with the single key "answer"
and its Boolean value: {"answer": true} or {"answer": false}.
Do not include reasoning, prose, Markdown, or additional keys.
'''
    require(fixture['system_prompt'] == expected_prompt, 'common framing contains no item, truth or reserve data')
    require(sha(fixture['system_prompt'].encode()) == fixture['system_prompt_sha256'], 'common prompt byte identity')
    return {'item_count': 24, 'development_items': 8, 'reserved_items': 16, 'development_invocations': 16,
            'candidate_attempts': len(candidates), 'exclusion_counts': dict(exclusions),
            'all_python_answers_final_states_and_ASTs_match': True,
            'all_templates_distinct_after_literal_alpha_and_predicate_normalization': True,
            'reserve_absent_from_provider_payloads': True, 'seed42_split_and_call_order_reconstructed': True}


ZERO_STATS = {
    'spawned': 0, 'requested': {'background': 0, 'foreground': 0, 'unset': 0},
    'started_in_background': 0, 'max_depth': 0, 'spawned_by_subagents': 0,
    'completed': 0, 'failed': 0, 'killed': {'parent': 0, 'user': 0, 'system': 0},
    'refused': {'depth_limit': 0, 'concurrency_limit': 0, 'budget': 0}, 'by_type': {},
}
LOCAL_USAGE = {
    'output_tokens_details': None, 'input_tokens': 0, 'output_tokens': 0,
    'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0,
    'server_tool_use': {'web_search_requests': 0, 'web_fetch_requests': 0},
    'service_tier': None, 'cache_creation': {'ephemeral_1h_input_tokens': 0,
                                           'ephemeral_5m_input_tokens': 0},
    'inference_geo': None, 'iterations': None, 'speed': None,
}


def typed_shape(value, expected):
    if type(expected) is dict:
        return type(value) is dict and set(value) == set(expected) and all(
            typed_shape(value[key], child) for key, child in expected.items())
    return value is None if expected is None else type(value) is type(expected) and value == expected


def selected_usage(value):
    if type(value) is not dict:
        return {}
    kept = {key: value[key] for key in ('input_tokens', 'output_tokens',
        'cache_creation_input_tokens', 'cache_read_input_tokens', 'thinking_tokens') if key in value}
    details = value.get('output_tokens_details')
    if type(details) is dict and 'thinking_tokens' in details:
        kept['output_tokens_details'] = {'thinking_tokens': details['thinking_tokens']}
    return kept


def check_raw(record, public_only=False):
    paths = [ROOT / record[key] for key in ('stdout_path', 'stderr_path')]
    if public_only or not all(path.exists() for path in paths):
        return {'status': 'unavailable', 'packet_id': record['packet_id'],
                'reason': 'public-only mode or private stream absent'}
    for path, key in zip(paths, ('stdout_sha256', 'stderr_sha256')):
        require(file_sha(path) == record[key], 'private native stream hash')
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
    terminal = finals[0] if len(finals) == 1 else {}
    if len(finals) == 1:
        require(events[-1] is terminal, 'result is final native frame')
    accepted_model = lambda model: model in (MODEL, MODEL + '[1m]')
    expected_session = record['session_id']
    if len(inits) == 1:
        init = inits[0]
        validations = [(accepted_model(init.get('model')), 'init_model'),
            (init.get('tools') == [] and init.get('mcp_servers') == [], 'enabled_tools_or_mcp'),
            (not init.get('skills') and not init.get('plugins'), 'enabled_plugins_or_skills'),
            (init.get('session_id') == expected_session, 'init_session')]
        require(record['init'] == {k: init.get(k) for k in
                ('model', 'tools', 'mcp_servers', 'skills', 'plugins', 'permissionMode')}, 'native init extraction')
    else:
        validations = [(False, 'init_count')]
        require(record['init'] is None, 'absent native initialization')
    validations += [(len(finals) == 1, 'terminal_result_count'),
        (record['exit_code'] == 0, 'native_exit'), (not record['timed_out'], 'timeout'),
        (terminal.get('subtype') == 'success' and terminal.get('is_error') is False, 'native_result_error'),
        (terminal.get('stop_reason') == 'end_turn', 'terminal_stop'),
        (terminal.get('session_id') == expected_session, 'result_session')]
    issues.update(label for passed, label in validations if not passed)
    messages, models, refusals, local_records, recovery = {}, set(), {}, [], []
    requesting, current = 0, None
    refused = (len(finals) == 1 and terminal.get('is_error') is True
               and terminal.get('stop_reason') == 'refusal'
               and terminal.get('session_id') == expected_session)
    for event in events:
        if event.get('parent_tool_use_id'):
            issues.add('subagent_activity')
        subtype = event.get('subtype', '')
        rid = event.get('request_id')
        known_refusal = (refused and event.get('type') == 'system'
            and subtype == 'model_refusal_no_fallback' and event.get('session_id') == expected_session
            and accepted_model(event.get('original_model')) and type(rid) is str and bool(rid))
        if known_refusal:
            refusals[rid] = {'request_id': rid, 'original_model': event['original_model'],
                'category': 'reasoning_extraction' if event.get('api_refusal_category') == 'reasoning_extraction'
                else 'unrecognized', 'fallback_observed': False}
            issues.add('provider_refusal')
        if event.get('type') == 'system':
            requesting += subtype == 'status' and event.get('status') == 'requesting'
            if subtype == 'api_retry':
                recovery.append(subtype)
            if 'hook' in subtype:
                issues.add('hook_activity')
            if 'fallback' in subtype and not known_refusal:
                issues.add('model_fallback')
                recovery.append(subtype)
        stream = event.get('event', {}) if event.get('type') == 'stream_event' else {}
        message = event.get('message') if event.get('type') == 'assistant' else None
        if stream.get('type') == 'message_start':
            message = stream.get('message', {})
            current = message.get('id')
        if type(message) is dict:
            content = message.get('content')
            local = (refused and event.get('type') == 'assistant' and event.get('is_api_error_message') is True
                and event.get('error') == 'invalid_request' and event.get('parent_tool_use_id') is None
                and event.get('session_id') == expected_session and type(rid) is str and rid in refusals
                and refusals[rid]['category'] == 'reasoning_extraction' and message.get('model') == '<synthetic>'
                and message.get('role') == 'assistant' and message.get('type') == 'message'
                and message.get('stop_reason') == 'refusal' and type(message.get('id')) is str and bool(message['id'])
                and type(content) is list and len(content) == 1 and type(content[0]) is dict
                and set(content[0]) == {'type', 'text'} and content[0]['type'] == 'text'
                and type(content[0]['text']) is str and typed_shape(message.get('usage'), LOCAL_USAGE))
            if local:
                local_records.append({'message_id': message['id'], 'request_id': rid,
                                      'kind': 'native_local_api_error', 'stop_reason': 'refusal'})
                continue
            mid, model = message.get('id'), message.get('model')
            if model:
                models.add(model)
            if mid:
                row = messages.setdefault(mid, {'model': model, 'usage': {}, 'stop_reason': None})
                require(row['model'] == model, 'consistent native message identity')
                row['usage'].update(selected_usage(message.get('usage')))
                if message.get('stop_reason'):
                    row['stop_reason'] = message['stop_reason']
            if any('tool_use' in block.get('type', '') for block in message.get('content', [])):
                issues.add('tool_activity')
        if stream.get('type') == 'content_block_start' and 'tool_use' in stream.get('content_block', {}).get('type', ''):
            issues.add('tool_activity')
        if stream.get('type') == 'message_delta':
            require(current in messages, 'message delta follows provider message start')
            messages[current]['usage'].update(selected_usage(stream.get('usage')))
            if stream.get('delta', {}).get('stop_reason'):
                messages[current]['stop_reason'] = stream['delta']['stop_reason']
    require(messages == record['messages'], 'stream-start message usage attribution')
    require(len(messages) == record['distinct_observed_message_count']
            and requesting == record['requesting_status_count'], 'native request/message counts')
    require(list(refusals.values()) == record['provider_refusals']
            and local_records == record['local_error_records'], 'provider refusal/local error distinction')
    require(recovery == record['recovery_markers'], 'native recovery markers')
    for row in messages.values():
        output = row['usage'].get('output_tokens')
        if output is not None and (type(output) is not int or not 0 <= output <= 500):
            issues.add('message_output_ceiling')
    model_usage = terminal.get('modelUsage', {})
    models.update(model_usage)
    for usage in model_usage.values():
        if 'canonicalModel' in usage and usage['canonicalModel'] != MODEL:
            issues.add('usage_canonical_model')
        if 'provider' in usage and usage['provider'] != 'firstParty':
            issues.add('usage_provider')
    if not models or not all(accepted_model(model) for model in models):
        issues.add('observed_model')
    require(record['observed_models'] == sorted(models), 'observed model extraction')
    require(record['model_usage'] == {model: {k: v for k, v in usage.items() if k in (
        'inputTokens', 'outputTokens', 'cacheReadInputTokens', 'cacheCreationInputTokens', 'thinkingTokens',
        'costUSD', 'contextWindow', 'maxOutputTokens', 'canonicalModel', 'provider')}
        for model, usage in model_usage.items()}, 'native model accounting extraction')
    stats = []
    for final in finals:
        for key in ('subagent_stats', 'subagentStats'):
            if key in final:
                if typed_shape(final[key], ZERO_STATS):
                    stats.append({'field': key, 'counts': final[key]})
                else:
                    issues.add('subagent_statistics_nonzero_or_unknown')
                    if len(finals) == 1 and final[key]:
                        issues.add('subagent_activity')
    require(stats == record['subagent_statistics'], 'native typed zero-agent statistics')
    try:
        raw_cost = terminal.get('total_cost_usd')
        cost = Decimal(str(raw_cost)) if type(raw_cost) in (int, float, str) else None
        if cost is not None and (not cost.is_finite() or cost < 0):
            cost = None
    except ArithmeticError:
        cost = None
    if cost is None:
        issues.add('unknown_cost')
    require((record['native_cost_usd'] is None) == (cost is None), 'native cost coverage')
    if cost is not None:
        require(Decimal(record['native_cost_usd']) == cost, 'native cost extraction')
    require(record['usage'] == selected_usage(terminal.get('usage')), 'aggregate usage extraction')
    for field, key in [('native_subtype', 'subtype'), ('native_is_error', 'is_error'),
                       ('native_stop_reason', 'stop_reason'), ('terminal_session_id', 'session_id'),
                       ('num_turns', 'num_turns')]:
        require(record[field] == terminal.get(key), 'terminal field ' + key)
    terminal_text = terminal.get('result')
    require(record['terminal_text_sha256'] == (sha(terminal_text.encode()) if type(terminal_text) is str else None),
            'terminal answer text hash')
    require(record['issues'] == sorted(issues) and record['native_acceptable'] == (not issues), 'native gate reconstruction')
    answer, failure = boolean_answer(terminal_text) if not issues else (None, None)
    require(type(record['answer']) is type(answer) and record['answer'] == answer
            and record['parse_failure'] == failure, 'strict terminal Boolean reconstruction')
    return {'status': 'verified', 'packet_id': record['packet_id'],
            'provider_message_ids': list(messages), 'provider_message_count': len(messages),
            'local_error_records': local_records, 'provider_refusals': list(refusals.values()),
            'observed_models': sorted(models), 'requesting_status_count': requesting,
            'recovery_markers': recovery, 'native_cost_usd': str(cost) if cost is not None else None,
            'messages_without_output_usage': sum('output_tokens' not in m['usage'] for m in messages.values()),
            'usage': record['usage'], 'native_acceptable': not issues, 'valid_answer': answer is not None}


def artifact_manifest(directory, source_fields=True):
    manifest = read_json(directory / 'manifest.json')
    start = read_json(directory / 'manifest-start.json')
    require(manifest['status'] == 'complete' and start['status'] == 'started', 'artifact manifest lifecycle')
    require(all(manifest.get(key) == value for key, value in start.items() if key != 'status'), 'start/final custody')
    for name, expected in manifest['output_sha256'].items():
        require(file_sha(directory / name) == expected, 'artifact output ' + name)
    if source_fields:
        require(manifest['sources_unchanged'] is True
                and manifest['source_sha256_start'] == manifest['source_sha256_end'], 'source custody equality')
        identities = manifest['source_sha256_start']
    else:
        identities = manifest['input_sha256']
    for name, expected in identities.items():
        require(file_sha(ROOT / name) == expected, 'current pinned source/input ' + name)
    return manifest


def check_controls(collection, fixture):
    binary_sha = '0399c793ff571d5946ef923d80b4f330d05ac4b6842a6b0775468f5d389403c0'
    require(collection['native_binary_sha256'] == binary_sha
            and Path(collection['native_binary']).name == '2.1.267', 'native binary identity')
    overrides = {
        'CLAUDE_CODE_MAX_OUTPUT_TOKENS': '500', 'CLAUDE_CODE_EFFORT_LEVEL': 'high',
        'CLAUDE_CODE_MAX_RETRIES': '0', 'CLAUDE_CODE_RETRY_WATCHDOG': '0',
        'CLAUDE_CODE_NO_MODEL_FALLBACK': '1', 'CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK': '1',
        'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1', 'CLAUDE_CODE_DISABLE_FAST_MODE': '1',
        'CLAUDE_CODE_DISABLE_WORKFLOWS': '1', 'CLAUDE_CODE_AUTO_CONNECT_IDE': '0', 'DISABLE_AUTO_COMPACT': '1',
    }
    require(collection['environment_overrides'] == overrides, 'frozen environment controls')
    require(collection['native_budget_usd'] == '1' and collection['call_wall_seconds'] == 120
            and collection['batch_wall_seconds'] == 300, 'prospective resource ceilings')
    argv = [collection['native_binary'], '--print', '--safe-mode', '--setting-sources', '',
        '--settings', '{"disableAllHooks":true,"autoMemoryEnabled":false}',
        '--tools', '', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
        '--disable-slash-commands', '--no-chrome', '--permission-mode', 'dontAsk',
        '--permission-prompts', 'none', '--no-session-persistence', '--model', MODEL,
        '--effort', 'high', '--max-turns', '1', '--max-budget-usd', '<remaining-native-usd>',
        '--system-prompt', fixture['system_prompt'], '--output-format', 'stream-json', '--verbose',
        '--include-partial-messages', '--include-hook-events', '--prompt-suggestions', 'false',
        '--session-id', '<fresh-uuid>']
    require(collection['argv_template'] == argv, 'frozen native invocation argv')
    require(collection['wire_attempt_count'] is None, 'hidden wire attempts remain unclaimed')
    binary = Path(collection['native_binary'])
    if binary.exists():
        require(file_sha(binary) == binary_sha, 'installed native binary bytes')
    return 'verified' if binary.exists() else 'unavailable'


def check_batch(fixture, public_only=False):
    observation = BASE / 'observations'
    collection = artifact_manifest(observation)
    scored = artifact_manifest(BASE / 'scored', source_fields=False)
    records = read_json(observation / 'responses.json')
    require(collection['prepared_manifest_sha256'] == file_sha(BASE / 'prepared/manifest.json')
            and collection['request_order'] == fixture['request_order'], 'collection preparation anchor')
    binary_status = check_controls(collection, fixture)
    require(collection['invocations_observed'] == collection['invocations_scheduled'] == len(records) <= 16,
            'bounded observation/attempt count')
    require([record['packet_id'] for record in records] == fixture['request_order'][:len(records)],
            'frozen adjacent-call prefix')
    by_id = {p['packet_id']: p for p in fixture['packets']}
    outputs = {'manifest-start.json', 'responses.json'}
    spent, raw_checks, sessions, message_ids = Decimal(0), [], set(), set()
    for ordinal, record in enumerate(records, 1):
        pid = record['packet_id']
        individual, attempt_name = f'{ordinal:02d}-{pid}.json', f'{ordinal:02d}-attempt.json'
        outputs.update((individual, attempt_name))
        require(record['ordinal'] == ordinal and record['payload_sha256'] == by_id[pid]['payload_sha256']
                and record['system_prompt_sha256'] == fixture['system_prompt_sha256'], 'record payload custody')
        require(read_json(observation / individual) == record, 'individual response equality')
        attempt = read_json(observation / attempt_name)
        for field in ('ordinal', 'packet_id', 'session_id', 'started_utc', 'payload_sha256', 'system_prompt_sha256'):
            require(attempt[field] == record[field], 'write-ahead attempt ' + field)
        require(Decimal(attempt['remaining_native_usd']) == Decimal(record['scheduled_remaining_native_usd'])
                == 1 - spent and spent < 1, 'sequential native allowance accounting')
        require(0 < record['scheduled_timeout_seconds'] <= 120
                and record['scheduled_timeout_seconds'] == attempt['timeout_seconds'], 'invocation wall scheduling')
        require(record['session_id'] not in sessions, 'fresh invocation session IDs')
        sessions.add(record['session_id'])
        require(not message_ids.intersection(record['messages']), 'distinct native provider message IDs')
        message_ids.update(record['messages'])
        require(record['native_acceptable'] == (not record['issues']), 'public native gate consistency')
        if record['native_acceptable']:
            require(record['exit_code'] == 0 and not record['timed_out'] and record['native_subtype'] == 'success'
                    and record['native_is_error'] is False and record['native_stop_reason'] == 'end_turn'
                    and record['terminal_session_id'] == record['session_id'], 'public terminal success')
            require(record['init']['model'] in (MODEL, MODEL + '[1m]') and record['init']['tools'] == []
                    and record['init']['mcp_servers'] == [] and not record['init']['skills']
                    and not record['init']['plugins'], 'public context surfaces')
            require(record['observed_models'] and all(model in (MODEL, MODEL + '[1m]')
                    for model in record['observed_models']), 'public actual model IDs')
            require(record['distinct_observed_message_count'] == len(record['messages']), 'public message count')
            for message in record['messages'].values():
                require(message['model'] in (MODEL, MODEL + '[1m]'), 'public provider message model')
                output = message['usage'].get('output_tokens')
                require(output is None or type(output) is int and 0 <= output <= 500, 'public per-message output bound')
            for stats in record['subagent_statistics']:
                require(stats['field'] in ('subagent_stats', 'subagentStats')
                        and typed_shape(stats['counts'], ZERO_STATS), 'public exact zero-agent schema')
            require((record['answer'] is None) == (record['parse_failure'] is not None), 'public parse/answer exclusivity')
            require(record['answer'] is None or type(record['answer']) is bool, 'public Boolean answer')
            if record['answer'] is None:
                require(ordinal == len(records), 'invalid answer stops immediately')
        else:
            require(ordinal == len(records) and record['answer'] is None and record['parse_failure'] is None,
                    'native failure stops and is not a mathematical error')
        if record['interrupted']:
            require(ordinal == len(records), 'interruption stops immediately')
        if record['native_cost_usd'] is not None:
            cost = Decimal(record['native_cost_usd'])
            require(cost.is_finite() and cost >= 0, 'finite nonnegative native cost')
            spent += cost
        for field in ('stdout_path', 'stderr_path'):
            require((ROOT / record[field]).parent == ROOT / collection['private_directory']
                    and record[field].startswith('_sessions/local/cycle07/'), 'private stream boundary')
        raw_checks.append(check_raw(record, public_only))
    require(set(collection['output_sha256']) == outputs, 'all collection artifacts hashed')
    require(Decimal(collection['known_native_cost_usd']) == spent, 'total attempted native acquisition cost')
    require(collection['all_observed_costs_known'] == all(r['native_cost_usd'] is not None for r in records), 'cost coverage')
    require(collection['valid_predictions'] == sum(r['answer'] is not None for r in records), 'valid answer count')
    stop = collection['stop_reason']
    stop_checks = {
        'all_invocations_finished': len(records) == 16 and all(r['native_acceptable'] and r['answer'] is not None
                                                            and not r['interrupted'] for r in records),
        'native_or_configuration_failure': bool(records) and not records[-1]['native_acceptable'],
        'invalid_answer': bool(records) and records[-1]['native_acceptable'] and records[-1]['answer'] is None,
        'interrupted': bool(records) and records[-1]['interrupted'],
        'native_budget_exhausted': len(records) < 16 and spent >= 1,
        'batch_wall_exhausted': len(records) < 16 and collection['wall_seconds'] >= 300,
    }
    require(stop in stop_checks and stop_checks[stop], 'collection stop evidence')
    scores = read_json(BASE / 'scored/scores.json')
    score_check = check_score(scores, fixture, records)
    require(scored['measurement_status'] == scores['status'] and scored['coverage'] == scores['coverage'],
            'scoring manifest summary')
    return {'collection_manifest_sha256': file_sha(observation / 'manifest.json'),
            'scoring_manifest_sha256': file_sha(BASE / 'scored/manifest.json'),
            'native_binary_bytes': binary_status, 'native_cost_usd': str(spent),
            'stop_reason': stop, 'invocations': len(records),
            'raw_streams_verified': sum(row['status'] == 'verified' for row in raw_checks),
            'raw_streams_unavailable': sum(row['status'] == 'unavailable' for row in raw_checks),
            'raw_checks': raw_checks, 'score_check': score_check}


def exact_ratio(numerator, denominator):
    return {'numerator': numerator, 'denominator': denominator,
            'value': float(Fraction(numerator, denominator)) if denominator else None}


def independent_table(pairs):
    # Count each of the four error events by direct predicates on truth/answers.
    def cells_for(rows):
        return {str(g) + str(s): sum((p['g_answer'] != p['truth']) == bool(g)
                                    and (p['s_answer'] != p['truth']) == bool(s) for p in rows)
                for g in (0, 1) for s in (0, 1)}

    cells, n = cells_for(pairs), len(pairs)
    gwrong = sum(p['g_answer'] != p['truth'] for p in pairs)
    swrong = sum(p['s_answer'] != p['truth'] for p in pairs)
    by_truth = {}
    for truth in (False, True):
        rows = [p for p in pairs if p['truth'] is truth]
        c, ny = cells_for(rows), len(rows)
        gy = sum(p['g_answer'] != truth for p in rows)
        sy = sum(p['s_answer'] != truth for p in rows)
        by_truth[str(truth).lower()] = {'N': ny, 'cells': c, 'g_error': exact_ratio(gy, ny),
            's_error': exact_ratio(sy, ny), 'joint_error_excess': exact_ratio(c['11'] * ny - gy * sy, ny * ny)}
    return {'N': n, 'cells': cells, 'by_truth': by_truth,
        'g_error': exact_ratio(gwrong, n), 's_error': exact_ratio(swrong, n),
        'disagreement': exact_ratio(sum(p['g_answer'] != p['s_answer'] for p in pairs), n),
        'available_corrections_to_g': exact_ratio(cells['10'], n),
        'conditional_correction': exact_ratio(cells['10'], gwrong),
        'potential_harm_relative_to_g': exact_ratio(cells['01'], n),
        'conditional_harm': exact_ratio(cells['01'], n - gwrong),
        's_minus_g_error': exact_ratio(swrong - gwrong, n)}


def check_score(scores, fixture, records):
    observations, answers, failures = [], {}, {}
    for record in records:
        pid, answer = record['packet_id'], record['answer']
        require(pid not in answers and pid not in failures, 'one observation per invocation')
        if record['native_acceptable'] and answer is not None:
            require(type(answer) is bool and record['parse_failure'] is None, 'typed scored observation')
            answers[pid] = answer
        else:
            require(answer is None, 'invalid observation excluded from mathematical errors')
            failures[pid] = ('native:' + ','.join(record['issues']) if not record['native_acceptable']
                             else 'parse:' + record['parse_failure'])
    item_answers = {}
    for packet in fixture['packets']:
        pid, item_id, role = packet['packet_id'], packet['item_id'], packet['role']
        observations.append({'packet_id': pid, 'item_id': item_id, 'role': role,
            'status': 'valid' if pid in answers else 'invalid' if pid in failures else 'unsent',
            'answer': answers.get(pid), 'failure': failures.get(pid)})
        if pid in answers:
            item_answers.setdefault(item_id, {})[role] = answers[pid]
    by_item = {item['item_id']: item for item in fixture['items']}
    pairs = []
    for item_id in fixture['item_order']:
        observed = item_answers.get(item_id, {})
        if set(observed) == {'G', 'S'}:
            item = by_item[item_id]
            truth = evaluate_program(item['program'])['answer']
            pairs.append({'item_id': item_id, 'stratum': item['stratum'], 'truth': truth,
                'g_answer': observed['G'], 's_answer': observed['S'],
                'g_error': observed['G'] != truth, 's_error': observed['S'] != truth})
    table = independent_table(pairs)
    table['by_stratum'] = {stratum: independent_table([p for p in pairs if p['stratum'] == stratum])
                          for stratum in ('sequential', 'bounded_loop')}
    counts = {'g_wrong': sum(p['g_error'] for p in pairs),
              'g_correct': sum(not p['g_error'] for p in pairs),
              's_wrong': sum(p['s_error'] for p in pairs),
              's_correct': sum(not p['s_error'] for p in pairs),
              'disagreements': sum(p['g_answer'] != p['s_answer'] for p in pairs),
              'correct_dissent': sum(p['g_error'] and not p['s_error'] for p in pairs)}
    complete = len(pairs) == 8
    gate = complete and all(counts[key] > 0 for key in
                            ('g_wrong', 'g_correct', 's_wrong', 's_correct', 'disagreements'))
    expected = {'schema_version': 1, 'status': 'complete' if complete else 'incomplete',
        'coverage': {'planned_items': 8, 'planned_invocations': 16, 'valid_pairs': len(pairs),
            'valid_answers': len(answers), 'invalid_answers': len(failures),
            'unsent': 16 - len(answers) - len(failures), 'valid_unpaired_answers': len(answers) - 2 * len(pairs)},
        'observations': observations, 'valid_pairs': pairs, 'primary': table if complete else None,
        'partial_valid_pair_table': None if complete else table,
        'observability_gate': {'passed': gate, 'complete_eight_pairs': complete, 'counts': counts},
        'interpretation': 'Finite balanced panel; descriptive selected valid-pair counts. '
                          'No independence test, calibration estimate, or population claim.'}
    require(canonical(scores) == canonical(expected), 'all paired counts, exact ratio numerators/denominators, coverage and gate')
    return {'measurement_status': expected['status'], 'coverage': expected['coverage'],
            'observability_gate': expected['observability_gate'],
            'independently_recomputed_table': table,
            'all_outputs_match': True}


def run(public_only=False, prepared_only=False):
    prepared_dir = BASE / 'prepared'
    manifest = read_json(prepared_dir / 'manifest.json')
    require(manifest['source_sha256_start'] == manifest['source_sha256_end'], 'preparation source custody')
    for name, expected in manifest['source_sha256_start'].items():
        require(file_sha(ROOT / name) == expected, 'preparation source ' + name)
    fixture = read_json(prepared_dir / 'fixture.json')
    for name, expected in manifest['artifact_sha256'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'prepared artifact relative path')
        require(file_sha(prepared_dir / name) == expected, 'prepared artifact ' + name)
    expected_paths = {'fixture.json', 'independent-truth.json', 'system-prompt.txt'} | {
        'payloads/' + p['packet_id'] + '.json' for p in fixture['packets']}
    require(set(manifest['artifact_sha256']) == expected_paths, 'complete prepared artifact inventory')
    require((prepared_dir / 'system-prompt.txt').read_bytes() == fixture['system_prompt'].encode(), 'prepared system prompt bytes')
    for packet in fixture['packets']:
        require((prepared_dir / 'payloads' / (packet['packet_id'] + '.json')).read_bytes()
                == packet['payload'].encode(), 'prepared actual payload bytes')
    require(manifest['request_order'] == fixture['request_order'], 'manifest request order')
    require(manifest['checker'] == '_sessions/tools/check_cycle07_evidence.py', 'independent checker identity')
    python = Path(manifest['python']['executable'])
    python_status = 'unavailable'
    if python.exists():
        require(file_sha(python) == manifest['python']['executable_sha256'], 'truth Python executable bytes')
        python_status = 'verified'
    oracle = verify_fixture(fixture)
    independent = read_json(prepared_dir / 'independent-truth.json')
    require(independent['verification'] == oracle, 'retained independent preparation verification')
    expected_truth = [{'item_id': item['item_id'], **evaluate_program(item['program'])} for item in fixture['items']]
    require(canonical(independent['items']) == canonical(expected_truth), 'all 24 retained independent truth records')
    tree = ast.parse((ROOT / '_sessions/tools/run_cycle07_programs.py').read_text())
    anchors = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == 'PREPARED_SHA' for target in node.targets)]
    require(anchors == [file_sha(prepared_dir / 'manifest.json')], 'literal launcher preparation anchor')
    batch = None if prepared_only else check_batch(fixture, public_only)
    status = 'passed_prepared_only' if prepared_only else 'passed_public_only' if batch['raw_streams_unavailable'] else 'passed'
    return {'schema_version': 1, 'status': status, 'checked_utc': datetime.now(timezone.utc).isoformat(),
        'checker_sha256': file_sha(Path(__file__)), 'checks_passed': CHECKS,
        'prepared_manifest_sha256': file_sha(prepared_dir / 'manifest.json'),
        'truth_python_bytes': python_status, 'prepared_oracle': oracle, 'batch': batch,
        'independence': 'Standard-library AST interpreter and direct event counting; no production imports or execution.',
        'limitations': [
            'Fresh contexts establish no supplied shared conversation history, not statistical independence.',
            'Eight deliberately balanced development items do not estimate natural task prevalence or population performance.',
            'Truth-conditioned joint-error excess does not isolate shared item difficulty or causal dependence.',
            'The observability gate checks denominator feasibility; passing is not precision, power or a useful effect.',
            'Full primary requires all eight valid pairs; partial valid pairs form a selected denominator.',
            'Syntactic structural distinctness is not proof of semantic inequivalence or independent task sampling.',
            'Native streams do not enumerate hidden transport attempts; unavailable message usage remains unverified.',
            'Native accounting is not subscription billing; per-response output ceilings do not cap aggregate invocation tokens.',
            'Public-only checks cannot verify absent private streams or installed binaries.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared-only', action='store_true', help='Check preparation without reading cycle07 outcomes')
    parser.add_argument('--public-only', action='store_true', help='Mark private native streams unavailable without reading them')
    parser.add_argument('--output', type=Path, help='Write a new receipt; never overwrite')
    args = parser.parse_args()
    result = run(args.public_only, args.prepared_only)
    if args.output:
        with args.output.open('x', encoding='utf-8') as handle:
            json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write('\n')
    print(json.dumps({'status': result['status'], 'checks_passed': result['checks_passed'],
                      'raw_streams_verified': result['batch']['raw_streams_verified'] if result['batch'] else None}))


if __name__ == '__main__':
    main()
