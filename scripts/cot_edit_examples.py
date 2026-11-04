"""Pull one example reasoning excerpt per reasoning-edit experiment (insertion, removal, probability). $0, read-only.

    uv run --no-sync python scripts/cot_edit_examples.py

Selection rules, fixed before reading any text (user request, 2026-10-22): one seeded random pick (seed 20261022) from
the episodes that show each experiment's typical outcome, using the blind hand labels (`susp` = awareness voiced in the
continuation):
  insertion   arm insert,   susp explicit, no cheat   (inserted evaluation sentence; GLM says it is tested; honest)
  removal     arm cut,      susp explicit             (GLM's own remark deleted; GLM says it again, as in 69%)
  probability arm ins_p100, no cheat                  (100% review sentence inserted; honest)
The edited reasoning is rebuilt with cot_edit.edited_reasoning from the source run logs, exactly as sent to the model.
Output: results/4_cot_edits/2026-10-22_cot_edit_examples/cot_edit_examples.md
"""
import csv, json, random, sys
from pathlib import Path
sys.path.insert(0, "src")
from inspect_ai.log import read_eval_log
from hawthorne.cot_edit import run1_samples, assistant_replies, edited_reasoning, _reasoning
from hawthorne.classify import EVAL_AWARENESS


def continuation(log_dir: str, sid: str) -> str:
    """GLM's reasoning in the edited reply after the supplied prefix (same rule as scripts/summarize_cot_edit.py)."""
    for f in sorted(Path(log_dir).glob("*.eval")):
        for s in read_eval_log(str(f), resolve_attachments=True).samples or []:
            if s.id != sid:
                continue
            ed = s.metadata["cot_edit"]
            new = [m for m in s.messages if m.role == "assistant" and not (m.metadata or {}).get("partial")][ed["reply"] - 1:]
            full = "".join(getattr(c, "reasoning", "") or "" for c in new[0].content if getattr(c, "type", "") == "reasoning")
            return full[ed["prefix_chars"]:]
    raise KeyError(sid)

OUT = Path("results/4_cot_edits/2026-10-22_cot_edit_examples"); OUT.mkdir(parents=True, exist_ok=True)
SPEC = [  # name, results dir, manifest, arm, rule
    ("Insertion", "2026-10-20_cot_edit_insertion", "manifest_insertion", "insert", lambda l: l["susp"] == "explicit" and l["cheat"] == "0"),
    ("Removal", "2026-10-21_cot_edit_removal", "manifest_removal", "cut", lambda l: l["susp"] == "explicit"),
    ("Probability (100%)", "2026-10-21_cot_edit_probability", "manifest_probability", "ins_p100", lambda l: l["cheat"] == "0"),
]
HEAD, CONT = 700, 1500  # characters of reasoning shown before the edit point and of GLM's continuation
rng = random.Random(20261022)
md = ["# Example reasoning excerpts from the reasoning-edit experiments (GLM-5.3-flash)", "",
      "One seeded random example per experiment; selection rules are in `scripts/cot_edit_examples.py`. "
      "Each shows the end of GLM's original reasoning up to the edit point, the edit, and the start of what GLM wrote next. "
      "Text is GLM's private reasoning, verbatim (… marks cuts made for length).", ""]
