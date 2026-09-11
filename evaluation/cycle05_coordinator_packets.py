"""Frozen cycle05 provider packets and exact diagnostic scoring (stdlib only).

The immutable cycle04 per-world artifact supplies baseline predictions and
generator weights. Provider payloads are serialized separately from evaluator
metadata. This module never calls a provider.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
BASELINE_DIRECTORY = ROOT / 'results/cycle04-2026-09-10/exact'
BASELINE_MANIFEST_SHA256 = '83eae092a1dc2ab2bada9631927063095fe265777bd5fbd10d3d03a5686963c5'
SPECIALIST_VALUES = ('11/20', '17/20')
ARMS = ('padded', 'copied', 'independent')
VIEWS = ('blind', 'aware')
ROLES = ('generalist', 'generalist', 'generalist', 'specialist')
REPORT_IDS = ('r_94c2', 'r_b170', 'r_28e9', 'r_5a63')
PARTITIONS = ((0, None, None, 1), (0, 0, 0, 1), (0, 1, 2, 3))
SHUFFLE_SEED = 42
CODE = 'evaluation/cycle05_coordinator_packets.py'
TESTS = 'evaluation/tests/test_cycle05_coordinator_packets.py'
DESIGN = '_sessions/cycles/2026-09-10-cycle05-coordinator-packet-design.md'
SYSTEM_PROMPT = """You are estimating a probability under the following specified sensor model.
Truth Y is either +1 or -1. Its positive prior is supplied in model_parameters.
There are four primitive sensor readings G1, G2, G3, and S. Conditional on Y,
these four readings are mutually independent. For each possible value of Y,
each Gi equals Y with probability p_generalist and equals -Y otherwise; S
equals Y with probability p_specialist and equals -Y otherwise. All parameters
are known exactly. Fraction strings in the input denote exact rational numbers.

A construction is sampled independently of Y and all primitive readings using
the supplied construction_prior. The ordered report roles are generalist,
generalist, generalist, specialist. The three constructions are:
  padded: [G1, null, null, S]. The nulls are empty padding slots, not readings.
  copied: [G1, G1, G1, S]. The first three slots repeat one primitive reading.
  independent: [G1, G2, G3, S]. Each slot uses a distinct primitive reading.
Report IDs are fixed opaque slot labels and provide no additional evidence.

If parent_partition is present, it is trusted lineage aligned with the report
slots: equal non-null labels mean the same primitive reading was repeated;
distinct labels mean distinct primitive readings. A null slot has a null label.
If parent_partition is absent, only the reports and the supplied model are
observed; marginalize over all constructions compatible with those reports.

Compute the probability that Y is +1 conditional on exactly the supplied
observation and model. Return only a JSON object with the single key
"p_positive" and a finite JSON number between 0 and 1. Do not include prose,
Markdown, additional keys, a quoted probability, or a fraction expression.
"""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {str(key): exact_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [exact_json(item) for item in value]
    return value


class ProbabilityParseError(ValueError):
    """A raw response is unusable; code is stable failure metadata."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def parse_probability(raw):
    """Parse one unmodified JSON response, retaining the exact decimal value."""
    if type(raw) is not str:
        raise ProbabilityParseError('not_text', 'response must be text')

    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ProbabilityParseError('duplicate_key', 'duplicate JSON key')
            result[key] = value
        return result

    def reject_constant(_):
        raise ProbabilityParseError('nonfinite', 'nonfinite JSON number')

    try:
        result = json.loads(raw, parse_int=Fraction, parse_float=Fraction,
                            parse_constant=reject_constant, object_pairs_hook=object_pairs)
    except ProbabilityParseError:
        raise
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ProbabilityParseError('malformed_json', 'response is not one JSON object') from error
    if type(result) is not dict:
        raise ProbabilityParseError('not_object', 'response must be a JSON object')
    if set(result) != {'p_positive'}:
        raise ProbabilityParseError('keys', 'response must have exactly the p_positive key')
    probability = result['p_positive']
    if type(probability) is not Fraction:
        raise ProbabilityParseError('not_number', 'probability must be a JSON number')
    if not 0 <= probability <= 1:
        raise ProbabilityParseError('out_of_range', 'probability must be between zero and one')
    return probability


