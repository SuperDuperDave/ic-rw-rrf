#!/usr/bin/env python3
"""Plot saved exact cycle04 mixtures; optional matplotlib, no experiment rerun."""

from fractions import Fraction
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parent
LABELS = {
    'naive_report_independence': 'Treat every report as independent',
    'payload_quotient': 'Merge matching generalist answers',
    'optimal_blind_bayes': 'Optimal Bayes: lineage hidden',
    'equal_root_weighting': 'Equal weight per known root',
    'optimal_aware_bayes': 'Optimal Bayes: lineage supplied',
    'protected_minority': 'Protect the disagreeing specialist',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    source = ROOT / 'exact/summary.json'
    summary = json.loads(source.read_text())
    names = summary['policy_order']
    values = {ps: {name: {metric: summary['mixtures'][ps]['policies'][name][metric]
                         for metric in ('brier_loss', 'classification_error')}
                   for name in names} for ps in ('11/20', '17/20')}
    meta = {'source_sha256': sha(source), 'script_sha256': sha(__file__),
            'exact_values': values, 'policy_order': names,
            'mixture': 'equal padded/copied/independent; separate known pS settings'}
    old_cache = os.environ.get('MPLCONFIGDIR')
    try:
        with tempfile.TemporaryDirectory(prefix='cycle04-plot-') as cache:
            os.environ['MPLCONFIGDIR'] = cache
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from matplotlib.ticker import PercentFormatter

            meta['matplotlib_version'] = matplotlib.__version__
            with plt.rc_context({'font.family': 'DejaVu Sans', 'font.size': 10,
                                 'svg.fonttype': 'none', 'svg.hashsalt': 'icrrf-cycle04'}):
                fig, axes = plt.subplots(2, 2, figsize=(14, 9.5))
                fig.subplots_adjust(left=.29, right=.95, top=.82, bottom=.22,
                                    wspace=.20, hspace=.55)
                fig.suptitle('Agreement, evidence origin, and useful dissent',
                             x=.04, y=.96, ha='left', fontsize=20, weight='bold', color='#243442')
                fig.text(.04, .912, 'Cycle 04  |  Exact known-truth fixture  |  Lower loss and error are better',
                         color='#586a78', fontsize=12)
                colors = ['#b4c2cb', '#b4c2cb', '#586a78', '#b4c2cb', '#267786', '#c48243']
                for row, metric in enumerate(('brier_loss', 'classification_error')):
                    maxval = max(float(Fraction(values[ps][name][metric]))
                                 for ps in values for name in names)
                    for col, ps in enumerate(('11/20', '17/20')):
                        ax = axes[row, col]
                        numbers = [float(Fraction(values[ps][name][metric])) for name in names]
                        ax.barh(range(len(names)), numbers, color=colors, height=.63)
                        ax.set_yticks(range(len(names)), [LABELS[n] for n in names] if col == 0 else ['']*len(names))
                        ax.invert_yaxis()
                        ax.set_xlim(0, maxval * 1.24)
                        ax.set_axisbelow(True)
                        ax.grid(axis='x', color='#e7ecef')
                        ax.tick_params(axis='both', length=0, pad=7, labelcolor='#243442')
                        for spine in ax.spines.values():
                            spine.set_visible(False)
                        for index, value in enumerate(numbers):
                            exact = Fraction(values[ps][names[index]][metric])
                            decimal = Decimal(exact.numerator) / Decimal(exact.denominator)
                            label = (str(decimal.quantize(Decimal('.0001'), rounding=ROUND_HALF_UP)) if row == 0
                                     else str((100*decimal).quantize(Decimal('.001'), rounding=ROUND_HALF_UP))+'%')
                            ax.text(value + maxval*.025, index, label, va='center', fontsize=9, color='#243442')
                        title = ('Weak specialist: 55% accuracy' if col == 0 else 'Strong specialist: 85% accuracy')
                        ax.set_title(title if row == 0 else '', loc='left', pad=14, weight='bold', color='#243442')
                        ax.set_xlabel('Expected Brier loss' if row == 0 else 'Expected classification error', color='#243442')
                        if row:
                            ax.xaxis.set_major_formatter(PercentFormatter(1))
                notes = [
                    'Each panel averages the three constructions equally; all policies know source reliability and the construction mixture.',
                    'Teal and equal-root policies receive trusted lineage. Its acquisition cost is not modeled.',
                    'Padded / copied / independent arms acquire 2 / 2 / 4 primitive readings; each has four report slots.',
                    'Exact finite-world expectations, not measured LLM performance. Full per-cell results and rational values accompany the figure.',
                ]
                for y, note in zip((.15, .117, .084, .051), notes):
                    fig.text(.04, y, note, color='#586a78', fontsize=10)
                assert sha(source) == meta['source_sha256']
                for suffix in ('png', 'svg'):
                    metadata = {'Title': 'Cycle04 known-truth evidence experiment',
                                'Description': json.dumps(meta, sort_keys=True)}
                    if suffix == 'svg':
                        metadata.update(Date=None, Creator='plot_known_truth.py')
                    target = ROOT / ('known_truth.' + suffix)
                    fig.savefig(target, dpi=180, metadata=metadata)
                    if suffix == 'svg':
                        target.write_text('\n'.join(line.rstrip() for line in target.read_text().splitlines())+'\n')
                    print(target)
                plt.close(fig)
    finally:
        if old_cache is None:
            os.environ.pop('MPLCONFIGDIR', None)
        else:
            os.environ['MPLCONFIGDIR'] = old_cache


if __name__ == '__main__':
    main()
