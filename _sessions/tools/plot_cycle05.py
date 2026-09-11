#!/usr/bin/env python3
"""Export selected empirical probabilities; optional matplotlib, no model calls."""
from fractions import Fraction
import json
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '_sessions/local/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = ROOT / 'results/cycle05-replication-2026-09-10'
fixture = json.loads((ROOT / 'results/cycle05-2026-09-10/prepared/fixture.json').read_text())
scores = json.loads((BASE / 'scored/scores.json').read_text())
if scores['status'] != 'complete':
    raise ValueError('this figure requires the complete fixed diagnostic set')
predictions = {r['packet_id']: float(Fraction(r['p_positive'])) for r in scores['packets']}
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6), sharey=True)
plotted = []
for ax, ps in zip(axes, ('11/20', '17/20')):
    pairs = {p['arm']: p for p in fixture['pairs'] if p['p_specialist'] == ps and p['generalist_sign'] == 1}
    for j, arm in enumerate(('padded', 'copied', 'independent')):
        p = pairs[arm]
        for offset, view, color in ((-.16, 'blind', '#69778c'), (.16, 'aware', '#007c83')):
            value = predictions[p[view + '_packet_id']]
            ax.bar(j + offset, value, .29, color=color, label=view.title() if j == 0 else None)
            ax.text(j + offset, value + .022, f'{value:.3f}', ha='center', fontsize=9)
            plotted.append({'p_specialist': ps, 'arm': arm, 'view': view,
                            'packet_id': p[view + '_packet_id'], 'p_positive': value})
    ax.axhline(.5, color='#6b4d42', linestyle='--', linewidth=1)
    ax.set_title(f'Specialist accuracy {float(Fraction(ps)):.0%}', fontsize=12)
    ax.set_xticks(range(3), ['One G + padding', 'Three copies', 'Three independent G'])
    ax.tick_params(axis='x', labelsize=9)
    ax.set_ylim(0, 1.03)
    ax.spines[['top', 'right']].set_visible(False)
axes[0].set_ylabel('Returned probability of positive truth')
axes[1].legend(frameon=False, loc='upper right')
fig.suptitle('The coordinator used supplied lineage to interpret agreement', fontsize=14)
fig.text(.5, .015, 'Shown: positive generalists oppose a negative specialist. Dashed line: decision threshold.\n'
         'One response per unique input; supplied calibration and true lineage. No uncertainty intervals.',
         ha='center', fontsize=9)
fig.tight_layout(rect=(0, .095, 1, .94))
fig.savefig(BASE / 'coordinator_probabilities.png', dpi=180)
fig.savefig(BASE / 'coordinator_probabilities.svg')
plt.close(fig)
svg = BASE / 'coordinator_probabilities.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
(BASE / 'plotted_values.json').write_text(json.dumps(plotted, indent=2) + '\n')