def model_parameters(p_specialist):
    if type(p_specialist) is not str or p_specialist not in SPECIALIST_VALUES:
        raise ValueError('specialist accuracy must be one of the frozen rational strings')
    return {'truth_prior_positive': '1/2', 'p_generalist': '7/10',
            'p_specialist': p_specialist,
            'construction_prior': {arm: '1/3' for arm in ARMS}}


def validate_payload(payload):
    """Reject added evaluation fields and observations outside the fixed set."""
    if type(payload) is not dict or set(payload) not in (
            {'model_parameters', 'reports'},
            {'model_parameters', 'reports', 'parent_partition'}):
        raise ValueError('provider payload has unexpected fields')
    parameters = payload['model_parameters']
    if type(parameters) is not dict or parameters != model_parameters(parameters.get('p_specialist')):
        raise ValueError('provider parameters do not match the frozen model')
    reports = payload['reports']
    if type(reports) is not list or len(reports) != 4:
        raise ValueError('exactly four report slots are required')
    for index, report in enumerate(reports):
        if (type(report) is not dict or set(report) != {'report_id', 'role', 'value'} or
                report['report_id'] != REPORT_IDS[index] or report['role'] != ROLES[index] or
                (report['value'] is not None and
                 (type(report['value']) is not int or report['value'] not in (-1, 1)))):
            raise ValueError('report slot violates the frozen observation boundary')
    values = [report['value'] for report in reports]
    if (values[0] is None or values[3] is None or
            ((values[1] is None) != (values[2] is None)) or
            any(value != -values[3] for value in values[:3] if value is not None)):
        raise ValueError('reports are not a selected diagnostic observation')
    if 'parent_partition' in payload:
        partition = payload['parent_partition']
        if (type(partition) is not list or len(partition) != 4 or
                any(value is not None and type(value) is not int for value in partition) or
                tuple(partition) not in PARTITIONS or
                any((value is None) != (root is None) for value, root in zip(values, partition))):
            raise ValueError('parent partition violates the frozen observation boundary')
    return payload


def load_baseline(source_directory=BASELINE_DIRECTORY):
    """Verify the anchored cycle04 manifest before reading either exact file."""
    directory = Path(source_directory)
    manifest_bytes = (directory / 'manifest.json').read_bytes()
    if sha256_bytes(manifest_bytes) != BASELINE_MANIFEST_SHA256:
        raise ValueError('immutable cycle04 manifest hash mismatch')
    manifest = json.loads(manifest_bytes)
    if manifest['status'] != 'complete' or manifest['sources_unchanged'] is not True:
        raise ValueError('cycle04 source is not a completed immutable run')
    verified, documents = {}, {}
    for name in ('summary.json', 'per_world.json'):
        data = (directory / name).read_bytes()
        digest = sha256_bytes(data)
        if digest != manifest['output_sha256'][name]:
            raise ValueError('immutable cycle04 output hash mismatch: ' + name)
        verified[name] = digest
        documents[name] = json.loads(data)
    return documents['summary.json'], documents['per_world.json']['rows'], {
        'manifest_sha256': BASELINE_MANIFEST_SHA256, 'output_sha256': verified}


