#!/usr/bin/env python3
"""Independently reconstruct the frozen cycle04 finite model using stdlib only.

This checker does not import the experiment implementation. Both Bayes
references are computed by directly conditioning independently generated
finite tables; elementary likelihood products provide a second aware check.
"""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path
import platform
import sys


F = Fraction
REPO = Path(__file__).resolve().parents[2]
ARMS = ("padded", "copied", "independent")
RELIABILITIES = (F(11, 20), F(17, 20))
POLICIES = (
    "naive_report_independence", "payload_quotient", "optimal_blind_bayes",
    "equal_root_weighting", "optimal_aware_bayes", "protected_minority",
)
BLIND = "optimal_blind_bayes"
AWARE = "optimal_aware_bayes"
METRICS = ("brier_loss", "classification_error", "correction", "harm")
WORLD_KEYS = ("y", "g1", "g2", "g3", "s")
PARTITIONS = {
    "padded": (0, None, None, 1),
    "copied": (0, 0, 0, 1),
    "independent": (0, 1, 2, 3),
}
ACQUISITIONS = {"padded": 2, "copied": 2, "independent": 4}
FROZEN_SOURCES = {
    "_sessions/cycles/2026-09-10-cycle04-known-truth-design.md":
        "319827f9bae8d902318f34d79f7d8cfdb67a0a917f9e57c0894f2517ce7b3d7b",
    "_sessions/cycles/2026-09-10-cycle04-execution-protocol.md":
        "8f39df12a59f57baa533ebdd878e01b836cb0017189ba4942aa3e4290f250c9c",
}


class VerificationError(Exception):
    """A named exact check failed."""


class Checks:
    def __init__(self):
        self.counts = defaultdict(int)

    def require(self, category, condition, detail):
        self.counts[category] += 1
        if not condition:
            raise VerificationError("{}: {}".format(category, detail))

    def exact(self, value, expected, detail):
        self.require("canonical_rationals", isinstance(value, str), detail)
        try:
            parsed = F(value)
        except (ValueError, ZeroDivisionError) as exc:
            raise VerificationError("Invalid rational at {}: {}".format(detail, value)) from exc
        self.require("canonical_rationals", str(parsed) == value, detail)
        self.require("exact_evidence", parsed == expected,
                     "{}: recorded {}, reconstructed {}".format(detail, value, expected))


def primitive_worlds(p_specialist):
    for number, world in enumerate(itertools.product((-1, 1), repeat=5)):
        weight = F(1, 2)
        for reading, accuracy in zip(world[1:], (F(7, 10),) * 3 + (p_specialist,)):
            weight *= accuracy if reading == world[0] else 1 - accuracy
        yield "w{:02d}".format(number), world, weight


def payloads(world, arm):
    _, g1, g2, g3, specialist = world
    if arm == "padded":
        return (g1, None, None, specialist)
    if arm == "copied":
        return (g1, g1, g1, specialist)
    return (g1, g2, g3, specialist)


def canonical_partition(labels):
    distinct = {}
    answer = []
    for label in labels:
        if label is None:
            answer.append(None)
        else:
            if label not in distinct:
                distinct[label] = len(distinct)
            answer.append(distinct[label])
    return tuple(answer)


def likelihood_posterior(readings):
    positive = negative = F(1, 2)
    for value, accuracy in readings:
        positive *= accuracy if value == 1 else 1 - accuracy
        negative *= accuracy if value == -1 else 1 - accuracy
    return positive / (positive + negative)


def decide(probability, coin):
    if probability == F(1, 2):
        return coin
    return 1 if probability > F(1, 2) else -1


def paired_losses(probability, baseline, truth):
    error = correction = harm = F(0)
    for coin in (-1, 1):
        wrong = decide(probability, coin) != truth
        baseline_wrong = decide(baseline, coin) != truth
        error += F(wrong, 2)
        correction += F(baseline_wrong and not wrong, 2)
        harm += F(not baseline_wrong and wrong, 2)
    return {
        "p_positive": probability,
        "brier_loss": (probability - int(truth == 1)) ** 2,
        "classification_error": error,
        "correction": correction,
        "harm": harm,
    }


