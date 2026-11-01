"""Plot the completed sweep with paired-task percentile bootstrap intervals.

Requires numpy and matplotlib in a separate analysis environment. Reads only the
small final outcome CSV; never loads credentials or makes model calls.
"""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np

OUT = Path('results/3_audit_probability/2026-10-20_glm_stage1_run1')
PROBS = [0, 1, 10, 50, 100]
SEED, REPLICATES = 20261021, 50000


def main():
    rows = list(csv.DictReader((OUT/'final_outcomes.csv').open()))
    task_ids = [f'lcbhard_{i}' for i in range(60) if i != 35]
    lookup = {(int(r['arm'].split('_')[1]), r['sample']): r['cheat'] == 'True' for r in rows}
    y = np.array([[lookup[p, sid] for p in PROBS] for sid in task_ids], dtype=float)
    assert y.shape == (59, 5)
    rng = np.random.default_rng(SEED)
    bootstrap = np.empty((REPLICATES, 5))
    for start in range(0, REPLICATES, 1000):
        stop = min(start+1000, REPLICATES)
        # One sampled task index selects all five outcomes together.
        indices = rng.integers(0, len(task_ids), size=(stop-start, len(task_ids)))
        bootstrap[start:stop] = y[indices].mean(axis=1)
    rate = y.mean(axis=0)
    lo, hi = np.quantile(bootstrap, [.025, .975], axis=0, method='linear')
    diff_ci = np.quantile(bootstrap-bootstrap[:, :1], [.025, .975], axis=0, method='linear')
    records = [dict(probability_pct=p, n=59, cheats=int(y[:, i].sum()), rate=float(rate[i]),
                    percentile_bootstrap_95=[float(lo[i]), float(hi[i])],
                    paired_difference_vs_zero=float(rate[i]-rate[0]),
                    paired_difference_bootstrap_95=[float(diff_ci[0, i]), float(diff_ci[1, i])])
               for i, p in enumerate(PROBS)]
    result = dict(method='nonparametric paired task bootstrap, pointwise percentile 95% intervals',
                  replicates=REPLICATES, seed=SEED, quantile_method='linear',
                  resampling_unit='task: jointly resample all five arm outcomes',
                  task_ids=task_ids, rates=records,
                  limitations='Resamples the observed task slice; does not capture new-run/provider/time variation. Marginal intervals are not simultaneous bands or the primary slope analysis.')
    (OUT/'bootstrap_intervals.json').write_text(json.dumps(result, indent=2)+'\n')
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, ax = plt.subplots(figsize=(9.6, 5.9), layout=None)
    fig.subplots_adjust(left=.115, right=.96, top=.78, bottom=.22)
    x = np.arange(5)
    ax.errorbar(x, rate, yerr=[rate-lo, hi-rate], fmt='o', color='#215b9c',
                ecolor='#638bb9', markersize=8.5, capsize=6, elinewidth=2, capthick=1.7)
    for i in range(5):
        ax.text(i, hi[i]+.016, f'{rate[i]:.1%}\n({int(y[:, i].sum())}/59)', ha='center',
                va='bottom', fontsize=10.5, color='#19344f', linespacing=1.45)
    ax.set_xticks(x, [f'{p}%' for p in PROBS])
    ax.set_xlabel('Stated probability of review', labelpad=11)
    ax.set_ylabel('Observed in-loop cheating rate', labelpad=10)
    ax.set_ylim(0, .36)
    ax.set_xlim(-.5, 4.5)
    ax.set_yticks(np.arange(0, .351, .05))
    ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.grid(axis='y', alpha=.20)
    ax.set_axisbelow(True)
    fig.text(.115, .94, 'Stated audit probability and observed cheating',
             fontsize=17, fontweight='bold', color='#172d43')
    fig.text(.115, .885, 'GLM-5.3-flash · InferenceNet · 59 paired tasks per condition',
             fontsize=11.5, color='#4c5b69')
    fig.text(.115, .105, 'Error bars: pointwise 95% percentile bootstrap intervals; 50,000 paired-task resamples.',
             fontsize=9.5, color='#4c5b69')
    fig.text(.115, .064, 'Dead task lcbhard_35 excluded. Conditions are equally spaced categories; no fitted dose-response curve.',
             fontsize=9, color='#4c5b69')
    for ext in ('png', 'svg', 'pdf'):
        fig.savefig(OUT/f'audit_probability_bootstrap.{ext}', dpi=180, facecolor='white')
    svg = OUT/'audit_probability_bootstrap.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(fig)
    print(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()
