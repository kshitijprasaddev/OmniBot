#!/usr/bin/env bash
# Copyright 2026 OhhO Robotics
# SPDX-License-Identifier: Apache-2.0
#
# Run the headless Gazebo Nav2 scenarios, each in a fresh sim from the start pose.
#
#   scripts/run_nav_scenarios.sh [--repeat N] [--results FILE] [--timeout S] SCENARIO...
#
#   scripts/run_nav_scenarios.sh kitchen desk door          # CI smoke: 3 scenarios
#   scripts/run_nav_scenarios.sh --repeat 5 kitchen         # nightly stability check
#
# SCENARIO is a waypoint name from config/waypoints.yaml (kitchen, desk, door).
# Exit code is non-zero if any run fails. One JSON line per run goes to FILE
# (default nav-results.jsonl) and a Markdown table is printed at the end.
# Needs a sourced ROS 2 Jazzy workspace with Gazebo Harmonic. Simulation only.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_FILE="${SCRIPT_DIR}/../test/test_nav_sim_scenarios.py"
REPEAT=1
RESULTS="nav-results.jsonl"
RUN_TIMEOUT_S=600
SCENARIOS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repeat) REPEAT="$2"; shift 2 ;;
    --results) RESULTS="$2"; shift 2 ;;
    --timeout) RUN_TIMEOUT_S="$2"; shift 2 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) SCENARIOS+=("$1"); shift ;;
  esac
done
[[ ${#SCENARIOS[@]} -gt 0 ]] || { echo "give at least one scenario" >&2; exit 2; }

RESULTS="$(cd "$(dirname "${RESULTS}")" && pwd)/$(basename "${RESULTS}")"
LOG_DIR="$(dirname "${RESULTS}")/nav-logs"
mkdir -p "${LOG_DIR}"
: > "${RESULTS}"

failures=0
for ((run = 1; run <= REPEAT; run++)); do
  for scenario in "${SCENARIOS[@]}"; do
    echo "=== run ${run}/${REPEAT}: ${scenario} ==="
    log="${LOG_DIR}/run${run}_${scenario}.log"
    lines_before=$(wc -l < "${RESULTS}")
    OMNIBOT_NAV_SCENARIO="${scenario}" OMNIBOT_NAV_RESULTS_FILE="${RESULTS}" \
      timeout --signal=INT --kill-after=30 "${RUN_TIMEOUT_S}" \
      launch_test "${TEST_FILE}" 2>&1 | tee "${log}" | grep -E "EVIDENCE|NAV_RESULT|FAIL|Ran [0-9]+ test|OK$"
    status=${PIPESTATUS[0]}
    if [[ ${status} -ne 0 ]]; then
      echo "run ${run} ${scenario}: launch_test exited ${status}"
      failures=$((failures + 1))
      # A timeout, crash, or not-ready sim leaves no result line; record it.
      if [[ $(wc -l < "${RESULTS}") -eq ${lines_before} ]]; then
        printf '{"scenario": "%s", "success": false, "reason": "launch_test exited %s before a result"}\n' \
          "${scenario}" "${status}" >> "${RESULTS}"
      fi
    fi
    # Make sure no Gazebo/Nav2 process leaks into the next fresh start.
    pkill -f "gz sim" 2>/dev/null || true
    pkill -f "ros_gz_bridge|parameter_bridge" 2>/dev/null || true
    sleep 3
  done
done

echo
python3 "${SCRIPT_DIR}/summarize_nav_results.py" "${RESULTS}" || { [[ ${failures} -gt 0 ]] || failures=1; }
echo "nav scenarios: ${failures} failure(s)"
[[ ${failures} -eq 0 ]]
