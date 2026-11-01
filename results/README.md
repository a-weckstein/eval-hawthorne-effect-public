# results/

One folder per experimental phase, in the order of the presentation. Inside each phase, one folder per run, named `<date>_<run>`. Every run folder has a `samples.csv` (one row per task and arm) or an equivalent outcomes file; the column list is in the docstring of `scripts/summarize_logs.py`. Raw Inspect `.eval` logs are not included.

| Folder | Phase | What is in it |
|---|---|---|
| `1_screening/` | Phase I, model screening | Seven 20-task screens (prompt A, neutral preamble, 3 attempts), one folder per model. |
| `2_hawthorne_effect/` | Phase II, review-notice effect | gpt-5.6-luna stage 0, 0b and run 3 (101 tasks); GLM-5.3-flash confirmation runs 1 and 2 and the wording head-to-head (59 tasks); hand-labelled evaluation-awareness remarks (`eval_awareness_handlabels.csv`) and the suspicion-vs-cheating analysis. |
| `3_audit_probability/` | Phase III, stated audit probability | GLM sweep over 0/1/10/50/100% (59 tasks), the 42-task extension, the exploratory 101-task pool, and the pre-registered mixed-model slope. Each folder has its own README. |
| `4_cot_edits/` | Phase IV, chain-of-thought edits | Insertion, removal and in-reasoning probability experiments (`episodes_detail.csv`, blind labels), quoted examples, and the manifests in `cot_edit/`. |
| `figures/` | All phases | Figures and tables used in the presentation, one PNG per slide plus the CSV behind each and `deck_figures.pdf`. Regenerate with `Rscript analysis/make_deck_figures.R`. |
| `figures/from_deck/` | Phases III and IV | Images taken from the slide deck whose generating code is not in this repository (see below). |

## Figures taken from the deck only

Produced by collaborators outside this repository and copied from the deck. The data behind them is here; the plotting code is not.

| File | Data source |
|---|---|
| `from_deck/fig5_audit_probability_quadratic_fit.png` | `3_audit_probability/2026-10-21_glm_stage1_pooled_exploratory/final_outcomes.csv`. The quadratic curve in log(1 + review %) is descriptive and was chosen after viewing the results. |
| `from_deck/fig5b_audit_probability_trace_examples.png` | Selected reasoning and reply excerpts from separate sessions of the sweep; not evidence of causation. |
| `from_deck/fig6b_cot_insertion_example.jpg` | One task from `4_cot_edits/2026-10-20_cot_edit_insertion/`. |
| `from_deck/fig7_review_gap_by_attempt.png` | `2_hawthorne_effect/2026-10-14_glm_confirm_run1/samples.csv` and `2026-10-18_glm_confirm_run2/samples.csv`, neutral vs all_reviewed, cumulative first cheat by attempt (`first_pass_attempt` column). |
| `from_deck/ref_cot_injection_paper_header.png` | Header of the related ICLR 2026 submission cited in the deck. |
