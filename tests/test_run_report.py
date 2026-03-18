"""Methods-ready run_report.json / run_report.md."""

import json
from pathlib import Path

from looplab.benchmark.run_report import build_run_report, format_run_report_markdown, write_run_report_artifacts


def test_build_run_report_methods_and_experiment(tmp_path: Path):
    (tmp_path / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"event_type": "trial_start", "lsl_time": 1.0, "payload": {}}),
                json.dumps({"event_type": "block_start", "lsl_time": 0.0, "payload": {}}),
                json.dumps(
                    {
                        "event_type": "control_signal",
                        "lsl_time": 2.0,
                        "payload": {"action": "set_difficulty", "params": {}},
                    }
                ),
                json.dumps({"event_type": "adaptive_params_update", "lsl_time": 2.0, "payload": {}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    cfg = {
        "lsl": {"chunk_size": 8},
        "buffer": {"max_samples": 500, "n_channels": 2},
        "preprocess": "none",
        "feature_extractor": "simple",
        "model": "identity",
        "policy": "adaptive_difficulty",
    }
    (tmp_path / "config_snapshot.json").write_text(json.dumps(cfg), encoding="utf-8")
    (tmp_path / "session_summary.json").write_text(
        json.dumps({"duration_sec": 4.0, "backend": "synthetic", "run_health": "healthy"}),
        encoding="utf-8",
    )
    bench = {
        "e2e_mean": 0.02,
        "e2e_stats": {"mean": 0.02, "std": 0.001, "p95": 0.03},
        "by_label": {"window_ready": [1, 2, 3], "policy_done": [1, 2, 3]},
    }
    (tmp_path / "benchmark_summary.json").write_text(json.dumps(bench), encoding="utf-8")
    (tmp_path / "replay_result.json").write_text(
        json.dumps({"matches": True, "match_count": 5, "mismatch_count": 0, "total_logged": 5, "total_replayed": 5}),
        encoding="utf-8",
    )
    (tmp_path / "diagnostics.json").write_text(
        json.dumps({"health": "healthy", "findings": [{"level": "info", "code": "x", "message": "ok"}]}),
        encoding="utf-8",
    )

    r = build_run_report(tmp_path)
    assert r["methods"]["model_name"] == "identity"
    assert r["methods"]["policy_name"] == "adaptive_difficulty"
    assert r["methods"]["window_size_samples"] == 8
    assert r["experiment_summary"]["trial_start"] == 1
    assert r["experiment_summary"]["has_experiment_events"] is True
    assert r["adaptation"]["first_control_action"] == "set_difficulty"
    assert r["adaptation"]["adaptive_params_update"] == 1
    assert r["replay_agreement"]["matches"] is True
    assert r["methods"]["timing_summary"]["e2e_seconds"]["p95"] == 0.03
    inv = {x["name"]: x["present"] for x in r["artifact_inventory"]}
    assert inv["config_snapshot.json"] is True
    assert inv["run_report.json"] is False

    md = format_run_report_markdown(r)
    assert "Methods (citable)" in md
    assert "identity" in md

    write_run_report_artifacts(tmp_path)
    assert (tmp_path / "run_report.json").exists()
    assert (tmp_path / "run_report.md").exists()
    r2 = json.loads((tmp_path / "run_report.json").read_text(encoding="utf-8"))
    inv2 = {x["name"]: x for x in r2["artifact_inventory"]}
    assert inv2["run_report.json"]["present"] is True


def test_task_level_summary_psychopy_e2e(tmp_path: Path):
    (tmp_path / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"event_type": "stimulus_intended", "lsl_time": 1.0, "payload": {}}),
                json.dumps({"event_type": "stimulus_realized", "lsl_time": 1.01, "payload": {}}),
                json.dumps({"event_type": "trial_start", "lsl_time": 1.0, "payload": {}}),
                json.dumps({"event_type": "trial_outcome", "lsl_time": 2.0, "payload": {}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    cfg = {
        "lsl": {"chunk_size": 8},
        "buffer": {"max_samples": 500, "n_channels": 2},
        "preprocess": "none",
        "feature_extractor": "simple",
        "model": "identity",
        "policy": "identity",
    }
    (tmp_path / "config_snapshot.json").write_text(json.dumps(cfg), encoding="utf-8")
    (tmp_path / "session_summary.json").write_text(
        json.dumps({"duration_sec": 4.0, "backend": "synthetic", "paradigm": "psychopy_e2e"}),
        encoding="utf-8",
    )
    (tmp_path / "benchmark_summary.json").write_text(
        json.dumps({"intended_to_realized_mean": 0.015, "by_label": {"window_ready": [1]}}),
        encoding="utf-8",
    )

    r = build_run_report(tmp_path)
    assert r["methods"]["adaptation_target"] == "psychopy_e2e: set_value → stimulus radius"
    tls = r.get("task_level_summary")
    assert tls is not None
    assert tls["stimulus_realized"] == 1
    assert tls["stimulus_intended"] == 1
    assert tls["trial_outcomes"] == 1
    assert tls["adaptive_param_logged"] == "stimulus_size"
    assert tls["intended_to_realized_mean_sec"] == 0.015

    md = format_run_report_markdown(r)
    assert "Task-level summary (PsychoPy bridge)" in md
    assert "stimulus_size" in md
