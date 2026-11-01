"""Render completed extension/exploratory reports without altering the original."""
import json
from pathlib import Path

EXT = Path('results/3_audit_probability/2026-10-21_glm_stage1_extension')
POOL = Path('results/3_audit_probability/2026-10-21_glm_stage1_pooled_exploratory')
PRIMARY = Path('results/3_audit_probability/2026-10-21_glm_stage1_primary_analysis')
PROBS = ('0', '1', '10', '50', '100')


def rates(a):
    text = ['| Review probability | Cheats / tasks | Rate | Wilson 95% CI |', '|---|---:|---:|---:|']
    for p in PROBS:
        s = a['per_arm'][p]
        lo, hi = s['wilson_95']
        text.append(f"| {p}% | {s['cheats']}/{s['n']} | {100*s['rate']:.1f}% | {100*lo:.1f}–{100*hi:.1f}% |")
    return text


def contrasts(a, key):
    text = ['| Probability vs 0% | Difference (pp) | Paired Newcombe 95% CI (pp) | Arm-only / 0%-only | Exact McNemar p | Holm p |',
            '|---|---:|---:|---:|---:|---:|']
    for p in PROBS[1:]:
        s = a[key][p]
        lo, hi = s['newcombe_95']
        text.append(f"| {p}% | {100*s['difference']:+.1f} | {100*lo:+.1f} to {100*hi:+.1f} | {s['arm_only']} / {s['control_only']} | {s['exact_mcnemar_p']:.4f} | {s['holm_p']:.4f} |")
    return text


