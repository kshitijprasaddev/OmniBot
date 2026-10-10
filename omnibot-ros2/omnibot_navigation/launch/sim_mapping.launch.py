#!/usr/bin/env python3
# Copyright 2026 OhhO Robotics
# SPDX-License-Identifier: Apache-2.0
"""slam_toolbox mapping in the apartment world, headless Gazebo Harmonic.

    ros2 launch omnibot_navigation sim_mapping.launch.py
    ros2 launch omnibot_navigation sim_mapping.launch.py sweep:=true

Starts omnibot_bringup sim.launch.py (world:=apartment) and slam_toolbox
(config/slam_toolbox_params.yaml, mode mapping) on the Gazebo clock. Drive with
teleop, or pass `sweep:=true` to run scripts/sim_map_sweep.py, which drives a
fixed route over the whole room. `scripts/generate_sim_map.sh` runs this launch
with the sweep and saves the result to maps/.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    nav = get_package_share_directory("omnibot_navigation")
    bringup = get_package_share_directory("omnibot_bringup")

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(bringup, "launch", "sim.launch.py")),
        launch_arguments={
            "world": LaunchConfiguration("world"),
            "gui": LaunchConfiguration("gui"),
            "drive": "planar",
            "rosbridge": "false",
        }.items(),
    )

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav, "launch", "slam_toolbox.launch.py")
        ),
        launch_arguments={"use_sim_time": "true"}.items(),
    )

    sweep = Node(
        package="omnibot_navigation",
        executable="sim_map_sweep.py",
        name="sim_map_sweep",
        output="screen",
        condition=IfCondition(LaunchConfiguration("sweep")),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("world", default_value="apartment"),
            DeclareLaunchArgument("gui", default_value="false"),
            DeclareLaunchArgument(
                "sweep",
                default_value="false",
                description="Run the scripted mapping sweep (sim_map_sweep.py)",
            ),
            sim,
            slam,
            sweep,
        ]
    )
