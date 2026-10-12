#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateThroughPoses
from rclpy.action import ActionClient

from waypoint_loader import load_waypoint_file, resolve_waypoint_path, select_route


class WaypointNavigator(Node):
    """
    Autonomous waypoint navigation for OmniBot.

    Loads the named waypoints from config/waypoints.yaml (map frame) and sends
    them to Nav2 as one NavigateThroughPoses goal. `route` is a comma-separated
    list that picks and orders waypoints by name, e.g. "kitchen,desk,door".
    An empty route visits every waypoint in file order.
    """

    def __init__(self):
        super().__init__("waypoint_navigator")

        self.declare_parameter("waypoint_file", "waypoints.yaml")
        self.declare_parameter("route", "")
        self.declare_parameter("loop_waypoints", False)
        self.declare_parameter("waypoint_timeout", 30.0)

        self.waypoint_file = self.get_parameter("waypoint_file").value
        self.route = [
            name.strip()
            for name in str(self.get_parameter("route").value).split(",")
            if name.strip()
        ]
        self.loop_waypoints = self.get_parameter("loop_waypoints").value
        self.waypoint_timeout = self.get_parameter("waypoint_timeout").value

        self.navigate_through_poses_client = ActionClient(
            self, NavigateThroughPoses, "navigate_through_poses"
        )

        self.waypoints = []
        self.is_navigating = False
        self.has_run = False

        self.load_waypoints()

        self.navigation_timer = self.create_timer(1.0, self.navigation_loop)

        self.get_logger().info("Waypoint Navigator initialized")
        self.get_logger().info(
            "Route: " + " -> ".join(w.name for w in self.waypoints)
            if self.waypoints
            else "No waypoints loaded"
        )

    def load_waypoints(self):
        """Load the named waypoints from YAML."""
        path = resolve_waypoint_path(self.waypoint_file)
        try:
            _, by_name = load_waypoint_file(path)
            self.waypoints = select_route(by_name, self.route)
            self.get_logger().info(f"Loaded {len(self.waypoints)} waypoints from {path}")
        except (OSError, ValueError, KeyError) as error:
            self.get_logger().error(f"Error loading waypoints from {path}: {error}")
            self.waypoints = []

    def navigation_loop(self):
        """Start (or, with loop_waypoints, restart) navigation when idle."""
        if self.is_navigating or not self.waypoints:
            return
        if self.has_run and not self.loop_waypoints:
            self.navigation_timer.cancel()
            return
        self.start_autonomous_navigation()

    def start_autonomous_navigation(self):
        """Start autonomous navigation through waypoints."""
        self.get_logger().info("Starting autonomous navigation")
        self.is_navigating = True

        goal_poses = []
        for waypoint in self.waypoints:
            pose = PoseStamped()
            pose.header.frame_id = waypoint.frame_id
            pose.header.stamp = self.get_clock().now().to_msg()
            pose.pose.position.x = waypoint.x
            pose.pose.position.y = waypoint.y
            pose.pose.position.z = waypoint.z
            pose.pose.orientation.x = waypoint.qx
            pose.pose.orientation.y = waypoint.qy
            pose.pose.orientation.z = waypoint.qz
            pose.pose.orientation.w = waypoint.qw
            goal_poses.append(pose)

        self.send_navigation_goal(goal_poses)

    def send_navigation_goal(self, poses):
        """Send navigation goal to Nav2."""
        goal_msg = NavigateThroughPoses.Goal()
        goal_msg.poses = poses

        self.get_logger().info(f"Sending navigation goal with {len(poses)} poses")

        if not self.navigate_through_poses_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error("NavigateThroughPoses action server not available")
            self.is_navigating = False
            return

        self.send_goal_future = self.navigate_through_poses_client.send_goal_async(
            goal_msg, feedback_callback=self.feedback_callback
        )
        self.send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        """Handle goal response."""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info("Goal rejected by server")
            self.is_navigating = False
            return

        self.get_logger().info("Goal accepted by server")
        self.result_future = goal_handle.get_result_async()
        self.result_future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback_msg):
        """Handle navigation feedback."""
        feedback = feedback_msg.feedback
        self.get_logger().info(
            f"Navigation feedback: {feedback.current_pose.pose.position.x:.2f}, "
            f"{feedback.current_pose.pose.position.y:.2f}"
        )

    def get_result_callback(self, future):
        """Handle navigation result."""
        future.result()
        self.get_logger().info("Navigation completed")
        self.is_navigating = False
        self.has_run = True

        if self.loop_waypoints:
            self.get_logger().info("Looping waypoints - restarting navigation")


def main(args=None):
    rclpy.init(args=args)

    waypoint_navigator = WaypointNavigator()

    try:
        rclpy.spin(waypoint_navigator)
    except KeyboardInterrupt:
        waypoint_navigator.get_logger().info("Shutting down waypoint navigator")
    finally:
        waypoint_navigator.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
