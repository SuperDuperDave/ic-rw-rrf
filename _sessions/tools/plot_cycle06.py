#!/usr/bin/env python3
"""Plot scored cycle06 probabilities; optional matplotlib, no provider calls."""
from fractions import Fraction
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/cycle06-2026-09-10'
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '_sessions/local/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    scores = json.loads((BASE / 'scored/scores.json').read_text())
    rows = scores['packets']
    fig, axes = plt.subplots(2, 2, figsize=(10, 7.8), sharey=True)
    plotted = []
    configurations = [(sign, reliability) for sign in (1, -1) for reliability in ('11/20', '17/20')]
    for ax, (sign, reliability) in zip(axes.flat, configurations):
        tick_labels = []
        for position, hint in enumerate(('copied', 'independent')):
            row = next(r for r in rows if r['p_specialist'] == reliability and r['noisy_lineage_hint'] == hint and r['generalist_sign'] == sign)
            points = [('blind', row['comparators']['blind']['p_positive'], -.12, '#8792a2', 's'),
                      ('naive_hint_trust', row['comparators']['naive_hint_trust']['p_positive'], 0, '#b37c4f', '^'),
                      ('noisy_bayes', row['reference_p_positive'], .12, '#007b83', 'o'),
                      ('model', row['p_positive'], .12, '#111111', 'x')]
            for policy, raw, offset, color, marker in points:
                if raw is None:
                    continue
                value = float(Fraction(raw))
                label = {'blind': 'Ignore hint (exact)', 'naive_hint_trust': 'Trust hint (exact)',
                         'noisy_bayes': 'Use hint uncertainty (exact)', 'model': 'Returned probability'}[policy]
                ax.scatter(position + offset, value, color=color, marker=marker,
                           s=76 if policy == 'model' else 66, label=label if position == 0 else None,
                           zorder=5 if policy == 'model' else 3)
                plotted.append({'packet_id': row['packet_id'], 'policy': policy, 'p_positive': raw})
            if row['p_positive'] is not None:
                ax.annotate(f"{float(Fraction(row['p_positive'])):.3f}",
                            (position + .12, float(Fraction(row['p_positive']))),
                            xytext=(7, 7), textcoords='offset points', fontsize=9)
            status = {'valid': 'Valid', 'invalid': 'Refused', 'missing': 'Not sent'}[row['status']]
            tick_labels.append(f'Hint: {hint}\n{status}')
        ax.axhline(.5, color='#9a8783', linestyle='--', linewidth=1)
        direction = 'positive' if sign == 1 else 'negative'
        ax.set_title(f'Specialist {float(Fraction(reliability)):.0%}; generalists {direction}')
        ax.set_xticks((0, 1), tick_labels)
        ax.set_xlim(-.4, 1.45)
        ax.set_ylim(0, 1)
        ax.spines[['top', 'right']].set_visible(False)
    for ax in axes[:, 0]:
        ax.set_ylabel('Probability of positive truth')
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(.5, .055), ncol=2, frameon=False, fontsize=9)
    fig.suptitle('Noisy provenance: incomplete experiment (3 of 8 valid)', fontsize=14)
    fig.text(.5, .012, 'Generalists oppose the specialist. Colored points are theoretical; black crosses are valid returned probabilities.',
             ha='center', fontsize=8.5)
    fig.tight_layout(rect=(0, .14, 1, .95))
    fig.savefig(BASE / 'noisy_lineage.png', dpi=180)
    fig.savefig(BASE / 'noisy_lineage.svg')
    plt.close(fig)
    svg = BASE / 'noisy_lineage.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
    (BASE / 'plotted_values.json').write_text(json.dumps(plotted, indent=2) + '\n')


if __name__ == '__main__':
    main()
