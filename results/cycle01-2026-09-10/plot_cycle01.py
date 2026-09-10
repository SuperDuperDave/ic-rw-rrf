#!/usr/bin/env python3
"""Render the saved cycle01 summaries; does not rerun or modify experiments.

Run from any directory: python3 -B /path/to/plot_cycle01.py
Uses the already-installed matplotlib; writes only overview.svg / overview.png
beside this script. Temporary matplotlib caches are removed after rendering.
The SVG description and PNG metadata retain exact plotted values and input hashes.
"""

import hashlib
import json
import math
import os
from pathlib import Path
import tempfile


CONFIGURATIONS = ((2019, 4), (2019, 5), (2019, 6), (2019, 7), (2020, 4))
TITLE = "Rank-fusion calibration and candidate depth"
BLUE = "#245B78"
ORANGE = "#B95F21"
INK = "#243442"
MUTED = "#536472"


def load_plot_data(directory):
    sources = {}
    summaries = {}
    for name in ("geometry", "tail"):
        relative = name + "/summary.json"
        raw = (directory / relative).read_bytes()
        sources[relative] = hashlib.sha256(raw).hexdigest()
        data = json.loads(raw)
        rows = data["summaries"]
        index = {(row["year"], len(row["rankers"])): row for row in rows}
        if len(index) != len(rows) or set(index) != set(CONFIGURATIONS):
            raise ValueError("unexpected or duplicate configurations in " + relative)
        summaries[name] = index

    plotted = []
    for year, n_rankers in CONFIGURATIONS:
        geometry = summaries["geometry"][(year, n_rankers)]
        tail = summaries["tail"][(year, n_rankers)]
        expected_queries = 43 if year == 2019 else 54
        if geometry["n_queries"] != expected_queries or tail["n_queries"] != expected_queries:
            raise ValueError("query counts changed; revise the figure annotations")
        row = {
            "year": year,
            "n_rankers": n_rankers,
            "n_queries": expected_queries,
            "k60": geometry["means"]["k60"],
            "selected_k": geometry["means"]["selected_k"],
        }
        for arm_name in ("full", "top30_cap"):
            arm = tail["depth_arms"][arm_name]
            paired = arm["k200_minus_k60"]
            interval = paired["conditional_query_bootstrap_95"]
            point = paired["mean_delta"]
            if (len(interval) != 2 or not interval[0] <= point <= interval[1]
                    or not all(math.isfinite(value) for value in interval + [point])):
                raise ValueError("invalid saved interval")
            if not math.isclose(point, arm["mean_ndcg10_k200"] - arm["mean_ndcg10_k60"],
                                rel_tol=0, abs_tol=1e-12):
                raise ValueError("saved mean and paired difference disagree")
            row[arm_name] = {"mean_delta": point, "conditional_query_bootstrap_95": interval}
        plotted.append(row)
    return {"source_sha256": sources, "rows": plotted}


