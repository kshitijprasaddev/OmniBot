# Copyright 2026 OhhO Robotics
# SPDX-License-Identifier: Apache-2.0
"""Headless Gazebo integration test: Nav2 reaches a named waypoint in 60 s.

One scenario per run. Pick it with OMNIBOT_NAV_SCENARIO=kitchen|desk|door
(default kitchen). Each run starts a fresh sim, so the robot always begins at
the spawn pose (0, 0, yaw 0).

Pass criteria, all required:
  1. Nav2 reports NavigateToPose SUCCEEDED within 60 s of simulation time,
     counted from goal acceptance.
  2. The final ground-truth pose (/odom, exact in the planar sim) is within
     0.30 m and 0.50 rad of the waypoint in config/waypoints.yaml.
Nav2's own goal checker is tighter (config/nav2_params.yaml
general_goal_checker: 0.20 m, 0.30 rad); the 0.30 m / 0.50 rad check is the
tolerance this test enforces independently of Nav2's estimate.

OMNIBOT_NAV_RESULTS_FILE, if set, gets one JSON line appended per run.
Needs ROS 2 Jazzy + Gazebo Harmonic; the CMake target is only registered when
OMNIBOT_NAV_SIM=1 at configure time.
"""

import math
import os
import sys
import unittest
from pathlib import Path

import launch_testing
import rclpy
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from go_to_waypoint import (  # noqa: E402
    DEFAULT_TIMEOUT_S,
    GOAL_XY_TOLERANCE_M,
    GOAL_YAW_TOLERANCE_RAD,
    START_POSE_TOLERANCE_M,
    WaypointGoalClient,
    emit,
)
from waypoint_loader import load_initial_pose, load_waypoints  # noqa: E402

SCENARIOS = ("kitchen", "desk", "door")
SCENARIO = os.environ.get("OMNIBOT_NAV_SCENARIO", "kitchen")
RESULTS_FILE = os.environ.get("OMNIBOT_NAV_RESULTS_FILE", "")
# 60 s is the acceptance limit. The override exists only to prove the test fails
# when the robot is too slow (e.g. OMNIBOT_NAV_TIMEOUT_S=5); CI never sets it.
TIMEOUT_S = float(os.environ.get("OMNIBOT_NAV_TIMEOUT_S", DEFAULT_TIMEOUT_S))


def generate_test_description():
    nav = FindPackageShare("omnibot_navigation").find("omnibot_navigation")
    return LaunchDescription(
        [
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(nav, "launch", "sim_navigation.launch.py")
                ),
                launch_arguments={"gui": "false", "world": "apartment"}.items(),
            ),
            launch_testing.actions.ReadyToTest(),
        ]
    ), {}


class TestNavScenario(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = WaypointGoalClient(use_sim_time=True)

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def test_reaches_waypoint_from_start_pose(self):
        self.assertIn(SCENARIO, SCENARIOS, f"OMNIBOT_NAV_SCENARIO must be one of {SCENARIOS}")
        waypoint = load_waypoints()[SCENARIO]

        self.assertTrue(
            self.node.wait_until_ready(240.0),
            "sim, TF map->base_link, or Nav2 lifecycle did not become ready in 240 s",
        )
        truth = self.node.ground_truth()
        self.assertIsNotNone(truth, "no /odom before the goal was sent")
        initial = load_initial_pose()
        self.assertLessEqual(
            math.hypot(truth[0] - initial[0], truth[1] - initial[1]),
            START_POSE_TOLERANCE_M,
            f"robot was not at the start pose {initial} when the goal was sent: {truth}",
        )
        result = self.node.navigate_to(waypoint, TIMEOUT_S)
        result["scenario"] = SCENARIO
        emit(result, RESULTS_FILE or None)
        print(
            f"EVIDENCE scenario={SCENARIO} success={result['success']} "
            f"time_to_goal_s={result.get('time_to_goal_s')} "
            f"final_error_xy_m={result.get('final_error_xy_m')} "
            f"(limit {TIMEOUT_S:.0f} s, {GOAL_XY_TOLERANCE_M} m, "
            f"{GOAL_YAW_TOLERANCE_RAD} rad)",
            flush=True,
        )
        self.assertTrue(result["success"], f"{SCENARIO}: {result['reason']}")
