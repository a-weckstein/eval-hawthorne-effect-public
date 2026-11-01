# results/

One folder per experimental phase, in the order of the final presentation. Inside each phase, one folder per run, named `<date>_<run>`. Every run folder has a `samples.csv` (one row per task and arm) or an equivalent outcomes file; the column list is in the docstring of `scripts/summarize_logs.py`. Raw Inspect `.eval` logs (about 220 MB) are not included.

| Folder | Phase | What is in it |
|---|---|---|
| `1_screening/` | Phase I, model screening | Seven 20-task screens (prompt A, neutral preamble, 3 attempts), one folder per model. |
| `2_hawthorne_effect/` | Phase II, review-notice effect | gpt-5.6-luna stage 0 and 0b (103 tasks, 4 and 8 arms), luna run 3 with the filler control; GLM-5.3-flash confirmation runs 1 and 2 (4 arms × 60 tasks) and the wording head-to-head (run 3); the follow-up-question manipulation check; hand-labelled evaluation-awareness remarks (`eval_awareness_handlabels.csv`) and the suspicion-vs-cheating analysis. |
| `3_audit_probability/` | Phase III, stated audit probability | GLM sweep over 0/1/10/50/100% (59 tasks), the 42-task extension, the exploratory 101-task pool, the pre-registered mixed-model slope (R and Python). Each folder has its own README. |
| `4_cot_edits/` | Phase IV, chain-of-thought edits | Insertion, removal and in-reasoning probability experiments (`episodes_detail.csv`, blind labels), the insertion follow-up, outcome-flip analysis, quoted examples, and the manifests in `cot_edit/`. `2026-10-18_prefill_probe_real/` is the feasibility probe for continuing GLM's reasoning. |
| `figures/` | All phases | Figures and tables used in the presentation, one PNG per slide plus the CSV behind each and `deck_figures.pdf`. Regenerate with `Rscript analysis/make_deck_figures.R`. |
| `figures/from_deck/` | Phases III and "other" | Images taken from the final slide deck whose generating code is **not** in this repository (see below). |

## Figures taken from the deck only

These were produced by collaborators outside this repository and are copied from the presentation file in `docs/presentation/`. The data behind them is in this repository; the plotting code is not.

| File | Slide | Data source |
|---|---|---|
| `from_deck/fig5_audit_probability_quadratic_fit.png` | Phase III results | `3_audit_probability/2026-10-21_glm_stage1_pooled_exploratory/final_outcomes.csv` (101 tasks). The quadratic curve in log(1 + review %) is descriptive and was chosen after viewing the results. |
| `from_deck/fig5b_audit_probability_trace_examples.png` | Phase III follow-up | Selected reasoning and reply excerpts from separate sessions of the sweep; not evidence of causation. |
| `from_deck/fig6b_cot_insertion_example.jpg` | Phase IV insertion | One task from `4_cot_edits/2026-10-20_cot_edit_insertion/`. |
| `from_deck/fig7_review_gap_by_attempt.png` | "Other": cumulative cheating by attempt | `2_hawthorne_effect/2026-10-14_glm_confirm_run1/samples.csv` and `2026-10-18_glm_confirm_run2/samples.csv`, neutral vs all_reviewed, pooled descriptively (118 task-runs per condition; `first_pass_attempt` column). No confidence intervals. |
| `from_deck/ref_cot_injection_paper_header.png` | Phase IV | Header of the related ICLR 2026 submission cited in the deck. |
