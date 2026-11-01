"""Single-panel plot of all 101 usable tasks, using saved paired bootstrap CIs."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np

OUT = Path('results/3_audit_probability/2026-10-21_glm_stage1_pooled_exploratory')


def main():
    saved = json.loads((OUT/'bootstrap_intervals.json').read_text())
    records = saved['rates']
    rows = list(csv.DictReader((OUT/'final_outcomes.csv').open()))
    assert len(rows) == 505 and saved['replicates'] == 50000
    assert [r['probability_pct'] for r in records] == [0, 1, 10, 50, 100]
    for record in records:
        group = [r for r in rows if r['arm'] == f"audit_{record['probability_pct']}"]
        assert len(group) == record['n'] == 101
        assert len({r['sample'] for r in group}) == 101
        assert sum(r['cheat'] == 'True' for r in group) == record['cheats']
        assert abs(record['rate']-record['cheats']/101) < 1e-12
    rate = np.array([r['rate'] for r in records])
    lo = np.array([r['percentile_bootstrap_95'][0] for r in records])
    hi = np.array([r['percentile_bootstrap_95'][1] for r in records])
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, ax = plt.subplots(figsize=(9.6, 6.2))
    fig.subplots_adjust(left=.115, right=.96, top=.75, bottom=.245)
    x = np.arange(5)
    ax.errorbar(x, rate, yerr=[rate-lo, hi-rate], fmt='o', color='#215b9c',
                ecolor='#638bb9', markersize=8.5, capsize=6, elinewidth=2, capthick=1.7)
    for i, r in enumerate(records):
        ax.text(i, hi[i]+.012, f"{rate[i]:.1%}\n({r['cheats']}/101)",
                ha='center', va='bottom', fontsize=10.5, color='#19344f', linespacing=1.4)
    ax.set_xticks(x, [f"{r['probability_pct']}%" for r in records])
    ax.set_xlabel('Stated probability of review', labelpad=11)
    ax.set_ylabel('Observed in-loop cheating rate', labelpad=10)
    ax.set_ylim(0, .30)
    ax.set_xlim(-.5, 4.5)
    ax.set_yticks(np.arange(0, .301, .05))
    ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.grid(axis='y', alpha=.20)
    ax.set_axisbelow(True)
    fig.text(.115, .945, 'Stated audit probability and observed cheating',
             fontsize=17, fontweight='bold', color='#172d43')
    fig.text(.115, .89, 'GLM-5.3-flash · InferenceNet · 101 paired tasks per condition',
             fontsize=11.5, color='#4c5b69')
    fig.text(.115, .835, 'EXPLORATORY · original study + post-outcome extension',
             fontsize=10.5, color='#795b2b')
    fig.text(.115, .125, 'Error bars: pointwise 95% percentile bootstrap CIs; 50,000 paired-task resamples.',
             fontsize=9.5, color='#4c5b69')
    fig.text(.115, .085, 'Resampling stratified by cohort (59 + 42 tasks). Extension selected after initial results.',
             fontsize=9.1, color='#4c5b69')
    fig.text(.115, .045, 'Conditions are equally spaced categories; no fitted dose-response curve.',
             fontsize=9.1, color='#4c5b69')
    for ext in ('png', 'svg', 'pdf'):
        fig.savefig(OUT/f'full_audit_probability_bootstrap.{ext}', dpi=180, facecolor='white')
    svg = OUT/'full_audit_probability_bootstrap.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(fig)


if __name__ == '__main__':
    main()