def condition_tables(p_specialist):
    blind = defaultdict(lambda: [F(0), F(0)])
    aware = defaultdict(lambda: [F(0), F(0)])
    for _, world, weight in primitive_worlds(p_specialist):
        for arm in ARMS:
            observation = payloads(world, arm)
            for table, key in ((blind, observation),
                               (aware, (observation, PARTITIONS[arm]))):
                table[key][0] += weight / 3
                if world[0] == 1:
                    table[key][1] += weight / 3
    return blind, aware


def probabilities(observation, partition, p_specialist, blind, aware):
    generalists = [(value, F(7, 10)) for value in observation[:3] if value is not None]
    specialist = (observation[3], p_specialist)
    roots = {}
    for slot, (value, root) in enumerate(zip(observation, partition)):
        if value is not None:
            roots[root] = (value, p_specialist if slot == 3 else F(7, 10))
    blind_mass, blind_positive = blind[observation]
    aware_mass, aware_positive = aware[(observation, partition)]
    blind_probability = blind_positive / blind_mass
    minority_pattern = (None not in observation[:3]
                        and observation[0] == observation[1] == observation[2]
                        and observation[0] != observation[3])
    return {
        "naive_report_independence": likelihood_posterior(generalists + [specialist]),
        "payload_quotient": likelihood_posterior(sorted(set(generalists)) + [specialist]),
        BLIND: blind_probability,
        "equal_root_weighting": F(sum(value == 1 for value, _ in roots.values()), len(roots)),
        AWARE: aware_positive / aware_mass,
        "protected_minority": (likelihood_posterior([specialist])
                               if minority_pattern else blind_probability),
    }, likelihood_posterior(roots.values())


def reconstruct(checks):
    rows = []
    cells = {}
    mixtures = {}
    copy_stats = {}
    for p_specialist in RELIABILITIES:
        p_key = str(p_specialist)
        blind, aware = condition_tables(p_specialist)
        checks.require("normalization", sum(v[0] for v in blind.values()) == 1,
                       "blind observation mass " + p_key)
        checks.require("normalization", sum(v[0] for v in aware.values()) == 1,
                       "aware observation mass " + p_key)
        for observation, (mass, positive) in blind.items():
            refinements = [(key, value) for key, value in aware.items() if key[0] == observation]
            refined_mass = sum(value[0] for _, value in refinements)
            refined_positive = sum(value[0] * (value[1] / value[0]) for _, value in refinements)
            checks.require("tower_identity", refined_mass == mass and refined_positive / mass == positive / mass,
                           repr(observation))
        per_arm = {arm: [] for arm in ARMS}
        per_world = {}
        for world_id, world, weight in primitive_worlds(p_specialist):
            per_world[world] = {}
            for arm in ARMS:
                observation = payloads(world, arm)
                partition = PARTITIONS[arm]
                probs, product_aware = probabilities(observation, partition, p_specialist, blind, aware)
                checks.require("aware_conditional_product", probs[AWARE] == product_aware,
                               p_key + "/" + world_id + "/" + arm)
                obvious_lineage = arm == "padded" or len(set(observation[:3])) > 1
                if obvious_lineage:
                    checks.require("unambiguous_observation", probs[AWARE] == probs[BLIND], repr(observation))
                row_metrics = {policy: paired_losses(probs[policy], probs[BLIND], world[0]) for policy in POLICIES}
                for policy, metrics in row_metrics.items():
                    checks.require("paired_decomposition",
                                   metrics["correction"] - metrics["harm"] ==
                                   row_metrics[BLIND]["classification_error"] - metrics["classification_error"],
                                   policy + "/" + world_id)
                    if policy == BLIND:
                        checks.require("shared_tie_self_comparison", metrics["correction"] == metrics["harm"] == 0,
                                       world_id)
                reference = {"p_specialist": p_key, "world_id": world_id, "world_tuple": world,
                             "arm": arm, "weight": weight, "payloads": observation,
                             "partition": partition, "policies": row_metrics}
                rows.append(reference)
                per_arm[arm].append(reference)
                per_world[world][arm] = reference
        cells[p_key] = {}
        for arm, arm_rows in per_arm.items():
            checks.require("normalization", sum(row["weight"] for row in arm_rows) == 1, p_key + "/" + arm)
            cells[p_key][arm] = {
                policy: {metric: sum(row["weight"] * row["policies"][policy][metric] for row in arm_rows)
                         for metric in METRICS} for policy in POLICIES}
        mix = {policy: {metric: sum(cells[p_key][arm][policy][metric] for arm in ARMS) / 3
                        for metric in METRICS} for policy in POLICIES}
        gap = sum(row["weight"] / 3 * (row["policies"][AWARE]["p_positive"] -
                                      row["policies"][BLIND]["p_positive"]) ** 2
                  for arm_rows in per_arm.values() for row in arm_rows)
        checks.require("brier_information_identity", mix[BLIND]["brier_loss"] - mix[AWARE]["brier_loss"] == gap, p_key)
        for policy in POLICIES:
            if policy not in (AWARE, "equal_root_weighting"):
                for metric in ("brier_loss", "classification_error"):
                    checks.require("blind_mixture_optimality", mix[BLIND][metric] <= mix[policy][metric], policy)
            for arm in ARMS:
                for metric in ("brier_loss", "classification_error"):
                    checks.require("aware_arm_optimality", cells[p_key][arm][AWARE][metric] <= cells[p_key][arm][policy][metric],
                                   arm + "/" + policy)
        mixtures[p_key] = {"policies": mix, "posterior_squared_gap": gap}
        copy_stats[p_key] = {}
        for policy in POLICIES:
            changed = [pair for pair in per_world.values()
                       if pair["padded"]["policies"][policy]["p_positive"] !=
                       pair["copied"]["policies"][policy]["p_positive"]]
            copy_stats[p_key][policy] = (len(changed), sum((pair["padded"]["weight"] for pair in changed), F(0)))
            if policy in (AWARE, "equal_root_weighting"):
                checks.require("copy_invariance", len(changed) == 0, policy)
        for world, arm_rows in per_world.items():
            opposite = per_world[tuple(-value for value in world)]
            for arm in ARMS:
                checks.require("sign_symmetry", arm_rows[arm]["weight"] == opposite[arm]["weight"], arm)
                for policy in POLICIES:
                    original = arm_rows[arm]["policies"][policy]
                    reverse = opposite[arm]["policies"][policy]
                    checks.require("sign_symmetry", original["p_positive"] + reverse["p_positive"] == 1,
                                   arm + "/" + policy)
                    for metric in METRICS:
                        checks.require("sign_symmetry", original[metric] == reverse[metric], arm + "/" + policy + "/" + metric)
    return rows, cells, mixtures, copy_stats


