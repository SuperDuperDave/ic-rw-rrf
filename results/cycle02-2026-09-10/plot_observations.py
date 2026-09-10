#!/usr/bin/env python3
"""Plot frozen cycle02 observations; never run or modify the numerical audit.

From any directory: python3 -B /path/to/plot_observations.py
Requires matplotlib; creates only observations.png and observations.svg beside
this script. Temporary plotting caches are removed. Figure metadata records the
input SHA256, exact plotted counts, script hash, and matplotlib version.
"""

import hashlib
import json
import os
from pathlib import Path
import tempfile


TITLE = 'Judgment availability and candidate access'
INK = '#243442'
MUTED = '#586A78'
JUDGED = '#267786'
UNJUDGED = '#DBAC83'
EXISTING = '#DCE3E7'
YEARS = ('2019', '2020')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_counts(row):
    fields = ('n_candidates', 'n_judged', 'n_unjudged')
    if any(type(row[key]) is not int or row[key] < 0 for key in fields):
        raise ValueError('saved counts must be nonnegative integers')
    if row['n_judged'] + row['n_unjudged'] != row['n_candidates']:
        raise ValueError('saved judgment counts do not add to candidate count')
    return {key: row[key] for key in fields}


def load_plot_data(directory):
    relative = 'observations/summary.json'
    path = directory / relative
    raw = path.read_bytes()
    summary = json.loads(raw)
    if set(summary['years']) != set(YEARS):
        raise ValueError('expected the two frozen TREC DL years')
    if summary['source_id'] != 'splade_pp_ensemble_distil':
        raise ValueError('figure source label must match the frozen source identity')
    rows = []
    for year in YEARS:
        annual = summary['years'][year]
        full = annual['arms']['full']
        owners = full['owners']['fixed_cohort']
        row = {'year': year, 'n_queries': annual['n_eligible_queries'], 'owners': {}}
        for name in ('new_source', 'pooled_lexical'):
            owner = owners[name]
            paired = owner['eligibility']['with_judged_both_groups']
            if owner['n_queries_total'] != row['n_queries'] or paired['n_queries'] != len(paired['qids']):
                raise ValueError('saved query denominators disagree')
            row['owners'][name] = {
                'groups': {group: validate_counts(owner['groups'][group])
                           for group in ('tail_supported', 'isolated')},
                'n_queries_judged_both_groups': paired['n_queries'],
            }
        row['outside_top10'] = validate_counts(full['new_source_top10_outside_lexical_full_union'])
        row['whole_top10'] = validate_counts(full['source_judgment_coverage'][summary['source_id']]['top10'])
        if row['whole_top10']['n_candidates'] != 10 * row['n_queries']:
            raise ValueError('top10 denominator is not ten documents per eligible query')
        if row['outside_top10']['n_candidates'] > row['whole_top10']['n_candidates']:
            raise ValueError('outside candidates cannot exceed the complete top10')
        rows.append(row)
    return {'source_sha256': {relative: hashlib.sha256(raw).hexdigest()},
            'source_id': summary['source_id'], 'rows': rows}


def axis_style(ax):
    ax.set_axisbelow(True)
    ax.grid(axis='x', color='#E5EAED', linewidth=0.7)
    for name in ('top', 'right', 'left'):
        ax.spines[name].set_visible(False)
    ax.spines['bottom'].set_color('#BCC7CE')
    ax.tick_params(axis='both', length=0, pad=8, colors=MUTED)


