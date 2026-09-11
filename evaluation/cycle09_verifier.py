"""Strict response maps and descriptive scoring for the cycle09 verifier pilot."""
import json


ORDER = ('base', 'repeat')
SYSTEM_PROMPT = '''For each report ID in original_ids, decide whether its certificate is a valid
execution of program. Each numbered row must record the complete state after
that assignment, including unchanged variables and their exact types. Check
from the initial assignments through the final Boolean assignment. Agreement
with the final answer alone is insufficient. root_id identifies copies of an
artifact; it does not certify correctness or independent errors. Return exactly
one JSON object with only the IDs in original_ids as keys and Boolean values:
true means the certificate is valid, false means it is invalid. Return no other
text. Evaluate the supplied packet.
'''


class MapParseError(ValueError):
    pass


def parse_validity(text, expected_ids):
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
    if type(result) is not dict or set(result) != set(expected_ids):
        raise MapParseError('wrong_id_set')
    if any(type(value) is not bool for value in result.values()):
        raise MapParseError('not_boolean')
    return result


def score_decisions(fixture, predictions, failures):
    """Keep every planned decision; invalid/unsent are never wrong judgments."""
    if set(predictions) & set(failures) or not (set(predictions) | set(failures)) <= set(ORDER):
        raise ValueError('unknown or overlapping observation keys')
    packets = {packet['packet_id']: json.loads(packet['payload']) for packet in fixture['packets']}
    if set(packets) != set(ORDER):
        raise ValueError('expected exactly the two fixed packets')
    rows, per_packet = [], {}
    for packet_id in ORDER:
        ids = packets[packet_id]['original_ids']
        if len(ids) != 3 or len(set(ids)) != 3:
            raise ValueError('expected three original IDs')
        expected = fixture['reference_policies'][packet_id]['exact_checker']['decisions']
        if set(expected) != set(ids) or any(type(v) is not bool for v in expected.values()):
            raise ValueError('invalid reference decision map')
        observed = predictions.get(packet_id)
        if observed is not None:
            observed = parse_validity(json.dumps(observed), ids)
        elif packet_id in predictions:
            raise ValueError('null prediction must be a collection failure')
        status = 'accepted' if observed is not None else 'invalid' if packet_id in failures else 'unsent'
        current = [{'packet_id': packet_id, 'original_id': rid, 'expected_validity': expected[rid],
                    'returned_validity': observed[rid] if observed is not None else None,
                    'correct': (observed[rid] is expected[rid]) if observed is not None else None,
                    'status': status, 'collection_failure': failures.get(packet_id)} for rid in ids]
        rows.extend(current)
        per_packet[packet_id] = {'correct': sum(row['correct'] is True for row in current),
                                 'accepted': sum(row['status'] == 'accepted' for row in current),
                                 'planned': 3, 'status': status}
    complete = len(predictions) == 2
    transitions = None
    if complete:
        if packets['base']['original_ids'] != packets['repeat']['original_ids']:
            raise ValueError('original IDs differ across packets')
        by_key = {(row['packet_id'], row['original_id']): row for row in rows}
        transitions = [{'original_id': rid,
                        'base_validity': by_key['base', rid]['returned_validity'],
                        'repeat_validity': by_key['repeat', rid]['returned_validity'],
                        'base_correct': by_key['base', rid]['correct'],
                        'repeat_correct': by_key['repeat', rid]['correct']}
                       for rid in packets['base']['original_ids']]
    totals = {'correct': sum(row['correct'] is True for row in rows),
              'accepted': sum(row['status'] == 'accepted' for row in rows), 'planned': 6}
    references = json.loads(json.dumps(fixture['reference_policies']))
    for pid, packet in packets.items():
        ids = packet['original_ids']
        truth = fixture['reference_policies'][pid]['exact_checker']['decisions']
        originals = {row['report_id']: row for row in packet['reports'][:3]}
        maps = {
            'first_original_only': {rid: rid == ids[0] for rid in ids},
            'final_answer_only': {rid: originals[rid]['certificate']['rows'][-1]['state']['result']
                                  is fixture['python_truth']['answer'] for rid in ids},
        }
        for name, decisions in maps.items():
            references[pid][name] = {'decisions': decisions,
                'correct': sum(decisions[rid] is truth[rid] for rid in ids), 'valid': 3, 'planned': 3}
    return {'schema_version': 1, 'status': 'complete' if complete else 'partial',
            'full_primary': {'counts': totals, 'transitions': transitions} if complete else None,
            'observed_counts': totals, 'per_packet': per_packet, 'decisions': rows,
            'invocations': {'accepted': len(predictions), 'invalid': len(failures),
                            'unsent': 2 - len(predictions) - len(failures), 'planned': 2},
            'reference_policies': references,
            'independent_task_count': None,
            'interpretation': 'Six planned judgments repeat three certificates on one program; no population or mechanism inference.'}
