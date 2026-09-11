"""Finite policy-vector scoring for cycle10, sharing the frozen strict parser."""
import json

from evaluation.cycle09_verifier import MapParseError, SYSTEM_PROMPT, parse_validity


ORDER = ('R0-P1', 'R1-P2', 'R0-P3', 'R1-P1', 'R0-P2', 'R1-P3')


def score_decisions(fixture, predictions, failures):
    if set(predictions) & set(failures) or not (set(predictions) | set(failures)) <= set(ORDER):
        raise ValueError('unknown or overlapping observation keys')
    packets = {row['packet_id']: row for row in fixture['packets']}
    if set(packets) != set(ORDER) or fixture['request_order'] != list(ORDER):
        raise ValueError('expected exactly the six fixed packets and order')
    rows, per_packet = [], {}
    for pid in ORDER:
        meta = packets[pid]
        if (len(meta['private_order']) != 3 or set(meta['private_order']) != {'V', 'I', 'F'}
                or meta['program_id'] != pid.split('-')[0]):
            raise ValueError('invalid private type or program grouping')
        packet = json.loads(meta['payload'])
        ids = packet['original_ids']
        if len(ids) != 3 or len(set(ids)) != 3:
            raise ValueError('expected three original IDs')
        truth = fixture['reference_policies'][pid]['exact_checker']['decisions']
        if set(truth) != set(ids) or any(type(v) is not bool for v in truth.values()):
            raise ValueError('invalid reference decision map')
        observed = predictions.get(pid)
        if observed is not None:
            observed = parse_validity(json.dumps(observed), ids)
        elif pid in predictions:
            raise ValueError('null prediction must be a collection failure')
        status = 'accepted' if observed is not None else 'invalid' if pid in failures else 'unsent'
        current = [{'packet_id': pid, 'program_id': meta['program_id'],
                    'position': position, 'private_type': label, 'original_id': rid,
                    'expected_validity': truth[rid],
                    'returned_validity': observed[rid] if observed is not None else None,
                    'correct': observed[rid] is truth[rid] if observed is not None else None,
                    'status': status, 'collection_failure': failures.get(pid)}
                   for position, (rid, label) in enumerate(zip(ids, meta['private_order']), 1)]
        if len(current) != 3:
            raise ValueError('incomplete private scoring labels')
        rows.extend(current)
        per_packet[pid] = {'correct': sum(row['correct'] is True for row in current),
                          'accepted': 3 if observed is not None else 0,
                          'planned': 3, 'status': status}
    complete = len(predictions) == len(ORDER)
    counts = {'correct': sum(row['correct'] is True for row in rows),
              'accepted': sum(row['status'] == 'accepted' for row in rows), 'planned': 18}
    names = set(fixture['reference_policies'][ORDER[0]])
    if any(set(fixture['reference_policies'][pid]) != names for pid in ORDER):
        raise ValueError('policy inventory differs between packets')
    comparisons = {}
    for name in sorted(names):
        comparable = [row for row in rows if row['status'] == 'accepted']
        mismatches = sum(row['returned_validity'] is not
                         fixture['reference_policies'][row['packet_id']][name]['decisions'][row['original_id']]
                         for row in comparable)
        comparisons[name] = {'mismatches': mismatches, 'compared': len(comparable), 'planned': 18,
                             'matches_full_vector': mismatches == 0 if complete else None}
    by_root = {}
    for row in rows:
        by_root.setdefault(row['original_id'], []).append({k: row[k] for k in
            ('packet_id', 'program_id', 'private_type', 'position', 'returned_validity', 'correct', 'status')})
    for appearances in by_root.values():
        if len(appearances) != 3 or {row['position'] for row in appearances} != {1, 2, 3}:
            raise ValueError('root appearances do not span the three positions')
        if (len({row['private_type'] for row in appearances}) != 1
                or len({row['program_id'] for row in appearances}) != 1):
            raise ValueError('inconsistent private type or program for one root')
    by_type = {label: [{k: row[k] for k in
        ('packet_id', 'program_id', 'position', 'returned_validity', 'correct', 'status')}
        for row in rows if row['private_type'] == label] for label in ('V', 'I', 'F')}
    return {'schema_version': 1, 'status': 'complete' if complete else 'partial',
            'full_primary': {'counts': counts, 'policy_comparisons': comparisons} if complete else None,
            'observed_counts': counts, 'per_packet': per_packet, 'decisions': rows,
            'policy_comparisons': comparisons, 'by_root_position': by_root, 'by_type_endpoint': by_type,
            'invocations': {'accepted': len(predictions), 'invalid': len(failures),
                            'unsent': len(ORDER) - len(predictions) - len(failures), 'planned': len(ORDER)},
            'reference_policy_totals': fixture['policy_totals'],
            'independent_task_count': None,
            'interpretation': '18 judgments on six certificates from two endpoint variants of one arithmetic skeleton; named output policies, not internal mechanisms.'}