def main():
    a = json.loads((EXT/'final_analysis.json').read_text())
    pool = json.loads((POOL/'final_analysis.json').read_text())
    assert a['collection'] == 'complete' and a['completed_sessions'] == 210
    fits = {name: json.loads((PRIMARY/f'{name}.json').read_text())
            for name in ('original_primary', 'extension_exploratory', 'pooled_exploratory')}
    for data, name, folder in ((a, 'extension_exploratory', EXT), (pool, 'pooled_exploratory', POOL)):
        data['primary_probability_slope'] = dict(status='fitted_in_separate_supplement',
            interpretation=fits[name]['label'], result=f'../{PRIMARY.name}/{name}.json')
        (folder/'final_analysis.json').write_text(json.dumps(data, indent=2)+'\n')
    h = a['health']
    tests = a['paired_vs_zero']
    any_sig = any(s['holm_p'] < .05 for s in tests.values())
    lines = ['# Remaining-task extension: completed results', '',
      '**210/210 sessions completed**, with 42 unique, scored, error-free outcomes per condition. No original task IDs were rerun. The original 300-session study and its report remain frozen.', '',
      'This extension was selected **after inspecting the original outcomes**. It is a separately authorized cohort, not a preplanned expansion. Any pool with the first study is exploratory.', '',
      '![Extension and exploratory pooled bootstrap intervals](extension_and_exploratory_pool_bootstrap.png)', '',
      '## Extension alone', '']+rates(a)+['', 'Exact paired comparisons versus 0%, Holm across the four tests; difference intervals are pointwise, not multiplicity adjusted.', '']+contrasts(a, 'paired_vs_zero')
    lines += ['', ('At least one extension-only secondary comparison has Holm p < .05; interpret within the post-outcome cohort.' if any_sig else 'None of the extension-only secondary contrasts reaches Holm-adjusted p < .05. This is not evidence of equivalence or proof of no effect.'), '',
      '## Planned primary estimand and exploratory fits', '',
      f"The original-study planned task-random-intercept linear probability slope is now fitted in a separate supplement: beta={fits['original_primary']['beta']:.3f}, SE={fits['original_primary']['beta_se']:.3f}, two-sided Wald p={fits['original_primary']['wald_p']:.4f}; likelihood-ratio sensitivity p={fits['original_primary']['likelihood_ratio_p']:.4f}. No clear linear slope is established. The extension and pooled slope fits are exploratory. A linear slope does not test every possible nonmonotonic shape.", '',
      '[Primary model methods and numerical checks](../2026-10-21_glm_stage1_primary_analysis/README.md). The older frozen report records the then-pending fit; this supplement supplies the later analysis without rewriting it.', '',
      '## Protocol, health, costs, and limitations', '',
      'Same GLM-5.3-flash / InferenceNet / OpenRouter configuration and numeric audit notices: 0/1/10/50/100%; three attempts, low reasoning, 64k cap, five concurrent arms and eight connection slots, Docker, paper_A work tickets. IDs 60–102 were used except dead task 87, excluded before dispatch. Exactly 42 usable tasks per arm. The outcome is any in-loop pass; zero means no observed successful hack, not verified honest intent.', '',
      f"Integrity: {a['request_notices_verified']} saved API request notices/routing records verified; only InferenceNet observed. All approved IDs matched, no duplicates, no scored errors; original raw hashes unchanged. Cut-off replies: {h['n_cut_off']}/{h['model_calls']} ({100*h['n_cut_off']/h['model_calls']:.1f}%); multi-code-block replies: {h['n_reply_multi_block']}/{h['model_calls']} ({100*h['n_reply_multi_block']/h['model_calls']:.1f}%); syntax errors: {h['n_attempt_syntax_error']}/{h['attempts']} attempts.", '',
      'Per-arm cut-offs: '+', '.join(f"{p}%: {a['health_by_arm'][p]['cutoffs']}/{a['health_by_arm'][p]['model_calls']}" for p in PROBS)+'. '+
      f"The maximum arm difference is {100*a['cutoff_rate_spread']:.2f} percentage points, "+
      ('**above the preplanned 5-point interpretation flag**.' if a['cutoff_spread_over_5pp'] else 'below the preplanned 5-point flag.')+' Observed successful-hack rates can be lower bounds when replies are truncated; compare conditions cautiously.', '',
      'Conditional sensitivity among tasks with at least one nonempty, nontruncated reply: '+
      ', '.join(f"{p}%: {a['per_arm'][p]['finished_reply_sensitivity']['cheats']}/{a['per_arm'][p]['finished_reply_sensitivity']['n']}" for p in PROBS)+
      '. These selected denominators are a sensitivity analysis, not replacement paired treatment estimates.', '',
      'Mac sleep and retries split collection over time. Truncation and upstream code extraction can suppress observed successful hacks. One wording, model, host and task family cannot establish broad generality. Bootstrap intervals are pointwise 95% percentile intervals from 50,000 paired-task resamples (seed 20261023); pooled resampling retains the original/extension sizes of 59/42. They do not capture new-run/provider variation.', '',
      f"Extension recorded response charges: **${a['recorded_response_cost_usd']:.6f}**. Conservative extension ledger: **${a['budget']['charged_or_reserved_usd']:.6f}**, below the separately authorized **$4 cap**. Ledger minus recorded response charges: **${a['conservative_unknown_call_provisions_usd']:.6f}**; these provisions are not confirmed charges. No requests remain in flight. Final billing reconciliation is pending. Original-study charges/provisions remain separate ($4.257210332 recorded / $7.137210332 conservative).", '',
      '[Exploratory 101-task pooled report](../2026-10-21_glm_stage1_pooled_exploratory/README.md). Raw traces, credentials and local checkpoint archives remain local. Completed outcomes and partial records are kept separately.', '',
      'Files: [outcomes](final_outcomes.csv), [detailed summaries](samples.csv), [analysis](final_analysis.json), [bootstrap intervals](bootstrap_intervals.json), [configuration](run_config.json), [PNG](extension_and_exploratory_pool_bootstrap.png), [SVG](extension_and_exploratory_pool_bootstrap.svg), [PDF](extension_and_exploratory_pool_bootstrap.pdf).']
    (EXT/'README.md').write_text('\n'.join(lines)+'\n')
    pooled_plot = ('full_audit_probability_bootstrap.png' if (POOL/'full_audit_probability_bootstrap.png').exists()
                   else '../2026-10-21_glm_stage1_extension/extension_and_exploratory_pool_bootstrap.png')
    pooled_lines = ['# EXPLORATORY pooled results: original study + extension', '',
      '**101 usable paired tasks per condition / 505 usable sessions**: 59 original plus 42 extension tasks. The extension was chosen after viewing original outcomes, so this is not a preplanned 101-task confirmatory experiment. Dead tasks 35 and 87 are excluded. Original results remain frozen.', '',
      f'![All-task bootstrap intervals]({pooled_plot})', '']+rates(pool)+['',
      'Exploratory paired contrasts versus 0% (Holm within four pooled tests; this does not correct post-outcome sample selection or all analyses across cohorts):', '']+contrasts(pool, 'paired_vs_zero')+['',
      f"Exploratory random-intercept probability slope: beta={fits['pooled_exploratory']['beta']:.3f}, SE={fits['pooled_exploratory']['beta_se']:.3f}, two-sided Wald p={fits['pooled_exploratory']['wald_p']:.4f}. Do not substitute this for the original-study primary result. See [primary/GLMM methods](../2026-10-21_glm_stage1_primary_analysis/README.md).", '',
      'Intervals are pointwise. Bootstrap keeps the 59/42 cohort sizes fixed and jointly resamples the five arm outcomes for each task (50,000 replicates; seed 20261023). Time splits, provider drift, truncation and extraction remain limitations. The extension cutoff-rate spread exceeds the preplanned 5-point flag; see its health report. Nonsignificance does not establish equivalence or absence of an effect.', '',
      '[Extension report, costs and health](../2026-10-21_glm_stage1_extension/README.md); [original frozen report](../2026-10-20_glm_stage1_run1/README.md); [pooled outcomes](final_outcomes.csv); [pooled analysis](final_analysis.json); [bootstrap intervals](bootstrap_intervals.json).']
    (POOL/'README.md').write_text('\n'.join(pooled_lines)+'\n')
    primary_lines = ['# Planned primary slope: later analysis supplement', '',
      'The original 59-task study is the confirmatory cohort for the planned estimand `cheat ~ probability + (1 | task)`, with probability as a fraction from 0 to 1. Extension and pooled fits below are explicitly exploratory because the extension was selected after viewing outcomes.', '',
      '| Cohort | Tasks | Slope beta | SE | Wald 95% CI | Two-sided Wald p | LR sensitivity p |', '|---|---:|---:|---:|---:|---:|---:|']
    for name, fit in fits.items():
        lo, hi = fit['beta_wald_95']
        primary_lines.append(f"| {fit['label']} | {fit['tasks']} | {fit['beta']:.4f} | {fit['beta_se']:.4f} | {lo:.4f} to {hi:.4f} | {fit['wald_p']:.4f} | {fit['likelihood_ratio_p']:.4f} |")
    primary_lines += ['', 'Method: a Python marginal maximum-likelihood implementation of the specified binomial-logit Gaussian task-random-intercept model. Scalar random effects are integrated with 320-node fixed Gauss-Hermite quadrature. This is not an execution of R/lme4; its [GLMM documentation](https://lme4.github.io/lme4/reference/glmer.html) describes the model and role of random-effect integration. The numerical implementation and Wald inference were finalized after collection; the earlier plan fixed the estimand/model but not a specific fitting implementation.', '',
      'Checks: analytic gradients/Hessians against finite differences; stable estimates and log likelihood at 80/160/320 nodes; multiple optimization starts; independent adaptive integration and derivative-free optimizer agreement. Exact errors, convergence diagnostics, source hashes and NumPy/SciPy versions are in each JSON. The fitting environment is isolated from the experiment runtime.', '',
      'A linear slope does not test every step or U-shaped alternative. The likelihood-ratio check is a sensitivity analysis, not a second selected primary test. These are one-model/one-host results with substantial task and run uncertainty. No sample-size change or stopping decision was based on these tests.', '',
      'Reproduce with `python analysis/fit_stage1_glmm.py` in an environment containing NumPy/SciPy. JSON files: [original primary](original_primary.json), [extension exploratory](extension_exploratory.json), [pooled exploratory](pooled_exploratory.json). Original-study artifacts were not overwritten.']
    (PRIMARY/'README.md').write_text('\n'.join(primary_lines)+'\n')
    # Normalize new CSV summaries only; leave original-study bytes unchanged.
    sample_file = EXT/'samples.csv'
    sample_file.write_bytes(sample_file.read_bytes().replace(b'\r\n', b'\n'))


if __name__ == '__main__':
    main()
