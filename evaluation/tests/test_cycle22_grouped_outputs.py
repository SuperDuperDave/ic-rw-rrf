"""Synthetic tests only; no run bodies, qrels files, or empirical artifacts."""

from copy import deepcopy
from fractions import Fraction
from itertools import product
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import cycle22_grouped_outputs as producer
from evaluation.cycle22_grouped_outputs import analyze, build_policies


def value(item):
    return Fraction(item["fraction"])


def fixture():
    anchors = [f"p{i:02}" for i in range(1, 10)]
    fillers = [f"f{i:02}" for i in range(88)]
    return {
        "S": anchors + ["z", "x", "y"] + fillers,
        "R0": anchors + ["x", "z"] + fillers + ["y"],
        "R1": anchors + ["z", "x"] + fillers + ["y"],
        "R2": anchors + ["x"] + fillers + ["y", "z"],
        "R3": anchors + ["y", fillers[0], "z"] + fillers[1:] + ["x"],
    }


def panel(team_sources, query_ids=None):
    qids = query_ids or ["q"]
    orders = fixture()
    groups, runs = {}, {}
    for team, source_names in team_sources.items():
        groups[team] = []
        for index, source in enumerate(source_names):
            name = f"{team}_{index}"
            groups[team].append(name)
            runs[name] = {q: list(orders[source]) for q in qids}
    return build_policies(groups, runs, {q: orders["S"] for q in qids}, qids)


def oracle_head(member_orders, s_order):
    """Independent Fraction expression of normalized fusion, not integer units."""
    s = {d: Fraction(1, 60 + r) for r, d in enumerate(s_order, 1)}
    members = [{d: Fraction(1, 60 + r) for r, d in enumerate(o, 1)} for o in member_orders]
    docs = set(s).union(*members)
    return sorted(docs, key=lambda d: (-(s.get(d, 0) + sum(v.get(d, 0) for v in members)
                                         / len(members)), d))[:10]


def oracle_effect(policies, labels, team=None):
    """Count head relevance directly, without producer coefficients or bounds."""
    totals = []
    for t in [team] if team else policies["teams"]:
        rows = []
        for q in policies["query_ids"]:
            entry = policies["queries"][q]["teams"][t]
            gp = Fraction(sum(labels.get((q, d), 0) > 0 for d in entry["G"]), 10)
            hp = [Fraction(sum(labels.get((q, d), 0) > 0 for d in head), 10)
                  for head in entry["members"].values()]
            rows.append(gp - sum(hp) / len(hp))
        totals.append(sum(rows) / len(rows))
    return sum(totals) / len(totals)


