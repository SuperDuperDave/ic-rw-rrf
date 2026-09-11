"""Frozen cycle06 noisy-lineage packets and exact scoring (stdlib only).

References integrate the anchored cycle04 world rows through a binary channel.
Only separately serialized observation payloads belong in provider requests.
This module never calls a provider or reads model outcomes during preparation.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction
import json
from pathlib import Path
import random
import subprocess
import sys

if __package__:
    from . import cycle05_coordinator_packets as frozen
else:
    import cycle05_coordinator_packets as frozen


ROOT = frozen.ROOT
BASELINE_DIRECTORY = frozen.BASELINE_DIRECTORY
SPECIALIST_VALUES = frozen.SPECIALIST_VALUES
REPORT_IDS = frozen.REPORT_IDS
ROLES = frozen.ROLES
HINTS = ('copied', 'independent')
REFERENCES = ('noisy_bayes', 'blind', 'naive_hint_trust')
HINT_FLIP_PROBABILITY = Fraction(1, 4)
SHUFFLE_SEED = 42
CODE = 'evaluation/cycle06_noisy_lineage.py'
TESTS = 'evaluation/tests/test_cycle06_noisy_lineage.py'
DESIGN = '_sessions/cycles/2026-09-10-cycle06-known-noise-design.md'
canonical_json = frozen.canonical_json
exact_json = frozen.exact_json
sha256_bytes = frozen.sha256_bytes
parse_probability = frozen.parse_probability
ProbabilityParseError = frozen.ProbabilityParseError
expected_brier = frozen.expected_brier
decision = frozen.decision

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

The supplied reports are non-null, so padded construction is ruled out. Before
conditioning on their signs, copied and independent have equal prior probability.
The field noisy_lineage_hint is a noisy observation of this binary construction,
not verified lineage. Conditional on either true non-null construction A, the
hint equals A with probability 1 - hint_flip_probability, and equals the other
non-null construction with probability hint_flip_probability. Conditional on A,
this hint is independent of Y and all primitive readings. The actual construction
and primitive parent identities are not supplied. Condition on both the report
values and the noisy hint using the specified model.

Compute the probability that Y is +1 conditional on exactly the supplied
observation and model. Return only a JSON object with the single key
"p_positive" and a finite JSON number between 0 and 1. Do not include prose,
Markdown, additional keys, a quoted probability, or a fraction expression.
"""


def model_parameters(p_specialist):
    return dict(frozen.model_parameters(p_specialist),
                hint_flip_probability=str(HINT_FLIP_PROBABILITY))


def validate_payload(payload):
    """Whitelist the complete provider observation; reject evaluator metadata."""
    if type(payload) is not dict or set(payload) != {
            'model_parameters', 'reports', 'noisy_lineage_hint'}:
        raise ValueError('provider payload has unexpected fields')
    parameters = payload['model_parameters']
    if type(parameters) is not dict or parameters != model_parameters(parameters.get('p_specialist')):
        raise ValueError('provider parameters do not match the frozen model')
    if type(payload['noisy_lineage_hint']) is not str or payload['noisy_lineage_hint'] not in HINTS:
        raise ValueError('noisy lineage hint must be copied or independent')
    # Reuse the frozen report/ID/role/type boundary after removing only the
    # disclosed channel parameter. Trusted parent_partition is never forwarded.
    frozen.validate_payload({
        'model_parameters': frozen.model_parameters(parameters['p_specialist']),
        'reports': payload['reports']})
    if any(report['value'] is None for report in payload['reports']):
        raise ValueError('cycle06 requests must have non-null reports')
    return payload


def reference_cells(rows, flip_probability=HINT_FLIP_PROBABILITY):
    """Integrate raw world masses through the channel, including boundary checks.

    Retain the original unconditional 1/3 construction mass. Conditioning this
    on non-null reports gives the disclosed 1/2 copied/independent prior.
    Boundary error rates are analytical only, never additional provider inputs.
    """
    if type(flip_probability) is not Fraction or not 0 <= flip_probability <= Fraction(1, 2):
        raise ValueError('channel error must be an exact Fraction between zero and one half')
    cells = {}
    selected_rows = 0
    for index, row in enumerate(rows):
        if row['arm'] not in HINTS:
            continue
        reports = row['reports']
        if not all(report['value'] == -reports[3]['value'] for report in reports[:3]):
            continue
        selected_rows += 1
        for hint in HINTS:
            key = (row['p_specialist'], reports[0]['value'], hint)
            if key not in cells:
                cells[key] = {'diagnostic_mass': Fraction(0),
                              'truth_positive_mass': Fraction(0),
                              'source_row_weights': [], 'reports': reports,
                              'blind': row['policies']['optimal_blind_bayes']['p_positive']}
            cell = cells[key]
            if cell['blind'] != row['policies']['optimal_blind_bayes']['p_positive']:
                raise AssertionError('same reports disagree on immutable blind reference')
            if row['arm'] == hint:
                naive = row['policies']['optimal_aware_bayes']['p_positive']
                if 'naive_hint_trust' in cell and cell['naive_hint_trust'] != naive:
                    raise AssertionError('same lineage disagrees on immutable aware reference')
                cell['naive_hint_trust'] = naive
            channel = 1 - flip_probability if row['arm'] == hint else flip_probability
            mass = Fraction(row['world_probability']) / 3 * channel
            cell['diagnostic_mass'] += mass
            cell['truth_positive_mass'] += mass * (row['world']['y'] == 1)
            cell['source_row_weights'].append({'source_row_id': index, 'augmented_mass': mass})
    for cell in cells.values():
        cell['noisy_bayes'] = cell['truth_positive_mass'] / cell['diagnostic_mass']
    return cells, selected_rows