def build_fixture(source_directory=BASELINE_DIRECTORY):
    """Prepare all twenty requests in memory; no durable freeze or provider call."""
    summary, rows, baseline = load_baseline(source_directory)
    if len(rows) != 192 or summary['known_parameters']['p_specialist_values'] != list(SPECIALIST_VALUES):
        raise ValueError('cycle04 evidence has the wrong frozen dimensions')
    groups, paired_groups, totals = {}, {}, defaultdict(Fraction)
    selected_rows = 0
    for index, row in enumerate(rows):
        reports = row['reports']
        specialist = reports[3]['value']
        if not all(report['value'] == -specialist for report in reports[:3] if report['value'] is not None):
            continue
        selected_rows += 1
        p_specialist = row['p_specialist']
        mass = Fraction(row['world_probability']) / 3
        positive_mass = mass * (row['world']['y'] == 1)
        totals[p_specialist] += mass
        ids = {}
        for view in VIEWS:
            payload = {'model_parameters': model_parameters(p_specialist), 'reports': reports}
            if view == 'aware':
                payload['parent_partition'] = row['canonical_partition']
            validate_payload(payload)
            payload_text = canonical_json(payload)
            payload_digest = sha256_bytes(payload_text.encode('utf-8'))
            packet_id = 'p_' + payload_digest[:20]
            ids[view] = packet_id
            reference = row['policies']['optimal_' + view + '_bayes']['p_positive']
            if packet_id not in groups:
                groups[packet_id] = {
                    'packet_id': packet_id, 'view': view, 'p_specialist': p_specialist,
                    'generalist_sign': reports[0]['value'], 'payload': payload_text,
                    'payload_sha256': payload_digest, 'diagnostic_mass': Fraction(0),
                    'truth_positive_mass': Fraction(0), 'reference_p_positive': reference,
                    'source_row_ids': []}
            group = groups[packet_id]
            if group['payload'] != payload_text or group['reference_p_positive'] != reference:
                raise AssertionError('payload identity or immutable baseline mismatch')
            group['diagnostic_mass'] += mass
            group['truth_positive_mass'] += positive_mass
            group['source_row_ids'].append(index)
        pair_key = (ids['aware'], ids['blind'])
        if pair_key not in paired_groups:
            paired_groups[pair_key] = {
                'aware_packet_id': ids['aware'], 'blind_packet_id': ids['blind'],
                'p_specialist': p_specialist, 'arm': row['arm'],
                'generalist_sign': reports[0]['value'], 'diagnostic_mass': Fraction(0),
                'truth_positive_mass': Fraction(0),
                'aware_q': row['policies']['optimal_aware_bayes']['p_positive'],
                'blind_q': row['policies']['optimal_blind_bayes']['p_positive']}
        paired_groups[pair_key]['diagnostic_mass'] += mass
        paired_groups[pair_key]['truth_positive_mass'] += positive_mass
    packets = sorted(groups.values(), key=lambda packet: packet['packet_id'])
    for packet in packets:
        packet['diagnostic_weight'] = packet['diagnostic_mass'] / totals[packet['p_specialist']]
        if packet['truth_positive_mass'] / packet['diagnostic_mass'] != Fraction(packet['reference_p_positive']):
            raise AssertionError('generator conditioning disagrees with immutable baseline')
    pairs = sorted(paired_groups.values(), key=lambda pair: pair['aware_packet_id'])
    for pair in pairs:
        pair['diagnostic_weight'] = pair['diagnostic_mass'] / totals[pair['p_specialist']]
    if Counter(packet['view'] for packet in packets) != {'blind': 8, 'aware': 12} or len(pairs) != 12:
        raise AssertionError('diagnostic observation counts disagree with design')
    request_order = [packet['packet_id'] for packet in packets]
    random.Random(SHUFFLE_SEED).shuffle(request_order)
    return exact_json({
        'schema_version': 1, 'baseline': baseline, 'system_prompt': SYSTEM_PROMPT,
        'system_prompt_sha256': sha256_bytes(SYSTEM_PROMPT.encode('utf-8')),
        'shuffle_seed': SHUFFLE_SEED, 'request_order': request_order,
        'packets': packets, 'pairs': pairs, 'diagnostic_world_arm_rows': selected_rows,
        'diagnostic_mass_by_p_specialist': dict(totals)})


def validate_fixture(fixture):
    """Check every reference and provider byte against fresh immutable inputs."""
    expected = build_fixture()
    if fixture != expected:
        raise ValueError('fixture differs from the frozen canonical preparation')
    return fixture


