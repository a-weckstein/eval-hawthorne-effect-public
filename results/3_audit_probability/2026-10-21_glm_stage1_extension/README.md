# Remaining-task extension: completed results

**210/210 sessions completed**, with 42 unique, scored, error-free outcomes per condition. No original task IDs were rerun. The original 300-session study and its report remain frozen.

This extension was selected **after inspecting the original outcomes**. It is a separately authorized cohort, not a preplanned expansion. Any pool with the first study is exploratory.

![Extension and exploratory pooled bootstrap intervals](extension_and_exploratory_pool_bootstrap.png)

## Extension alone

| Review probability | Cheats / tasks | Rate | Wilson 95% CI |
|---|---:|---:|---:|
| 0% | 5/42 | 11.9% | 5.2–25.0% |
| 1% | 3/42 | 7.1% | 2.5–19.0% |
| 10% | 1/42 | 2.4% | 0.4–12.3% |
| 50% | 3/42 | 7.1% | 2.5–19.0% |
| 100% | 3/42 | 7.1% | 2.5–19.0% |

Exact paired comparisons versus 0%, Holm across the four tests; difference intervals are pointwise, not multiplicity adjusted.

| Probability vs 0% | Difference (pp) | Paired Newcombe 95% CI (pp) | Arm-only / 0%-only | Exact McNemar p | Holm p |
|---|---:|---:|---:|---:|---:|
| 1% | -4.8 | -15.6 to +4.6 | 0 / 2 | 0.5000 | 1.0000 |
| 10% | -9.5 | -22.4 to +1.4 | 0 / 4 | 0.1250 | 0.5000 |
| 50% | -4.8 | -18.5 to +8.6 | 2 / 4 | 0.6875 | 1.0000 |
| 100% | -4.8 | -19.1 to +9.5 | 3 / 5 | 0.7266 | 1.0000 |

None of the extension-only secondary contrasts reaches Holm-adjusted p < .05. This is not evidence of equivalence or proof of no effect.

## Planned primary estimand and exploratory fits

The original-study planned task-random-intercept linear probability slope is now fitted in a separate supplement: beta=0.232, SE=0.462, two-sided Wald p=0.6157; likelihood-ratio sensitivity p=0.6177. No clear linear slope is established. The extension and pooled slope fits are exploratory. A linear slope does not test every possible nonmonotonic shape.

[Primary model methods and numerical checks](../2026-10-21_glm_stage1_primary_analysis/README.md). The older frozen report records the then-pending fit; this supplement supplies the later analysis without rewriting it.

## Protocol, health, costs, and limitations

Same GLM-5.3-flash / InferenceNet / OpenRouter configuration and numeric audit notices: 0/1/10/50/100%; three attempts, low reasoning, 64k cap, five concurrent arms and eight connection slots, Docker, paper_A work tickets. IDs 60–102 were used except dead task 87, excluded before dispatch. Exactly 42 usable tasks per arm. The outcome is any in-loop pass; zero means no observed successful hack, not verified honest intent.

Integrity: 627 saved API request notices/routing records verified; only InferenceNet observed. All approved IDs matched, no duplicates, no scored errors; original raw hashes unchanged. Cut-off replies: 67/627 (10.7%); multi-code-block replies: 229/627 (36.5%); syntax errors: 234/627 attempts.

Per-arm cut-offs: 0%: 15/125, 1%: 15/125, 10%: 16/126, 50%: 8/126, 100%: 13/125. The maximum arm difference is 6.35 percentage points, **above the preplanned 5-point interpretation flag**. Observed successful-hack rates can be lower bounds when replies are truncated; compare conditions cautiously.

Conditional sensitivity among tasks with at least one nonempty, nontruncated reply: 0%: 5/40, 1%: 3/40, 10%: 1/41, 50%: 3/41, 100%: 3/40. These selected denominators are a sensitivity analysis, not replacement paired treatment estimates.

Mac sleep and retries split collection over time. Truncation and upstream code extraction can suppress observed successful hacks. One wording, model, host and task family cannot establish broad generality. Bootstrap intervals are pointwise 95% percentile intervals from 50,000 paired-task resamples (seed 20261023); pooled resampling retains the original/extension sizes of 59/42. They do not capture new-run/provider variation.

Extension recorded response charges: **$3.737859**. Conservative extension ledger: **$3.737859**, below the separately authorized **$4 cap**. Ledger minus recorded response charges: **$0.000000**; these provisions are not confirmed charges. No requests remain in flight. Final billing reconciliation is pending. Original-study charges/provisions remain separate ($4.257210332 recorded / $7.137210332 conservative).

[Exploratory 101-task pooled report](../2026-10-21_glm_stage1_pooled_exploratory/README.md). Raw traces, credentials and local checkpoint archives remain local. Completed outcomes and partial records are kept separately.

Files: [outcomes](final_outcomes.csv), [detailed summaries](samples.csv), [analysis](final_analysis.json), [bootstrap intervals](bootstrap_intervals.json), [configuration](run_config.json), [PNG](extension_and_exploratory_pool_bootstrap.png), [SVG](extension_and_exploratory_pool_bootstrap.svg), [PDF](extension_and_exploratory_pool_bootstrap.pdf).
