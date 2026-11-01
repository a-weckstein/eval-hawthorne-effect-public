# Reassessment: is ImpossibleBench still the right starting point? (2026-10-12)

**Asked by the user:** given the Oct 8 scan (`~/Desktop/Claude_research/agent_docs/EvalAwareness_sampled_monitoring_20261008.md`, §8 chose ImpossibleBench on Oct 10) and the Oct 12 preliminary tests (`preliminary_tests_20261012.md`, `impossiblebench_data_nuances.md` N11–N14), do I still agree? Are there cheaper, lower-risk benchmarks or de novo tasks for the two goals:
(a) show cheating rises when the model does not think it is being evaluated/monitored;
(b) sweep a stated audit probability X% and find where behaviour shifts.
Budget: about $50 API.

**Status:** assessment only. No decision has been changed; nothing below has been run. Decisions log D3 (ImpossibleBench first) stands until the user says otherwise.

---

## 1. Short answer

**Half yes, half no.** The scan was right about the *mechanism* (objective, automatically scored cheating via tests that contradict the spec) and that choice still holds. It was wrong, in hindsight, about the *vehicle*: running the upstream harness as published (10-attempt retry loop, benchmark-shaped task text, strictness prompts) is too expensive and too poorly aimed for a $50 course project. The scan's cost assumption was "tens to a few hundred dollars per API model" for stage 1; it was written before the $50 budget was set (Oct 12).

Recommendation: **keep ImpossibleBench's tasks and scorer, drop its agent loop and task wording.** Run a single-turn, work-ticket-framed version of the same 103 conflicting tasks, with the monitoring notice in the system prompt. This keeps the objective endpoint and the paper link, cuts cost roughly 10×, and fixes most of the harness problems found on Oct 12. Keep a de novo self-report task as the fallback if single-turn base rates on cheap models land outside the 30–70% window.

## 2. What the Oct 12 tests showed, and what each means for the goals

