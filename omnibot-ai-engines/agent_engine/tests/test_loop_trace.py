"""Loop trace JSONL recorder tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_engine.core.harness import AgentHarness
from agent_engine.core.loop_trace import LoopTraceRecorder
from agent_engine.core.types import Plan, ToolCall
from agent_engine.integrations.learning_engine import WorldStateVerifier
from agent_engine.reasoners.scripted import ScriptedReasoner

from .helpers import FakePerceptor, make_registry, make_world


class TestLoopTrace(unittest.TestCase):
    def test_trace_records_perceive_reason_verify_act_reflect(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            trace = LoopTraceRecorder(path=str(path))
            plans = [
                Plan(calls=[ToolCall("navigate_to", {"location": "kitchen"})]),
                Plan(goal_complete=True),
            ]
            harness = AgentHarness(
                FakePerceptor(make_world()),
                ScriptedReasoner(plans),
                make_registry([]),
                verifier=WorldStateVerifier(),
                trace=trace,
            )
            harness.submit_goal("go to the kitchen")
            harness.run_until_idle()
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            steps = [json.loads(line)["step"] for line in lines]
            self.assertIn("perceive", steps)
            self.assertIn("reason", steps)
            self.assertIn("verify", steps)
            self.assertIn("act", steps)
            self.assertIn("reflect", steps)


if __name__ == "__main__":
    unittest.main()
