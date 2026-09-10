#!/usr/bin/env python3
"""Plot saved cycle03 intervals; requires optional matplotlib, no recomputation.

Read association/summary.json beside this file. Emit association.png/.svg here.
Both figures embed the exact plotted values and source/script SHA256 identities.
"""

import hashlib
import json
import os
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parent
INK, MUTED, TEAL, PALE = '#243442', '#586a78', '#267786', '#b7ccd1'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_data():
    path = ROOT / 'association/summary.json'
    result = json.loads(path.read_text())
    rows = []
    for outcome, title in [('grade_ge_2', 'Primary: relevance grade ≥2'),
                           ('grade_gt_0', 'Sensitivity: relevance grade >0')]:
        for year in ('2019', '2020'):
            annual = result['years'][year]
            value = annual['outcomes'][outcome]
            sharp = value['empirical_sharp_interval']
            envelope = value['bootstrap']['exploratory_uncertainty_envelope']
            assert -1 <= sharp['lower'] <= sharp['upper'] <= 1
            assert -1 <= envelope['lower'] <= envelope['upper'] <= 1
            rows.append({'year': year, 'outcome': outcome, 'title': title,
                         'n_queries': annual['n_queries_eligible'],
                         'sharp': [sharp['lower'], sharp['upper']],
                         'envelope': [envelope['lower'], envelope['upper']]})
    return {'rows': rows, 'source_sha256': digest(path),
            'script_sha256': digest(__file__), 'decision_delta': 0.10}


def main():
    data = load_data()
    previous = os.environ.get('MPLCONFIGDIR')
    try:
        with tempfile.TemporaryDirectory(prefix='cycle03-plot-') as cache:
            os.environ['MPLCONFIGDIR'] = cache
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from matplotlib.lines import Line2D

            data['matplotlib_version'] = matplotlib.__version__
            with plt.rc_context({'font.family': 'DejaVu Sans', 'font.size': 11,
                                 'svg.fonttype': 'none', 'svg.hashsalt': 'icrrf-cycle03',
                                 'figure.facecolor': 'white', 'axes.facecolor': 'white'}):
                fig, axes = plt.subplots(2, 1, figsize=(12, 8.5), sharex=True)
                fig.subplots_adjust(left=0.18, right=0.96, top=0.78, bottom=0.27, hspace=0.6)
                fig.suptitle('Specialist relevance: what the missing labels permit',
                             x=0.06, y=0.96, ha='left', fontsize=19, fontweight='bold', color=INK)
                fig.text(0.06, 0.903, 'Cycle 03  |  Fixed SPLADE++ specialists  |  Separate annual query panels',
                         color=MUTED, fontsize=11)
                legend = [Line2D([0], [0], color=TEAL, linewidth=8, label='Finite-panel sharp interval'),
                          Line2D([0], [0], color=PALE, linewidth=3, marker='|', markersize=10,
                                 label='Exploratory bootstrap envelope')]
                fig.legend(handles=legend, loc='upper left', bbox_to_anchor=(0.06, 0.874),
                           ncol=2, frameon=False, labelcolor=INK)
                for ax, subset in zip(axes, (data['rows'][:2], data['rows'][2:])):
                    ax.set_title(subset[0]['title'], loc='left', color=INK, fontweight='bold', pad=16)
                    ax.axvspan(-10, 10, color='#f0f2f3', zorder=0)
                    ax.axvline(0, color=MUTED, linewidth=1)
                    for delta in (-10, 10):
                        ax.axvline(delta, color='#9babb4', linewidth=0.8, linestyle='--')
                    labels = []
                    for y, row in zip((1, 0), subset):
                        lo, hi = [v * 100 for v in row['envelope']]
                        sl, su = [v * 100 for v in row['sharp']]
                        ax.plot([lo, hi], [y, y], color=PALE, linewidth=3, zorder=2)
                        ax.plot([lo, hi], [y, y], '|', color=MUTED, markersize=13, zorder=3)
                        ax.plot([sl, su], [y, y], color=TEAL, linewidth=8, solid_capstyle='butt', zorder=4)
                        ax.text((sl + su) / 2, y + 0.24, f'[{sl:+.1f}, {su:+.1f}] pp',
                                color=TEAL, ha='center', fontsize=10)
                        labels.append(f"{row['year']}  ·  {row['n_queries']} queries")
                    ax.set_yticks([1, 0], labels)
                    ax.set_ylim(-0.55, 1.6)
                    ax.tick_params(axis='both', length=0, labelcolor=INK, pad=9)
                    for edge in ('top', 'left', 'right'):
                        ax.spines[edge].set_visible(False)
                    ax.spines['bottom'].set_color('#c6d0d6')
                    ax.grid(axis='x', color='#e7ecef', linewidth=0.7)
                    ax.set_axisbelow(True)
                lo = min(-15, min(r['envelope'][0] * 100 for r in data['rows']) - 5)
                hi = max(15, max(r['envelope'][1] * 100 for r in data['rows']) + 5)
                axes[1].set_xlim(lo, hi)
                axes[1].set_xlabel('Supported minus isolated relevance rate (percentage points)', color=INK, labelpad=13)
                notes = [
                    'Gray band: ±10 percentage points, the prespecified research decision threshold.',
                    'Sharp intervals allow every missing label to favor the opposite group. Query contrasts have equal weight.',
                    'The bootstrap envelope adds conditional query-sampling uncertainty; it is not an exact confidence guarantee.',
                    'Association does not isolate candidate access from corroboration or demonstrate a fusion gain.',
                    'The secondary threshold is descriptive and cannot override the primary decision.',
                ]
                for y, note in zip((0.18, 0.147, 0.114, 0.081, 0.048), notes):
                    fig.text(0.06, y, note, color=MUTED, fontsize=9.2)
                assert digest(ROOT / 'association/summary.json') == data['source_sha256']
                for suffix in ('png', 'svg'):
                    metadata = {'Title': 'Cycle03 specialist relevance association',
                                'Description': json.dumps(data, sort_keys=True)}
                    if suffix == 'svg':
                        metadata.update({'Date': None, 'Creator': 'plot_association.py'})
                    path = ROOT / ('association.' + suffix)
                    fig.savefig(path, dpi=180, metadata=metadata)
                    if suffix == 'svg':
                        path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines()) + '\n')
                    print(path)
                plt.close(fig)
    finally:
        if previous is None:
            os.environ.pop('MPLCONFIGDIR', None)
        else:
            os.environ['MPLCONFIGDIR'] = previous


if __name__ == '__main__':
    main()
