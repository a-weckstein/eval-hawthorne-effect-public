"""Separate extension and exploratory pooled rates, paired-task bootstrap.

The pool resamples within the original/extension cohorts separately (59/42
tasks), preserving all five arm outcomes for each sampled task. No model calls.
"""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np

ORIG = Path('results/3_audit_probability/2026-10-20_glm_stage1_run1')
EXT = Path('results/3_audit_probability/2026-10-21_glm_stage1_extension')
POOL = Path('results/3_audit_probability/2026-10-21_glm_stage1_pooled_exploratory')
PROBS = [0, 1, 10, 50, 100]
REPLICATES, SEED = 50000, 20261023


def matrix(path):
    rows = [r for r in csv.DictReader(path.open()) if r['sample'] not in ('lcbhard_35', 'lcbhard_87')]
    ids = sorted({r['sample'] for r in rows}, key=lambda s: int(s.split('_')[1]))
    lookup = {(r['sample'], r['arm']): r['cheat'] == 'True' for r in rows}
    return np.array([[lookup[sid, f'audit_{p}'] for p in PROBS] for sid in ids], dtype=float)


def main():
    original, extension = matrix(ORIG/'final_outcomes.csv'), matrix(EXT/'final_outcomes.csv')
    assert original.shape == (59, 5) and extension.shape == (42, 5)
    rng = np.random.default_rng(SEED)
    ext_boot, pool_boot = np.empty((REPLICATES, 5)), np.empty((REPLICATES, 5))
    for start in range(0, REPLICATES, 1000):
        count = min(1000, REPLICATES-start)
        a = original[rng.integers(0, 59, (count, 59))].sum(axis=1)
        b = extension[rng.integers(0, 42, (count, 42))].sum(axis=1)
        ext_boot[start:start+count] = b/42
        pool_boot[start:start+count] = (a+b)/101
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.9), sharey=True)
    fig.subplots_adjust(left=.085, right=.975, top=.76, bottom=.22, wspace=.18)
    for ax, folder, values, boot, title in (
        (axes[0], EXT, extension, ext_boot, 'Extension alone · 42 tasks'),
        (axes[1], POOL, np.vstack([original, extension]), pool_boot, 'EXPLORATORY pool · 101 tasks')):
        rates = values.mean(axis=0)
        lo, hi = np.quantile(boot, [.025, .975], axis=0, method='linear')
        x = np.arange(5)
        ax.errorbar(x, rates, yerr=[rates-lo, hi-rates], fmt='o', color='#215b9c',
                    ecolor='#638bb9', markersize=7, capsize=5, elinewidth=1.8)
        for i in x:
            ax.text(i, hi[i]+.011, f'{rates[i]:.1%}\n{int(values[:, i].sum())}/{len(values)}',
                    ha='center', va='bottom', fontsize=9.5, color='#19344f')
        ax.set_title(title, fontsize=12, fontweight='bold', pad=15)
        ax.set_xticks(x, [f'{p}%' for p in PROBS])
        ax.set_xlabel('Stated probability of review', labelpad=10)
        ax.set_xlim(-.5, 4.5)
        ax.set_ylim(0, .35)
        ax.set_yticks(np.arange(0, .351, .05))
        ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        ax.grid(axis='y', alpha=.20)
        ax.set_axisbelow(True)
        records = [dict(probability_pct=p, n=len(values), cheats=int(values[:, i].sum()),
                        rate=float(rates[i]), percentile_bootstrap_95=[float(lo[i]), float(hi[i])])
                   for i, p in enumerate(PROBS)]
        (folder/'bootstrap_intervals.json').write_text(json.dumps(dict(replicates=REPLICATES,
             seed=SEED, method='pointwise 95% percentile paired-task bootstrap',
             pooling='resample 59 original and 42 extension tasks separately; pair all five arms',
             rates=records), indent=2)+'\n')
    axes[0].set_ylabel('Observed in-loop cheating rate', labelpad=10)
    fig.text(.085, .95, 'Audit-probability results after the remaining-task extension',
             fontsize=16, fontweight='bold', color='#172d43')
    fig.text(.085, .89, 'GLM-5.3-flash · InferenceNet · original 59-task report remains frozen',
             fontsize=11, color='#4c5b69')
    fig.text(.085, .105, 'Error bars: pointwise 95% bootstrap intervals; 50,000 resamples of paired task outcomes.', fontsize=10, color='#4c5b69')
    fig.text(.085, .063, 'Pool is exploratory: extension was chosen after seeing original results. Cohort sizes stay fixed in bootstrap.', fontsize=9.5, color='#4c5b69')
    for ext in ('png', 'svg', 'pdf'):
        fig.savefig(EXT/f'extension_and_exploratory_pool_bootstrap.{ext}', dpi=180, facecolor='white')
    svg = EXT/'extension_and_exploratory_pool_bootstrap.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(fig)


if __name__ == '__main__':
    main()