def verify_metric_map(recorded, expected, checks, context, include_probability=False):
    required = set(METRICS) | ({"p_positive"} if include_probability else set())
    checks.require("schema", set(recorded) == required, context + " metric keys")
    for metric in required:
        checks.exact(recorded[metric], expected[metric], context + "/" + metric)


def verify_evidence(per_world, summary, reference, checks):
    rows, cells, mixtures, copy_stats = reference
    checks.require("schema", per_world["schema_version"] == summary["schema_version"] == 1, "schema version")
    checks.require("schema", per_world["comparator"] == BLIND, "named comparator")
    checks.require("schema", summary["policy_order"] == list(POLICIES), "policy order")
    checks.require("schema", summary["arms"] == list(ARMS), "arm order")
    expected_claims = {
        "world_rows": 192, "aware_conditioning_rows": 192,
        "paired_decomposition_rows": 1152, "all_cell_masses_one": True,
        "all_mixture_masses_one": True, "aware_copy_invariance": True,
        "conditional_expectation_and_brier_identity": True,
    }
    checks.require("summary_claims", summary["checks"] == expected_claims,
                   "producer check counts and structural claims")
    parameters = summary["known_parameters"]
    checks.exact(parameters["p_generalist"], F(7, 10), "known_parameters/p_generalist")
    checks.exact(parameters["truth_prior_positive"], F(1, 2), "known_parameters/truth_prior_positive")
    checks.require("schema", parameters["p_specialist_values"] == list(map(str, RELIABILITIES)),
                   "known_parameters/p_specialist_values")
    checks.require("schema", set(parameters["arm_prior"]) == set(ARMS), "known_parameters/arm_prior")
    for arm in ARMS:
        checks.exact(parameters["arm_prior"][arm], F(1, 3), "known_parameters/arm_prior/" + arm)
    resources = summary["resource_accounting"]
    checks.require("resource_accounting", resources["report_slots"] == resources["acquisition_ceiling"] == 4,
                   "four slots and acquisition ceiling")
    checks.require("resource_accounting", resources["informative_acquisitions"] == ACQUISITIONS,
                   "primitive acquisitions")
    checks.require("resource_accounting",
                   resources["provenance_cost"] == "trusted lineage supplied; acquisition cost not modeled",
                   "provenance cost qualification")
    checks.require("schema", len(per_world["rows"]) == len(rows) == 192, "192 world-arm rows")
    checks.require("schema", set(summary["cells"]) == set(map(str, RELIABILITIES)), "six cells")
    checks.require("schema", set(summary["mixtures"]) == set(map(str, RELIABILITIES)), "two known-parameter mixtures")
    checks.require("schema", set(summary["copy_invariance"]) == set(map(str, RELIABILITIES)), "two copy comparisons")
    report_ids = None
    blind_outputs = {}
    aware_outputs = {}
    for index, (recorded, expected) in enumerate(zip(per_world["rows"], rows)):
        context = "row {}".format(index)
        for key in ("p_specialist", "world_id", "arm"):
            checks.require("row_identity", recorded[key] == expected[key], context + "/" + key)
        checks.require("row_identity", recorded["world"] == dict(zip(WORLD_KEYS, expected["world_tuple"])), context + "/world")
        checks.exact(recorded["world_probability"], expected["weight"], context + "/world_probability")
        checks.require("resource_accounting", recorded["informative_acquisitions"] == ACQUISITIONS[expected["arm"]], context)
        checks.require("resource_accounting", recorded["report_slots"] == 4, context)
        reports = recorded["reports"]
        checks.require("observation", len(reports) == 4, context + "/report count")
        checks.require("observation", [report["role"] for report in reports] == ["generalist"] * 3 + ["specialist"], context + "/roles")
        checks.require("observation", tuple(report["value"] for report in reports) == expected["payloads"], context + "/payloads")
        ids = tuple(report["report_id"] for report in reports)
        checks.require("observation", all(isinstance(value, str) for value in ids) and len(set(ids)) == 4, context + "/unique IDs")
        if report_ids is None:
            report_ids = ids
        checks.require("observation", ids == report_ids, context + "/constant positional IDs")
        partition = recorded["parent_partition"]
        checks.require("observation", len(partition) == 4, context + "/partition size")
        checks.require("observation", tuple(recorded["canonical_partition"]) == expected["partition"], context + "/canonical partition")
        checks.require("observation", canonical_partition(partition) == expected["partition"], context + "/opaque partition")
        renamed = [None if label is None else "renamed-{}".format(root)
                   for label, root in zip(partition, expected["partition"])]
        checks.require("root_renaming", canonical_partition(renamed) == expected["partition"], context)
        checks.require("schema", set(recorded["policies"]) == set(POLICIES), context + "/policies")
        for policy in POLICIES:
            verify_metric_map(recorded["policies"][policy], expected["policies"][policy], checks,
                              context + "/" + policy, include_probability=True)
            visible = (expected["p_specialist"], expected["payloads"])
            if policy in (AWARE, "equal_root_weighting"):
                key = (policy, visible, expected["partition"])
                cache = aware_outputs
            else:
                key = (policy, visible)
                cache = blind_outputs
            probability = recorded["policies"][policy]["p_positive"]
            if key in cache:
                checks.require("observation_equivalence", cache[key] == probability, context + "/" + policy)
            cache[key] = probability
    for p_key in map(str, RELIABILITIES):
        checks.require("schema", set(summary["cells"][p_key]) == set(ARMS), p_key + "/arms")
        for arm in ARMS:
            recorded = summary["cells"][p_key][arm]
            context = "cells/" + p_key + "/" + arm
            checks.require("summary_counts", recorded["world_count"] == 32, context)
            checks.exact(recorded["probability_mass"], F(1), context + "/probability_mass")
            checks.require("resource_accounting", recorded["informative_acquisitions"] == ACQUISITIONS[arm], context)
            checks.require("schema", set(recorded["policies"]) == set(POLICIES), context + "/policies")
            for policy in POLICIES:
                verify_metric_map(recorded["policies"][policy], cells[p_key][arm][policy], checks, context + "/" + policy)
            for metric in ("brier_loss", "classification_error"):
                checks.exact(recorded["aware_minus_blind"][metric],
                             cells[p_key][arm][AWARE][metric] - cells[p_key][arm][BLIND][metric],
                             context + "/aware_minus_blind/" + metric)
        recorded = summary["mixtures"][p_key]
        context = "mixtures/" + p_key
        checks.exact(recorded["arm_probability"], F(1, 3), context + "/arm_probability")
        checks.exact(recorded["probability_mass"], F(1), context + "/probability_mass")
        checks.exact(recorded["expected_informative_acquisitions"], F(8, 3), context + "/expected_informative_acquisitions")
        checks.require("summary_counts", recorded["world_arm_rows"] == 96, context + "/world_arm_rows")
        checks.require("schema", set(recorded["policies"]) == set(POLICIES), context + "/policies")
        for policy in POLICIES:
            verify_metric_map(recorded["policies"][policy], mixtures[p_key]["policies"][policy], checks, context + "/" + policy)
        for metric in ("brier_loss", "classification_error"):
            checks.exact(recorded["aware_minus_blind"][metric],
                         mixtures[p_key]["policies"][AWARE][metric] - mixtures[p_key]["policies"][BLIND][metric],
                         context + "/aware_minus_blind/" + metric)
        checks.exact(recorded["posterior_squared_gap"], mixtures[p_key]["posterior_squared_gap"], context + "/posterior_squared_gap")
        checks.require("summary_claims", recorded["conditional_expectation_identity"] is True, context)
        checks.require("schema", set(summary["copy_invariance"][p_key]) == set(POLICIES), p_key + "/copy policies")
        for policy in POLICIES:
            recorded = summary["copy_invariance"][p_key][policy]
            count, mass = copy_stats[p_key][policy]
            context = "copy_invariance/" + p_key + "/" + policy
            checks.require("summary_counts", recorded["world_pairs"] == 32, context + "/world_pairs")
            checks.require("copy_counts", recorded["changed_count"] == count, context + "/changed_count")
            checks.exact(recorded["changed_probability_mass"], mass, context + "/changed_probability_mass")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_hashes(directory):
    return {str(path.relative_to(directory)): sha256(path)
            for path in sorted(directory.rglob("*")) if path.is_file()}


