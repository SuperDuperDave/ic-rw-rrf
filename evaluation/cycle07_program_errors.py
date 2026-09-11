"""Cycle07 bounded integer programs, sealed observations, and joint-error counts.

Standard library only. Preparation never reads solver responses or calls a
provider. Python truth execution accepts only the fully validated bounded AST.
"""

import argparse
import ast
from collections import Counter
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import platform
import random
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
CODE = 'evaluation/cycle07_program_errors.py'
TESTS = 'evaluation/tests/test_cycle07_program_errors.py'
CHECKER = '_sessions/tools/check_cycle07_evidence.py'
DESIGN = '_sessions/cycles/2026-09-10-cycle07-observation-design.md'
GRAMMAR = '_sessions/cycles/2026-09-10-cycle07-program-grammar.md'
PROTOCOL = '_sessions/cycles/2026-09-10-cycle07-execution-protocol.md'
SHUFFLE_SEED = 42
CANDIDATE_SEED = 420007
MAX_ATTEMPTS = 1000
MAX_MAGNITUDE = 1_000_000
MAX_STEPS = 128
STRATA = ('sequential', 'bounded_loop')
ROLES = ('G', 'S')
CELLS = tuple(itertools.product(STRATA, (False, True)))
ROLE_INSTRUCTIONS = {
    'G': 'Evaluate the supplied program and answer the final Boolean question.',
    'S': 'Check sequential updates, loop bounds and branch conditions when evaluating '
         'the supplied program, then answer the final Boolean question.',
}
SYSTEM_PROMPT = '''The input contains a complete Python program and a role instruction.
Follow the role instruction and determine the Boolean value assigned to result
by the final line after executing the program. Python integer arithmetic and
range semantics apply. Return only a JSON object with the single key "answer"
and its Boolean value: {"answer": true} or {"answer": false}.
Do not include reasoning, prose, Markdown, or additional keys.
'''


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _file_sha(path):
    return sha256_bytes(Path(path).read_bytes())


class AnswerParseError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AnswerParseError('duplicate_key')
        result[key] = value
    return result


def _reject_constant(_value):
    raise AnswerParseError('nonfinite')


def parse_answer(text):
    """Parse exactly one JSON object containing exactly one Boolean answer."""
    if type(text) is not str:
        raise AnswerParseError('not_text')
    try:
        value = json.loads(text, object_pairs_hook=_unique_pairs,
                           parse_constant=_reject_constant)
    except AnswerParseError:
        raise
    except (ValueError, TypeError, RecursionError) as error:
        raise AnswerParseError('malformed_json') from error
    if type(value) is not dict:
        raise AnswerParseError('not_object')
    if set(value) != {'answer'}:
        raise AnswerParseError('keys')
    if type(value['answer']) is not bool:
        raise AnswerParseError('not_boolean')
    return value['answer']


strictparse_answer = parse_answer