def build_fixture(source_directory=BASELINE_DIRECTORY):
    """Build exactly eight inputs in memory; no durable preparation or calls."""
    summary, rows, baseline = frozen.load_baseline(source_directory)
    if len(rows) != 192 or summary['known_parameters']['p_specialist_values'] != list(SPECIALIST_VALUES):
        raise ValueError('cycle04 evidence has the wrong frozen dimensions')
    cells, selected_rows = reference_cells(rows)
    packets, totals = [], defaultdict(Fraction)
    for (specialist, sign, hint), cell in cells.items():
        payload = {'model_parameters': model_parameters(specialist),
                   'reports': cell['reports'], 'noisy_lineage_hint': hint}
        validate_payload(payload)
        payload_text = canonical_json(payload)
        digest = sha256_bytes(payload_text.encode('utf-8'))
        packets.append({
            'packet_id': 'p_' + digest[:20], 'p_specialist': specialist,
            'generalist_sign': sign, 'noisy_lineage_hint': hint,
            'payload': payload_text, 'payload_sha256': digest,
            'diagnostic_mass': cell['diagnostic_mass'],
            'truth_positive_mass': cell['truth_positive_mass'],
            'reference_p_positive': cell['noisy_bayes'],
            'references': {name: Fraction(cell[name]) for name in REFERENCES},
            'source_row_weights': cell['source_row_weights']})
        totals[specialist] += cell['diagnostic_mass']
    if len(packets) != 8 or len({packet['payload'] for packet in packets}) != 8 or selected_rows != 40:
        raise AssertionError('diagnostic observation counts disagree with design')
    packets.sort(key=lambda packet: packet['packet_id'])
    for packet in packets:
        packet['diagnostic_weight'] = packet['diagnostic_mass'] / totals[packet['p_specialist']]
    request_order = [packet['packet_id'] for packet in packets]
    random.Random(SHUFFLE_SEED).shuffle(request_order)
    return exact_json({
        'schema_version': 1, 'baseline': baseline, 'system_prompt': SYSTEM_PROMPT,
        'system_prompt_sha256': sha256_bytes(SYSTEM_PROMPT.encode('utf-8')),
        'shuffle_seed': SHUFFLE_SEED, 'request_order': request_order,
        'hint_flip_probability': HINT_FLIP_PROBABILITY,
        'packets': packets, 'diagnostic_world_arm_rows': selected_rows,
        'diagnostic_mass_by_p_specialist': dict(totals)})


def validate_fixture(fixture):
    if fixture != build_fixture():
        raise ValueError('fixture differs from the frozen canonical preparation')
    return fixture


