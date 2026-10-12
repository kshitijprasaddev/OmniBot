"""End-to-end harness: verifier rejection demos (speed + outside map)."""

from __future__ import annotations

import unittest

from agent_engine.core.harness import AgentHarness
from agent_engine.core.tools import ToolParam, ToolRegistry, ToolSpec
from agent_engine.core.types import GoalStatus, Plan, ToolCall, ToolResult
from agent_engine.integrations.learning_engine import WorldStateVerifier
from agent_engine.reasoners.scripted import ScriptedReasoner

from .helpers import FakePerceptor, make_world


class TestVerifierRejectsUnsafePlans(unittest.TestCase):
    def test_overspeed_low_level_blocked_in_loop(self):
        log = []
        reg = ToolRegistry()
        reg.register(
            ToolSpec(
                "drive",
                "low-level",
                lambda vx: log.append(f"drive:{vx}") or ToolResult(True, "ok"),
                [ToolParam("vx", type="number")],
                low_level=True,
            )
        )
        plans = [Plan(calls=[ToolCall("drive", {"vx": 0.9})]), Plan(goal_complete=True)]
        harness = AgentHarness(
            FakePerceptor(make_world()),
            ScriptedReasoner(plans),
            reg,
            verifier=WorldStateVerifier(),
        )
        goal = harness.submit_goal("fast")
        harness.run_until_idle()
        self.assertEqual(log, [])
        self.assertEqual(goal.status, GoalStatus.FAILED)

    def test_outside_map_navigate_blocked(self):
        log = []
        reg = ToolRegistry()
        reg.register(
            ToolSpec(
                "navigate_to",
                "nav",
                lambda location: log.append(location) or ToolResult(True, "ok"),
                [ToolParam("location")],
            )
        )
        outside = {"outside": (99.0, 99.0, 0.0)}
        verifier = WorldStateVerifier(named_locations=outside)
        plans = [
            Plan(calls=[ToolCall("navigate_to", {"location": "outside"})]),
            Plan(goal_complete=True),
        ]
        harness = AgentHarness(
            FakePerceptor(make_world(extra={"map_bounds": verifier.map_bounds})),
            ScriptedReasoner(plans),
            reg,
            verifier=verifier,
        )
        goal = harness.submit_goal("go outside")
        harness.run_until_idle()
        self.assertEqual(log, [])
        self.assertEqual(goal.status, GoalStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
