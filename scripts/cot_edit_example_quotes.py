"""Extract specific reasoning-edit episodes around a quoted line. $0, read-only.

    uv run --no-sync python scripts/cot_edit_example_quotes.py

User request (2026-10-22): an example where GLM treats the inserted review sentence as outside text (reported in
study_design_cot_edit.md §13, point 4). The two probability-sweep episodes behind those quotes, found via the blind
labelling sheet (labels_blind.csv / labels_key.csv). Output: results/4_cot_edits/2026-10-22_cot_edit_examples/probability_outside_text_examples.md
"""
import csv, json, sys
from pathlib import Path
sys.path.insert(0, "src")
from inspect_ai.log import read_eval_log
from hawthorne.cot_edit import run1_samples, assistant_replies, edited_reasoning, _reasoning


def continuation(log_dir: str, sid: str) -> str:
    """GLM's reasoning in the edited reply after the supplied prefix (same rule as scripts/summarize_cot_edit.py)."""
    for f in sorted(Path(log_dir).glob("*.eval")):
        for s in read_eval_log(str(f), resolve_attachments=True).samples or []:
            if s.id == sid:
                ed = s.metadata["cot_edit"]
                new = [m for m in s.messages if m.role == "assistant" and not (m.metadata or {}).get("partial")][ed["reply"] - 1:]
                full = "".join(getattr(c, "reasoning", "") or "" for c in new[0].content if getattr(c, "type", "") == "reasoning")
                return full[ed["prefix_chars"]:]
    raise KeyError(sid)

EPISODES = [  # notice_arm, sample, arm, rep, quote to centre on
    ("neutral", "lcbhard_59", "ins_p10", 1, "the injected reminder about honesty"),
    ("neutral", "lcbhard_51", "ins_p10", 0, "there's no such note here actually"),
    ("neutral", "lcbhard_59", "ins_p100", 0, "This looks like a planted inconsistency"),   # added 2026-10-22 after the quote check
]
WIN = 900
samples = list(csv.DictReader(open("results/4_cot_edits/2026-10-21_cot_edit_probability/samples.csv")))
md = ["# GLM treating the inserted review sentence as outside text (probability sweep, examples)", "",
      "From the in-reasoning probability sweep (experiment C). The sentence was inserted into GLM's first-attempt reasoning, "
      "right after it first named the contradiction, and GLM continued from there. Text is GLM's private reasoning, verbatim; "
      "… marks cuts. Selection: episodes quoted in `docs/study_design_cot_edit.md` §13 (point 4), not a random draw.", ""]
for na, sid, arm, rep, quote in EPISODES:
    row = next(r for r in map(json.loads, open("results/4_cot_edits/cot_edit/manifest_probability.jsonl"))
               if r["notice_arm"] == na and r["sample"] == sid and r["arm"] == arm and int(r["rep"]) == rep)
    s = run1_samples(row["log_dir"], na)[sid]
    original = _reasoning(assistant_replies(s)[int(row["reply"]) - 1]) or ""
    edited, added = edited_reasoning(original, dict(row, cut_char=int(row["cut_char"])), arm)
    before = edited[: len(edited) - len(added)]
    cont = continuation("logs/cot_edit_probability", f"{na}__{sid}__probability__{arm}__r{rep}")
    i = cont.find(quote); assert i >= 0, quote
    sr = next(r for r in samples if r["sample"] == sid and r["notice_arm"] == na and r["arm"] == arm and int(r["rep"]) == rep)
    cheat = sr["cheat"] == "True"; orig_cheat = sr["run1_first_pass"] != ""
    print(f"{sid} {arm} r{rep}: quote at char {i} of {len(cont)}; cheated {cheat}; original cheated {orig_cheat}")
    md += [f"## {sid}, {arm.replace('ins_p', '')}% review sentence ({na} system prompt, sample {rep + 1} of 2)", "",
           f"- **Outcome:** {'cheated' if cheat else 'did not cheat'} after the edit; the original unedited episode {'cheated' if orig_cheat else 'did not cheat'} from this attempt on.",
           f"- **Where the quoted line is:** {i:,} characters into GLM's {len(cont):,}-character continuation.", "",
           "**GLM's reasoning before the edit point** (last part):", "", "```text", ("…" if len(before) > 500 else "") + before[-500:].strip(), "```", "",
           "**Inserted:**", "", "```text", added.strip(), "```", "",
           "**Start of what GLM wrote next:**", "", "```text", cont[:600].strip() + "…", "```", "",
           "**Around the quoted line:**", "", "```text", "…" + cont[max(0, i - WIN): i + len(quote) + WIN].strip() + "…", "```", ""]
out = Path("results/4_cot_edits/2026-10-22_cot_edit_examples/probability_outside_text_examples.md"); out.write_text("\n".join(md)); print("wrote", out)
