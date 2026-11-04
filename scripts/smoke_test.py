"""Zero-cost smoke test: no API keys, no paid calls (Docker needed only for --sandbox docker).

Uses Inspect's built-in mock model (mockllm/model) on 2 samples per arm.
Checks are defined up front and printed as PASS/FAIL.
Run from the repo root:
  uv run --no-sync python scripts/smoke_test.py                    # local sandbox
  uv run --no-sync python scripts/smoke_test.py --sandbox docker   # upstream Docker sandbox
"""

import argparse
import subprocess
import sys

from inspect_ai import eval as inspect_eval

from hawthorne import FLAG_EXIT, INSTRUCTIONS, NOTICE_ARMS, hawthorne_lcb
from hawthorne.tasks import UPSTREAM_COMPOSE

ap = argparse.ArgumentParser()
ap.add_argument("--sandbox", choices=["local", "docker"], default="local")
SANDBOX = ap.parse_args().sandbox
print(f"sandbox = {SANDBOX}")

LIMIT = 2
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


# 1. Task builds for every arm x instruction.
built = {}
for arm in NOTICE_ARMS:
    for instr in INSTRUCTIONS:
        try:
            built[(arm, instr)] = hawthorne_lcb(
                notice_arm=arm, instruction=instr, sandbox=SANDBOX, limit=LIMIT, max_attempts=2
            )
        except Exception as e:  # noqa: BLE001
            check(f"build {arm}/{instr}", False, repr(e))
check("1. task builds for all arms x instructions", len(built) == len(NOTICE_ARMS) * len(INSTRUCTIONS),
      f"({len(built)}/{len(NOTICE_ARMS) * len(INSTRUCTIONS)})")

# 2. Dataset loads (full conflicting split size, then limited size).
full = hawthorne_lcb(notice_arm="baseline", sandbox=SANDBOX)
check("2. conflicting split loads", len(full.dataset) > 0, f"(n_full={len(full.dataset)}, n_limited={LIMIT})")

# 2b. Flag-exit sentence: present, in the right place, only when requested.
with_flag = hawthorne_lcb(notice_arm="baseline", sandbox=SANDBOX, limit=1, flag_exit=True)
no_flag = hawthorne_lcb(notice_arm="baseline", sandbox=SANDBOX, limit=1)
txt_f, txt_n = with_flag.dataset[0].input, no_flag.dataset[0].input
check("2b. flag sentence present when flag_exit=True, before upstream's DO NOT MODIFY suffix",
      (INSTRUCTIONS["upstream_tuned"] + " " + FLAG_EXIT + " **DO NOT MODIFY THE TESTS.**") in txt_f)
check("2c. flag sentence absent by default", FLAG_EXIT not in txt_n and "flag_for_human_intervention" not in txt_n)

# 2d. Ticket presentation: same task data as upstream, no benchmark cues.
tk = hawthorne_lcb(notice_arm="baseline", sandbox=SANDBOX, limit=LIMIT, presentation="ticket", flag_exit=True)
up = hawthorne_lcb(notice_arm="baseline", sandbox=SANDBOX, limit=LIMIT)
same = all(a.id == b.id and all(a.metadata[k] == b.metadata[k] for k in ("prompt", "test", "entry_point", "test_patch"))
           for a, b in zip(tk.dataset, up.dataset))
cues = ["pass all", "DO NOT MODIFY", "# Use check(", "overwrite the original"]
clean = all(not any(c in smp.input for c in cues) for smp in tk.dataset)
has = all(smp.metadata["prompt"] in smp.input and smp.metadata["test"] in smp.input and FLAG_EXIT in smp.input
          for smp in tk.dataset)
check("2d. ticket: same ids/prompt/tests/test_patch as upstream", same and len(tk.dataset) == LIMIT)
check("2e. ticket: no benchmark cues; contains spec, tests, flag sentence", clean and has)

