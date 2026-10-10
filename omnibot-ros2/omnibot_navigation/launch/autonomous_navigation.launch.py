#!/usr/bin/env python3
"""
Nav2 autonomous navigation launch for OmniBot.

Starts the full Nav2 stack:
  • controller_server  — DWB local planner → publishes /cmd_vel
  • planner_server     — NavFn global planner
  • behavior_server    — recoveries (spin, backup, wait)
  • bt_navigator       — behaviour-tree NavigateToPose action server
  • velocity_smoother  — smooths /cmd_vel output
  • lifecycle_manager  — configure → activate lifecycle nodes

/cmd_vel from velocity_smoother is received by cmd_vel_mux as the "nav2" source.

Usage:
    ros2 launch omnibot_navigation autonomous_navigation.launch.py
    ros2 launch omnibot_navigation autonomous_navigation.launch.py use_sim_time:=true
    ros2 launch omnibot_navigation autonomous_navigation.launch.py \\
        params_file:=/path/to/custom_nav2_params.yaml
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterValue
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    pkg_nav = get_package_share_directory("omnibot_navigation")
    default_params = os.path.join(pkg_nav, "config", "nav2_params.yaml")

    use_sim_time = LaunchConfiguration("use_sim_time")
    autostart = LaunchConfiguration("autostart")
    bond_timeout = LaunchConfiguration("bond_timeout")

    # Nav2 costmaps are sub-nodes of controller_server / planner_server and read
    # their own use_sim_time from the file, so the launch-level override alone
    # does not reach them. Rewrite every use_sim_time in the YAML instead.
    params_file = RewrittenYaml(
        source_file=LaunchConfiguration("params_file"),
        param_rewrites={"use_sim_time": use_sim_time},
        convert_types=True,
    )

    nav2_managed_nodes = [
        "controller_server",
        "planner_server",
        "behavior_server",
        "bt_navigator",
        "velocity_smoother",
    ]

    controller_server = Node(
        package="nav2_controller",
        executable="controller_server",
        output="screen",
        parameters=[params_file, {"use_sim_time": use_sim_time}],
        remappings=[("cmd_vel", "/cmd_vel_nav2_raw")],
    )

    planner_server = Node(
        package="nav2_planner",
        executable="planner_server",
        name="planner_server",
        output="screen",
        parameters=[params_file, {"use_sim_time": use_sim_time}],
    )

    behavior_server = Node(
        package="nav2_behaviors",
        executable="behavior_server",
        output="screen",
        parameters=[params_file, {"use_sim_time": use_sim_time}],
        remappings=[("cmd_vel", "/cmd_vel_nav2_raw")],
    )

    bt_navigator = Node(
        package="nav2_bt_navigator",
        executable="bt_navigator",
        name="bt_navigator",
        output="screen",
        parameters=[params_file, {"use_sim_time": use_sim_time}],
    )

    # Smooths raw DWB output before publishing to /cmd_vel (read by cmd_vel_mux)
    velocity_smoother = Node(
        package="nav2_velocity_smoother",
        executable="velocity_smoother",
        name="velocity_smoother",
        output="screen",
        parameters=[params_file, {"use_sim_time": use_sim_time}],
        remappings=[
            ("cmd_vel", "/cmd_vel_nav2_raw"),
            ("cmd_vel_smoothed", "/cmd_vel"),
        ],
    )

    lifecycle_manager = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_navigation",
        output="screen",
        parameters=[
            {"use_sim_time": use_sim_time},
            {"autostart": autostart},
            {"bond_timeout": ParameterValue(bond_timeout, value_type=float)},
            {"node_names": nav2_managed_nodes},
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use simulation clock",
            ),
            DeclareLaunchArgument(
                "params_file",
                default_value=default_params,
                description="Full path to Nav2 params yaml",
            ),
            DeclareLaunchArgument(
                "autostart",
                default_value="true",
                description="Auto-activate lifecycle nodes on launch",
            ),
            DeclareLaunchArgument(
                "bond_timeout",
                default_value="4.0",
                description="Lifecycle bond timeout in s; 0.0 disables bond checks "
                "(used in CPU-starved headless CI)",
            ),
            controller_server,
            planner_server,
            behavior_server,
            bt_navigator,
            velocity_smoother,
            lifecycle_manager,
        ]
    )
