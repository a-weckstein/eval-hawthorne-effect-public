"""Run the reasoning-edit experiment from a manifest (one Inspect task per edited-reply index, run concurrently).

  uv run --no-sync python scripts/run_cot_edit.py --manifest results/4_cot_edits/cot_edit/manifest_insertion.jsonl \
      --log-dir logs/cot_edit_pilot --paid-ok
Refuses without --paid-ok unless --model is mockllm/. Paid runs cost money: check model, size and cost first.
Defaults match GLM run 1: glmraw/z-ai/glm-5.3-flash, host InferenceNet, effort low, 64k cap.
"""
import argparse, json
from dotenv import load_dotenv
from inspect_ai import eval as inspect_eval
import hawthorne.glm_raw  # noqa: F401  (registers the glmraw provider)
from hawthorne.cot_edit import hawthorne_cot_edit

ap = argparse.ArgumentParser()
ap.add_argument("--manifest", required=True)
ap.add_argument("--run1", default="logs/glm_confirm_run1")
ap.add_argument("--model", default="glmraw/z-ai/glm-5.3-flash")
ap.add_argument("--provider", default="InferenceNet")
ap.add_argument("--max-tokens", type=int, default=64000)
ap.add_argument("--reasoning-effort", default="low")
ap.add_argument("--max-connections", type=int, default=8)
ap.add_argument("--sandbox", default="docker", choices=["docker", "local"])
ap.add_argument("--paid-ok", action="store_true")
ap.add_argument("--budget", type=float, default=None, help="hard cap in USD on OpenRouter-reported spend for this run (required for paid runs)")
ap.add_argument("--log-dir", required=True)
a = ap.parse_args()
if not a.model.startswith("mockllm/") and not a.paid_ok:
    raise SystemExit("paid model: check the cost, then pass --paid-ok")
if a.model.startswith("glmraw/") and a.sandbox != "docker":
    raise SystemExit("real-model runs use the Docker sandbox")
if not a.model.startswith("mockllm/") and a.budget is None:
    raise SystemExit("paid run: pass --budget USD (the spending ceiling); the connector stops calling once it is reached")
import csv
rows_ = [json.loads(l) for l in open(a.manifest) if l.strip()]
run1_cost = {(r["arm"], r["sample"]): float(r["cost_usd"]) for r in csv.DictReader(open("results/2_hawthorne_effect/2026-10-14_glm_confirm_run1/samples.csv"))}
upper = sum(run1_cost.get((r["notice_arm"], r["sample"]), 0.0) for r in rows_)
print(f"{len(rows_)} episodes; upper estimate from run-1 cost of the same tasks: ${upper:.2f} (insertion side ran at 0.49x this); hard cap: {a.budget}")
load_dotenv(".env")
replies = sorted({json.loads(l)["reply"] for l in open(a.manifest) if l.strip()})
tasks = [hawthorne_cot_edit(manifest=a.manifest, run1_log_dir=a.run1, reply=k, sandbox=a.sandbox) for k in replies]
margs = {"provider": a.provider, "budget_usd": a.budget} if a.model.startswith("glmraw/") else {}
logs = inspect_eval(tasks, model=a.model, model_args=margs, log_dir=a.log_dir, max_tasks=len(tasks),
                    max_connections=a.max_connections, max_tokens=a.max_tokens, reasoning_effort=a.reasoning_effort,
                    fail_on_error=False, display="plain")
for lg in logs:
    print(f"{lg.eval.task}: status={lg.status} -> {lg.location}")
print(f"\nSummarise: uv run --no-sync python scripts/summarize_cot_edit.py {a.log_dir}")
