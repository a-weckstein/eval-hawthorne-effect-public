# docs/

Working notes kept during the project, copied as they were at the end of the study. They record the reasoning behind each choice and the full result tables; the headline results are summarised in the top-level README. They were written for the people running the study, so they refer to "the user" or "the owner" (the project lead) and to decision numbers (D1–D36) and nuance numbers (N1–N23).

| File | What it holds |
|---|---|
| `study_design_stage0.md` | Arms and fixed settings of the review-notice study; results of luna stage 0, 0b and run 3 and GLM confirmation runs 1 and 2 (§6–10). |
| `study_design_stage1.md` | The stated-audit-probability sweep: estimand, claims ladder, the primary slope analysis (§9) and the wording head-to-head (§10). |
| `study_design_cot_edit.md` | The reasoning-edit experiment: mechanism, arms, task selection, and the results of the insertion, removal, in-reasoning probability and follow-up runs (§10–14). |
| `decisions_log.md` | Every design decision, dated, with its rationale (D1–D36). |
| `impossiblebench_data_nuances.md` | Quirks of the benchmark, scorer and harness found along the way (N1–N23). Read before running anything. |
| `model_tracker.md` | One row per model screened: weights, release month, runs, cheat rate, health and cost. |
| `screening_run_plan.md` | How the model screen was planned and run. |
| `spend_log.md` | Every paid run with its estimated and observed cost. |
| `presentation_outline.md` | Slide-by-slide notes that map each figure to its data and code. |
| `preliminary_tests_20261012.md`, `benchmark_reassessment_20261012.md` | Early checks of the benchmark and scorer before any paid run. |
| `stage1_improvements_proposal_20261013.md`, `review_stage1_proposal_20261013.md` | The proposal that produced the stage 0b arms and the filler control, and its review. |
| `presentation/` | The final in-class presentation (2026-10-22). |

Some early-screen result folders these notes mention (local Qwen3-8B pilots, the claude-haiku-5.5 screens, screens B–D, the mixed reasoning-edit pilot) were left out of this public copy because they did not feed the final results; their summaries survive in `model_tracker.md` and `screening_run_plan.md`.
