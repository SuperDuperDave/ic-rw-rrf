"""Exact, standard-library cycle04 fixture under a frozen six-cell contract.

Run only into a fresh results directory. Policy packets contain observations;
the evaluator alone owns realized arm, truth, potential readings and costs.
"""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from fractions import Fraction
from functools import lru_cache
import hashlib
from itertools import product
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import NamedTuple, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = '_sessions/cycles/2026-09-10-cycle04-execution-protocol.md'
DESIGN = '_sessions/cycles/2026-09-10-cycle04-known-truth-design.md'
PROTOCOL_SHA256 = '8f39df12a59f57baa533ebdd878e01b836cb0017189ba4942aa3e4290f250c9c'
DESIGN_SHA256 = '319827f9bae8d902318f34d79f7d8cfdb67a0a917f9e57c0894f2517ce7b3d7b'
CODE = 'evaluation/cycle04_known_truth.py'
TESTS = 'evaluation/tests/test_cycle04_known_truth.py'
ARMS = ('padded', 'copied', 'independent')
SPECIALIST_ACCURACIES = (Fraction(11, 20), Fraction(17, 20))
REPORT_IDS = ('r_94c2', 'r_b170', 'r_28e9', 'r_5a63')
ROOT_IDS = ('q_f40a', 'q_27bd', 'q_6c18', 'q_d953')
ROLES = ('generalist', 'generalist', 'generalist', 'specialist')
ACQUISITIONS = {'padded': 2, 'copied': 2, 'independent': 4}
BASELINE = 'optimal_blind_bayes'
METRICS = ('brier_loss', 'classification_error', 'correction', 'harm')


class Parameters(NamedTuple):
    p_specialist: Fraction
    p_generalist: Fraction = Fraction(7, 10)
    truth_prior_positive: Fraction = Fraction(1, 2)
    arm_prior: Tuple[Fraction, ...] = (Fraction(1, 3),) * 3


class Report(NamedTuple):
    report_id: str
    role: str
    value: Optional[int]


class BlindPacket(NamedTuple):
    reports: Tuple[Report, ...]


class AwarePacket(NamedTuple):
    reports: Tuple[Report, ...]
    parent_partition: Tuple[Optional[str], ...]


class World(NamedTuple):
    y: int
    g1: int
    g2: int
    g3: int
    s: int


def validate_parameters(parameters):
    if (type(parameters) is not Parameters or
            type(parameters.p_specialist) is not Fraction or
            parameters.p_specialist not in SPECIALIST_ACCURACIES or
            type(parameters.p_generalist) is not Fraction or
            parameters.p_generalist != Fraction(7, 10) or
            type(parameters.truth_prior_positive) is not Fraction or
            parameters.truth_prior_positive != Fraction(1, 2) or
            type(parameters.arm_prior) is not tuple or
            any(type(weight) is not Fraction for weight in parameters.arm_prior) or
            parameters.arm_prior != (Fraction(1, 3),) * 3):
        raise ValueError('parameters must equal one of the two frozen settings')


def validate_reports(reports):
    if type(reports) is not tuple or len(reports) != 4:
        raise ValueError('a packet must contain exactly four report slots')
    if any(type(report) is not Report for report in reports):
        raise ValueError('report slots must be Report values')
    ids = [report.report_id for report in reports]
    if any(type(label) is not str or not label for label in ids) or len(set(ids)) != 4:
        raise ValueError('report IDs must be nonempty and unique within the packet')
    if tuple(report.role for report in reports) != ROLES:
        raise ValueError('roles must match the four frozen positions')
    values = tuple(report.value for report in reports)
    if any(value is not None and (type(value) is not int or value not in (-1, 1))
           for value in values):
        raise ValueError('readings must be integer signs or null')
    if values[0] is None or values[3] is None or ((values[1] is None) != (values[2] is None)):
        raise ValueError('only the two padded middle slots may be null')


def blind_key(packet):
    if type(packet) is not BlindPacket:
        raise ValueError('blind policies accept only BlindPacket, with no lineage or evaluator metadata')
    validate_reports(packet.reports)
    return tuple((report.role, report.value) for report in packet.reports)


