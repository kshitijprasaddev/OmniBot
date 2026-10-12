# Copyright 2026 OhhO Robotics
# SPDX-License-Identifier: Apache-2.0
"""Launch smoke test for agent.launch.py (world_state + agent_node)."""

import os
import time
import unittest

import launch_testing
import rclpy
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare
from std_msgs.msg import String


def generate_test_description():
    pkg = FindPackageShare("omnibot_orchestration").find("omnibot_orchestration")
    launch_file = os.path.join(pkg, "launch", "agent.launch.py")
    return LaunchDescription(
        [
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(launch_file),
                launch_arguments={"use_sim_time": "false"}.items(),
            ),
            launch_testing.actions.ReadyToTest(),
        ]
    ), {}


class TestAgentLaunch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node("agent_launch_smoke")
        cls.traces = []
        cls.node.create_subscription(String, "/agent/loop_trace", cls.traces.append, 10)

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def test_goal_produces_loop_trace(self):
        pub = self.node.create_publisher(String, "/agent/goal", 10)
        deadline = time.time() + 25.0
        msg = String()
        msg.data = "go to the kitchen"
        while time.time() < deadline:
            pub.publish(msg)
            rclpy.spin_once(self.node, timeout_sec=0.2)
            if any("verify" in t.data for t in self.traces):
                return
        self.fail("no /agent/loop_trace verify event within 25s")


@launch_testing.post_shutdown_test()
class TestAgentLaunchShutdown(unittest.TestCase):
    def test_exit_cleanly(self, proc_info):
        launch_testing.asserts.assertExitCodes(proc_info)
