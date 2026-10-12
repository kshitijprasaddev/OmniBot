# OHH-31 evidence — agent goal → mission planner → Nav2

## Loop trace (JSONL)

Each agent run appends one JSON object per harness step to:

- ROS topic `/agent/loop_trace` (`std_msgs/String`, one JSON line per message)
- File `loop_trace_path` (default `~/.omnibot/agent_loop_trace.jsonl`)

Steps recorded: `perceive` → `reason` → `verify` → `act` → `reflect`.

### Example (`kitchen_goal_trace.jsonl`)

```json
{"ts":1730000000.1,"goal_id":"abc123","step":"perceive","detail":"perceived world state"}
{"ts":1730000000.2,"goal_id":"abc123","step":"reason","detail":"scripted: go to kitchen","calls":["navigate_to"]}
{"ts":1730000000.3,"goal_id":"abc123","step":"verify","detail":"plan verified","approved":1,"blocked":[]}
{"ts":1730000000.4,"goal_id":"abc123","step":"act","detail":"executed 1 call(s)","tools":["navigate_to"]}
{"ts":1730000000.5,"goal_id":"abc123","step":"reflect","detail":"reflection success=true","success":true}
```

Regenerate checked-in traces (no ROS):

```bash
python scripts/ohh31_record_evidence.py
```

## Sim command

With `agent_nav2.launch.py` and Nav2 sim running:

```bash
ros2 topic pub --once /agent/goal std_msgs/msg/String "{data: 'go to the kitchen'}"
ros2 topic echo /mission/command --once
ros2 topic echo /agent/loop_trace
```

`/mission/command` should show `navigate:kitchen` (mission planner → `navigate_to_pose`).

## Verifier rejection demo

See `verifier_reject_outside_map.jsonl` — `verify` step lists a blocked `navigate_to` with
`navigation: goal (99.00, 99.00) outside map envelope`.

Overspeed low-level commands are gated by `learning_engine.verification.SafetyCheck` (see
`agent_engine/tests/test_agent_nav_pipeline.py`).

## Teleop override

`omnibot_hybrid/test/test_cmd_vel_mux.py::TestTeleopPreemptsAutonomy` asserts Nav2 twists are
ignored while the mux is in `teleop` mode.