def validate_program(source):
    """Check the entire AST, including unreachable branches, before execution.

    The static execution ceiling proves termination for this language. State
    initialization is checked along every possible branch before compilation.
    """
    if type(source) is not str or not 0 < len(source.encode('utf-8')) <= 16_384:
        raise ValueError('invalid_source_size')
    try:
        tree = ast.parse(source, mode='exec')
    except (SyntaxError, RecursionError) as error:
        raise ValueError('invalid_syntax') from error
    nodes = list(ast.walk(tree))
    if len(nodes) > 512:
        raise ValueError('ast_size_bound')
    statements = [node for node in nodes if isinstance(node, ast.stmt)]
    if not 8 <= len(statements) <= 14:
        raise ValueError('source_line_bound')
    # One statement/header per nonblank line, with no comments/docstrings.
    if len([line for line in source.splitlines() if line.strip()]) != len(statements):
        raise ValueError('one_statement_per_line')
    last = tree.body[-1]
    if not (isinstance(last, ast.Assign) and len(last.targets) == 1
            and isinstance(last.targets[0], ast.Name) and last.targets[0].id == 'result'):
        raise ValueError('missing_final_result')
    final = last.value
    if not (isinstance(final, ast.Compare) and len(final.ops) == 1
            and isinstance(final.ops[0], ast.Eq) and len(final.comparators) == 1
            and isinstance(final.left, ast.BinOp) and isinstance(final.left.op, ast.Mod)
            and isinstance(final.left.left, ast.Name) and final.left.left.id == 'a'
            and isinstance(final.left.right, ast.Constant) and type(final.left.right.value) is int
            and final.left.right.value == 3 and isinstance(final.comparators[0], ast.Constant)
            and type(final.comparators[0].value) is int and final.comparators[0].value in (0, 1, 2)):
        raise ValueError('invalid_final_predicate')
    loops = sum(isinstance(node, ast.For) for node in nodes)
    conditionals = sum(isinstance(node, ast.If) for node in nodes)
    if loops > 1 or conditionals > (1 if loops else 2):
        raise ValueError('control_count_bound')

    def scalar(node):
        if not isinstance(node, ast.Name) or node.id not in ('a', 'b', 'c', 'i'):
            raise ValueError('invalid_scalar')

    def integer(node, known):
        if isinstance(node, ast.Constant):
            if type(node.value) is not int or abs(node.value) > MAX_MAGNITUDE:
                raise ValueError('invalid_integer_literal')
        elif isinstance(node, ast.Name):
            scalar(node)
            if node.id not in known:
                raise ValueError('uninitialized_scalar')
        elif isinstance(node, ast.UnaryOp):
            if not (isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant)
                    and type(node.operand.value) is int and node.operand.value >= 0):
                raise ValueError('invalid_signed_literal')
            integer(node.operand, known)
        elif isinstance(node, ast.BinOp):
            if type(node.op) not in (ast.Add, ast.Sub, ast.Mult, ast.Mod):
                raise ValueError('invalid_integer_operator')
            if isinstance(node.op, ast.Mod) and not (
                    isinstance(node.right, ast.Constant) and type(node.right.value) is int
                    and node.right.value > 0):
                raise ValueError('nonpositive_or_nonliteral_modulus')
            integer(node.left, known)
            integer(node.right, known)
        else:
            raise ValueError('invalid_integer_expression')

    def comparison(node, known):
        if not (isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1
                and type(node.ops[0]) in (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
            raise ValueError('invalid_comparison')
        integer(node.left, known)
        integer(node.comparators[0], known)

    def block(body, known, inside_loop=False, inside_if=False):
        known = set(known)
        worst = 0
        for node in body:
            if isinstance(node, ast.Assign):
                if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                    raise ValueError('invalid_assignment')
                if node is last:
                    comparison(node.value, known)
                else:
                    scalar(node.targets[0])
                    integer(node.value, known)
                    known.add(node.targets[0].id)
                worst += 1
            elif isinstance(node, ast.If):
                if node.orelse or inside_if or (loops and not inside_loop):
                    raise ValueError('invalid_conditional_location')
                comparison(node.test, known)
                child_worst, _ = block(node.body, known, inside_loop, True)
                worst += 1 + child_worst
            elif isinstance(node, ast.For):
                if inside_loop or inside_if or node.orelse:
                    raise ValueError('invalid_loop_location')
                scalar(node.target)
                call = node.iter
                if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                        and call.func.id == 'range' and len(call.args) == 1 and not call.keywords
                        and isinstance(call.args[0], ast.Constant) and type(call.args[0].value) is int
                        and 3 <= call.args[0].value <= 6):
                    raise ValueError('invalid_bounded_range')
                n = call.args[0].value
                known.add(node.target.id)
                child_worst, child_known = block(node.body, known, True)
                known.update(child_known)  # range executes at least three times.
                worst += n + 1 + n * child_worst
            else:
                raise ValueError('invalid_statement')
        return worst, known

    worst, _known = block(tree.body, set())
    if worst > MAX_STEPS:
        raise ValueError('static_step_bound')
    return tree, {'static_statement_count': len(statements),
                  'worst_case_executed_statements': worst,
                  'stratum': 'bounded_loop' if loops else 'sequential'}


def python_truth(source):
    """Execute validated code under this exact Python, with bounded instrumentation.

    Instrumentation wraps arithmetic results but delegates all state transitions
    and branching to Python. This is independent of the audit AST interpreter.
    The unchanged source is executed only after the instrumented version passes.
    """
    tree, metadata = validate_program(source)
    count, maximum = 0, 0

    def bound(value):
        nonlocal maximum
        if type(value) is not int or abs(value) > MAX_MAGNITUDE:
            raise ValueError('intermediate_magnitude_bound')
        maximum = max(maximum, abs(value))
        return value

    def tick():
        nonlocal count
        count += 1
        if count > MAX_STEPS:
            raise ValueError('executed_statement_bound')

    class Instrument(ast.NodeTransformer):
        def _wrap(self, node):
            self.generic_visit(node)
            return ast.copy_location(ast.Call(func=ast.Name(id='_bound', ctx=ast.Load()),
                                              args=[node], keywords=[]), node)

        visit_BinOp = _wrap
        visit_UnaryOp = _wrap

        def visit_Constant(self, node):
            return ast.copy_location(ast.Call(func=ast.Name(id='_bound', ctx=ast.Load()),
                                              args=[node], keywords=[]), node)

        def _tick_node(self, node):
            return ast.copy_location(ast.Expr(value=ast.Call(
                func=ast.Name(id='_tick', ctx=ast.Load()), args=[], keywords=[])), node)

        def visit_Assign(self, node):
            self.generic_visit(node)
            return [self._tick_node(node), node]

        def visit_If(self, node):
            self.generic_visit(node)
            return [self._tick_node(node), node]

        def visit_For(self, node):
            self.generic_visit(node)
            node.body.insert(0, self._tick_node(node))
            return [self._tick_node(node), node]

    instrumented = ast.fix_missing_locations(Instrument().visit(copy.deepcopy(tree)))
    safe_globals = {'__builtins__': {}, 'range': range, '_bound': bound, '_tick': tick}
    checked_state = {}
    exec(compile(instrumented, '<cycle07-bounded>', 'exec'), safe_globals, checked_state)
    if count > metadata['worst_case_executed_statements']:
        raise AssertionError('actual count exceeds static termination proof')
    final_state = {}
    exec(compile(tree, '<cycle07-validated>', 'exec'), {'__builtins__': {}, 'range': range}, final_state)
    if final_state != checked_state or type(final_state.get('result')) is not bool:
        raise AssertionError('instrumented and unchanged Python disagree')
    answer = final_state.pop('result')
    return {'answer': answer, 'final_state': dict(sorted(final_state.items())),
            'executed_statements': count, 'max_abs_intermediate': maximum,
            'ast_dump': ast.dump(tree, include_attributes=False),
            'predicate': ast.unparse(tree.body[-1].value), **metadata}


def normalized_template(source):
    """Conservative syntax identity modulo constants, alpha names and predicate."""
    tree = ast.parse(source)
    tree.body.pop()
    names = {}

    class Normalize(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id == 'range':
                return node
            new = names.setdefault(node.id, 'v' + str(len(names)))
            return ast.copy_location(ast.Name(id=new, ctx=node.ctx), node)

        def visit_Constant(self, node):
            return ast.copy_location(ast.Constant(value=0), node)

        def visit_UnaryOp(self, node):
            if isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
                return ast.copy_location(ast.Constant(value=0), node)
            return self.generic_visit(node)

    return ast.dump(Normalize().visit(tree), include_attributes=False)


def _candidate(attempt, rng):
    structures = tuple(itertools.product(('+', '-', '*'), ('+', '-', '*'),
                                        (0, 1, 2), ('<', '>', '==')))
    structural_index = (attempt // 2) % len(structures)
    op1, op2, tail, cmp = structures[structural_index]
    a, b, c, mod, n, q, rhs = (rng.randint(low, high) for low, high in
                              ((1, 9), (2, 7), (1, 6), (5, 11), (3, 6), (7, 13), (0, 2)))
    tail_expression = ('(a + b) + c', '(a - b) + c', '(a + b) - c')[tail]
    prefix = f'a = {a}\nb = {b}\nc = {c}\n'
    if attempt % 2 == 0:
        stratum = 'sequential'
        body = (f'a = a {op1} b\nb = (a + c) % {mod}\nif b {cmp} c:\n'
                f'    a = a {op2} c\nc = c + b\nif a % 2 == 0:\n    b = b + a\n')
    else:
        stratum = 'bounded_loop'
        body = (f'for i in range({n}):\n    a = a {op1} b\n    b = (b + i) % {mod}\n'
                f'    if b {cmp} c:\n        a = a {op2} i\n'
                f'    c = (c + a) % {q}\nb = b + c\n')
    return {'attempt': attempt, 'stratum': stratum, 'structural_index': structural_index,
            'structure': [op1, op2, tail, cmp], 'parameters': [a, b, c, mod, n, q, rhs],
            'program': prefix + body + f'a = {tail_expression}\nresult = (a % 3 == {rhs})\n'}


def validate_payload(payload):
    if type(payload) is not dict or set(payload) != {'program', 'role_instruction'}:
        raise ValueError('provider payload has unexpected fields')
    if type(payload['role_instruction']) is not str or payload['role_instruction'] not in ROLE_INSTRUCTIONS.values():
        raise ValueError('provider role instruction is not frozen')
    validate_program(payload['program'])
    return payload


def build_fixture():
    """Return the deterministic local fixture in memory; never write or call out."""
    if not (ROOT / GRAMMAR).is_file():
        raise ValueError('pre-enumeration grammar is missing')
    rng, counts, seen = random.Random(CANDIDATE_SEED), Counter(), set()
    candidates, items = [], []
    for attempt in range(MAX_ATTEMPTS):
        candidate = _candidate(attempt, rng)
        candidate['program_sha256'] = sha256_bytes(candidate['program'].encode('utf-8'))
        try:
            truth = python_truth(candidate['program'])
        except ValueError as error:
            candidate.update(status='excluded', reason=str(error))
            candidates.append(candidate)
            continue
        template = normalized_template(candidate['program'])
        digest = sha256_bytes(template.encode('utf-8'))
        candidate.update(template_hash=digest, truth=truth['answer'])
        cell = candidate['stratum'], truth['answer']
        if digest in seen:
            candidate.update(status='excluded', reason='duplicate_accepted_template')
        elif counts[cell] >= 6:
            candidate.update(status='excluded', reason='cell_full')
        else:
            candidate.update(status='accepted', reason=None)
            seen.add(digest)
            counts[cell] += 1
            items.append({'item_id': 'i_' + candidate['program_sha256'][:20],
                          'template_id': 't_' + digest[:20], 'template_hash': digest,
                          'normalized_template': template, 'program': candidate['program'],
                          'program_sha256': candidate['program_sha256'], 'attempt': attempt,
                          'stratum': candidate['stratum'], 'truth': truth['answer'],
                          'python_truth': truth})
        candidates.append(candidate)
        if all(counts[cell] == 6 for cell in CELLS):
            break
    else:
        raise ValueError('required cells unfilled within 1000 attempts')
    by_template = {item['template_id']: item for item in items}
    split_rng, split_cells = random.Random(SHUFFLE_SEED), []
    for stratum, truth in CELLS:
        order = sorted(item['template_id'] for item in items
                       if (item['stratum'], item['truth']) == (stratum, truth))
        split_rng.shuffle(order)
        split_cells.append({'stratum': stratum, 'truth': truth, 'template_order': order})
        for index, template_id in enumerate(order):
            item = by_template[template_id]
            item['split'] = 'development' if index < 2 else 'reserved'
            item['first_role'] = ROLES[index] if index < 2 else None
    item_order = sorted(item['item_id'] for item in items if item['split'] == 'development')
    random.Random(SHUFFLE_SEED).shuffle(item_order)
    by_item = {item['item_id']: item for item in items}
    packets = []
    for item_id in item_order:
        item = by_item[item_id]
        first = item['first_role']
        for role in (first, 'S' if first == 'G' else 'G'):
            payload = canonical_json(validate_payload({'program': item['program'],
                                                       'role_instruction': ROLE_INSTRUCTIONS[role]}))
            digest = sha256_bytes(payload.encode('utf-8'))
            packets.append({'packet_id': 'p_' + digest[:20], 'item_id': item_id, 'role': role,
                            'payload': payload, 'payload_sha256': digest})
    if len(items) != 24 or len({p['packet_id'] for p in packets}) != 16:
        raise AssertionError('fixed fixture dimensions failed')
    return {'schema_version': 1, 'system_prompt': SYSTEM_PROMPT,
            'system_prompt_sha256': sha256_bytes(SYSTEM_PROMPT.encode('utf-8')),
            'candidate_seed': CANDIDATE_SEED, 'shuffle_seed': SHUFFLE_SEED,
            'bounds': {'max_attempts': MAX_ATTEMPTS, 'max_abs_integer': MAX_MAGNITUDE,
                       'max_executed_statements': MAX_STEPS, 'source_lines': [8, 14]},
            'generation': {'attempt_count': len(candidates), 'candidates': candidates,
                           'exclusion_counts': dict(sorted(Counter(c['reason'] for c in candidates
                                                                  if c['status'] == 'excluded').items()))},
            'split_cells': split_cells, 'item_order': item_order,
            'request_order': [p['packet_id'] for p in packets], 'packets': packets,
            'items': sorted(items, key=lambda item: item['item_id'])}


def validate_fixture(fixture):
    if fixture != build_fixture():
        raise ValueError('fixture differs from canonical preparation')
    return fixture


def _ratio(numerator, denominator):
    return {'numerator': numerator, 'denominator': denominator,
            'value': numerator / denominator if denominator else None}


def _table(pairs):
    by_truth = {}
    total = Counter({'00': 0, '01': 0, '10': 0, '11': 0})
    for truth in (False, True):
        counts = Counter({'00': 0, '01': 0, '10': 0, '11': 0})
        for pair in pairs:
            if pair['truth'] is truth:
                counts[str(int(pair['g_error'])) + str(int(pair['s_error']))] += 1
        n = sum(counts.values())
        g_wrong, s_wrong = counts['10'] + counts['11'], counts['01'] + counts['11']
        # Exact integer numerator for C_y avoids subtractive floating error.
        excess = _ratio(counts['11'] * n - g_wrong * s_wrong, n * n)
        by_truth[str(truth).lower()] = {'N': n, 'cells': dict(counts),
            'g_error': _ratio(g_wrong, n), 's_error': _ratio(s_wrong, n),
            'joint_error_excess': excess}
        total.update(counts)
    n = sum(total.values())
    g_wrong, s_wrong = total['10'] + total['11'], total['01'] + total['11']
    return {'N': n, 'cells': dict(total), 'by_truth': by_truth,
            'g_error': _ratio(g_wrong, n), 's_error': _ratio(s_wrong, n),
            'disagreement': _ratio(total['10'] + total['01'], n),
            'available_corrections_to_g': _ratio(total['10'], n),
            'conditional_correction': _ratio(total['10'], g_wrong),
            'potential_harm_relative_to_g': _ratio(total['01'], n),
            'conditional_harm': _ratio(total['01'], n - g_wrong),
            's_minus_g_error': _ratio(s_wrong - g_wrong, n)}


def score_answers(fixture, answers, failures=None):
    """Score typed Boolean observations without imputing invalid/unsent answers."""
    validate_fixture(fixture)
    failures = {} if failures is None else failures
    if type(answers) is not dict or type(failures) is not dict:
        raise ValueError('answer/failure mappings required')
    ids = set(fixture['request_order'])
    if not set(answers) <= ids or not set(failures) <= ids or set(answers) & set(failures):
        raise ValueError('unknown or overlapping answer/failure IDs')
    if any(type(value) is not bool for value in answers.values()):
        raise ValueError('answers must be Boolean')
    if any(type(value) is not str or not value for value in failures.values()):
        raise ValueError('failures must have nonempty codes')
    items = {item['item_id']: item for item in fixture['items']}
    observations, by_item = [], {}
    for packet in fixture['packets']:
        pid, item_id, role = packet['packet_id'], packet['item_id'], packet['role']
        status = 'valid' if pid in answers else 'invalid' if pid in failures else 'unsent'
        observations.append({'packet_id': pid, 'item_id': item_id, 'role': role, 'status': status,
                             'answer': answers.get(pid), 'failure': failures.get(pid)})
        if pid in answers:
            by_item.setdefault(item_id, {})[role] = answers[pid]
    pairs = []
    for item_id in fixture['item_order']:
        observed = by_item.get(item_id, {})
        if set(observed) != set(ROLES):
            continue
        item = items[item_id]
        pairs.append({'item_id': item_id, 'stratum': item['stratum'], 'truth': item['truth'],
                      'g_answer': observed['G'], 's_answer': observed['S'],
                      'g_error': observed['G'] != item['truth'],
                      's_error': observed['S'] != item['truth']})
    table = _table(pairs)
    table['by_stratum'] = {stratum: _table([p for p in pairs if p['stratum'] == stratum])
                           for stratum in STRATA}
    complete = len(pairs) == 8
    counts = {'g_wrong': table['g_error']['numerator'],
              'g_correct': len(pairs) - table['g_error']['numerator'],
              's_wrong': table['s_error']['numerator'],
              's_correct': len(pairs) - table['s_error']['numerator'],
              'disagreements': table['disagreement']['numerator'],
              'correct_dissent': table['available_corrections_to_g']['numerator']}
    gate = complete and all(counts[key] > 0 for key in
                            ('g_wrong', 'g_correct', 's_wrong', 's_correct', 'disagreements'))
    return {'schema_version': 1, 'status': 'complete' if complete else 'incomplete',
            'coverage': {'planned_items': 8, 'planned_invocations': 16,
                         'valid_pairs': len(pairs), 'valid_answers': len(answers),
                         'invalid_answers': len(failures), 'unsent': len(ids - set(answers) - set(failures)),
                         'valid_unpaired_answers': len(answers) - 2 * len(pairs)},
            'observations': observations, 'valid_pairs': pairs,
            'primary': table if complete else None,
            'partial_valid_pair_table': table if not complete else None,
            'observability_gate': {'passed': gate, 'complete_eight_pairs': complete, 'counts': counts},
            'interpretation': 'Finite balanced panel; descriptive selected valid-pair counts. '
                              'No independence test, calibration estimate, or population claim.'}


def _sources():
    return {path: _file_sha(ROOT / path) for path in (CODE, TESTS, CHECKER, DESIGN, GRAMMAR, PROTOCOL)}


def _load_checker():
    spec = importlib.util.spec_from_file_location('cycle07_independent_checker', ROOT / CHECKER)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    return checker


def _python_identity():
    executable = Path(sys.executable).resolve()
    return {'executable': str(executable), 'executable_sha256': _file_sha(executable),
            'version': sys.version, 'implementation': platform.python_implementation()}


def prepare_fixture(output_directory, preparation_argv=None):
    """Verify independent truth and write a new, exclusively created preparation."""
    started = time.monotonic()
    source_hashes = _sources()
    fixture = build_fixture()
    checker = _load_checker()
    evidence = checker.verify_fixture(fixture)
    truth_fields = ('answer', 'final_state', 'executed_statements', 'ast_dump', 'predicate',
                    'max_abs_intermediate', 'static_statement_count', 'stratum')
    reconstructed = []
    for item in fixture['items']:
        checked = checker.evaluate_program(item['program'])
        for field in truth_fields:
            if checked[field] != item['python_truth'][field]:
                raise ValueError('independent truth discrepancy: ' + item['item_id'] + ':' + field)
        reconstructed.append({'item_id': item['item_id'], **checked})
    if source_hashes != _sources():
        raise ValueError('source changed during truth preparation')
    local_seconds = time.monotonic() - started
    artifacts = {'fixture.json': canonical_json(fixture) + '\n',
                 'independent-truth.json': canonical_json({'verification': evidence,
                                                          'items': reconstructed}) + '\n',
                 'system-prompt.txt': fixture['system_prompt']}
    artifacts.update({'payloads/' + p['packet_id'] + '.json': p['payload'] for p in fixture['packets']})
    manifest = {'schema_version': 1, 'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
                'source_sha256_start': source_hashes, 'source_sha256_end': _sources(),
                'python': _python_identity(),
                'preparation_argv': list(preparation_argv) if preparation_argv is not None else list(sys.argv),
                'local_generation_truth_wall_seconds': local_seconds,
                'checker': CHECKER, 'request_order': fixture['request_order'],
                'artifact_sha256': {path: sha256_bytes(text.encode('utf-8')) for path, text in artifacts.items()}}
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'payloads').mkdir()
    for path, text in artifacts.items():
        with (output / path).open('x', encoding='utf-8', newline='') as stream:
            stream.write(text)
    with (output / 'manifest.json').open('x', encoding='utf-8', newline='') as stream:
        stream.write(canonical_json(manifest) + '\n')
    return manifest


def validate_fixture_custody(directory, expected_manifest_sha=None):
    directory = Path(directory)
    if expected_manifest_sha is not None and _file_sha(directory / 'manifest.json') != expected_manifest_sha:
        raise ValueError('prepared manifest hash mismatch')
    manifest = json.loads((directory / 'manifest.json').read_text(), object_pairs_hook=_unique_pairs,
                          parse_constant=_reject_constant)
    if manifest['source_sha256_start'] != manifest['source_sha256_end']:
        raise ValueError('preparation source custody mismatch')
    if manifest['source_sha256_start'] != _sources():
        raise ValueError('prepared source hash mismatch')
    if manifest['python'] != _python_identity():
        raise ValueError('prepared Python identity mismatch')
    for relative, digest in manifest['artifact_sha256'].items():
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts or _file_sha(directory / path) != digest:
            raise ValueError('prepared artifact hash mismatch')
    fixture = json.loads((directory / 'fixture.json').read_text(), object_pairs_hook=_unique_pairs,
                         parse_constant=_reject_constant)
    validate_fixture(fixture)
    if fixture['request_order'] != manifest['request_order']:
        raise ValueError('prepared request order mismatch')
    required = {'fixture.json', 'independent-truth.json', 'system-prompt.txt'} | {
        'payloads/' + packet['packet_id'] + '.json' for packet in fixture['packets']}
    if set(manifest['artifact_sha256']) != required:
        raise ValueError('prepared artifact inventory mismatch')
    if (directory / 'system-prompt.txt').read_bytes() != fixture['system_prompt'].encode('utf-8'):
        raise ValueError('prepared system prompt mismatch')
    for packet in fixture['packets']:
        if (directory / 'payloads' / (packet['packet_id'] + '.json')).read_bytes() != packet['payload'].encode('utf-8'):
            raise ValueError('prepared payload mismatch')
    checker = _load_checker()
    checker.verify_fixture(fixture)
    independent = json.loads((directory / 'independent-truth.json').read_text())
    records = {record['item_id']: record for record in independent['items']}
    if len(records) != 24 or len(independent['items']) != 24:
        raise ValueError('independent truth inventory mismatch')
    for item in fixture['items']:
        expected = {'item_id': item['item_id'], **checker.evaluate_program(item['program'])}
        if records.get(item['item_id']) != expected:
            raise ValueError('independent truth record mismatch')
    return fixture, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prepare = sub.add_parser('prepare')
    prepare.add_argument('--output', required=True)
    validate = sub.add_parser('validate')
    validate.add_argument('--prepared', required=True)
    validate.add_argument('--manifest-sha256')
    args = parser.parse_args(argv)
    if args.command == 'prepare':
        manifest = prepare_fixture(args.output)
        print(canonical_json({'prepared': args.output, 'artifact_count': len(manifest['artifact_sha256'])}))
    else:
        fixture, _manifest = validate_fixture_custody(args.prepared, args.manifest_sha256)
        print(canonical_json({'valid': True, 'items': len(fixture['items']),
                              'development_invocations': len(fixture['request_order'])}))


if __name__ == '__main__':
    main()