def canonical_partition(packet):
    if type(packet) is not AwarePacket:
        raise ValueError('aware policies accept only AwarePacket')
    validate_reports(packet.reports)
    if type(packet.parent_partition) is not tuple or len(packet.parent_partition) != 4:
        raise ValueError('the partition must contain four aligned slots')
    names, readings, canonical = {}, {}, []
    for report, root in zip(packet.reports, packet.parent_partition):
        if report.value is None:
            if root is not None:
                raise ValueError('null slots cannot have a root')
            canonical.append(None)
            continue
        if type(root) is not str or not root:
            raise ValueError('non-null slots require an opaque root label')
        reading = (report.role, report.value)
        if root in readings and readings[root] != reading:
            raise ValueError('one root must have one role and reading')
        readings[root] = reading
        if root not in names:
            names[root] = len(names)
        canonical.append(names[root])
    result = tuple(canonical)
    if result not in ((0, None, None, 1), (0, 0, 0, 1), (0, 1, 2, 3)):
        raise ValueError('partition is outside the frozen construction model')
    return result


def aware_key(packet):
    partition = canonical_partition(packet)
    return (tuple((report.role, report.value) for report in packet.reports), partition)


def world_probability(world, parameters):
    validate_parameters(parameters)
    if type(world) is not World or any(type(v) is not int or v not in (-1, 1) for v in world):
        raise ValueError('world must contain five integer signs')
    probability = parameters.truth_prior_positive if world.y == 1 else 1 - parameters.truth_prior_positive
    for value, accuracy in zip(world[1:], (parameters.p_generalist,) * 3 + (parameters.p_specialist,)):
        probability *= accuracy if value == world.y else 1 - accuracy
    return probability


def enumerate_worlds(parameters):
    validate_parameters(parameters)
    return tuple((World(*values), world_probability(World(*values), parameters))
                 for values in product((-1, 1), repeat=5))


def make_packets(world, arm):
    """Generator boundary: arm and latent readings do not become packet fields."""
    if arm == 'padded':
        values, roots = (world.g1, None, None, world.s), (ROOT_IDS[0], None, None, ROOT_IDS[3])
    elif arm == 'copied':
        values, roots = (world.g1,) * 3 + (world.s,), (ROOT_IDS[0],) * 3 + (ROOT_IDS[3],)
    elif arm == 'independent':
        values, roots = tuple(world[1:]), ROOT_IDS
    else:
        raise ValueError('unknown construction')
    reports = tuple(Report(label, role, value) for label, role, value in zip(REPORT_IDS, ROLES, values))
    return BlindPacket(reports), AwarePacket(reports, roots)


def likelihood_posterior(readings, parameters):
    validate_parameters(parameters)
    positive, negative = parameters.truth_prior_positive, 1 - parameters.truth_prior_positive
    for role, value in readings:
        accuracy = parameters.p_specialist if role == 'specialist' else parameters.p_generalist
        positive *= accuracy if value == 1 else 1 - accuracy
        negative *= accuracy if value == -1 else 1 - accuracy
    return positive / (positive + negative)


@lru_cache(maxsize=4)
def conditioning_table(parameters, aware=False):
    """Exact posterior lookup; keys include only permitted observations."""
    validate_parameters(parameters)
    masses = defaultdict(lambda: [Fraction(0), Fraction(0)])
    for world, weight in enumerate_worlds(parameters):
        for arm, arm_weight in zip(ARMS, parameters.arm_prior):
            blind, visible_lineage = make_packets(world, arm)
            key = aware_key(visible_lineage) if aware else blind_key(blind)
            masses[key][0] += weight * arm_weight
            masses[key][1] += weight * arm_weight * (world.y == 1)
    return {key: positive / total for key, (total, positive) in masses.items()}


def naive_report_independence(packet, parameters):
    readings = blind_key(packet)
    return likelihood_posterior([(role, value) for role, value in readings if value is not None], parameters)


def payload_quotient(packet, parameters):
    readings = blind_key(packet)
    return likelihood_posterior(sorted(set((role, value) for role, value in readings if value is not None)), parameters)


def optimal_blind_bayes(packet, parameters):
    key = blind_key(packet)
    validate_parameters(parameters)
    return conditioning_table(parameters)[key]