def decision(probability):
    return 'tie' if probability == Fraction(1, 2) else ('positive' if probability > Fraction(1, 2) else 'negative')


def expected_brier(probability, mass, positive_mass):
    return positive_mass * (1 - probability) ** 2 + (mass - positive_mass) * probability ** 2


def _view_summary(packets, predictions):
    total = sum((Fraction(packet['diagnostic_mass']) for packet in packets), Fraction(0))
    valid = [packet for packet in packets if packet['packet_id'] in predictions]
    mass = sum((Fraction(packet['diagnostic_mass']) for packet in valid), Fraction(0))
    regret = error = brier = ideal = Fraction(0)
    for packet in valid:
        p, q = predictions[packet['packet_id']], Fraction(packet['reference_p_positive'])
        weight, positive = Fraction(packet['diagnostic_mass']), Fraction(packet['truth_positive_mass'])
        regret += weight * (p - q) ** 2
        error += weight * abs(p - q)
        brier += expected_brier(p, weight, positive)
        ideal += expected_brier(q, weight, positive)
    return {'packet_count': len(packets), 'valid_packet_count': len(valid),
            'full_diagnostic_mass': total, 'valid_diagnostic_mass': mass,
            'diagnostic_mass_coverage': mass / total,
            'conditional_excess_brier': regret / mass if mass else None,
            'conditional_absolute_posterior_error': error / mass if mass else None,
            'expected_brier': brier / mass if mass else None,
            'ideal_expected_brier': ideal / mass if mass else None}


def _paired_summary(pairs, predictions):
    total = sum((Fraction(pair['diagnostic_mass']) for pair in pairs), Fraction(0))
    valid = [pair for pair in pairs if pair['aware_packet_id'] in predictions and pair['blind_packet_id'] in predictions]
    mass = sum((Fraction(pair['diagnostic_mass']) for pair in valid), Fraction(0))
    actual = ideal = squared_gap = regret_delta = cross = Fraction(0)
    aware_brier = blind_brier = Fraction(0)
    for pair in valid:
        weight, positive = Fraction(pair['diagnostic_mass']), Fraction(pair['truth_positive_mass'])
        pa, pb = predictions[pair['aware_packet_id']], predictions[pair['blind_packet_id']]
        qa, qb = Fraction(pair['aware_q']), Fraction(pair['blind_q'])
        aware_brier += expected_brier(pa, weight, positive)
        blind_brier += expected_brier(pb, weight, positive)
        actual += expected_brier(pa, weight, positive) - expected_brier(pb, weight, positive)
        ideal += expected_brier(qa, weight, positive) - expected_brier(qb, weight, positive)
        squared_gap += weight * (qa - qb) ** 2
        regret_delta += weight * ((pa - qa) ** 2 - (pb - qb) ** 2)
        cross += 2 * ((pa - qa) * (weight * qa - positive) - (pb - qb) * (weight * qb - positive))
    if actual != ideal + regret_delta + cross or ideal != -squared_gap:
        raise AssertionError('paired expected-Brier decomposition failed')
    if len(valid) == len(pairs) and cross:
        raise AssertionError('full-pair posterior cross term must vanish')
    divide = lambda value: value / mass if mass else None
    return {'pair_count': len(pairs), 'valid_pair_count': len(valid),
            'full_diagnostic_mass': total, 'valid_diagnostic_mass': mass,
            'diagnostic_mass_coverage': mass / total,
            'aware_expected_brier': divide(aware_brier), 'blind_expected_brier': divide(blind_brier),
            'aware_minus_blind_expected_brier': divide(actual),
            'ideal_information_gap': divide(ideal), 'posterior_squared_gap': divide(squared_gap),
            'original_posterior_regret_delta': divide(regret_delta),
            'selection_cross_term': divide(cross),
            'decomposition': 'actual gap = ideal information gap + original posterior regret delta + selection cross term'}


