"""Tests for offline ScriptedBrain NL → navigate_to planning."""

from __future__ import annotations

import unittest

from agent_engine.core.harness import AgentHarness
from agent_engine.core.types import GoalStatus
from agent_engine.reasoners.scripted_brain import ScriptedBrain, parse_navigation_location

from .helpers import FakePerceptor, make_registry, make_world


class TestParseNavigation(unittest.TestCase):
    def test_go_to_kitchen(self):
        self.assertEqual(parse_navigation_location("go to the kitchen"), "kitchen")

    def test_move_to_desk(self):
        self.assertEqual(parse_navigation_location("Move to desk please"), "desk")

    def test_door(self):
        self.assertEqual(parse_navigation_location("navigate to the door"), "door")


class TestScriptedBrainHarness(unittest.TestCase):
    def test_kitchen_goal_publishes_navigate(self):
        log = []
        harness = AgentHarness(
            FakePerceptor(make_world()),
            ScriptedBrain(),
            make_registry(log),
        )
        goal = harness.submit_goal("go to the kitchen")
        harness.run_until_idle()
        self.assertEqual(log, ["navigate_to:kitchen"])
        self.assertEqual(goal.status, GoalStatus.SUCCEEDED)


if __name__ == "__main__":
    unittest.main()
