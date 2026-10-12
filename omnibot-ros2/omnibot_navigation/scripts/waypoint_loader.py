#!/usr/bin/env python3
# Copyright 2026 OhhO Robotics
# SPDX-License-Identifier: Apache-2.0
"""Load and validate the named waypoints in config/waypoints.yaml.

This module has no ROS dependency, so the CPU CI job can unit-test it.
`waypoint_navigator.py`, `go_to_waypoint.py` and the Gazebo scenario test all
read waypoints through it.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path

import yaml

PACKAGE_NAME = "omnibot_navigation"
YAW_TOLERANCE_RAD = math.radians(1.0)


@dataclass(frozen=True)
class Waypoint:
    name: str
    x: float
    y: float
    z: float
    qx: float
    qy: float
    qz: float
    qw: float
    frame_id: str = "map"

    @property
    def yaw(self) -> float:
        return yaw_from_quaternion(self.qx, self.qy, self.qz, self.qw)


def yaw_from_quaternion(qx: float, qy: float, qz: float, qw: float) -> float:
    """Heading about +Z, in radians, from a quaternion."""
    return math.atan2(
        2.0 * (qw * qz + qx * qy),
        1.0 - 2.0 * (qy * qy + qz * qz),
    )


def quaternion_from_yaw(yaw: float) -> tuple[float, float, float, float]:
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


def angle_diff(a: float, b: float) -> float:
    """Smallest signed difference a - b, in (-pi, pi]."""
    diff = (a - b + math.pi) % (2.0 * math.pi) - math.pi
    return math.pi if diff == -math.pi else diff


def default_waypoint_path(filename: str = "waypoints.yaml") -> Path:
    """Installed share/ path when sourced, else the source tree next to scripts/."""
    try:
        from ament_index_python.packages import get_package_share_directory

        installed = Path(get_package_share_directory(PACKAGE_NAME)) / "config" / filename
        if installed.is_file():
            return installed
    except Exception:  # not sourced, or ament_index_python is not installed
        pass
    return Path(__file__).resolve().parents[1] / "config" / filename


def resolve_waypoint_path(waypoint_file: str) -> Path:
    """`waypoint_file` is an absolute/relative path or a name under config/."""
    candidate = Path(waypoint_file)
    if candidate.is_file():
        return candidate
    return default_waypoint_path(os.path.basename(waypoint_file))


def parse_waypoints(data: dict) -> dict[str, Waypoint]:
    """Validate parsed YAML and return waypoints keyed by name (file order)."""
    if not isinstance(data, dict) or "waypoints" not in data:
        raise ValueError("waypoints file must be a mapping with a 'waypoints' list")
    frame_id = str(data.get("frame_id", "map"))
    result: dict[str, Waypoint] = {}
    for index, entry in enumerate(data["waypoints"] or []):
        name = entry.get("name") if isinstance(entry, dict) else None
        if not name or not isinstance(name, str):
            raise ValueError(f"waypoint #{index} has no name")
        if name in result:
            raise ValueError(f"duplicate waypoint name {name!r}")
        position = entry.get("position") or {}
        orientation = entry.get("orientation") or {}
        try:
            waypoint = Waypoint(
                name=name,
                x=float(position["x"]),
                y=float(position["y"]),
                z=float(position.get("z", 0.0)),
                qx=float(orientation.get("x", 0.0)),
                qy=float(orientation.get("y", 0.0)),
                qz=float(orientation["z"]),
                qw=float(orientation["w"]),
                frame_id=frame_id,
            )
        except KeyError as missing:
            raise ValueError(f"waypoint {name!r} is missing {missing}") from missing
        norm = math.sqrt(waypoint.qx**2 + waypoint.qy**2 + waypoint.qz**2 + waypoint.qw**2)
        if abs(norm - 1.0) > 1e-3:
            raise ValueError(f"waypoint {name!r} quaternion is not unit length ({norm:.4f})")
        if "yaw_deg" in entry:
            declared = math.radians(float(entry["yaw_deg"]))
            if abs(angle_diff(declared, waypoint.yaw)) > YAW_TOLERANCE_RAD:
                raise ValueError(
                    f"waypoint {name!r}: yaw_deg={entry['yaw_deg']} disagrees with "
                    f"the quaternion (yaw {math.degrees(waypoint.yaw):.1f} deg)"
                )
        result[name] = waypoint
    return result


def load_waypoint_file(path: str | os.PathLike) -> tuple[dict, dict[str, Waypoint]]:
    """Return (raw YAML mapping, waypoints by name)."""
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data, parse_waypoints(data)


def load_waypoints(path: str | os.PathLike | None = None) -> dict[str, Waypoint]:
    resolved = Path(path) if path else default_waypoint_path()
    return load_waypoint_file(resolved)[1]


def load_initial_pose(path: str | os.PathLike | None = None) -> tuple[float, float, float]:
    """(x, y, yaw rad) of the robot spawn pose declared in the waypoints file."""
    data, _ = load_waypoint_file(Path(path) if path else default_waypoint_path())
    pose = data.get("initial_pose") or {}
    return (
        float(pose.get("x", 0.0)),
        float(pose.get("y", 0.0)),
        math.radians(float(pose.get("yaw_deg", 0.0))),
    )


def select_route(waypoints: dict[str, Waypoint], route: list[str]) -> list[Waypoint]:
    """Waypoints in `route` order; an empty route means every waypoint in file order."""
    if not route:
        return list(waypoints.values())
    unknown = [name for name in route if name not in waypoints]
    if unknown:
        raise KeyError(
            f"unknown waypoint(s) {unknown}; known: {sorted(waypoints)}"
        )
    return [waypoints[name] for name in route]