def _contrasts(fixture, predictions):
    packets = fixture['packets']
    by_id = {packet['packet_id']: packet for packet in packets}
    shape_ids = {(packet['view'], packet['p_specialist'], packet['generalist_sign'],
                  tuple(report['value'] for report in json.loads(packet['payload'])['reports']),
                  tuple(json.loads(packet['payload']).get('parent_partition', []))): packet['packet_id']
                 for packet in packets}
    symmetry, copy_changes, lineage = [], [], []
    for key, packet_id in shape_ids.items():
        view, specialist, sign, values, partition = key
        if sign != 1:
            continue
        opposite = shape_ids[(view, specialist, -1, tuple(-value if value is not None else None for value in values), partition)]
        p, other = predictions.get(packet_id), predictions.get(opposite)
        symmetry.append({'positive_generalist_packet_id': packet_id, 'negative_generalist_packet_id': opposite,
                         'probability_sum_minus_one': p + other - 1 if p is not None and other is not None else None})
    for specialist in SPECIALIST_VALUES:
        for sign in (-1, 1):
            relevant = [pair for pair in fixture['pairs'] if pair['p_specialist'] == specialist and pair['generalist_sign'] == sign]
            by_arm = {pair['arm']: pair for pair in relevant}
            for view in VIEWS:
                padded = by_arm['padded'][view + '_packet_id']
                copied = by_arm['copied'][view + '_packet_id']
                p, c = predictions.get(padded), predictions.get(copied)
                copy_changes.append({'view': view, 'p_specialist': specialist, 'generalist_sign': sign,
                                     'padded_packet_id': padded, 'copied_packet_id': copied,
                                     'copied_minus_padded': c - p if p is not None and c is not None else None,
                                     'reference_copied_minus_padded': Fraction(by_id[copied]['reference_p_positive']) - Fraction(by_id[padded]['reference_p_positive'])})
            copied, independent = by_arm['copied']['aware_packet_id'], by_arm['independent']['aware_packet_id']
            c, i = predictions.get(copied), predictions.get(independent)
            lineage.append({'p_specialist': specialist, 'generalist_sign': sign,
                            'copied_packet_id': copied, 'independent_packet_id': independent,
                            'independent_minus_copied': i - c if c is not None and i is not None else None,
                            'reference_independent_minus_copied': Fraction(by_id[independent]['reference_p_positive']) - Fraction(by_id[copied]['reference_p_positive'])})
    return {'sign_symmetry': symmetry, 'padded_to_copied': copy_changes, 'aware_lineage_contrast': lineage}


def score_predictions(fixture, predictions, failures=None):
    """Score exact probabilities; absent/invalid responses are never imputed.

    Programmatic predictions must be Fraction values. Actual native response
    text must first pass parse_probability; rational oracle tests need no lossy
    decimal rendering. Every partial summary declares its conditional mass.
    """
    validate_fixture(fixture)
    if type(predictions) is not dict or any(type(p) is not Fraction or not 0 <= p <= 1 for p in predictions.values()):
        raise ValueError('predictions must map packet IDs to exact Fraction probabilities')
    ids = set(fixture['request_order'])
    failures = {} if failures is None else failures
    if type(failures) is not dict or any(type(code) is not str or not code for code in failures.values()):
        raise ValueError('failures must map packet IDs to nonempty failure codes')
    if (set(predictions) | set(failures)) - ids or set(predictions) & set(failures):
        raise ValueError('unknown packet IDs or simultaneous prediction and failure')
    complete = len(predictions) == 20
    rows = []
    for packet_id in fixture['request_order']:
        packet = next(item for item in fixture['packets'] if item['packet_id'] == packet_id)
        q, p = Fraction(packet['reference_p_positive']), predictions.get(packet_id)
        rows.append({'packet_id': packet_id, 'view': packet['view'], 'p_specialist': packet['p_specialist'],
                     'status': 'valid' if p is not None else ('invalid' if packet_id in failures else 'missing'),
                     'failure_type': failures.get(packet_id), 'p_positive': p,
                     'reference_p_positive': q, 'absolute_posterior_error': abs(p - q) if p is not None else None,
                     'excess_brier': (p - q) ** 2 if p is not None else None,
                     'sign_decision': decision(p) if p is not None else None,
                     'reference_sign_decision': decision(q),
                     'sign_matches_reference': decision(p) == decision(q) if p is not None else None})
    view_summaries = {specialist: {view: _view_summary(
        [packet for packet in fixture['packets'] if packet['p_specialist'] == specialist and packet['view'] == view], predictions)
        for view in VIEWS} for specialist in SPECIALIST_VALUES}
    paired = {specialist: _paired_summary([pair for pair in fixture['pairs'] if pair['p_specialist'] == specialist], predictions)
              for specialist in SPECIALIST_VALUES}
    return exact_json({
        'schema_version': 1, 'status': 'complete' if complete else 'incomplete',
        'coverage': {'planned': 20, 'valid': len(predictions), 'invalid': len(failures),
                     'missing': 20 - len(predictions) - len(failures), 'failure_types': dict(Counter(failures.values()))},
        'primary': view_summaries if complete else None,
        'valid_subset_diagnostic': None if complete else {'label': 'descriptive valid-subset summaries; changed denominators', 'by_p_specialist': view_summaries},
        'paired': {'label': 'full diagnostic pairs' if complete else 'descriptive same-case valid-pair subset; changed denominators', 'by_p_specialist': paired},
        'packets': rows, 'contrasts': _contrasts(fixture, predictions)})