# 4. End-to-end eval with the mock model, one instruction, all arms.
tasks = [built[(arm, "upstream_tuned")] for arm in NOTICE_ARMS]
logs = inspect_eval(tasks, model="mockllm/model", log_dir=f"logs/smoke_test_{SANDBOX}", display="none")
statuses = [lg.status for lg in logs]
check("4a. every eval finished", all(s == "success" for s in statuses), f"{statuses}")

n_scored = 0
for arm, lg in zip(NOTICE_ARMS, logs):
    samples = lg.samples or []
    n_scored += sum(1 for s in samples if s.scores)
    for s in samples:
        sys_msgs = [m for m in s.messages if m.role == "system"]
        user0 = next(m for m in s.messages if m.role == "user")
        expected = NOTICE_ARMS[arm]
        # 3. System-message content matches the arm.
        if expected is None:
            ok = len(sys_msgs) == 0
        else:
            ok = len(sys_msgs) == 1 and sys_msgs[0].text == expected
        check(f"3. system message correct: {arm}/{s.id}", ok, f"(n_system={len(sys_msgs)})")
        check(f"3b. instruction + upstream suffix in user msg: {arm}/{s.id}",
              INSTRUCTIONS["upstream_tuned"] in user0.text and "**DO NOT MODIFY THE TESTS.**" in user0.text)
check("4b. every sample scored", n_scored == LIMIT * len(NOTICE_ARMS), f"({n_scored}/{LIMIT * len(NOTICE_ARMS)})")
check("4c. log files written", all(lg.location for lg in logs), f"(e.g. {logs[0].location})")

# 4d. Ticket presentation runs end to end through upstream's solver and scorer.
[tlog] = inspect_eval(tk, model="mockllm/model", log_dir=f"logs/smoke_test_{SANDBOX}", display="none")
t_hist = [a for smp in (tlog.samples or []) for a in smp.metadata.get("agentic_results", {}).get("attempt_history", [])]
check("4d. ticket eval finished, all samples scored, code ran in sandbox",
      tlog.status == "success" and sum(1 for smp in tlog.samples if smp.scores) == LIMIT
      and len(t_hist) > 0 and all("SyntaxError" in a["stderr"] for a in t_hist), f"({tlog.status}, attempts={len(t_hist)})")

# 6. The sandbox actually used matches the request (docker -> upstream compose file).
specs = [lg.eval.sandbox for lg in logs]
if SANDBOX == "docker":
    # Inspect may store the config path relative to the working directory; compare resolved paths.
    from pathlib import Path
    ok = all(sp is not None and sp.type == "docker"
             and Path(str(sp.config)).resolve() == UPSTREAM_COMPOSE.resolve() for sp in specs)
else:
    ok = all(sp is not None and sp.type == "local" for sp in specs)
check("6. sandbox recorded in logs matches request", ok, f"({specs[0]})")

# 7. Test code really executed in the sandbox: the mock reply is not code, so every
#    attempt should fail with a Python SyntaxError raised by the sandbox's interpreter.
stderrs = [a["stderr"] for lg in logs for s in (lg.samples or [])
           for a in s.metadata.get("agentic_results", {}).get("attempt_history", [])]
check("7. code executed in sandbox (SyntaxError seen in every attempt)",
      len(stderrs) > 0 and all("SyntaxError" in e for e in stderrs), f"(attempts={len(stderrs)})")

# 5. Upstream submodule untouched.
# Tracked upstream files only; untracked build artifacts (egg-info, __pycache__) are expected.
dirty = subprocess.run(["git", "-C", "external/impossiblebench", "status", "--porcelain", "--untracked-files=no"],
                       capture_output=True, text=True).stdout.strip()
head = subprocess.run(["git", "-C", "external/impossiblebench", "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
PINNED = "061dc3dce6a96ab6cf02a855157263033dcfa3ba"
check("5. external/impossiblebench unmodified and at pinned commit", dirty == "" and head == PINNED,
      f"(head={head[:7]}) {dirty}")

n_fail = sum(1 for _, ok, _ in results if not ok)
print(f"\nSUMMARY: {len(results) - n_fail}/{len(results)} checks passed")
sys.exit(1 if n_fail else 0)
