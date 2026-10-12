"""ScriptedBrain — offline natural-language goals without an LLM.

Parses phrases like ``go to the kitchen`` into a ``navigate_to`` tool plan.
Used on the robot when ``ANTHROPIC_API_KEY`` is unset and in headless sim.
"""

from __future__ import annotations

import re
from typing import Sequence

from ..core.blackboard import WorldState
from ..core.types import Goal, Plan, ToolCall, ToolResult
from ..navigation.waypoints import SIM_NAMED_LOCATIONS

_GO_RE = re.compile(
    r"\b(?:go|move|navigate|drive)\s+(?:to\s+)?(?:the\s+)?({})\b".format(
        "|".join(SIM_NAMED_LOCATIONS)
    ),
    re.IGNORECASE,
)


def parse_navigation_location(text: str) -> str | None:
    """Return a known waypoint name from natural language, or ``None``."""
    if not text:
        return None
    m = _GO_RE.search(text.strip())
    if m:
        return m.group(1).lower()
    lowered = text.lower()
    for name in SIM_NAMED_LOCATIONS:
        if re.search(rf"\b{re.escape(name)}\b", lowered):
            return name
    return None


class ScriptedBrain:
    """Deterministic reasoner for typed / spoken go-to goals."""

    def plan(
        self,
        goal: Goal,
        world: WorldState,
        memory_context: str,
        history: Sequence[ToolResult],
    ) -> Plan:
        if history:
            return Plan(rationale="scripted: navigation dispatched", goal_complete=True)

        structured = goal.structured or {}
        location = structured.get("location") or structured.get("navigate")
        if isinstance(location, str):
            location = location.lower().strip()
        else:
            location = parse_navigation_location(goal.text)

        if location and location in SIM_NAMED_LOCATIONS:
            return Plan(
                rationale=f"scripted: go to {location}",
                calls=[ToolCall("navigate_to", {"location": location})],
            )
        return Plan(
            give_up=True,
            rationale=f"scripted: cannot parse navigation goal from {goal.text!r}",
        )

    def reset(self) -> None:
        pass