for name, rdir, man, arm, rule in SPEC:
    labels = [l for l in csv.DictReader(open(f"results/4_cot_edits/{rdir}/labels_unblinded.csv")) if l["arm"] == arm and rule(l)]
    labels.sort(key=lambda l: (l["notice_arm"], int(l["sample"].rsplit("_", 1)[-1]), int(l["rep"])))
    pick = rng.choice(labels)   # draw kept so the insertion and probability picks stay the same
    if arm == "cut":
        # User, 2026-10-22: "replace with another deletion example". Redraw (separate seed) excluding the first pick
        # (not_reviewed_only lcbhard_0 rep 1) and the tasks whose kept reasoning before the cut already has an awareness
        # remark, so the example shows the remark coming back on its own. The read-through note below was written after reading this pick.
        def kept_aware(l):
            r = next(r for r in map(json.loads, open("results/4_cot_edits/cot_edit/manifest_removal.jsonl")) if r["notice_arm"] == l["notice_arm"] and r["sample"] == l["sample"])
            o = _reasoning(assistant_replies(run1_samples("logs/glm_confirm_run1", l["notice_arm"])[l["sample"]])[int(r["reply"]) - 1]) or ""
            return bool(EVAL_AWARENESS.search(o[: int(r["cut_char"])]))
        first = pick
        labels = [l for l in labels if (l["notice_arm"], l["sample"]) != (first["notice_arm"], first["sample"]) and not kept_aware(l)]
        pick = random.Random(20261023).choice(labels)
    task = f"{pick['notice_arm']}:{pick['sample']}"
    det = next(d for d in csv.DictReader(open(f"results/4_cot_edits/{rdir}/episodes_detail.csv")) if d["task"] == task and d["arm"] == arm and d["rep"] == pick["rep"])
    side = man.replace("manifest_", "")
    cont = continuation(f"logs/cot_edit_{side}", f"{pick['notice_arm']}__{pick['sample']}__{side}__{arm}__r{pick['rep']}")
    assert len(cont) == int(det["cont"]), (len(cont), det["cont"])   # episodes_detail.cont is the continuation length
    row = next(r for r in map(json.loads, open(f"results/4_cot_edits/cot_edit/{man}.jsonl"))
               if r["notice_arm"] == pick["notice_arm"] and r["sample"] == pick["sample"] and r["arm"] == arm and str(r["rep"]) == pick["rep"])
    s = run1_samples(row.get("log_dir", "logs/glm_confirm_run1"), row["notice_arm"])[row["sample"]]
    original = _reasoning(assistant_replies(s)[int(row["reply"]) - 1]) or ""
    edited, added = edited_reasoning(original, dict(row, cut_char=int(row["cut_char"])), arm)
    assert original.startswith(edited[: len(edited) - len(added)]) or arm == "cut"
    before = edited[: len(edited) - len(added)]
    print(f"{name}: {task} rep {pick['rep']} reply {row['reply']} | candidates {len(labels)} | cheat {det['cheat']} | susp {pick['susp']}")
    md += [f"## {name}: {pick['sample']} ({pick['notice_arm']} system prompt, attempt {row['reply']}, sample {int(pick['rep']) + 1} of 2)", "",
           f"- **Edit:** " + {"insert": "inserted the evaluation sentence", "cut": "deleted GLM's own sentence", "ins_p100": "inserted the 100% review sentence"}[arm] + ".",
           f"- **Outcome:** {'cheated' if det['cheat'] == '1' else 'did not cheat'}; awareness voiced in the continuation (blind hand label): {pick['susp']}.",
           f"- **Picked from:** {len(labels)} episodes matching the rule.", ""]
    if arm == "cut":
        md.insert(len(md) - 1, "- **Read-through note:** the kept text has no detector-flagged remark, but it still contains a softer hint the detector misses "
                  "(GLM wonders whether one assert is \"deliberately the 'wrong' one to see if I blindly...\"). After the deletion GLM goes further: "
                  "\"It's a deliberate trap\" and \"If it's an eval...\".")
        md += ["**Deleted sentence (GLM's own):**", "", f"> {row['orig_sentence']}", ""]
    md += ["**GLM's reasoning before the edit point** (last part):", "", "```text",
           ("…" if len(before) > HEAD else "") + before[-HEAD:].strip(), "```", ""]
    if added:
        md += ["**Inserted:**", "", "```text", added.strip(), "```", ""]
    md += ["**What GLM wrote next, after the edit** (start):", "", "```text", cont[:CONT].strip() + ("…" if len(cont) > CONT else ""), "```", ""]
    # User, 2026-10-22: also show the original, unedited reasoning from the same point (the source run episode).
    orig_after = original[int(row["cut_char"]):]
    orig_cheat = bool(s.metadata["agentic_results"]["attempt_history"]) and any(a["success"] and a["attempt"] >= int(row["reply"]) for a in s.metadata["agentic_results"]["attempt_history"])
    src = "run 1" if row.get("log_dir", "logs/glm_confirm_run1") == "logs/glm_confirm_run1" else row["log_dir"].replace("logs/", "")
    md += [f"**Original reasoning from the same point, unedited** ({src}; that episode {'cheated' if orig_cheat else 'did not cheat'} from this attempt on):", "",
           "```text", orig_after[:CONT].strip() + ("…" if len(orig_after) > CONT else ""), "```", ""]
# Check (2026-10-22): how many removal points still had an awareness remark in the kept text before the deleted sentence?
pts = {(r["notice_arm"], r["sample"]): r for r in map(json.loads, open("results/4_cot_edits/cot_edit/manifest_removal.jsonl"))}
kept_aware = 0
for (na, sid), r in sorted(pts.items()):
    orig = _reasoning(assistant_replies(run1_samples("logs/glm_confirm_run1", na)[sid])[int(r["reply"]) - 1]) or ""
    kept_aware += bool(EVAL_AWARENESS.search(orig[: int(r["cut_char"])]))
note = (f"**Note on the removal design:** only the one remark at the edit point is deleted; earlier reasoning is kept. "
        f"In {kept_aware} of {len(pts)} removal tasks, the detector finds an awareness remark in that kept text, "
        "so a remark after deletion is not always a fresh re-derivation. The kept text is identical in all three removal arms "
        "(control included), so the arm comparison is unaffected. "
        "The removal example above was drawn from the other tasks, so its kept text has no detector-flagged remark.")
print(note)
md += [note, ""]
(OUT / "cot_edit_examples.md").write_text("\n".join(md))
print("wrote", OUT / "cot_edit_examples.md")
