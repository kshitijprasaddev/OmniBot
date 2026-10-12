"""JSONL loop trace for perceive → reason → verify → act → reflect."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .types import Goal


@dataclass
class LoopTraceEvent:
    ts: float
    goal_id: Optional[str]
    step: str
    detail: str
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": self.ts,
            "goal_id": self.goal_id,
            "step": self.step,
            "detail": self.detail,
            **self.extra,
        }


class LoopTraceRecorder:
    """Append-only JSONL trace; optional callback for ROS topic publish."""

    def __init__(
        self,
        path: Optional[str] = None,
        on_event: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.path = Path(path).expanduser() if path else None
        self.on_event = on_event
        self.events: List[LoopTraceEvent] = []
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        step: str,
        goal: Optional[Goal],
        detail: str,
        **extra: Any,
    ) -> LoopTraceEvent:
        ev = LoopTraceEvent(
            ts=time.time(),
            goal_id=goal.id if goal else None,
            step=step,
            detail=detail,
            extra=extra,
        )
        self.events.append(ev)
        line = json.dumps(ev.to_dict(), separators=(",", ":"))
        if self.on_event:
            self.on_event(line)
        if self.path:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        return ev
