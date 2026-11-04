"""Run hawthorne_lcb for one model over chosen arms x instruction prompts (Docker sandbox).

Free local example:
  uv run --no-sync python scripts/run_pilot.py --model ollama/qwen3-8b-32k \
      --arms baseline --instructions upstream_tuned --flag-exit --limit 2 \
      --log-dir logs/pilot_local_qwen3-8b_flag

Paid models are refused unless --paid-ok is passed. Pass it only after checking
the run's model, sample size and estimated cost. Summarise with scripts/summarize_logs.py.

Token caps default to upstream demo.py (reasoning effort "medium", 4096 reasoning tokens) plus
a 16,000-token cap per reply.

--limit takes a count (N = first N tasks in dataset order; shuffle is off) or a range START:STOP
(0-based, STOP exclusive, like a Python slice). A 20-task canary is `--limit 20`; continuing the
same config on the remaining tasks without re-running the canary is `--limit 20:103`. Summarise
both log dirs together: `summarize_logs.py logs/a_canary logs/a_rest`.

--max-tasks N runs N arms concurrently (sharing --max-connections), so time or routing drift cannot
line up with arm. --provider pins the OpenRouter upstream provider with fallbacks off; the
provider that actually served each call is recorded in the log and reported by summarize_logs.py.

--temperature is passed to the provider only when given; by default the provider's own default
applies (same as upstream demo.py, which sets none). Record the value used in the spend log.
"""

import argparse

from dotenv import load_dotenv
from inspect_ai import eval as inspect_eval

from hawthorne import INSTRUCTIONS, NOTICE_ARMS, hawthorne_lcb
import hawthorne.glm_raw  # noqa: F401  (registers glmraw/: raw-template OpenRouter route with a hard run budget)

FREE_PREFIXES = ("ollama/", "mockllm/", "vllm/")

def parse_limit(text: str):
    """'20' -> 20 (first 20 tasks); '20:103' -> (20, 103) (tasks 20..102, 0-based)."""
    if ":" in text:
        start, stop = (int(x) for x in text.split(":", 1))
        if not 0 <= start < stop:
            raise argparse.ArgumentTypeError(f"bad range {text!r}: need 0 <= START < STOP")
        return (start, stop)
    n = int(text)
    if n <= 0:
        raise argparse.ArgumentTypeError(f"bad count {text!r}: need a positive integer")
    return n


ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--arms", nargs="+", default=["baseline"], choices=list(NOTICE_ARMS))
ap.add_argument("--instructions", nargs="+", default=["upstream_tuned"], choices=list(INSTRUCTIONS))
ap.add_argument("--flag-exit", action="store_true", help="append FLAG_EXIT to the instruction")
ap.add_argument("--presentation", choices=["upstream", "ticket"], default="upstream", help="task wording")
ap.add_argument("--split", default="conflicting")
ap.add_argument("--limit", type=parse_limit, default=5, help="count N, or range START:STOP (0-based, STOP exclusive)")
ap.add_argument("--temperature", type=float, default=None, help="sampling temperature; omit for the provider default")
ap.add_argument("--max-attempts", type=int, default=10)
ap.add_argument("--max-connections", type=int, default=1)
ap.add_argument("--max-tasks", type=int, default=1, help="arms run concurrently; default 1 = one after another")
ap.add_argument("--provider", default=None, help="OpenRouter upstream provider to pin, fallbacks off, e.g. OpenAI, DeepSeek")
ap.add_argument("--max-tokens", type=int, default=16000, help="cap per reply")
ap.add_argument("--reasoning-effort", default="medium", choices=["none", "minimal", "low", "medium", "high"])
ap.add_argument("--reasoning-tokens", type=int, default=4096)
ap.add_argument("--paid-ok", action="store_true", help="required for any non-local model; check the cost first")
ap.add_argument("--budget", type=float, default=None, help="glmraw/ models only: hard cap in USD on OpenRouter-reported spend (required for glmraw)")
ap.add_argument("--log-dir", required=True)
args = ap.parse_args()

if not args.model.startswith(FREE_PREFIXES) and not args.paid_ok:
    raise SystemExit(f"{args.model} is a paid model. Check the cost (model, size), "
                     "then rerun with --paid-ok.")

load_dotenv()  # API keys from .env (git-ignored); not needed for local models

# A count is applied inside the task (as before). A range is applied by Inspect's eval(limit=...)
# after the task builds its full dataset, so START:STOP indexes the same dataset order as a count.
task_limit = args.limit if isinstance(args.limit, int) else None
eval_limit = args.limit if isinstance(args.limit, tuple) else None

tasks = [hawthorne_lcb(split=args.split, notice_arm=arm, instruction=instr, flag_exit=args.flag_exit,
                       presentation=args.presentation, max_attempts=args.max_attempts, sandbox="docker", limit=task_limit)
         for arm in args.arms for instr in args.instructions]
gen_kwargs = {"temperature": args.temperature} if args.temperature is not None else {}
model_args = {}
if args.model.startswith("glmraw/"):
    if args.budget is None:
        raise SystemExit("glmraw/ runs need --budget USD (hard cap)")
    model_args = {"provider": args.provider, "budget_usd": args.budget}
elif args.provider:
    if not args.model.startswith("openrouter/"):
        raise SystemExit("--provider only applies to openrouter/ models")
    # OpenRouter routing: only this upstream provider, no fallback (inspect_ai openrouter.py, 'provider' model arg).
    model_args["provider"] = {"order": [args.provider], "allow_fallbacks": False}
logs = inspect_eval(tasks, model=args.model, model_args=model_args, log_dir=args.log_dir, max_connections=args.max_connections,
                    max_tasks=args.max_tasks, limit=eval_limit, max_tokens=args.max_tokens, reasoning_effort=args.reasoning_effort,
                    reasoning_tokens=args.reasoning_tokens, fail_on_error=False, display="plain", **gen_kwargs)
for lg in logs:
    print(f"{lg.eval.task}: status={lg.status} -> {lg.location}")
print(f"\nSummarise: uv run --no-sync python scripts/summarize_logs.py {args.log_dir}")