def make_cli_fixture(root, full_depth=100, include_short=True):
    """Export a wholly synthetic29-team/81-source custody bundle for integration."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    inputs = root / "inputs"
    inputs.mkdir()
    qids, f = producer.QUERY_IDS, fixture()

    def write(path, value):
        path = root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def spec(path):
        return {"path": str(path.relative_to(root)), **producer.identity(path)}

    groups, items, receipt_inputs = {}, {}, {}
    for index in range(29):
        team = f"team{index:02}"
        groups[team] = [f"{team}_run{i}" for i in range(2 if index < 6 else 3)]
    extra = [f"extra{i:04}" for i in range(max(0, full_depth - 100))]
    for index, name in enumerate(r for members in groups.values() for r in members):
        source = ("R0", "R3", "R1", "R2")[index % 4]
        lines = []
        for qid in qids:
            order = f[source] + extra
            if include_short and index == 0 and qid == "1":
                order = order[:1]
            for rank, doc in enumerate(order, 1):
                # Canonical score ordering overrides this deliberately shifted metadata.
                lines.append(f"{qid} Q0 {doc} {rank - 1} {len(order) - rank}.0 {name}\n")
        data = "".join(lines).encode("ascii")
        filename = f"{index + 1:03}.run"
        decoded, raw = inputs / filename, inputs / (filename + ".download")
        decoded.write_bytes(data)
        compressed = index == 0
        raw.write_bytes(gzip.compress(data, mtime=0) if compressed else data)
        raw_id, decoded_id = producer.identity(raw), producer.identity(decoded)
        md5 = raw_id["md5"]
        items[name] = {"filename": filename, "publisher_md5": md5, "max_bytes": 16 * 1024 * 1024,
                       "url": "https://ir.nist.gov/trec-covid/archive/round1/" + name}
        receipt_inputs[name] = {**decoded_id, "filename": filename, "raw_filename": raw.name,
                               "raw": raw_id, "gzip": compressed, "publisher_md5": md5,
                               "matched_representation": [key for key, info in (("raw", raw_id), ("expanded", decoded_id))
                                                           if info["md5"] == md5]}
    historical = write("cached/S.json", {"query_ids": qids, "queries": {
        q: {"sources": {"S": {"retained_order": f["S"]}}, "policies": {"S": f["S"][:10]}} for q in qids}})
    prior = write("cached/verification.json", {"status": "passed", "custody": {
        "outputs": {"policies.json": producer.identity(historical)}}})
    inventory = write("cached/inventory.json", {
        "schema": 1, "status": "synthetic metadata feasible", "eligible_teams": 29, "eligible_runs": 81,
        "archive_metadata_team_and_run_match": True, "run_bodies_fetched": False,
        "teams": [{"team": t, "eligible": True, "automatic_runs": list(reversed(names)), "all_runs": names, "exclusion": None}
                  for t, names in groups.items()],
        "runs": [{"run": r, "team": t, "type": "automatic", "publisher_md5": items[r]["publisher_md5"],
                  "url": items[r]["url"]} for t, names in groups.items() for r in names],
    })
    docids = root / "cached/docids.txt"
    docids.write_text("\n".join(f["S"] + extra + ["A.; Bennett", "A.; Bennett"]) + "\n", encoding="ascii")
    qrels = root / "cached/late.qrels"
    lines = []
    for qid in qids:
        lines.extend([f"{qid} 0.5 x 0\n", f"{qid} 5 z 1\n"])
        if int(qid) % 3 == 0:
            lines.append(f"{qid} 5 y 2\n")
    lines.append("1 5 off_inventory 2\n")
    qrels.write_text("".join(lines), encoding="ascii")
    plan = {"schema": 1, "groups": groups, "query_ids": qids, "items": items,
            "inventory": spec(inventory), "S": spec(historical), "prior_verification": spec(prior),
            "docids": spec(docids), "qrels": spec(qrels),
            "timeout_seconds": 60, "max_acquisition_seconds": 900, "max_attempts_per_file": 1, "max_run_count": 180,
            "max_expanded_per_run": 256 * 1024 * 1024, "max_total_expanded_bytes": 1024 * 1024 * 1024,
            "max_total_bytes": 256 * 1024 * 1024}
    for name in (producer.PROTOCOL, producer.SOURCE, producer.TESTS, producer.ACQUIRER,
                 producer.ACQUIRER_TESTS, producer.CHECKER):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic frozen placeholder: " + name + "\n", encoding="ascii")
    write(producer.PLAN, plan)
    frozen = {name: producer.identity(root / name)["sha256"] for name in (
        producer.PROTOCOL, producer.PLAN, producer.SOURCE, producer.TESTS, producer.ACQUIRER,
        producer.ACQUIRER_TESTS, producer.CHECKER)}
    preflight = write("preflight.json", {"schema": 1, "status": "passed", "frozen": frozen})
    acquisition = write("acquisition.json", {"schema": 1, "status": "passed", "frozen": frozen,
                                             "preflight_sha256": producer.identity(preflight)["sha256"],
                                             "plan_sha256": producer.identity(root / producer.PLAN)["sha256"],
                                             "inputs": receipt_inputs,
                                             "transport": {r: {"url": items[r]["url"], "effective_url": items[r]["url"], "http_code": 200,
                                                               "headers": {"Content-Type": "application/octet-stream", "Content-Length": str(v["raw"]["bytes"])}}
                                                           for r, v in receipt_inputs.items()},
                                             "max_attempts_per_file": 1, "byte_limit_sentinel": 1, "elapsed_seconds": 0.0,
                                             "transfer_bytes_complete_bodies": sum(v["raw"]["bytes"] for v in receipt_inputs.values()),
                                             "expanded_bytes_complete_bodies": sum(v["bytes"] for v in receipt_inputs.values())})
    return preflight, inputs, acquisition, root / "output"


class GroupedOutputsTests(unittest.TestCase):
    def test_exact_heads_and_id_tie(self):
        p = panel({"pair": ["R0", "R3"], "triple": ["R0", "R0", "R3"]})
        for t, names in p["groups"].items():
            entry = p["queries"]["q"]["teams"][t]
            source_orders = [p["retained"]["members"][r]["q"] for r in names]
            self.assertEqual(entry["G"], oracle_head(source_orders, fixture()["S"]))
            for r, order in zip(names, source_orders):
                self.assertEqual(entry["members"][r], oracle_head([order], fixture()["S"]))
        self.assertEqual(p["queries"]["q"]["teams"]["pair"]["G"][-1], "z")
        # R0+S ties x and z exactly; x must win by ID, not insertion order.
        self.assertEqual(p["queries"]["q"]["teams"]["pair"]["members"]["pair_0"][-1], "x")

    def test_both_effect_signs_and_no_labels(self):
        p = panel({"t": ["R0", "R3"]})
        for z, xy, expected in [(1, 0, Fraction(1, 10)), (0, 1, Fraction(-1, 10))]:
            labels = {("q", "z"): z, ("q", "x"): xy, ("q", "y"): xy}
            a = analyze(p, labels)
            self.assertEqual(value(a["primary"]["lower"]), expected)
            self.assertEqual(value(a["primary"]["upper"]), expected)
            self.assertEqual(value(a["benchmark_missing_zero"]["G-meanH"]), expected)
        unknown = analyze(p, {})["primary"]
        self.assertEqual((value(unknown["lower"]), value(unknown["upper"])), (Fraction(-1, 10), Fraction(1, 10)))
        self.assertEqual(unknown["unknown_support"], 3)

    def test_sharpness_exhaustive_partial_label_completions(self):
        p = panel({"pair": ["R0", "R3"], "triple": ["R1", "R2", "R2"]})
        pairs = [("q", d) for d in ("x", "y", "z")]
        for grades in product((None, 0, 1), repeat=3):
            labels = {pair: grade for pair, grade in zip(pairs, grades) if grade is not None}
            unknown = [pair for pair in pairs if pair not in labels]
            completions = []
            for bits in product((0, 1), repeat=len(unknown)):
                completions.append(oracle_effect(p, labels | dict(zip(unknown, bits))))
            bounds = analyze(p, labels)["primary"]
            self.assertEqual(value(bounds["lower"]), min(completions))
            self.assertEqual(value(bounds["upper"]), max(completions))

    def test_shared_unknown_opposite_team_coefficients_cancel(self):
        p = panel({"one": ["R0", "R1"], "two": ["R1", "R2"]})
        a = analyze(p, {("q", "x"): 0})
        self.assertEqual(value(a["primary"]["width"]), 0)
        self.assertEqual(a["primary"]["unknown_support"], 0)
        self.assertEqual(a["primary"]["sign"], "zero")
        self.assertEqual(a["primary"]["decision"], "nonpositive")
        lo = sum(value(a["per_team"][t]["G-meanH"]["lower"]) for t in p["teams"]) / 2
        hi = sum(value(a["per_team"][t]["G-meanH"]["upper"]) for t in p["teams"]) / 2
        self.assertEqual((lo, hi), (Fraction(-1, 40), Fraction(1, 40)))
        self.assertTrue(all(value(row["primary"]) == 0 for row in a["pair_coefficients"]))

    def test_fixed_s_context_endpoint_average_is_sharp(self):
        p = panel({"one": ["R0", "R1"], "two": ["R1", "R2"]})
        a = analyze(p, {})
        for endpoint in ("lower", "upper"):
            mean = sum(value(a["per_team"][t]["G-S"][endpoint]) for t in p["teams"]) / 2
            self.assertEqual(value(a["G-S"][endpoint]), mean)

    def test_identical_sources_preserve_multiplicity_and_have_zero_primary(self):
        p = panel({"pair": ["R0", "R0"], "triple": ["R0", "R0", "R0"]})
        self.assertEqual(len(p["retained"]["members"]), 5)
        a = analyze(p, {})
        self.assertEqual(value(a["primary"]["lower"]), 0)
        self.assertEqual(value(a["primary"]["upper"]), 0)
        for q in p["queries"].values():
            for entry in q["teams"].values():
                self.assertTrue(all(head == entry["G"] for head in entry["members"].values()))

    def test_equal_team_weight_is_not_member_weight(self):
        p = panel({"pair": ["R0", "R3"], "triple": ["R1", "R2", "R2"]})
        labels = {("q", "x"): 0, ("q", "y"): 0, ("q", "z"): 1}
        a = analyze(p, labels)
        self.assertEqual(value(a["per_team"]["pair"]["G-meanH"]["known"]), Fraction(1, 10))
        self.assertEqual(value(a["per_team"]["triple"]["G-meanH"]["known"]), Fraction(-1, 30))
        self.assertEqual(value(a["primary"]["known"]), Fraction(1, 30))
        self.assertNotEqual(value(a["primary"]["known"]), Fraction(1, 50))
        self.assertEqual(a["denominators"]["group_size_lcm"], 6)

    def test_same_doc_in_distinct_queries_is_not_one_unknown(self):
        f = fixture()
        p = build_policies({"t": ["a", "b"]},
                           {"a": {"1": f["R0"], "2": f["R1"]},
                            "b": {"1": f["R1"], "2": f["R2"]}},
                           {"1": f["S"], "2": f["S"]}, ["1", "2"])
        a = analyze(p, {})
        self.assertEqual(a["primary"]["unknown_support"], 4)
        self.assertEqual(value(a["primary"]["width"]), Fraction(1, 10))
        for row in a["pair_coefficients"]:
            self.assertEqual(value(row["primary"]), Fraction(row["primary_numerator"], a["denominators"]["primary_mean"]))

    def test_grade_one_and_two_are_equally_positive(self):
        p = panel({"t": ["R0", "R3"]})
        one = analyze(p, {("q", "z"): 1})
        two = analyze(p, {("q", "z"): 2})
        self.assertEqual(one["primary"], two["primary"])
        self.assertEqual(one["benchmark_missing_zero"], two["benchmark_missing_zero"])

    def test_inert_labels_change_only_pair_count(self):
        p = panel({"t": ["R0", "R3"]})
        a, b = analyze(p, {}), analyze(p, {("unused", "outside"): 2})
        a.pop("qrels_pair_count")
        b.pop("qrels_pair_count")
        self.assertEqual(a, b)

    def test_short_member_orders_keep_full_family_weight_and_ten_heads(self):
        f = fixture()
        runs = {"a": {"q": ["new"]}, "b": {"q": ["x", "y"]}}
        p = build_policies({"t": ["a", "b"]}, runs, {"q": f["S"]}, ["q"])
        entry = p["queries"]["q"]["teams"]["t"]
        self.assertEqual(p["queries"]["q"]["retained_depths"], {"S": 100, "members": {"a": 1, "b": 2}})
        self.assertEqual(entry["G"], oracle_head([["new"], ["x", "y"]], f["S"]))
        self.assertEqual(len(set(entry["G"])), 10)
        self.assertEqual(analyze(p, {})["denominators"]["primary_mean"], 20)

    def test_invalid_retained_orders_and_cohorts(self):
        f = fixture()
        good = {"a": {"q": f["R0"]}, "b": {"q": f["R3"]}}
        cases = [[], f["R0"] + ["extra"], f["R0"][:-1] + [f["R0"][0]], ["bad id"]]
        for order in cases:
            runs = deepcopy(good)
            runs["a"]["q"] = order
            with self.assertRaises(ValueError):
                build_policies({"t": ["a", "b"]}, runs, {"q": f["S"]}, ["q"])
        for s in [f["S"][:-1], []]:
            with self.assertRaises(ValueError):
                build_policies({"t": ["a", "b"]}, good, {"q": s}, ["q"])
        for qids in [["q", "q"], ["other"], []]:
            with self.assertRaises(ValueError):
                build_policies({"t": ["a", "b"]}, good, {"q": f["S"]}, qids)

    def test_reject_missing_extra_and_duplicate_run_ids(self):
        f = fixture()
        runs = {"a": {"q": f["R0"]}, "b": {"q": f["R3"]}}
        for groups in [{"t": ["a", "a"]}, {"t": ["a"]}, {"t": ["a", "c"]},
                       {"t": ["a", "b"], "u": ["a", "b"]}]:
            with self.assertRaises(ValueError):
                build_policies(groups, runs, {"q": f["S"]}, ["q"])

    def test_invalid_labels(self):
        p = panel({"t": ["R0", "R3"]})
        for labels in [{("q", "z"): True}, {("q", "z"): 1.0}, {("q", "z"): 3},
                       {"q,z": 1}, {("q", "bad id"): 0}]:
            with self.assertRaises(ValueError):
                analyze(p, labels)

    def test_frozen_head_and_s_replay_validation(self):
        base = panel({"t": ["R0", "R3"]})
        p = deepcopy(base)
        p["queries"]["q"]["S"].reverse()
        with self.assertRaises(ValueError):
            analyze(p, {})
        for bad in [["outside"] * 10, ["outside"] + base["queries"]["q"]["teams"]["t"]["G"][1:]]:
            p = deepcopy(base)
            p["queries"]["q"]["teams"]["t"]["G"] = bad
            with self.assertRaises(ValueError):
                analyze(p, {})
        p = deepcopy(base)
        p["queries"]["q"]["retained_depths"]["members"]["t_0"] = 99
        with self.assertRaises(ValueError):
            analyze(p, {})

    def test_no_input_mutation_and_json_roundtrip(self):
        f = fixture()
        groups = {"t": ["a", "b"]}
        runs, s = {"a": {"q": f["R0"]}, "b": {"q": f["R3"]}}, {"q": f["S"]}
        before = deepcopy((groups, runs, s))
        p = build_policies(groups, runs, s, ["q"])
        frozen = deepcopy(p)
        labels = {("q", "z"): 2}
        a = analyze(p, labels)
        self.assertEqual((groups, runs, s), before)
        self.assertEqual(p, frozen)
        self.assertEqual(json.loads(json.dumps(p)), p)
        self.assertEqual(json.loads(json.dumps(a)), a)
        runs["a"]["q"][0] = "changed"
        self.assertEqual(p, frozen)

    def test_declared_panel_shape_and_denominator(self):
        groups = {f"t{i:02}": ["R0"] * (2 if i < 6 else 3) for i in range(29)}
        p = panel(groups, [str(i) for i in range(1, 31)])
        a = analyze(p, {})
        self.assertEqual(len(p["retained"]["members"]), 81)
        self.assertEqual(a["denominators"], {"group_size_lcm": 6, "primary_mean": 52200,
                                              "primary_per_query": 1740})
        self.assertEqual(value(a["primary"]["width"]), 0)
        self.assertTrue(all(a["checks"].values()))


class ParserAndCustodyTests(unittest.TestCase):
    def test_exact_decimal_order_ties_zero_rank_and_retention(self):
        text = "q Q0 a 0 1.00000000000000000000000000001 run\nq Q0 b 1 1.00000000000000000000000000002 run\n"
        got = producer.parse_run(text, {"a", "b"}, "run", ["q"])["queries"]["q"]
        self.assertEqual(got["retained_order"], ["b", "a"])
        self.assertEqual(got["supplied_rank_disagreements"], 1)
        text = "q Q0 b 0 1.0 run\nq Q0 a 1 1 run\n"
        got = producer.parse_run(text, {"a", "b"}, "run", ["q"])["queries"]["q"]
        self.assertEqual(got["retained_order"], ["a", "b"])
        self.assertEqual((got["tie_groups"], got["tied_documents"], got["tie_excess"]), (1, 2, 1))
        aliases = producer.parse_run("q Q0 a +001 1 run\nq Q0 b 000 0 run\n", {"a", "b"}, "run", ["q"])
        self.assertEqual([d["supplied_rank"] for d in aliases["queries"]["q"]["retained_details"]], [1, 0])
        docs = [f"d{i:04}" for i in range(1000)]
        text = "".join(f"q Q0 {doc} {i} {-i} run\n" for i, doc in enumerate(docs))
        got = producer.parse_run(text, set(docs), "run", ["q"])["queries"]["q"]
        self.assertEqual((got["full_depth"], got["retained_depth"]), (1000, 100))
        self.assertEqual(got["retained_order"], docs[:100])

    def test_run_rejections(self):
        valid = "q Q0 a 0 1 run\n"
        bad = [valid * 2, valid.replace(" 1 run", " NaN run"), valid.replace(" 1 run", " Infinity run"),
               valid.replace(" 0 ", " -1 "), valid.replace(" 0 ", " 0.0 "), valid.replace(" 0 ", " ١ "), valid.replace("run", "wrong"),
               valid.replace("q ", "other "), valid.replace(" a ", " outside "), "q Q0 a 0 1\n", ""]
        for text in bad:
            with self.assertRaises(ValueError):
                producer.parse_run(text, {"a"}, "run", ["q"])
        text = "".join(f"q Q0 d{i} {i} 1 run\n" for i in range(1001))
        with self.assertRaises(ValueError):
            producer.parse_run(text, {f"d{i}" for i in range(1001)}, "run", ["q"])

    def test_opaque_inventory_and_inert_qrels(self):
        ids = producer.parse_docids("a\nA.; Bennett\nA.; Bennett\n")
        self.assertEqual(ids, {"a", "A.; Bennett"})
        self.assertNotIn("Bennett", ids)
        for text in ["", "a\n\n", "a\r\n", "a\v", "a\f", "a\x00", "é\n", " \n"]:
            with self.assertRaises(ValueError):
                producer.parse_docids(text)
        labels = producer.parse_qrels("q 0.5 outside 2\nq 1 a 0\n", ["q"])
        self.assertEqual(labels, {("q", "outside"): 2, ("q", "a"): 0})
        for text in ["q 0 a 1\n", "q NaN a 1\n", "q 1 a 3\n", "q 1 a 0\nq 2 a 1\n", ""]:
            with self.assertRaises(ValueError):
                producer.parse_qrels(text, ["q"])

    def test_complete_cli_custody_and_label_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_cli_fixture(tmp)
            original = producer.parse_qrels

            def checked(text, query_ids=producer.QUERY_IDS):
                self.assertTrue((paths[3] / "policies.json").exists())
                self.assertTrue((paths[3] / "sources.json").exists())
                return original(text, query_ids)

            with patch.object(producer, "ROOT", Path(tmp)), patch.object(producer, "parse_qrels", checked):
                manifest = producer.execute(*paths)
            self.assertEqual(manifest["tracked_before"], manifest["tracked_after"])
            self.assertEqual(manifest["labels_joined_after_policies_sha256"], manifest["outputs"]["policies.json"]["sha256"])
            self.assertTrue((paths[3] / "success.json").exists())
            before = (paths[3] / "success.json").read_bytes()
            with patch.object(producer, "ROOT", Path(tmp)), self.assertRaises(FileExistsError):
                producer.execute(*paths)
            self.assertEqual((paths[3] / "success.json").read_bytes(), before)

    def test_identity_failure_precedes_any_parser(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_cli_fixture(tmp)
            with (Path(tmp) / producer.SOURCE).open("a") as handle:
                handle.write("changed")
            with patch.object(producer, "ROOT", Path(tmp)), patch.object(producer, "parse_run") as parse:
                with self.assertRaises(ValueError):
                    producer.execute(*paths)
                parse.assert_not_called()
            failure = json.loads((paths[3] / "failure.json").read_text())
            self.assertEqual(failure["stage"], "custody")
            self.assertFalse((paths[3] / "policies.json").exists())

    def test_label_failure_preserves_frozen_policies(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_cli_fixture(tmp)
            with patch.object(producer, "ROOT", Path(tmp)), patch.object(producer, "parse_qrels", side_effect=ValueError("synthetic invalid grade")):
                with self.assertRaises(ValueError):
                    producer.execute(*paths)
            self.assertTrue((paths[3] / "policies.json").exists())
            self.assertFalse((paths[3] / "analysis.json").exists())
            self.assertEqual(json.loads((paths[3] / "failure.json").read_text())["stage"], "labels")

    def test_after_hash_detects_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_cli_fixture(tmp)
            original = producer.analyze

            def mutate(policies, labels):
                result = original(policies, labels)
                with (paths[1] / "001.run").open("a") as handle:
                    handle.write("changed")
                return result

            with patch.object(producer, "ROOT", Path(tmp)), patch.object(producer, "analyze", mutate):
                with self.assertRaisesRegex(ValueError, "bytes changed"):
                    producer.execute(*paths)
            self.assertTrue((paths[3] / "failure.json").exists())
            self.assertFalse((paths[3] / "success.json").exists())


if __name__ == "__main__":
    unittest.main()