def root_readings(packet):
    partition = canonical_partition(packet)
    seen, readings = set(), []
    for report, root in zip(packet.reports, partition):
        if root is not None and root not in seen:
            seen.add(root)
            readings.append((report.role, report.value))
    return readings


def equal_root_weighting(packet, parameters):
    validate_parameters(parameters)
    readings = root_readings(packet)
    return Fraction(sum(value == 1 for _, value in readings), len(readings))


def optimal_aware_bayes(packet, parameters):
    return likelihood_posterior(root_readings(packet), parameters)


def protected_minority(packet, parameters):
    readings = blind_key(packet)
    validate_parameters(parameters)
    generals = [value for role, value in readings if role == 'generalist']
    specialist = readings[3][1]
    if all(value == -specialist for value in generals):
        return parameters.p_specialist if specialist == 1 else 1 - parameters.p_specialist
    return optimal_blind_bayes(packet, parameters)


POLICIES = {
    'naive_report_independence': naive_report_independence,
    'payload_quotient': payload_quotient,
    'optimal_blind_bayes': optimal_blind_bayes,
    'equal_root_weighting': equal_root_weighting,
    'optimal_aware_bayes': optimal_aware_bayes,
    'protected_minority': protected_minority,
}
AWARE_POLICIES = frozenset(('equal_root_weighting', 'optimal_aware_bayes'))


def class_decision(probability, tie_coin):
    if type(probability) is not Fraction or not 0 <= probability <= 1 or tie_coin not in (-1, 1):
        raise ValueError('expected a rational probability and a signed tie coin')
    return tie_coin if probability == Fraction(1, 2) else (1 if probability > Fraction(1, 2) else -1)


def paired_losses(probability, baseline_probability, truth):
    """One shared fair coin defines both policies' potential tie decisions."""
    error = correction = harm = Fraction(0)
    if type(truth) is not int or truth not in (-1, 1):
        raise ValueError('truth must be an integer sign')
    for coin in (-1, 1):
        wrong = class_decision(probability, coin) != truth
        baseline_wrong = class_decision(baseline_probability, coin) != truth
        error += Fraction(int(wrong), 2)
        correction += Fraction(int(baseline_wrong and not wrong), 2)
        harm += Fraction(int(not baseline_wrong and wrong), 2)
    return {'p_positive': probability, 'brier_loss': (probability - (truth == 1)) ** 2,
            'classification_error': error, 'correction': correction, 'harm': harm}


def aggregate(rows, mixture=False):
    divisor = Fraction(3) if mixture else Fraction(1)
    policies = {name: {metric: sum((row['world_probability'] * row['policies'][name][metric] / divisor
                                  for row in rows), Fraction(0)) for metric in METRICS} for name in POLICIES}
    baseline = policies[BASELINE]
    for name, values in policies.items():
        if values['correction'] - values['harm'] != baseline['classification_error'] - values['classification_error']:
            raise AssertionError('correction/harm identity failed for ' + name)
    return {'probability_mass': sum((row['world_probability'] / divisor for row in rows), Fraction(0)),
            'policies': policies,
            'aware_minus_blind': {metric: policies['optimal_aware_bayes'][metric] - baseline[metric]
                                 for metric in ('brier_loss', 'classification_error')}}


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {str(key): exact_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(item) for item in value]
    return value


