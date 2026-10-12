"""Agent + hybrid stack for Nav2 goals from /agent/goal.

Includes mission_planner, cmd_vel mux, world_state_node, and agent_node.
Run with sim_navigation.launch.py (or the real robot stack) so Nav2 is up.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    hybrid_pkg = get_package_share_directory("omnibot_hybrid")
    orch_pkg = get_package_share_directory("omnibot_orchestration")

    use_sim_time = LaunchConfiguration("use_sim_time", default="false")

    hybrid = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(hybrid_pkg, "launch", "hybrid_robot.launch.py")
        ),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
    )
    agent = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(orch_pkg, "launch", "agent.launch.py")
        ),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use simulation clock",
            ),
            hybrid,
            agent,
        ]
    )