def _summary(packets, predictions):
    total = sum((Fraction(packet['diagnostic_mass']) for packet in packets), Fraction(0))
    valid = [packet for packet in packets if packet['packet_id'] in predictions]
    mass = sum((Fraction(packet['diagnostic_mass']) for packet in valid), Fraction(0))
    divide = lambda value: value / mass if mass else None
    brier = regret = absolute_error = Fraction(0)
    comparisons = {name: defaultdict(Fraction) for name in REFERENCES}
    for packet in valid:
        p, q = predictions[packet['packet_id']], Fraction(packet['reference_p_positive'])
        weight, positive = Fraction(packet['diagnostic_mass']), Fraction(packet['truth_positive_mass'])
        brier += expected_brier(p, weight, positive)
        regret += weight * (p - q) ** 2
        absolute_error += weight * abs(p - q)
        for name, values in comparisons.items():
            reference = Fraction(packet['references'][name])
            values['expected_brier'] += expected_brier(reference, weight, positive)
            values['conditional_excess_brier'] += weight * (reference - q) ** 2
            values['model_squared_distance'] += weight * (p - reference) ** 2
            values['model_absolute_distance'] += weight * abs(p - reference)
    ideal = comparisons['noisy_bayes'].get('expected_brier', Fraction(0))
    if brier - ideal != regret:
        raise AssertionError('direct expected Brier does not equal Bayes risk plus regret')
    for values in comparisons.values():
        if values.get('expected_brier', Fraction(0)) - ideal != values.get('conditional_excess_brier', Fraction(0)):
            raise AssertionError('comparator expected Brier decomposition failed')
    return {
        'packet_count': len(packets), 'valid_packet_count': len(valid),
        'full_diagnostic_mass': total, 'valid_diagnostic_mass': mass,
        'diagnostic_mass_coverage': mass / total,
        'conditional_excess_brier': divide(regret),
        'conditional_absolute_posterior_error': divide(absolute_error),
        'expected_brier': divide(brier), 'ideal_expected_brier': divide(ideal),
        'comparators': {name: {
            **{key: divide(values.get(key, Fraction(0))) for key in (
                'expected_brier', 'conditional_excess_brier',
                'model_squared_distance', 'model_absolute_distance')},
            'model_minus_expected_brier': divide(brier - values.get('expected_brier', Fraction(0)))}
            for name, values in comparisons.items()}}


def _contrasts(fixture, predictions):
    cells = {(packet['p_specialist'], packet['generalist_sign'], packet['noisy_lineage_hint']): packet
             for packet in fixture['packets']}
    symmetry, hints = [], []
    for specialist in SPECIALIST_VALUES:
        for hint in HINTS:
            positive, negative = cells[specialist, 1, hint], cells[specialist, -1, hint]
            p, n = predictions.get(positive['packet_id']), predictions.get(negative['packet_id'])
            symmetry.append({
                'p_specialist': specialist, 'noisy_lineage_hint': hint,
                'positive_generalist_packet_id': positive['packet_id'],
                'negative_generalist_packet_id': negative['packet_id'],
                'probability_sum_minus_one': p + n - 1 if p is not None and n is not None else None,
                'reference_sum_minus_one': {name: Fraction(positive['references'][name]) +
                                          Fraction(negative['references'][name]) - 1 for name in REFERENCES}})
        for sign in (-1, 1):
            copied, independent = cells[specialist, sign, 'copied'], cells[specialist, sign, 'independent']
            c, i = predictions.get(copied['packet_id']), predictions.get(independent['packet_id'])
            hints.append({
                'p_specialist': specialist, 'generalist_sign': sign,
                'hint_copied_packet_id': copied['packet_id'], 'hint_independent_packet_id': independent['packet_id'],
                'hint_independent_minus_copied': i - c if c is not None and i is not None else None,
                'reference_hint_independent_minus_copied': {
                    name: Fraction(independent['references'][name]) - Fraction(copied['references'][name])
                    for name in REFERENCES}})
    return {'sign_symmetry': symmetry, 'hint_contrast': hints}


def score_predictions(fixture, predictions, failures=None):
    """Score exact probabilities without repair, imputation, or repeat-sample CIs."""
    validate_fixture(fixture)
    if type(predictions) is not dict or any(type(p) is not Fraction or not 0 <= p <= 1 for p in predictions.values()):
        raise ValueError('predictions must map packet IDs to exact Fraction probabilities')
    failures = {} if failures is None else failures
    if type(failures) is not dict or any(type(code) is not str or not code for code in failures.values()):
        raise ValueError('failures must map packet IDs to nonempty failure codes')
    ids = set(fixture['request_order'])
    if (set(predictions) | set(failures)) - ids or set(predictions) & set(failures):
        raise ValueError('unknown packet IDs or simultaneous prediction and failure')
    complete = len(predictions) == len(ids)
    by_id = {packet['packet_id']: packet for packet in fixture['packets']}
    rows = []
    for packet_id in fixture['request_order']:
        packet, p = by_id[packet_id], predictions.get(packet_id)
        q = Fraction(packet['reference_p_positive'])
        rows.append({
            'packet_id': packet_id, 'p_specialist': packet['p_specialist'],
            'generalist_sign': packet['generalist_sign'], 'noisy_lineage_hint': packet['noisy_lineage_hint'],
            'status': 'valid' if p is not None else ('invalid' if packet_id in failures else 'missing'),
            'failure_type': failures.get(packet_id), 'p_positive': p,
            'reference_p_positive': q, 'absolute_posterior_error': abs(p - q) if p is not None else None,
            'excess_brier': (p - q) ** 2 if p is not None else None,
            'sign_decision': decision(p) if p is not None else None,
            'reference_sign_decision': decision(q),
            'sign_matches_reference': decision(p) == decision(q) if p is not None else None,
            'comparators': {name: {
                'p_positive': Fraction(reference), 'sign_decision': decision(Fraction(reference)),
                'model_minus_reference': p - Fraction(reference) if p is not None else None}
                for name, reference in packet['references'].items()}})
    summaries = {specialist: _summary(
        [packet for packet in fixture['packets'] if packet['p_specialist'] == specialist], predictions)
        for specialist in SPECIALIST_VALUES}
    return exact_json({
        'schema_version': 1, 'status': 'complete' if complete else 'incomplete',
        'coverage': {'planned': len(ids), 'valid': len(predictions), 'invalid': len(failures),
                     'missing': len(ids) - len(predictions) - len(failures),
                     'failure_types': dict(Counter(failures.values()))},
        'primary': summaries if complete else None,
        'valid_subset_diagnostic': None if complete else {
            'label': 'descriptive valid-subset summaries; changed denominators', 'by_p_specialist': summaries},
        'packets': rows, 'contrasts': _contrasts(fixture, predictions)})


