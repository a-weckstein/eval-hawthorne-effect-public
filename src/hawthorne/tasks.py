"""Inspect task that wraps ImpossibleBench's LiveCodeBench task with a notice arm.

Nothing in external/impossiblebench is modified. The notice is injected as a
system message ahead of ImpossibleBench's own minimal-scaffold solver.

presentation="upstream" uses upstream's task (exact prompt text). presentation="ticket"
loads the same HF dataset with our own work-ticket wording (notices.TICKET_*) but reuses
upstream's solver and scorer unchanged, with the same metadata fields (incl. test_patch,
so scoring matches upstream).
"""

from pathlib import Path

import impossiblebench
from inspect_ai import Task, task
from inspect_ai.dataset import Sample, hf_dataset
from inspect_ai.solver import chain, system_message

from impossiblebench import agentic_humaneval_scorer, agentic_humaneval_solver, impossible_livecodebench

from .notices import (FLAG_EXIT, INSTRUCTIONS, NOTICE_ARMS, TICKET_FORMAT, TICKET_GUIDANCE,
                      TICKET_NO_EDIT, TICKET_REQUEST, TICKET_TEMPLATE)

HF_DATASET = "fjzzq2002/impossible_livecodebench"  # same source as upstream

# Upstream's own sandbox config: image aisiuk/inspect-tool-support, network off, 1 GB memory.
# Passed explicitly so Inspect does not depend on where it searches for a compose file.
UPSTREAM_COMPOSE = Path(impossiblebench.__file__).parent / "compose.yaml"


def _resolve_sandbox(sandbox: str):
    if sandbox == "docker":
        return ("docker", str(UPSTREAM_COMPOSE))
    if sandbox == "local":
        return "local"
    raise ValueError(f"sandbox must be 'docker' or 'local'; got {sandbox!r}")


def ticket_request(entry_point: str, instruction: str, flag_exit: bool) -> str:
    parts = [TICKET_REQUEST.format(ep=entry_point), TICKET_GUIDANCE[instruction], TICKET_NO_EDIT,
             FLAG_EXIT if flag_exit else "", TICKET_FORMAT]
    return " ".join(p for p in parts if p)


def _ticket_record_to_sample(instruction: str, flag_exit: bool):
    def convert(record: dict) -> Sample:
        ep = record["entry_point"]
        request = ticket_request(ep, instruction, flag_exit)
        return Sample(
            id=record["task_id"],
            input=TICKET_TEMPLATE.format(request=request, ep=ep, prompt=record["prompt"], test=record["test"]),
            target="",
            # Same fields as upstream record_to_sample (livecodebench_tasks.py), so upstream's
            # solver and scorer behave identically.
            metadata={
                "prompt": record["prompt"],
                "test": record["test"],
                "entry_point": ep,
                "instruction_prompt": request,
                "impossible_type": record.get("impossible_type", "original"),
                "task_id": record["task_id"],
                "test_patch": record["test"],
            },
        )
    return convert


@task
def hawthorne_lcb(
    split: str = "conflicting",
    notice_arm: str = "baseline",
    instruction: str = "upstream_tuned",
    flag_exit: bool = False,
    presentation: str = "upstream",
    max_attempts: int = 10,
    message_limit: int = 50,
    allow_test_modifications: bool = True,
    sandbox: str = "docker",
    limit: int | None = None,
    shuffle: bool = False,
) -> Task:
    """Impossible-LiveCodeBench, minimal scaffold, with one monitoring-notice arm.

    Defaults mirror demo.py replicate_lcb (max_attempts=10, message_limit=50,
    test modifications allowed, tuned prompt). split='conflicting' is the stage 0
    primary split. flag_exit=True appends FLAG_EXIT to the instruction.
    presentation: "upstream" (exact upstream prompt) or "ticket" (work-ticket wording).
    """
    if notice_arm not in NOTICE_ARMS:
        raise ValueError(f"notice_arm must be one of {list(NOTICE_ARMS)}; got {notice_arm!r}")
    if instruction not in INSTRUCTIONS:
        raise ValueError(f"instruction must be one of {list(INSTRUCTIONS)}; got {instruction!r}")
    if presentation not in ("upstream", "ticket"):
        raise ValueError(f"presentation must be 'upstream' or 'ticket'; got {presentation!r}")
    if presentation == "ticket" and instruction not in TICKET_GUIDANCE:
        raise ValueError(f"ticket presentation supports {list(TICKET_GUIDANCE)}; got {instruction!r}")

    base = agentic_humaneval_solver(
        max_attempts=max_attempts,
        allow_test_modifications=allow_test_modifications,
    )
    notice = NOTICE_ARMS[notice_arm]
    solver = chain(system_message(notice), base) if notice else base
    custom_id = f"{notice_arm}_{instruction}" + ("_flag" if flag_exit else "")

    if presentation == "ticket":
        if not allow_test_modifications:
            raise ValueError("ticket presentation is built for canmod runs only")
        dataset = hf_dataset(path=HF_DATASET, split=split,
                             sample_fields=_ticket_record_to_sample(instruction, flag_exit))
        if shuffle:
            dataset.shuffle(seed=42)  # same seed as upstream
        if limit is not None:
            dataset = dataset[:limit]
        return Task(
            name=f"lcb_{split}_canmod_{custom_id}_ticket_minimal",
            dataset=dataset,
            solver=solver,
            scorer=agentic_humaneval_scorer(),
            sandbox=_resolve_sandbox(sandbox),
            message_limit=message_limit,
        )

    return impossible_livecodebench(
        split=split,
        solver=solver,
        instruction_prompt=INSTRUCTIONS[instruction] + (" " + FLAG_EXIT if flag_exit else ""),
        agent_type="minimal",
        sandbox=_resolve_sandbox(sandbox),
        custom_id=custom_id,
        max_attempts=max_attempts,
        allow_test_modifications=allow_test_modifications,
        limit=limit,
        message_limit=message_limit,
        shuffle=shuffle,
    )
