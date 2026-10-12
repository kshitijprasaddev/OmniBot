"""Sim apartment waypoints (OHH-30) shared by the agent verifier and mission planner.

Coordinates match ``omnibot_navigation/config/waypoints.yaml`` (map frame).
"""

from __future__ import annotations

from typing import Dict, Tuple

# map frame positions for kitchen / desk / door in the Gazebo apartment world.
SIM_NAMED_LOCATIONS: Dict[str, Tuple[float, float, float]] = {
    "kitchen": (-1.9, 0.7, 3.141592653589793),  # yaw 180 deg
    "desk": (2.55, -0.45, 1.5707963267948966),  # yaw 90 deg
    "door": (-0.3, -1.45, -1.5707963267948966),  # yaw -90 deg
}

# Checked-in SLAM map ``omnibot_navigation/maps/apartment.yaml`` (+ PGM size).
APARTMENT_MAP_BOUNDS = {
    "origin": [-3.455, -2.746],
    "resolution": 0.05,
    "width": 138,
    "height": 105,
}


def goal_in_map(x: float, y: float, bounds: Dict) -> bool:
    ox, oy = float(bounds["origin"][0]), float(bounds["origin"][1])
    res = float(bounds["resolution"])
    xmax = ox + int(bounds["width"]) * res
    ymax = oy + int(bounds["height"]) * res
    return ox <= x <= xmax and oy <= y <= ymax


def yaw_for_location(name: str) -> float:
    entry = SIM_NAMED_LOCATIONS.get(name.lower())
    return entry[2] if entry else 0.0