def score_responses(fixture, responses, failures=None):
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
    paths = [ROOT / name for name in (CODE, TESTS, DESIGN, frozen.CODE, frozen.TESTS)]
    paths += [Path(protocol_path)]
    paths += [BASELINE_DIRECTORY / name for name in ('manifest.json', 'summary.json', 'per_world.json')]
    return {str(path.resolve().relative_to(ROOT)): sha256_bytes(path.read_bytes()) for path in paths}


def prepare_fixture(output, protocol_path, protocol_sha256):
    """Exclusively freeze packets only against the coordinator's protocol hash."""
    protocol_path = Path(protocol_path).resolve()
    source_start = _source_hashes(protocol_path)
    protocol_name = str(protocol_path.relative_to(ROOT))
    if source_start[protocol_name] != protocol_sha256:
        raise ValueError('frozen execution protocol hash mismatch')
    fixture = build_fixture()
    output = frozen._fresh_results_directory(output)
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
    frozen._write_json(output / 'manifest-start.json', manifest)
    try:
        frozen._write_json(output / 'fixture.json', fixture)
        source_end = _source_hashes(protocol_path)
        manifest.update(source_sha256_end=source_end, sources_unchanged=source_end == source_start)
        if source_end != source_start:
            raise ValueError('a frozen source changed during packet preparation')
        manifest.update(status='complete', finished_utc=datetime.now(timezone.utc).isoformat())
        manifest['output_sha256'] = {name: sha256_bytes((output / name).read_bytes())
                                    for name in ('fixture.json', 'manifest-start.json')}
        frozen._write_json(output / 'manifest.json', manifest)
    except Exception as error:
        manifest.update(status='invalid', finished_utc=datetime.now(timezone.utc).isoformat(),
                        error='{}: {}'.format(type(error).__name__, error))
        frozen._write_json(output / 'manifest-invalid.json', manifest)
        raise
    return fixture, manifest


def validate_fixture_custody(prepared_directory, expected_manifest_sha256=None):
    """Verify preparation, imported frozen code, sources, and canonical bytes."""
    directory = Path(prepared_directory)
    manifest_bytes = (directory / 'manifest.json').read_bytes()
    if expected_manifest_sha256 is not None and sha256_bytes(manifest_bytes) != expected_manifest_sha256:
        raise ValueError('prepared manifest hash mismatch')
    manifest = json.loads(manifest_bytes)
    if manifest.get('schema_version') != 1 or manifest.get('status') != 'complete' or manifest.get('sources_unchanged') is not True:
        raise ValueError('packet preparation did not complete with unchanged sources')
    protocol = (ROOT / manifest['protocol']).resolve()
    sources = _source_hashes(protocol)
    if manifest['source_sha256_start'] != sources or manifest['source_sha256_end'] != sources:
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
    fixture = validate_fixture(json.loads((directory / 'fixture.json').read_bytes()))
    if (manifest['system_prompt_sha256'] != fixture['system_prompt_sha256'] or
            manifest['provider_payload_sha256'] != {p['packet_id']: p['payload_sha256'] for p in fixture['packets']} or
            manifest['shuffle_seed'] != SHUFFLE_SEED or
            manifest['request_order_sha256'] != sha256_bytes(canonical_json(fixture['request_order']).encode('utf-8'))):
        raise ValueError('prepared provider bytes or order hash mismatch')
    return fixture, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--protocol-sha256', required=True)
    args = parser.parse_args(argv)
    try:
        fixture, _ = prepare_fixture(args.prepare, args.protocol, args.protocol_sha256)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    print('Prepared {} immutable requests in {}'.format(len(fixture['request_order']), args.prepare))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
