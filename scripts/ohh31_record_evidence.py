#!/usr/bin/env python3
"""Record agent loop JSONL traces for OHH-31 evidence (no ROS required)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "omnibot-ai-engines"))

from agent_engine.core.harness import AgentHarness
from agent_engine.core.loop_trace import LoopTraceRecorder
from agent_engine.core.types import Plan, ToolCall
from agent_engine.integrations.learning_engine import WorldStateVerifier
from agent_engine.reasoners.scripted import ScriptedReasoner
from agent_engine.reasoners.scripted_brain import ScriptedBrain
from agent_engine.tests.helpers import FakePerceptor, make_registry, make_world


def main() -> int:
    out_dir = REPO / "docs" / "evidence" / "ohh-31"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Happy path: go to the kitchen
    kitchen_trace = out_dir / "kitchen_goal_trace.jsonl"
    trace = LoopTraceRecorder(path=str(kitchen_trace))
    log = []
    harness = AgentHarness(
        FakePerceptor(make_world(extra={"map_bounds": WorldStateVerifier().map_bounds})),
        ScriptedBrain(),
        make_registry(log),
        verifier=WorldStateVerifier(),
        trace=trace,
    )
    harness.submit_goal("go to the kitchen")
    harness.run_until_idle()

    # Rejection demo: goal outside map
    reject_trace = out_dir / "verifier_reject_outside_map.jsonl"
    outside = {"outside": (99.0, 99.0, 0.0)}
    verifier = WorldStateVerifier(named_locations=outside)
    trace2 = LoopTraceRecorder(path=str(reject_trace))
    harness2 = AgentHarness(
        FakePerceptor(make_world(extra={"map_bounds": verifier.map_bounds})),
        ScriptedReasoner(
            [
                Plan(calls=[ToolCall("navigate_to", {"location": "outside"})]),
                Plan(goal_complete=True),
            ]
        ),
        make_registry([]),
        verifier=verifier,
        trace=trace2,
    )
    harness2.submit_goal("go outside the map")
    harness2.run_until_idle()

    summary = {
        "kitchen_mission_command": f"navigate:kitchen (tool log: {log})",
        "kitchen_trace": kitchen_trace.name,
        "reject_trace": reject_trace.name,
        "kitchen_steps": [
            json.loads(line)["step"]
            for line in kitchen_trace.read_text(encoding="utf-8").splitlines()
        ],
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
