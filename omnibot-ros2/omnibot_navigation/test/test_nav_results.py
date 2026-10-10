# Copyright 2026 OhhO Robotics
# SPDX-License-Identifier: Apache-2.0
"""ROS-free test of scripts/summarize_nav_results.py (the CI summary table)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import summarize_nav_results as summary  # noqa: E402


def _row(scenario, seconds, success=True, **extra):
    row = {
        "scenario": scenario,
        "success": success,
        "time_to_goal_s": seconds if success else None,
        "wall_time_s": seconds,
        "final_error_xy_m": 0.12,
        "final_error_yaw_rad": 0.2,
    }
    row.update(extra)
    return row


def test_table_has_a_row_per_run_and_a_per_scenario_summary():
    text = summary.render([_row("kitchen", 16.0), _row("kitchen", 18.0), _row("desk", 22.5)])
    assert text.count("| PASS |") == 3
    assert "| kitchen | 2 | 2 | 16.0 / 17.0 / 18.0 |" in text
    assert "| desk | 1 | 1 | 22.5 / 22.5 / 22.5 |" in text


def test_failed_run_is_reported_with_its_reason():
    text = summary.render([_row("door", 61.0, success=False, reason="not reached within 60 s")])
    assert "FAIL: not reached within 60 s" in text
    assert "| door | 1 | 0 | - |" in text


def test_main_exit_code_follows_the_results(tmp_path, capsys):
    good = tmp_path / "good.jsonl"
    good.write_text(json.dumps(_row("kitchen", 16.0)) + "\n", encoding="utf-8")
    bad = tmp_path / "bad.jsonl"
    bad.write_text(
        json.dumps(_row("kitchen", 16.0)) + "\n" + json.dumps(_row("desk", 70.0, success=False, reason="x")) + "\n",
        encoding="utf-8",
    )
    assert summary.main([str(good)]) == 0
    assert summary.main([str(bad)]) == 1
    assert summary.main([]) == 2
    capsys.readouterr()