def read_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def source_hashes(paths):
    result = {}
    for name in sorted(paths):
        path = (REPO / name).resolve()
        if REPO not in path.parents:
            raise VerificationError("Source path leaves repository: " + name)
        result[name] = sha256(path)
    return result


def verify_custody(manifest, initial_manifest, result_hashes, current_sources, checks):
    checks.require("custody", manifest["status"] == "complete", "producer completed")
    checks.require("custody", initial_manifest["status"] == "started", "initial manifest status")
    required_initial = {
        "status", "started_utc", "argv", "cwd", "python_version", "python_executable",
        "python_implementation", "protocol", "design", "source_sha256_start",
        "frozen_sha256", "git_state_start",
    }
    checks.require("custody", required_initial <= set(initial_manifest), "initial manifest required fields")
    for key, value in initial_manifest.items():
        if key != "status":
            checks.require("custody", manifest.get(key) == value, "initial record preserved: " + key)
    checks.require("custody", manifest["frozen_sha256"] == FROZEN_SOURCES, "declared frozen hashes")
    for field, expected in (("protocol", "_sessions/cycles/2026-09-10-cycle04-execution-protocol.md"),
                            ("design", "_sessions/cycles/2026-09-10-cycle04-known-truth-design.md")):
        checks.require("custody", manifest[field] == expected, "declared " + field)
    started = datetime.fromisoformat(manifest["started_utc"])
    finished = datetime.fromisoformat(manifest["finished_utc"])
    checks.require("custody", started.utcoffset() is not None and finished.utcoffset() is not None
                   and started.utcoffset().total_seconds() == finished.utcoffset().total_seconds() == 0
                   and started <= finished, "producer UTC execution interval")
    checks.require("custody", manifest["sources_unchanged"] is True, "producer source stability claim")
    checks.require("custody", manifest["source_sha256_start"] == manifest["source_sha256_end"], "producer source hashes match")
    for name, digest in manifest["source_sha256_start"].items():
        checks.require("custody", current_sources[name] == digest, "current source hash " + name)
    for name, digest in FROZEN_SOURCES.items():
        checks.require("custody", manifest["source_sha256_start"].get(name) == digest, "frozen source in producer manifest " + name)
        checks.require("custody", current_sources[name] == digest, "frozen source remains unchanged " + name)
    checks.require("custody", set(manifest["output_sha256"]) == {"manifest-start.json", "per_world.json", "summary.json"},
                   "complete numerical output hash list")
    for name, digest in manifest["output_sha256"].items():
        checks.require("custody", result_hashes[name] == digest, "producer output hash " + name)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True, help="Completed immutable cycle04 result directory")
    parser.add_argument("--output", type=Path, required=True, help="New independent receipt outside the result directory")
    args = parser.parse_args(argv)
    results = args.results.resolve()
    output = args.output.resolve()
    if output.exists():
        parser.error("Refusing to overwrite existing receipt: " + str(output))
    if results == output or results in output.parents:
        parser.error("Receipt must be outside the immutable results directory")
    if not results.is_dir():
        parser.error("Results directory does not exist: " + str(results))
    started = utc_now()
    checks = Checks()
    before = directory_hashes(results)
    sources_before = {}
    sources_after = {}
    error = None
    try:
        manifest = read_json(results / "manifest.json")
        source_paths = set(FROZEN_SOURCES) | set(manifest["source_sha256_start"])
        source_paths.add(str(Path(__file__).resolve().relative_to(REPO)))
        sources_before = source_hashes(source_paths)
        verify_custody(manifest, read_json(results / "manifest-start.json"), before, sources_before, checks)
        for truth in (-1, 1):
            tied = paired_losses(F(1, 2), F(1, 2), truth)
            checks.require("shared_tie_self_comparison", tied["classification_error"] == F(1, 2)
                           and tied["correction"] == tied["harm"] == 0, "synthetic tie case")
        reference = reconstruct(checks)
        verify_evidence(read_json(results / "per_world.json"), read_json(results / "summary.json"), reference, checks)
    except (VerificationError, KeyError, ValueError, TypeError, OSError, ZeroDivisionError) as exc:
        error = "{}: {}".format(type(exc).__name__, exc)
    after = directory_hashes(results)
    if sources_before:
        try:
            sources_after = source_hashes(sources_before)
        except (OSError, VerificationError) as exc:
            error = error or "Source hashing failed after verification: " + str(exc)
    try:
        checks.require("checker_custody", before == after, "results unchanged across independent check")
        checks.require("checker_custody", bool(sources_before) and sources_before == sources_after,
                       "sources and checker unchanged across independent check")
    except VerificationError as exc:
        error = error or str(exc)
    receipt = {
        "schema_version": 1,
        "status": "passed" if error is None else "failed",
        "method": "Independent standard-library finite-table reconstruction; no production-code imports",
        "argv": [sys.executable, str(Path(__file__).resolve())] + (list(argv) if argv is not None else sys.argv[1:]),
        "started_utc": started,
        "finished_utc": utc_now(),
        "python": platform.python_version(),
        "results_directory": str(results),
        "output_sha256_before": before,
        "output_sha256_after": after,
        "source_sha256_before": sources_before,
        "source_sha256_after": sources_after,
        "checks": dict(sorted(checks.counts.items())),
        "error": error,
        "scope": {"world_arm_rows": 192, "cells": 6, "known_parameter_mixtures": 2,
                  "policies": list(POLICIES)},
        "limitations": [
            "Numerical evidence and observation equivalence are checked; runtime input isolation requires source/test review.",
            "No empirical generalization, provenance acquisition cost, or model calibration is measured.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"status": receipt["status"], "receipt": str(output),
                      "receipt_sha256": sha256(output), "checks": sum(checks.counts.values()), "error": error}, sort_keys=True))
    return 0 if error is None else 1


if __name__ == "__main__":
    sys.exit(main())
