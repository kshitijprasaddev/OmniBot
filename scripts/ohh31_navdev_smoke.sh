#!/usr/bin/env bash
# Run inside the navdev container (ros:jazzy) — headless smoke, not on real hardware.
set -euo pipefail
WS=/ws
STAGE="${WS}/stage/ohh-31"
mkdir -p "${STAGE}"
echo "[ohh-31] staging sources into ${STAGE}"
cp -a /path/on/host/omnibot-ai-engines "${STAGE}/" 2>/dev/null || true

source /opt/ros/jazzy/setup.bash
python3 -m pip install --break-system-packages -e "${STAGE}/learning_engine" -e "${STAGE}/agent_engine" numpy
python3 -m unittest discover -s "${STAGE}/agent_engine/tests" -t "${STAGE}" -q
echo "[ohh-31] agent_engine unit tests OK"
