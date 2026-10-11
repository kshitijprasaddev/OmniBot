#!/usr/bin/env python3
# Copyright 2026 OhhO Robotics
# SPDX-License-Identifier: Apache-2.0
"""Drive a fixed collision-free sweep of the apartment world for mapping.

Used by scripts/generate_sim_map.sh while slam_toolbox is running
(sim_mapping.launch.py). The route is open-loop on /odom, so it needs no map
and no Nav2. /odom is the Gazebo world pose in the planar-drive sim, and the
route points below are world coordinates chosen for the furniture in
omnibot_bringup/worlds/apartment.sdf:

    kitchen counter  x -3.25..-2.65, y -0.30..1.70    fridge x -3.25..-2.55, y -1.50..-0.80
    desk             x  1.95.. 3.15, y  0.10..0.70    door leaf tip near (-0.07, -1.96)
    walls            x -3.42..3.42,  y -2.42..2.42

Every point keeps >= 0.5 m from those. The robot translates at SPEED while
turning at YAW_RATE so the 2-D lidar sees every face, spins a full turn at the
start and at the end, and finishes back at the start pose so slam_toolbox can
close the loop. Exits 0 and prints SWEEP_DONE when finished.
"""

from __future__ import annotations

import math
import sys

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.parameter import Parameter

ROUTE = [
    ("spin", 2.0 * math.pi),
    ("goto", 0.0, 1.7),
    ("goto", -1.8, 1.8),
    ("goto", -1.9, 0.0),
    ("goto", -1.9, -1.9),
    ("goto", -1.4, -1.4),
    ("goto", 1.4, -1.4),
    ("goto", 2.9, -1.4),
    ("goto", 2.9, -0.5),
    ("goto", 1.5, -0.3),
    ("goto", 1.5, 1.8),
    ("goto", 2.9, 1.8),
    ("goto", 0.0, 1.8),
    ("goto", 0.0, 0.0),
    ("spin", 2.0 * math.pi),
]

SPEED = 0.25  # m/s
YAW_RATE = 0.3  # rad/s while translating
SPIN_RATE = 0.5  # rad/s while turning on the spot
REACHED_M = 0.08
GAIN = 1.5


def wrap(angle: float) -> float:
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


class MapSweep(Node):
    def __init__(self):
        super().__init__(
            "sim_map_sweep",
            parameter_overrides=[Parameter("use_sim_time", Parameter.Type.BOOL, True)],
        )
        self.pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.create_subscription(Odometry, "/odom", self._on_odom, 10)
        self.pose = None
        self.step = 0
        self.spin_done = 0.0
        self.last_yaw = None
        self.done = False
        self.create_timer(0.05, self._tick)

    def _on_odom(self, msg):
        p = msg.pose.pose
        q = p.orientation
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        )
        self.pose = (p.position.x, p.position.y, yaw)

    def _tick(self):
        if self.pose is None or self.done:
            return
        x, y, yaw = self.pose
        cmd = Twist()
        if self.step >= len(ROUTE):
            self.pub.publish(cmd)
            self.get_logger().info("SWEEP_DONE")
            self.done = True
            return
        kind = ROUTE[self.step]
        if kind[0] == "spin":
            if self.last_yaw is None:
                self.last_yaw = yaw
            self.spin_done += abs(wrap(yaw - self.last_yaw))
            self.last_yaw = yaw
            if self.spin_done >= kind[1]:
                self._next()
            else:
                cmd.angular.z = SPIN_RATE
        else:
            dx, dy = kind[1] - x, kind[2] - y
            dist = math.hypot(dx, dy)
            if dist < REACHED_M:
                self._next()
            else:
                speed = min(SPEED, GAIN * dist)
                wx, wy = speed * dx / dist, speed * dy / dist
                cmd.linear.x = math.cos(yaw) * wx + math.sin(yaw) * wy
                cmd.linear.y = -math.sin(yaw) * wx + math.cos(yaw) * wy
                cmd.angular.z = YAW_RATE
        self.pub.publish(cmd)

    def _next(self):
        self.step += 1
        self.spin_done = 0.0
        self.last_yaw = None
        self.get_logger().info(f"sweep step {self.step}/{len(ROUTE)}")


def main(args=None):
    rclpy.init(args=args)
    node = MapSweep()
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.pub.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()
    return 0 if node.done else 1


if __name__ == "__main__":
    sys.exit(main())
