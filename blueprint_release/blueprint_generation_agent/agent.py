"""
Blueprint generation agent — dialogue-driven SCA blueprint generator.

Five conversational stages, each backed by a system prompt in `prompts/`:

    1. workflow_elicitation  — agent asks 2-5 clarifying questions about goal,
                               hard constraints, and tool boundaries
    2. node_decomposition    — agent proposes nodes + topology
                               (`sequence` / `fork_join` / `route_by` / `foreach`)
    3. pre_post_drafting     — agent drafts @precondition / @postcondition /
                               @retry / @timeout per node
    4. subtask_binding       — agent classifies each node deterministic / LLM /
                               KB; for LLM/KB nodes, fully specifies prompt+schema
                               or kb.query(...)
    5. compile_dryrun        — agent emits .py + smoke-runs; on failure,
                               recommends which earlier stage to revisit

A round is one human↔agent exchange. Most workflows converge in ≤5 rounds —
a single round usually advances one stage, but a human reaction in round N can
force re-entry to stage M < N (the topology refactor in `oom` round 3 is the
canonical case). See `convergence_stats.md` for the empirical distribution.

Usage
-----
    python agent.py                              # interactive REPL with stub LLM
    python agent.py --transcript out.md          # log full dialogue to file

Wire your own `LLMClient` for real generation. The bundled `StubLLMClient`
echoes inputs and is only useful for end-to-end shake-out.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol


# ---------- Conversation state ----------

@dataclass
class DialogueState:
    workflow_goal: str = ""
    clarifications: Dict[str, str] = field(default_factory=dict)
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    topology: Dict[str, Any] = field(default_factory=dict)
    decorators: Dict[str, Any] = field(default_factory=dict)
    bindings: Dict[str, Any] = field(default_factory=dict)
    blueprint_py: str = ""
    smoke_report: Dict[str, Any] = field(default_factory=dict)
    rounds: int = 0
    transcript: List[Dict[str, str]] = field(default_factory=list)


# ---------- LLM transport ----------

class LLMClient(Protocol):
    def invoke(self, system_prompt: str, user_message: str) -> str: ...


class StubLLMClient:
    """Echoes the user message — for end-to-end shake-out only."""

    def invoke(self, system_prompt: str, user_message: str) -> str:
        head = user_message[:120].replace("\n", " ")
        suffix = "…" if len(user_message) > 120 else ""
        return f"[stub agent reply — wire a real LLMClient]\n(saw: {head}{suffix})"


# ---------- Pipeline ----------

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def stage_1_workflow_elicitation(state: DialogueState, llm: LLMClient) -> str:
    return llm.invoke(_load("01_workflow_elicitation.md"), state.workflow_goal)


def stage_2_node_decomposition(state: DialogueState, llm: LLMClient) -> str:
    user = json.dumps(
        {"workflow_goal": state.workflow_goal, "clarifications": state.clarifications},
        ensure_ascii=False,
    )
    return llm.invoke(_load("02_node_decomposition.md"), user)


def stage_3_pre_post_drafting(state: DialogueState, llm: LLMClient) -> str:
    user = json.dumps(
        {
            "workflow_goal": state.workflow_goal,
            "clarifications": state.clarifications,
            "nodes": state.nodes,
            "topology": state.topology,
        },
        ensure_ascii=False,
    )
    return llm.invoke(_load("03_pre_post_drafting.md"), user)


def stage_4_subtask_binding(state: DialogueState, llm: LLMClient) -> str:
    user = json.dumps(
        {
            "nodes": state.nodes,
            "decorators": state.decorators,
            "clarifications": state.clarifications,
        },
        ensure_ascii=False,
    )
    return llm.invoke(_load("04_subtask_binding.md"), user)


def stage_5_compile_dryrun(state: DialogueState, llm: LLMClient) -> str:
    user = json.dumps(
        {
            "nodes": state.nodes,
            "topology": state.topology,
            "decorators": state.decorators,
            "bindings": state.bindings,
        },
        ensure_ascii=False,
    )
    return llm.invoke(_load("05_compile_dryrun.md"), user)


# ---------- Driver ----------

STAGES = {
    1: ("Workflow Elicitation", stage_1_workflow_elicitation),
    2: ("Node Decomposition",   stage_2_node_decomposition),
    3: ("Pre/Post Drafting",    stage_3_pre_post_drafting),
    4: ("Subtask Binding",      stage_4_subtask_binding),
    5: ("Compile + Dry-Run",    stage_5_compile_dryrun),
}

ROUND_HARD_CAP = 10


def _read_human(prompt: str) -> str:
    print(f"\n[human] {prompt}")
    print("(end input with a single '.' on its own line)")
    lines: List[str] = []
    for line in sys.stdin:
        if line.strip() == ".":
            break
        lines.append(line)
    return "".join(lines).strip()


def run(initial_goal: str, llm: LLMClient, transcript_path: Optional[Path] = None) -> DialogueState:
    state = DialogueState(workflow_goal=initial_goal)
    state.transcript.append({"role": "human", "stage": "0", "text": initial_goal})

    stage = 1
    while stage <= 5 and state.rounds < ROUND_HARD_CAP:
        state.rounds += 1
        title, fn = STAGES[stage]
        print(f"\n=== Round {state.rounds} — Stage {stage}: {title} ===")
        agent_msg = fn(state, llm)
        print(f"\n[agent]\n{agent_msg}")
        state.transcript.append({"role": "agent", "stage": str(stage), "text": agent_msg})

        if stage == 5 and agent_msg.lstrip().lower().startswith(("smoke result: pass", "pass")):
            print("\n=== Smoke PASS — handing off to human review ===")
            break

        human_msg = _read_human(
            f"Reply to stage {stage} (or 'next' to advance, 'redo N' to re-enter stage N, 'approved' to ship):"
        )
        state.transcript.append({"role": "human", "stage": str(stage), "text": human_msg})

        low = human_msg.lower()
        if low.startswith("redo "):
            try:
                stage = int(low.split()[1])
            except (IndexError, ValueError):
                stage += 1
        elif low == "approved":
            break
        else:
            stage += 1

    if state.rounds >= ROUND_HARD_CAP:
        print(f"\n=== {ROUND_HARD_CAP}-round cap reached — handing off for manual takeover ===")

    if transcript_path:
        transcript_path.write_text(_format_transcript(state), encoding="utf-8")
    return state


def _format_transcript(state: DialogueState) -> str:
    out = [f"# Dialogue transcript ({state.rounds} rounds)\n"]
    for entry in state.transcript:
        role = "**Human**" if entry["role"] == "human" else "**Agent**"
        out.append(f"## Stage {entry['stage']} — {role}\n\n{entry['text']}\n")
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--transcript", type=Path, default=None, help="Write the full dialogue transcript here.")
    p.add_argument("--llm-stub", action="store_true", help="Use the bundled stub LLM (echoes inputs).")
    args = p.parse_args()
    if not args.llm_stub:
        raise SystemExit(
            "Wire your LLMClient implementation, or pass --llm-stub for end-to-end shake-out."
        )
    print("Describe the workflow you want to compile into an SCA blueprint.")
    goal = _read_human("Workflow goal:")
    state = run(goal, StubLLMClient(), args.transcript)
    print(f"\n=== Done. {state.rounds} rounds. Transcript: {args.transcript or '(not saved)'} ===")


if __name__ == "__main__":
    main()