def score_responses(fixture, responses, failures=None):
    """Extract strict predictions while retaining explicit non-response failures."""
    if type(responses) is not dict:
        raise ValueError('responses must map packet IDs to raw response strings')
    predictions, failures = {}, dict(failures or {})
    if set(responses) & set(failures):
        raise ValueError('a response and external failure cannot share a packet ID')
    for packet_id, raw in responses.items():
        try:
            predictions[packet_id] = parse_probability(raw)
        except ProbabilityParseError as error:
            failures[packet_id] = error.code
    return score_predictions(fixture, predictions, failures)


def _source_hashes(protocol_path):
    paths = [ROOT / CODE, ROOT / TESTS, ROOT / DESIGN, protocol_path]
    paths += [BASELINE_DIRECTORY / name for name in ('manifest.json', 'summary.json', 'per_world.json')]
    return {str(path.resolve().relative_to(ROOT)): sha256_bytes(path.read_bytes()) for path in paths}


def _write_json(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write('\n')


def _fresh_results_directory(path):
    path = Path(path).resolve()
    results = (ROOT / 'results').resolve()
    if path == results:
        raise ValueError('output must be a fresh child directory of repository results/')
    try:
        path.relative_to(results)
    except ValueError as error:
        raise ValueError('output must be a fresh child directory of repository results/') from error
    path.mkdir(parents=True, exist_ok=False)
    return path


def prepare_fixture(output, protocol_path, protocol_sha256):
    """Freeze provider bytes and exact references after the contract is fixed.

    The protocol hash is supplied explicitly by the coordinator. No provider is
    invoked, and all files use exclusive creation. A failed prepare is retained
    as invalid evidence; it is not overwritten or silently retried.
    """
    protocol_path = Path(protocol_path).resolve()
    source_start = _source_hashes(protocol_path)
    protocol_name = str(protocol_path.relative_to(ROOT))
    if source_start[protocol_name] != protocol_sha256:
        raise ValueError('frozen execution protocol hash mismatch')
    fixture = build_fixture()
    output = _fresh_results_directory(output)
    manifest = {
        'schema_version': 1, 'status': 'started',
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'protocol': protocol_name, 'protocol_sha256': protocol_sha256,
        'source_sha256_start': source_start,
        'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'python_version': sys.version, 'shuffle_seed': SHUFFLE_SEED,
        'system_prompt_sha256': fixture['system_prompt_sha256'],
        'provider_payload_sha256': {packet['packet_id']: packet['payload_sha256'] for packet in fixture['packets']},
        'request_order_sha256': sha256_bytes(canonical_json(fixture['request_order']).encode('utf-8'))}
    _write_json(output / 'manifest-start.json', manifest)
    try:
        _write_json(output / 'fixture.json', fixture)
        source_end = _source_hashes(protocol_path)
        manifest['source_sha256_end'] = source_end
        manifest['sources_unchanged'] = source_end == source_start
        if source_end != source_start:
            raise ValueError('a frozen source changed during packet preparation')
        manifest['status'] = 'complete'
        manifest['finished_utc'] = datetime.now(timezone.utc).isoformat()
        manifest['output_sha256'] = {name: sha256_bytes((output / name).read_bytes())
                                     for name in ('fixture.json', 'manifest-start.json')}
        _write_json(output / 'manifest.json', manifest)
    except Exception as error:
        manifest.update({'status': 'invalid', 'finished_utc': datetime.now(timezone.utc).isoformat(),
                         'error': '{}: {}'.format(type(error).__name__, error)})
        _write_json(output / 'manifest-invalid.json', manifest)
        raise
    return fixture, manifest


def validate_fixture_custody(prepared_directory, expected_manifest_sha256=None):
    """Verify frozen artifacts, current source bytes, and canonical references.

    Callers can pin the manifest hash from a separate execution receipt; source
    and output hashes are checked even when no external hash is supplied.
    Returns (fixture, manifest), with no writes or provider operations.
    """
    directory = Path(prepared_directory)
    manifest_bytes = (directory / 'manifest.json').read_bytes()
    if expected_manifest_sha256 is not None and sha256_bytes(manifest_bytes) != expected_manifest_sha256:
        raise ValueError('prepared manifest hash mismatch')
    manifest = json.loads(manifest_bytes)
    if manifest.get('schema_version') != 1 or manifest.get('status') != 'complete' or manifest.get('sources_unchanged') is not True:
        raise ValueError('packet preparation did not complete with unchanged sources')
    protocol = (ROOT / manifest['protocol']).resolve()
    source_hashes = _source_hashes(protocol)
    if manifest['source_sha256_start'] != source_hashes or manifest['source_sha256_end'] != source_hashes:
        raise ValueError('prepared source custody mismatch')
    if manifest['protocol_sha256'] != sha256_bytes(protocol.read_bytes()):
        raise ValueError('prepared protocol hash mismatch')
    if set(manifest['output_sha256']) != {'fixture.json', 'manifest-start.json'}:
        raise ValueError('prepared output manifest has unexpected files')
    for name, digest in manifest['output_sha256'].items():
        if sha256_bytes((directory / name).read_bytes()) != digest:
            raise ValueError('prepared output hash mismatch: ' + name)
    start = json.loads((directory / 'manifest-start.json').read_bytes())
    if start.get('status') != 'started' or any(manifest.get(key) != value for key, value in start.items() if key != 'status'):
        raise ValueError('preparation start/final manifests disagree')
    fixture = json.loads((directory / 'fixture.json').read_bytes())
    validate_fixture(fixture)
    if (manifest['system_prompt_sha256'] != fixture['system_prompt_sha256'] or
            manifest['provider_payload_sha256'] != {p['packet_id']: p['payload_sha256'] for p in fixture['packets']} or
            manifest['shuffle_seed'] != SHUFFLE_SEED or
            manifest['request_order_sha256'] != sha256_bytes(canonical_json(fixture['request_order']).encode('utf-8'))):
        raise ValueError('prepared provider bytes or order hash mismatch')
    return fixture, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', type=Path, required=True, help='Fresh child directory of results/')
    parser.add_argument('--protocol', type=Path, required=True, help='Frozen execution protocol inside this repository')
    parser.add_argument('--protocol-sha256', required=True, help='Previously frozen exact execution protocol hash')
    args = parser.parse_args(argv)
    try:
        fixture, _ = prepare_fixture(args.prepare, args.protocol, args.protocol_sha256)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    print('Prepared {} immutable requests in {}'.format(len(fixture['request_order']), args.prepare))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