def make_figure(data, plt):
    from matplotlib.patches import Patch

    fig = plt.figure(figsize=(15, 9.3), dpi=150)
    left = fig.add_axes([0.197, 0.292, 0.397, 0.48])
    right = fig.add_axes([0.681, 0.573, 0.277, 0.193])
    table = fig.add_axes([0.669, 0.295, 0.30, 0.205])
    fig.text(0.035, 0.946, TITLE, fontsize=23, color=INK, weight='bold')
    fig.text(0.035, 0.902, 'Cycle 02  |  TREC Deep Learning 2019–2020  |  Frozen full-list observation inventory',
             fontsize=11, color=MUTED)
    fig.text(0.035, 0.852, 'A   Specialist candidates by owner and support', fontsize=13, color=INK, weight='bold')
    fig.text(0.669, 0.852, 'B   Beyond the retained lexical rankings', fontsize=13, color=INK, weight='bold')
    fig.text(0.669, 0.815, 'SPLADE++ top10 against the original lexical full-list union',
             fontsize=9.5, color=MUTED)

    left.legend(handles=[Patch(facecolor=JUDGED, label='Judged'),
                         Patch(facecolor=UNJUDGED, hatch='///', edgecolor='#9F724C', label='No judgment')],
                frameon=False, ncol=2, fontsize=10, loc='lower left',
                bbox_to_anchor=(-0.02, 1.018), columnspacing=1.8, handlelength=1.6)
    positions, labels = [], []
    for index, annual in enumerate(data['rows']):
        offset = index * 6.1
        left.text(-0.404, offset - 0.83,
                  '{}  ·  {} queries'.format(annual['year'], annual['n_queries']),
                  transform=left.get_yaxis_transform(), fontsize=11.5, color=INK, weight='bold')
        for owner, owner_label, base in (('new_source', 'SPLADE++', 0),
                                        ('pooled_lexical', 'Lexical pooled', 2.4)):
            for group, group_label, relative in (('tail_supported', 'tail supported', 0),
                                                 ('isolated', 'isolated', 1)):
                y = offset + base + relative
                row = annual['owners'][owner]['groups'][group]
                observed, missing = row['n_judged'], row['n_unjudged']
                key = '{}-{}-{}'.format(annual['year'], owner, group)
                bar = left.barh(y, observed, height=0.60, color=JUDGED, zorder=3)[0]
                bar.set_gid(key + '-judged')
                bar = left.barh(y, missing, left=observed, height=0.60, color=UNJUDGED,
                                hatch='///', edgecolor='#9F724C', linewidth=0.5, zorder=3)[0]
                bar.set_gid(key + '-unjudged')
                left.text(row['n_candidates'] + 3, y,
                          '{} J / {} U'.format(observed, missing),
                          fontsize=9.4, color=INK, va='center')
                positions.append(y)
                labels.append('{} · {}'.format(owner_label, group_label))
    left.set_yticks(positions)
    left.set_yticklabels(labels, fontsize=10)
    left.set_ylim(10.6, -1.3)
    left.set_xlim(0, 205)
    left.set_xticks([0, 50, 100, 150, 200])
    left.set_xlabel('Query-document count  ·  labels: judged (J) / unjudged (U)',
                    fontsize=10, color=INK, labelpad=12)
    left.axhline(4.65, color='#CBD5DC', linewidth=0.85, linestyle=(0, (3, 3)))
    axis_style(left)

    for index, annual in enumerate(data['rows']):
        y = index * 1.9
        outside = annual['outside_top10']
        total = annual['whole_top10']['n_candidates']
        inside = total - outside['n_candidates']
        components = (('outside-judged', outside['n_judged'], JUDGED, None),
                      ('outside-unjudged', outside['n_unjudged'], UNJUDGED, '///'),
                      ('in-lexical-union', inside, EXISTING, None))
        cumulative = 0
        for key, count, color, hatch in components:
            percentage = count / total * 100
            bar = right.barh(y, percentage, left=cumulative, height=0.38, color=color,
                             edgecolor='#9F724C' if hatch else 'white',
                             linewidth=0.5, hatch=hatch, zorder=3)[0]
            bar.set_gid('{}-{}'.format(annual['year'], key))
            cumulative += percentage
        right.text(0, y - 0.49, annual['year'], fontsize=11, color=INK, weight='bold')
        right.text(100, y - 0.49, '{} / {} outside'.format(outside['n_candidates'], total),
                   fontsize=10.5, color=INK, ha='right')
        right.text(0, y + 0.47,
                   'Outside: {} judged · {} unjudged'.format(outside['n_judged'], outside['n_unjudged']),
                   fontsize=9.4, color=MUTED)
    right.set_ylim(2.66, -0.84)
    right.set_xlim(0, 100)
    right.set_yticks([])
    right.set_xticks([0, 25, 50, 75, 100])
    right.set_xticklabels(['0%', '25%', '50%', '75%', '100%'], fontsize=9)
    right.set_xlabel('Share of all SPLADE++ top10 documents', fontsize=9.5, color=INK, labelpad=9)
    axis_style(right)
    right.legend(handles=[Patch(facecolor=EXISTING, label='Already in the lexical union')],
                 frameon=False, fontsize=9.3, loc='lower left', bbox_to_anchor=(-0.02, 1.02))

    table.set_axis_off()
    table.text(0, 0.92, 'Queries with ≥1 judged specialist in each group',
               fontsize=10.8, weight='bold', color=INK)
    table.text(0.46, 0.64, 'SPLADE++', fontsize=10, color=JUDGED, ha='center', weight='bold')
    table.text(0.85, 0.64, 'Lexical pooled', fontsize=10, color=INK, ha='center', weight='bold')
    for index, annual in enumerate(data['rows']):
        y = 0.42 - index * 0.28
        table.text(0, y, annual['year'], fontsize=11, color=INK)
        for owner, x, color in (('new_source', 0.46, JUDGED), ('pooled_lexical', 0.85, INK)):
            table.text(x, y,
                       '{} / {}'.format(annual['owners'][owner]['n_queries_judged_both_groups'], annual['n_queries']),
                       fontsize=17, weight='bold', color=color, ha='center')

    notes = (
        (0.206, 'Judged means a recorded assessment exists, including grade 0. Judgment availability does not establish relevance.'),
        (0.172, 'Specialist: source top10 and absent from every other source’s top30. Tail supported: rank >30 in another full list.'),
        (0.138, 'Full lists: four supplied lexical sources plus SPLADE++ top1000. All groups are fixed from these original lists.'),
        (0.104, 'Counts are query-document observations, not independent samples. Paired-query counts alone do not establish adequate precision.'),
    )
    for y, note in notes:
        fig.text(0.035, y, note, fontsize=9.7, color=MUTED)
    fig.text(0.035, 0.052, 'Source: observations/summary.json  ·  Cycle02 observation inventory  ·  2026-09-10',
             fontsize=9, color='#6B7D89')
    return fig