def build_results():
    """Build all frozen rows and exact summaries, without filesystem writes."""
    rows, cells, mixtures, invariance = [], {}, {}, {}
    checked_conditioning = checked_decomposition = 0
    for specialist in SPECIALIST_ACCURACIES:
        parameters = Parameters(specialist)
        parameter_rows = []
        worlds = enumerate_worlds(parameters)
        if len(worlds) != 32 or sum((weight for _, weight in worlds), Fraction(0)) != 1:
            raise AssertionError('world normalization failed')
        for index, (world, weight) in enumerate(worlds):
            for arm in ARMS:
                blind, aware = make_packets(world, arm)
                predictions = {name: policy(aware if name in AWARE_POLICIES else blind, parameters)
                               for name, policy in POLICIES.items()}
                if predictions['optimal_aware_bayes'] != conditioning_table(parameters, True)[aware_key(aware)]:
                    raise AssertionError('aware likelihood and finite conditioning disagree')
                checked_conditioning += 1
                losses = {name: paired_losses(probability, predictions[BASELINE], world.y)
                          for name, probability in predictions.items()}
                for values in losses.values():
                    if values['correction'] - values['harm'] != losses[BASELINE]['classification_error'] - values['classification_error']:
                        raise AssertionError('world paired decomposition failed')
                    checked_decomposition += 1
                row = {'p_specialist': specialist, 'world_id': 'w{:02d}'.format(index),
                       'world': world._asdict(), 'arm': arm, 'world_probability': weight,
                       'reports': [report._asdict() for report in blind.reports],
                       'parent_partition': aware.parent_partition, 'canonical_partition': canonical_partition(aware),
                       'informative_acquisitions': ACQUISITIONS[arm], 'report_slots': 4, 'policies': losses}
                rows.append(row)
                parameter_rows.append(row)
        cells[specialist] = {}
        for arm in ARMS:
            arm_rows = [row for row in parameter_rows if row['arm'] == arm]
            cells[specialist][arm] = dict(aggregate(arm_rows), world_count=len(arm_rows),
                                          informative_acquisitions=ACQUISITIONS[arm])
        mixture = aggregate(parameter_rows, mixture=True)
        squared_gap = sum((row['world_probability'] / 3 *
                           (row['policies']['optimal_aware_bayes']['p_positive'] - row['policies'][BASELINE]['p_positive']) ** 2
                           for row in parameter_rows), Fraction(0))
        if -mixture['aware_minus_blind']['brier_loss'] != squared_gap:
            raise AssertionError('mixture Brier conditional-expectation identity failed')
        grouped = defaultdict(lambda: [Fraction(0), Fraction(0), None])
        for row in parameter_rows:
            key = tuple((report['role'], report['value']) for report in row['reports'])
            group = grouped[key]
            group[0] += row['world_probability'] / 3
            group[1] += row['world_probability'] / 3 * row['policies']['optimal_aware_bayes']['p_positive']
            blind_probability = row['policies'][BASELINE]['p_positive']
            if group[2] is not None and group[2] != blind_probability:
                raise AssertionError('identical blind packets have different predictions')
            group[2] = blind_probability
        if any(weighted_aware / mass != blind_probability for mass, weighted_aware, blind_probability in grouped.values()):
            raise AssertionError('posterior conditional expectation failed')
        mixture.update({'arm_probability': Fraction(1, 3), 'world_arm_rows': len(parameter_rows),
                        'expected_informative_acquisitions': Fraction(8, 3), 'posterior_squared_gap': squared_gap,
                        'conditional_expectation_identity': True})
        mixtures[specialist] = mixture
        by_pair = {(row['world_id'], row['arm']): row for row in parameter_rows}
        invariance[specialist] = {}
        for name in POLICIES:
            changes = [by_pair[('w{:02d}'.format(index), 'padded')]['policies'][name]['p_positive'] !=
                       by_pair[('w{:02d}'.format(index), 'copied')]['policies'][name]['p_positive']
                       for index in range(32)]
            invariance[specialist][name] = {'world_pairs': 32, 'changed_count': sum(changes),
                                          'changed_probability_mass': sum((weight for changed, (_, weight)
                                                                           in zip(changes, worlds) if changed), Fraction(0))}
            if name in AWARE_POLICIES and any(changes):
                raise AssertionError('aware copy invariance failed')
    summary = {'schema_version': 1, 'policy_order': list(POLICIES), 'arms': ARMS,
               'known_parameters': {'p_generalist': Fraction(7, 10), 'p_specialist_values': SPECIALIST_ACCURACIES,
                                    'truth_prior_positive': Fraction(1, 2), 'arm_prior': {arm: Fraction(1, 3) for arm in ARMS}},
               'comparator': BASELINE, 'gap_sign': 'aware minus optimal blind; negative is improvement',
               'correction_harm_sign': 'correction - harm = error(optimal blind) - error(policy)',
               'resource_accounting': {'report_slots': 4, 'acquisition_ceiling': 4,
                                       'informative_acquisitions': ACQUISITIONS,
                                       'provenance_cost': 'trusted lineage supplied; acquisition cost not modeled'},
               'cells': cells, 'mixtures': mixtures, 'copy_invariance': invariance,
               'checks': {'world_rows': len(rows), 'aware_conditioning_rows': checked_conditioning,
                          'paired_decomposition_rows': checked_decomposition,
                          'all_cell_masses_one': all(cell['probability_mass'] == 1 for settings in cells.values() for cell in settings.values()),
                          'all_mixture_masses_one': all(mixture['probability_mass'] == 1 for mixture in mixtures.values()),
                          'aware_copy_invariance': True, 'conditional_expectation_and_brier_identity': True}}
    return exact_json(summary), exact_json({'schema_version': 1, 'comparator': BASELINE, 'rows': rows})


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hash_paths(root):
    return {name: sha256(root / name) for name in (PROTOCOL, DESIGN, CODE, TESTS)}


