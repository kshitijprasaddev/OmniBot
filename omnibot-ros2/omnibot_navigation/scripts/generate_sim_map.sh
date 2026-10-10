#!/usr/bin/env bash
# Copyright 2026 OhhO Robotics
# SPDX-License-Identifier: Apache-2.0
#
# Regenerate the checked-in apartment map (maps/apartment.{yaml,pgm,posegraph,data}).
#
#   source /opt/ros/jazzy/setup.bash && source install/setup.bash
#   omnibot-ros2/omnibot_navigation/scripts/generate_sim_map.sh [OUTPUT_DIR]
#
# Starts headless Gazebo (world:=apartment) and slam_toolbox with the scripted
# sweep (sim_map_sweep.py), waits for the sweep to finish, then saves the
# occupancy grid with nav2_map_server and the pose graph with slam_toolbox.
# OUTPUT_DIR defaults to this package's maps/ directory in the source tree.
# Needs ROS 2 Jazzy + Gazebo Harmonic; do not run it on a robot.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$(mkdir -p "${1:-${SCRIPT_DIR}/../maps}" && cd "${1:-${SCRIPT_DIR}/../maps}" && pwd)"
NAME="${MAP_NAME:-apartment}"
LOG="${LOG_FILE:-${TMPDIR:-/tmp}/generate_sim_map.log}"
SWEEP_TIMEOUT_S="${SWEEP_TIMEOUT_S:-900}"

echo "generate_sim_map: output ${OUT_DIR}/${NAME}.*  log ${LOG}"
: > "${LOG}"

setsid ros2 launch omnibot_navigation sim_mapping.launch.py sweep:=true >> "${LOG}" 2>&1 &
LAUNCH_PID=$!

cleanup() {
  kill -INT -- "-${LAUNCH_PID}" 2>/dev/null || true
  sleep 3
  kill -TERM -- "-${LAUNCH_PID}" 2>/dev/null || true
  pkill -f "gz sim" 2>/dev/null || true
}
trap cleanup EXIT

deadline=$((SECONDS + SWEEP_TIMEOUT_S))
until grep -q "SWEEP_DONE" "${LOG}"; do
  if ! kill -0 "${LAUNCH_PID}" 2>/dev/null; then
    echo "generate_sim_map: launch exited before the sweep finished; see ${LOG}" >&2
    exit 1
  fi
  if (( SECONDS > deadline )); then
    echo "generate_sim_map: sweep did not finish in ${SWEEP_TIMEOUT_S} s; see ${LOG}" >&2
    exit 1
  fi
  sleep 2
done
echo "generate_sim_map: sweep finished after $((SECONDS)) s; letting slam_toolbox settle"
sleep 8

ros2 run nav2_map_server map_saver_cli -f "${OUT_DIR}/${NAME}" \
  --fmt pgm \
  --ros-args -p save_map_timeout:=30.0 -p use_sim_time:=true

ros2 service call /slam_toolbox/serialize_map \
  slam_toolbox/srv/SerializePoseGraph "{filename: '${OUT_DIR}/${NAME}'}"

ls -l "${OUT_DIR}/${NAME}".*
echo "generate_sim_map: done"
