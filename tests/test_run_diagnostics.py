"""Run-quality diagnostics: thresholds, health rollup, JSON serialization."""

import json
from pathlib import Path

import pytest

from looplab.benchmark.diagnostics import (
    DiagnosticLevel,
    RunDiagnosticsConfig,
    build_run_diagnostics,
    diagnostics_to_jsonable,
    write_run_diagnostics_artifacts,
)


def test_e2e_latency_critical_finding():
    bench = {
        "e2e_latency_seconds": [0.1, 0.1],
        "e2e_stats": {"mean": 0.1, "std": 0.01, "p50": 0.1, "p95": 0.99},
    }
    d = build_run_diagnostics(
        {},
        bench,
        None,
        None,
        None,
        {"duration_sec": 10.0},
        RunDiagnosticsConfig(e2e_p95_critical_sec=0.5),
    )
    codes = {f["code"] for f in d["findings"]}
    assert "e2e_latency_high" in codes
    assert d["health"] in ("degraded", "unhealthy")


def test_missing_realized_critical():
    d = build_run_diagnostics(
        {"stimulus_intended": 100, "stimulus_realized": 50},
        {},
        None,
        None,
        None,
        {"duration_sec": 4.0},
        RunDiagnosticsConfig(realized_missing_ratio_critical=0.3),
    )
    assert any(f["code"] == "missing_realized_events" for f in d["findings"])
    assert d["health"] == "unhealthy"


def test_replay_mismatch_skipped_when_no_replay():
    d = build_run_diagnostics(
        {},
        {},
        {"match_count": 0, "mismatch_count": 10, "total_logged": 10, "total_replayed": 0, "matches": False},
        None,
        None,
        {"duration_sec": 4.0},
    )
    assert not any(f["code"] == "replay_mismatch" for f in d["findings"])


def test_replay_mismatch_when_replayed():
    d = build_run_diagnostics(
        {},
        {},
        {"match_count": 5, "mismatch_count": 5, "total_logged": 10, "total_replayed": 10, "matches": False},
        None,
        None,
        {"duration_sec": 4.0},
    )
    assert any(f["code"] == "replay_mismatch" for f in d["findings"])


def test_insufficient_stream_volume(tmp_path: Path):
    stream = tmp_path / "stream.jsonl"
    stream.write_text("{}\n" * 3, encoding="utf-8")
    d = build_run_diagnostics(
        {},
        {"e2e_latency_seconds": [0.01]},
        None,
        None,
        stream,
        {"duration_sec": 10.0},
        RunDiagnosticsConfig(min_stream_chunk_ratio_warning=0.5, min_expected_chunk_interval_sec=0.015),
    )
    assert any(f["code"] == "insufficient_stream_volume" for f in d["findings"])


def test_invalid_nan_ratio_in_stream(tmp_path: Path):
    stream = tmp_path / "stream.jsonl"
    lines = []
    for _ in range(20):
        lines.append(
            json.dumps(
                {
                    "t_start": 0.0,
                    "t_end": 0.1,
                    "n_samples": 2,
                    "n_channels": 1,
                    "data": [[float("nan"), float("nan")]],
                    "timestamps": [0.0, 0.02],
                }
            )
        )
    stream.write_text("\n".join(lines) + "\n", encoding="utf-8")
    d = build_run_diagnostics(
        {},
        {"e2e_latency_seconds": [0.01]},
        None,
        None,
        stream,
        {"duration_sec": 4.0},
        RunDiagnosticsConfig(invalid_nan_ratio_critical=0.05),
    )
    assert any(f["code"] == "invalid_stream_windows" for f in d["findings"])


def test_action_burst(tmp_path: Path):
    log = tmp_path / "events.jsonl"
    t0 = 1000.0
    lines = []
    for i in range(20):
        lines.append(
            json.dumps(
                {"event_type": "control_signal", "lsl_time": t0 + i * 0.005, "payload": {}}
            )
        )
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    d = build_run_diagnostics(
        {},
        {"e2e_latency_seconds": [0.01]},
        None,
        log,
        None,
        {"duration_sec": 4.0},
        RunDiagnosticsConfig(burst_window_sec=0.1, burst_count_critical=12),
    )
    assert any(f["code"] == "action_burst_suspicious" for f in d["findings"])


def test_low_model_confidence_fraction(tmp_path: Path):
    log = tmp_path / "events.jsonl"
    lines = []
    for _ in range(20):
        lines.append(
            json.dumps(
                {
                    "event_type": "model_output",
                    "lsl_time": 1000.0,
                    "payload": {"value": 0, "confidence": 0.2},
                }
            )
        )
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    d = build_run_diagnostics(
        {},
        {"e2e_latency_seconds": [0.01]},
        None,
        log,
        None,
        {"duration_sec": 4.0},
        RunDiagnosticsConfig(
            low_confidence_fraction_critical=0.7,
            min_model_outputs_for_confidence_check=10,
        ),
    )
    assert any(f["code"] == "low_model_confidence_run" for f in d["findings"])


def test_diagnostics_json_serializable():
    d = build_run_diagnostics(
        {"stimulus_intended": 10, "stimulus_realized": 9},
        {"e2e_stats": {"p95": 0.02, "std": 0.001, "mean": 0.02}},
        {"matches": True, "total_logged": 5, "total_replayed": 5, "mismatch_count": 0},
        None,
        None,
        {"duration_sec": 2.0},
    )
    out = diagnostics_to_jsonable(d)
    s = json.dumps(out)
    assert "health" in s


def test_write_run_diagnostics_artifacts(tmp_path: Path):
    session = {"duration_sec": 1.0}
    diag, inv = write_run_diagnostics_artifacts(
        tmp_path,
        {},
        {"e2e_latency_seconds": [0.01], "e2e_stats": {"p95": 0.01, "std": 0.001, "mean": 0.01}},
        None,
        tmp_path / "events.jsonl",
        tmp_path / "stream.jsonl",
        session,
        ["legacy_warn"],
    )
    assert (tmp_path / "diagnostics.json").exists()
    assert session.get("run_health") == "healthy"
    assert "legacy_warn" in inv


def test_degraded_run_downgrades_replay_finding():
    d = build_run_diagnostics(
        {},
        {},
        {"match_count": 0, "mismatch_count": 10, "total_logged": 10, "total_replayed": 10, "matches": False},
        None,
        None,
        {"duration_sec": 4.0, "degraded": True},
    )
    replay_findings = [f for f in d["findings"] if f["code"] == "replay_mismatch"]
    if replay_findings:
        assert replay_findings[0]["level"] != DiagnosticLevel.CRITICAL