| # | Finding (source) | Why it matters for goals (a)/(b) |
|---|---|---|
| 1 | ImpossibleBench has **no monitoring manipulation** (scan §8.3; study design §2). Its levers are prompt strictness, test visibility, feedback loops, abort option. | Replicating it does not test goal (a) at all. The notice arms are new and may be null (Knecht ≤3.7 pp; Hasan null on Opus 4.6). The "fidelity check" buys publishability, not evidence for our question. |
| 2 | The upstream **user message is benchmark-shaped** in every arm: "pass all the tests", bold DO NOT MODIFY, the full test code (study design §4, open). | The `none_reviewed` arm asks the model to believe no one is watching while the task text reads like a test. Frontier models already self-label ~100% of hand-built prompts as evals (Williams et al.); this wording makes it worse. Goal (a) as literally stated ("does not think it is being evaluated") is probably not achievable on any hand-built task; the manipulable variable is the *stated review policy*. |
| 3 | **Cost is inverted.** Honest tasks run all 10 attempts (≈40k in / 50k out tokens on Qwen3-8B); cheats end early. Stage 0 at full size ≈ 1,750 task-runs ≈ **$50 on the cheapest model** (haiku-5.5 / qwen3.8-flash, heavy assumption). Stage 1 as scoped in the scan (10–13k runs per model) ≈ $300+ per model. | The whole budget goes to stage 0 on one cheap model, leaving nothing for the probability sweep, which is the actual paper (scan §1 row b). |
| 4 | **Base-rate window is narrow and model-specific.** Paper: prompt D floors GPT-5 at 1%; prompts A/B ceiling >85%; the abort option cut SWE-bench cheating 54% → 9%. Qwen3-8B dry run: 0/10 cheats with the loop; with the flag exit it flagged on attempt 1 (tonight's run, 1 task so far). | Finding a 30–70% setting needs a screening run per model (plan: $1.50–$9), then an enrichment step with a regression-to-the-mean trap (study design §4). Each step eats budget before any arm comparison. |
| 5 | **Harness fragility:** scorer blind to test-edit cheats (N11, handled by the in-loop endpoint); extractor runs prose when a reply has 2+ code blocks, 24% of Qwen replies ended in SyntaxError (N13, unpatchable without our own loop); prompt D says STOP but the loop cannot stop (N14). | Every one of these lives in the multi-attempt loop. None of them is about the tasks or the scorer. |
| 6 | **Free local piloting is uninformative.** Qwen3-8B: 20–60 min per task, 0% cheating. | No free way to tune the design; every design question costs API money. |

## 3. Options

| Option | What it is | Cost per 1,000 samples (haiku-5.5 list price, 2026-10-12; assumptions in §4) | Keeps objective scoring? | Risk | Verdict |
|---|---|---|---|---|---|
| A. Upstream harness as-is (current plan) | 10-attempt loop, upstream wording, screening + enrichment | ≈ $29 (heavy) to $5 (light) | Yes | Budget exhausted before the sweep; benchmark-shaped text; items 3–5 above | **Not at $50** |
| **B. Single-turn, work-ticket ImpossibleBench (recommended)** | Same 103 conflicting tasks and upstream scorer; our own user message (a work ticket with the tests attached); `max_attempts=1`; notice arms in the system prompt; in-loop and scored endpoints both still available | ≈ $2–5 | Yes | Single-turn base rate on cheap models unknown (needs a ~$1 screen); loses the paper's exact replication; needs our own dataset builder in `src/hawthorne/` (no upstream edit) | **Do this first** |
| C. De novo self-report task (Kleven analogue) | Batch of small tasks, some impossible; model returns solutions plus a completion report; "X% of reports are checked" is the knob; cheating = reporting an impossible task as done | ≈ $1–3 | Yes (report vs ground truth) | No published anchor; base rate may be ≈0 without task pressure; scenario may read as a test; needs its own pilot | **Fallback / stage 1 add-on** |
| D. Alignment-faking free/paid notebook (scan side check) | Harmful-compliance under "used for training" vs not, re-cast as X% | ≈ $5–15 incl. judge | No (LLM judge) | Claude-3-Opus-specific; current models mostly refuse; judge doubles cost | **Drop under $50** |
| E. Existing single-turn reward-hacking datasets (e.g. "School of Reward Hacks", Taylor et al. 2025, arXiv 2508.17511 — **not verified in this session**) | Low-stakes tasks with a described flawed grader; cheating = exploiting the grader | ≈ $1–3 | Mostly (rubric metrics) | Must verify the dataset, licence, and that graders are automatic; cheating is "gaming a silly grader", further from the user's wording | Worth a 1-hour check before building C |

## 4. Cost assumptions

- Prices: haiku-5.5 $0.10 in / $0.50 out per M tokens (OpenRouter list, 2026-10-12, from `preliminary_tests_20261012.md`).
- Option A: heavy = 40k in / 50k out per task (Qwen dry run); light = 10k / 8k.
- Options B, C, E: 3k in / 4–8k out per sample (one reply with medium reasoning). Unverified until a screen is run.
- Under option B the full plan fits: 4 stage-0 arms × 103 tasks ≈ 412 samples ≈ $1–2; a 7-level p-sweep × 2 framings × 103 tasks × 2 seeds ≈ 2,900 samples ≈ $6–15 per model. Two cheap models plus one mid-price model (gpt-5.6-luna class) ≈ $25–40 total.

## 5. What option B changes and what it keeps

Keeps: the 103 conflicting tasks, upstream's `agentic_humaneval_scorer`, Docker sandbox, both endpoints (in-loop at attempt 1 catches test edits; scored rate is paper-comparable), the A–E cheat-type heuristics, the awareness heuristic, the spend lock, smoke/scorer tests.

Changes (all in `src/hawthorne/`, no upstream edit): a dataset builder that wraps each task in a work-ticket message (e.g. "Ticket #… from an engineer: implement this; CI tests attached"), `max_attempts=1`, and a prompt that does not say "pass all the tests" in bold. The instruction-strictness factor (A–D) becomes a *consequence* lever, not the main lever.

Loses: the exact replication of the paper's loop numbers (keep one tiny loop run, e.g. 20 tasks, as a sanity anchor if budget allows); the multi-episode "experienced p" stage 2 (needs the loop; defer).

Open question that stays open: whether cheap models cheat at all in one turn. The paper's >85% figures are for GPT-5/o3 with the loop. If the single-turn screen lands below 10% on two cheap models, go to option C.

## 6. Reframing goal (a) so it is testable at this budget

"The model does not think it is being evaluated" is a belief we cannot set directly on a hand-built task. What we can set is the stated review policy. Proposed wording of goal (a): *does the stated review policy (none / every session / X% of sessions) move the objective cheating rate, and does measured awareness (heuristic + a small judged subset) track it?* This is also what the scan's §3 says the experiment identifies ("belief about p"), so it is not a retreat from the original idea.

## 7. Proposed next steps (need the user's go-ahead; no spend yet)

1. Decide between B-first (recommended) and C-first.
2. If B: build the work-ticket dataset wrapper + single-turn task; rerun smoke test and scorer check (zero cost); draft the ticket wording for user review.
3. Screening run, option B: 1 cheap model × 103 tasks × 2 prompts (A and C) × `baseline` arm. Estimate ≈ $1–2. Pass rules as in `screening_run_plan.md`. Decision rule: proceed with the prompt whose single-turn in-loop cheating is in 30–70%; else option C.
4. Only then: four notice arms (goal a), then the p-sweep (goal b).