def make_figure(data, plt):
    """Build the two panels; artist IDs support independent numeric checking."""
    from matplotlib.ticker import FormatStrFormatter

    fig, axes = plt.subplots(1, 2, figsize=(12, 6.4), dpi=100)
    fig.subplots_adjust(left=0.09, right=0.98, bottom=0.33, top=0.77, wspace=0.39)
    fig.text(0.035, 0.955, TITLE, fontsize=20, weight="bold", color=INK)
    fig.text(0.035, 0.91,
             "Cycle 01  |  TREC Deep Learning 2019–2020  |  Exploratory development evidence",
             fontsize=10.5, color=MUTED)
    fig.text(0.09, 0.851, "A   Training-selected k vs fixed k=60", fontsize=12.5,
             weight="bold", color=INK)
    fig.text(0.608, 0.851, "B   k effect under depth truncation", fontsize=12.5,
             weight="bold", color=INK)

    labels = ["{} · n={}".format(row["year"], row["n_rankers"]) for row in data["rows"]]
    for ax in axes:
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=10, color=INK)
        ax.set_ylim(4.55, -0.55)
        ax.set_axisbelow(True)
        ax.grid(axis="x", color="#E2E7EB", linewidth=0.7)
        ax.axhline(3.5, color="#CDD5DB", linewidth=0.9, linestyle=(0, (3, 3)))
        ax.tick_params(axis="both", length=0, labelcolor=MUTED, pad=7)
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
        ax.spines["bottom"].set_color("#B8C3CB")

    left, right = axes
    for y, row in enumerate(data["rows"]):
        key = "{}-{}".format(row["year"], row["n_rankers"])
        left.plot([row["k60"], row["selected_k"]], [y, y], color="#AEBBC5", linewidth=1.6)
        for method, color, marker, offset, label in (
                ("k60", BLUE, "o", -16, "Fixed k=60"),
                ("selected_k", ORANGE, "s", 11, "Training-selected k")):
            line, = left.plot([row[method]], [y], marker=marker, markersize=6,
                              color=color, linestyle="none", zorder=3,
                              label=label if y == 0 else None)
            line.set_gid("geometry-{}-{}".format(method, key))
            left.annotate("{:.4f}".format(row[method]), (row[method], y),
                          xytext=(0, offset), textcoords="offset points",
                          ha="center", va="center", color=color, fontsize=9)
        for arm, color, marker, offset, label in (
                ("full", BLUE, "o", -0.13, "Full source lists"),
                ("top30_cap", ORANGE, "s", 0.13, "Top 30 per source")):
            value = row[arm]["mean_delta"]
            low, high = row[arm]["conditional_query_bootstrap_95"]
            container = right.errorbar(value, y + offset,
                                       xerr=[[value - low], [high - value]],
                                       fmt=marker, color=color, markersize=5.5,
                                       elinewidth=1.35, capsize=3, capthick=1.1,
                                       label=label if y == 0 else None, zorder=3)
            container.lines[0].set_gid("tail-{}-{}".format(arm, key))
            container.lines[2][0].set_gid("tail-{}-{}-interval".format(arm, key))

    left.set_xlim(0.33, 0.47)
    left.set_xticks([0.34, 0.36, 0.38, 0.40, 0.42, 0.44, 0.46])
    left.xaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    left.set_xlabel("Mean held-out nDCG@10 · full source lists", fontsize=10.5,
                    color=INK, labelpad=13)
    right.set_xlim(-0.02, 0.04)
    right.set_xticks([-0.02, -0.01, 0, 0.01, 0.02, 0.03, 0.04])
    right.xaxis.set_major_formatter(FormatStrFormatter("%+.2f"))
    right.axvline(0, color="#85939D", linewidth=1, linestyle=(0, (4, 3)), zorder=1)
    right.set_xlabel("Δ nDCG@10 (k=200 − k=60)", fontsize=10.5, color=INK, labelpad=13)
    for ax in axes:
        ax.legend(loc="lower left", bbox_to_anchor=(-0.02, 1.01), ncol=2,
                  frameon=False, fontsize=9, handletextpad=0.5, columnspacing=1.1)

    notes = (
        (0.208, "2019: the same 43 queries across n=4–7. 2020: 54 queries (n=4). n = number of rankers."),
        (0.168, "Selected k: training folds only; query-level held-out scores averaged over five seeds of five-fold CV."),
        (0.128, "Whiskers (B): conditional 95% query-bootstrap intervals; predictions fixed, not confirmatory."),
        (0.088, "Reused development data. Truncation changes evidence/candidates; attenuation does not isolate a causal mechanism."),
    )
    for y, note in notes:
        fig.text(0.035, y, note, fontsize=9.2, color=MUTED)
    fig.text(0.035, 0.035, "Source: cycle01 geometry/summary.json + tail/summary.json  ·  2026-09-10",
             fontsize=8.5, color="#697985")
    return fig


def main():
    directory = Path(__file__).resolve().parent
    data = load_plot_data(directory)
    previous_config = os.environ.get("MPLCONFIGDIR")
    try:
        with tempfile.TemporaryDirectory(prefix="cycle01-mpl-") as cache:
            os.environ["MPLCONFIGDIR"] = cache
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10,
                                 "svg.fonttype": "none", "svg.hashsalt": "icrrf-cycle01",
                                 "figure.facecolor": "white", "axes.facecolor": "white"}):
                fig = make_figure(data, plt)
                description = json.dumps(data, sort_keys=True)
                svg = directory / "overview.svg"
                png = directory / "overview.png"
                fig.savefig(svg, metadata={"Title": TITLE, "Description": description,
                                           "Creator": "plot_cycle01.py", "Date": None})
                fig.savefig(png, dpi=100, metadata={"Title": TITLE, "Description": description})
                plt.close(fig)
                print(svg)
                print(png)
    finally:
        if previous_config is None:
            os.environ.pop("MPLCONFIGDIR", None)
        else:
            os.environ["MPLCONFIGDIR"] = previous_config


if __name__ == "__main__":
    main()