def git_state(root):
    return {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
            'dirty_status': subprocess.check_output(
                ['git', '--no-optional-locks', 'status', '--short', '--untracked-files=all'],
                cwd=root, text=True).splitlines()}


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


def new_output_directory(path, root):
    path = (root / path).resolve() if not path.is_absolute() else path.resolve()
    results = (root / 'results').resolve()
    if path == results:
        raise ValueError('output must be a fresh child directory inside repository results/')
    try:
        path.relative_to(root.resolve())
        path.relative_to(results)
    except ValueError as error:
        raise ValueError('output must be a fresh directory inside repository results/') from error
    path.mkdir(parents=True, exist_ok=False)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Fresh immutable directory in results/')
    args = parser.parse_args(argv)
    root = ROOT.resolve()
    try:
        source_start = hash_paths(root)
        initial_git = git_state(root)
        output = new_output_directory(args.output, root)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    provenance = {'status': 'started', 'started_utc': datetime.now(timezone.utc).isoformat(),
                  'argv': list(sys.argv) if argv is None else [str(root / CODE)] + list(argv),
                  'cwd': str(Path.cwd()), 'python_version': platform.python_version(),
                  'python_executable': sys.executable, 'python_implementation': platform.python_implementation(),
                  'protocol': PROTOCOL, 'design': DESIGN, 'source_sha256_start': source_start,
                  'frozen_sha256': {PROTOCOL: PROTOCOL_SHA256, DESIGN: DESIGN_SHA256},
                  'git_state_start': initial_git}
    write_json(output / 'manifest-start.json', provenance)
    try:
        for name, digest in provenance['frozen_sha256'].items():
            if source_start[name] != digest:
                raise ValueError('frozen input hash mismatch: ' + name)
        summary, per_world = build_results()
        write_json(output / 'summary.json', summary)
        write_json(output / 'per_world.json', per_world)
        provenance['source_sha256_end'] = hash_paths(root)
        provenance['sources_unchanged'] = provenance['source_sha256_end'] == source_start
        if not provenance['sources_unchanged']:
            raise RuntimeError('protocol, design, code, or tests changed during execution; outputs are invalid')
        provenance['git_state_end'] = git_state(root)
        provenance['output_sha256'] = {path.name: sha256(path) for path in sorted(output.glob('*.json'))}
    except Exception as error:
        provenance.update({'status': 'invalid', 'finished_utc': datetime.now(timezone.utc).isoformat(),
                           'error': '{}: {}'.format(type(error).__name__, error)})
        try:
            provenance['source_sha256_end'] = hash_paths(root)
        except (OSError, ValueError) as hash_error:
            provenance['source_sha256_end_error'] = str(hash_error)
        provenance['sources_unchanged'] = provenance.get('source_sha256_end') == source_start
        try:
            provenance['git_state_end'] = git_state(root)
        except (OSError, subprocess.SubprocessError) as git_error:
            provenance['git_state_end_error'] = str(git_error)
        provenance['output_sha256'] = {path.name: sha256(path) for path in sorted(output.glob('*.json'))}
        write_json(output / 'manifest-invalid.json', provenance)
        raise
    provenance.update({'status': 'complete', 'finished_utc': datetime.now(timezone.utc).isoformat()})
    write_json(output / 'manifest.json', provenance)
    print('Wrote cycle04 exact fixture:', output, flush=True)


if __name__ == '__main__':
    main()