def main():
    directory = Path(__file__).resolve().parent
    data = load_plot_data(directory)
    data['script_sha256'] = digest(Path(__file__).resolve())
    previous = os.environ.get('MPLCONFIGDIR')
    try:
        with tempfile.TemporaryDirectory(prefix='cycle02-mpl-') as cache:
            os.environ['MPLCONFIGDIR'] = cache
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt

            data['matplotlib_version'] = matplotlib.__version__
            with plt.rc_context({'font.family': 'DejaVu Sans', 'font.size': 10,
                                 'svg.fonttype': 'none', 'svg.hashsalt': 'icrrf-cycle02',
                                 'figure.facecolor': 'white', 'axes.facecolor': 'white'}):
                fig = make_figure(data, plt)
                # The figure consumes only saved counts; verify the source stayed fixed.
                source = directory / 'observations' / 'summary.json'
                if digest(source) != data['source_sha256']['observations/summary.json']:
                    raise RuntimeError('frozen summary changed during plotting')
                description = json.dumps(data, sort_keys=True)
                for suffix in ('svg', 'png'):
                    path = directory / ('observations.' + suffix)
                    metadata = {'Title': TITLE, 'Description': description}
                    if suffix == 'svg':
                        metadata.update({'Creator': 'plot_observations.py', 'Date': None})
                    fig.savefig(path, dpi=180, metadata=metadata)
                    print(path)
                plt.close(fig)
    finally:
        if previous is None:
            os.environ.pop('MPLCONFIGDIR', None)
        else:
            os.environ['MPLCONFIGDIR'] = previous


if __name__ == '__main__':
    main()
