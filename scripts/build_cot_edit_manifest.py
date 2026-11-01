"""Build the reasoning-edit manifest ($0; reads run-1 logs and hand labels). Design: docs/study_design_cot_edit.md.

  uv run --no-sync python scripts/build_cot_edit_manifest.py --reps 2 --out results/4_cot_edits/cot_edit/manifest.jsonl
  uv run --no-sync python scripts/build_cot_edit_manifest.py --pilot 10 --reps 1 --out results/4_cot_edits/cot_edit/manifest_pilot.jsonl
--sides followup (D35): the 48 insertion points again, as side "followup" (arms insert_real / insert_hedged / prompt_eval):
  uv run --no-sync python scripts/build_cot_edit_manifest.py --sides followup --reps 2 --out results/4_cot_edits/cot_edit/manifest_followup.jsonl
--pilot N keeps the first N removal-side tasks (by task number, then notice arm); --pilot-insert M adds the first M
insertion-side tasks by the same rule (default 0). Mixed pilot (D27): --pilot 5 --pilot-insert 5 --reps 1.
"""
import argparse, collections, json
from pathlib import Path
from hawthorne.cot_edit import build_manifest, insertion_points, probability_points, removal_points

ap = argparse.ArgumentParser()
ap.add_argument("--labels", default="results/2_hawthorne_effect/2026-10-14_glm_confirm_run1/eval_awareness_handlabels.csv")
ap.add_argument("--run1", default="logs/glm_confirm_run1")
ap.add_argument("--reps", type=int, default=2)
ap.add_argument("--pilot", type=int, default=None)
ap.add_argument("--pilot-insert", type=int, default=0)
ap.add_argument("--sides", nargs="+", default=["removal", "insertion"])
ap.add_argument("--per-arm", type=int, default=20, help="probability side: tasks per notice arm (neutral, filler)")
ap.add_argument("--out", required=True)
a = ap.parse_args()
pts = removal_points(a.labels, a.run1) if "removal" in a.sides else []
order = lambda p: (int(p["sample"].rsplit("_", 1)[-1]), p["notice_arm"])
if a.pilot:
    pts = sorted(pts, key=order)[: a.pilot]
    if a.pilot_insert:
        pts += sorted(insertion_points(a.labels, a.run1), key=order)[: a.pilot_insert]
elif "insertion" in a.sides:
    pts += insertion_points(a.labels, a.run1)
if "followup" in a.sides:
    pts += [dict(p, side="followup") for p in insertion_points(a.labels, a.run1)]
if "probability" in a.sides:
    pts += probability_points(a.labels, a.run1, "results/2_hawthorne_effect/2026-10-18_glm_confirm_run2/eval_awareness_snippets.csv", "logs/glm_confirm_run2",
                              per_arm=a.per_arm)
rows = build_manifest(pts, a.reps)
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
with open(a.out, "w") as fh:
    for r in rows: fh.write(json.dumps(r) + "\n")
print(f"points: {len(pts)}  rows: {len(rows)}  -> {a.out}")
print("by side x arm:", dict(collections.Counter((r['side'], r['arm']) for r in rows)))
print("by edited reply:", dict(collections.Counter(r['reply'] for r in rows)))
print("by notice arm (points):", dict(collections.Counter((p['side'], p['notice_arm']) for p in pts)))
