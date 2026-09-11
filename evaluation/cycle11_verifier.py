"""Atomic answer/validity responses and descriptive cycle11 measurements."""
import json

from .cycle09_verifier import MapParseError
from .cycle11_certificates import validate_payload

ORDER = ('R0-A', 'R1-B', 'R0-B', 'R1-A')
SYSTEM_PROMPT = '''Determine the final Boolean result of program, and decide whether each
submission's certificate is a valid execution of that program. Each numbered
row must record the complete state after that assignment, including unchanged
variables and their exact types. Check from the initial assignments through
the final Boolean assignment. root_id identifies copies of an artifact; it
does not certify correctness or independent errors. Return exactly one JSON
object with only two keys: "answer", whose value is the program's final Boolean,
and "validity", whose value is an object with exactly the IDs in submission_ids
as keys and Boolean values (true for a valid certificate, false for an invalid
certificate). Return no other text. Evaluate the supplied packet.
'''


def parse_response(text, expected_ids):
    if len(expected_ids) != 4 or len(set(expected_ids)) != 4:
        raise ValueError('expected four distinct submission IDs')
    if type(text) is not str:
        raise MapParseError('not_text')

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise MapParseError('duplicate_key')
            result[key] = value
        return result

    def nonfinite(_value):
        raise MapParseError('nonfinite')

    try:
        result = json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)
    except MapParseError:
        raise
    except (ValueError, UnicodeError, RecursionError) as error:
        raise MapParseError('invalid_json') from error
    if type(result) is not dict or set(result) != {'answer', 'validity'}:
        raise MapParseError('wrong_outer_keys')
    if type(result['answer']) is not bool:
        raise MapParseError('answer_not_boolean')
    validity = result['validity']
    if type(validity) is not dict or set(validity) != set(expected_ids):
        raise MapParseError('wrong_id_set')
    if any(type(value) is not bool for value in validity.values()):
        raise MapParseError('validity_not_boolean')
    return result


def score_decisions(fixture, predictions, failures):
    if set(predictions) & set(failures) or not (set(predictions) | set(failures)) <= set(ORDER):
        raise ValueError('unknown or overlapping observation keys')
    packets = {p['packet_id']: p for p in fixture['packets']}
    programs = {p['program_id']: p for p in fixture['programs']}
    if len(fixture['packets']) != 4 or set(packets) != set(ORDER):
        raise ValueError('expected four frozen packets')
    answers, validities, diagnostics = [], [], {}
    for pid in ORDER:
        packet = packets[pid]
        payload = validate_payload(json.loads(packet['payload']))
        program = programs[packet['program_id']]
        if (payload['program'] != program['program'] or len(packet['private_order']) != 4
                or any(label not in ('V', 'F') for label in packet['private_order'])):
            raise ValueError('packet program or private labels disagree')
        for label, report in zip(packet['private_order'], payload['reports'][:4]):
            if (report['root_id'] != program['report_ids'][label]
                    or report['certificate'] != program['certificates'][label]):
                raise ValueError('packet certificate/root disagrees with private reference')
        observed = predictions.get(pid)
        if pid in predictions:
            observed = parse_response(json.dumps(observed), payload['submission_ids'])
        status = 'accepted' if observed is not None else 'invalid' if pid in failures else 'unsent'
        common = {'packet_id': pid, 'program_id': packet['program_id'],
                  'regime': pid[-1], 'status': status, 'collection_failure': failures.get(pid)}
        truth = program['python_truth']['answer']
        answer_correct = observed['answer'] is truth if observed is not None else None
        answers.append({**common, 'expected_answer': truth,
                        'returned_answer': observed['answer'] if observed is not None else None,
                        'correct': answer_correct})
        current, roots, endpoints = [], {}, set()
        for position, (label, report) in enumerate(zip(packet['private_order'], payload['reports'][:4]), 1):
            expected = program['certificate_checks'][label]['valid']
            returned = observed['validity'][report['report_id']] if observed is not None else None
            current.append({**common, 'submission_id': report['report_id'], 'root_id': report['root_id'],
                            'private_type': label, 'position': position, 'expected_validity': expected,
                            'returned_validity': returned,
                            'correct': returned is expected if observed is not None else None})
            if observed is not None:
                roots.setdefault(report['root_id'], []).append(returned)
                if returned:
                    endpoints.add(report['certificate']['rows'][-1]['state']['result'])
        validities.extend(current)
        diagnostics[pid] = None
        if observed is not None:
            reason = 'no-accepted-support' if not endpoints else 'conflicting-support' if len(endpoints) == 2 else None
            diagnostics[pid] = {
                'answer_correct': answer_correct,
                'all_validities_correct': all(row['correct'] for row in current),
                'accepted_support_endpoints': sorted(endpoints),
                'answer_support_consistent': observed['answer'] in endpoints if len(endpoints) == 1 else None,
                'undefined_reason': reason,
                'root_copy_disagreements': {root: len(set(values)) > 1 for root, values in roots.items()}}
    def counts(rows):
        return {'correct': sum(row['correct'] is True for row in rows),
                'accepted': sum(row['status'] == 'accepted' for row in rows), 'planned': len(rows)}
    totals = {'answers': counts(answers), 'validities': counts(validities)}
    complete = len(predictions) == 4
    return {'schema_version': 1, 'status': 'complete' if complete else 'partial',
            'full_primary': totals if complete else None, 'observed_counts': totals,
            'answers': answers, 'validities': validities, 'diagnostics': diagnostics,
            'invocations': {'attempted': len(predictions) + len(failures), 'accepted': len(predictions),
                            'invalid': len(failures), 'unsent': 4 - len(predictions) - len(failures), 'planned': 4},
            'reference_policy_totals': fixture['policy_totals'],
            'independent_task_count': None,
            'interpretation': 'Four reused-root packets on two program variants; output decisions and consistency do not identify internal strategy or multiagent benefit.'}
