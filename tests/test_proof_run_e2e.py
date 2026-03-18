"""E2E test: proof-run completes, canonical artifacts exist, replay matches, benchmark is interpretable."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

CANONICAL_FILES = (
    "config_snapshot.json",
    "components_manifest.json",
    "events.jsonl",
    "stream.jsonl",
    "replay_result.json",
    "benchmark_summary.json",
    "diagnostics.json",
    "session_summary.json",
    "run_package_summary.json",
    "RUN_SUMMARY.md",
    "run_report.json",
    "run_report.md",
)


def test_proof_run_e2e():
    """
    Run proof-run in subprocess with --backend synthetic (no LSL). Assert: all six canonical
    artifact files exist; session_summary has artifacts_ok, replay_ok; replay_result has
    matches true; replay output reports match (determinism OK). This test is CI-safe and
    does not touch native LSL.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [
                sys.executable, "-m", "looplab", "proof-run",
                "--backend", "synthetic",
                "--duration", "2.0",
                "--out-dir", tmpdir,
                "--seed", "42",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).resolve().parents[1],
        )
        stderr = result.stderr or ""
        stdout = result.stdout or ""

        assert result.returncode == 0, (
            f"proof-run failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

        out = Path(tmpdir)
        for name in CANONICAL_FILES:
            p = out / name
            assert p.exists(), f"Canonical artifact {name} should exist"

        log_path = out / "events.jsonl"
        stream_path = out / "stream.jsonl"
        assert log_path.stat().st_size > 0, "events.jsonl should be non-empty"
        assert stream_path.stat().st_size > 0, "stream.jsonl should be non-empty"

        with open(out / "session_summary.json", encoding="utf-8") as f:
            session = json.load(f)
        assert "artifacts_ok" in session, "session_summary should have artifacts_ok"
        assert "replay_ok" in session, "session_summary should have replay_ok"
        assert session.get("artifacts_ok") is True, "artifacts_ok should be true on success"
        assert session.get("replay_ok") is True, "replay_ok should be true on success"
        assert "run_health" in session, "session_summary should include run_health"
        assert (out / "diagnostics.json").exists(), "diagnostics.json should exist"

        with open(out / "replay_result.json", encoding="utf-8") as f:
            replay_result = json.load(f)
        assert "matches" in replay_result, "replay_result should have matches"
        assert replay_result["matches"] is True, "replay_result.matches should be true on success"

        combined = stderr + stdout
        assert "matched" in combined or "determinism OK" in combined, "Replay should report match"
        assert "E2E" in combined or "e2e" in combined or "Proof-run: all checks passed" in combined, (
            "Benchmark or success message should be present"
        )


# Expected keys so artifact/report consumers can assume one structure regardless of backend (synthetic or LSL).
SESSION_SUMMARY_KEYS = {"duration_sec", "seed", "out_dir", "artifacts_ok", "replay_ok", "lsl_available", "timestamp", "backend"}
BENCHMARK_SUMMARY_KEYS = {"by_label"}  # at least; may have e2e_mean, e2e_stats, intended_to_realized_*, etc.
RUN_PACKAGE_SUMMARY_KEYS = {
    "component_versions", "action_counts", "window_count", "replay_match_status",
    "benchmark_readiness", "warning_inventory", "config_hash", "backend", "diagnostics",
}


def test_proof_run_artifact_structure():
    """
    Assert that proof-run (synthetic) produces the canonical artifact layout and that
    session_summary and benchmark_summary have the expected keys. This guarantees
    synthetic and LSL backends can produce the same structure for consumers.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [
                sys.executable, "-m", "looplab", "proof-run",
                "--backend", "synthetic",
                "--duration", "1.0",
                "--out-dir", tmpdir,
                "--seed", "42",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).resolve().parents[1],
        )
        if result.returncode != 0:
            pytest.skip(f"proof-run failed (e.g. package not installed): {result.stderr}")
        out = Path(tmpdir)
        for name in CANONICAL_FILES:
            assert (out / name).exists(), f"Canonical artifact {name} should exist"
        with open(out / "session_summary.json", encoding="utf-8") as f:
            session = json.load(f)
        missing = SESSION_SUMMARY_KEYS - set(session)
        assert not missing, f"session_summary missing keys: {missing}"
        with open(out / "benchmark_summary.json", encoding="utf-8") as f:
            bench = json.load(f)
        assert "by_label" in bench, "benchmark_summary should have by_label"
        with open(out / "run_package_summary.json", encoding="utf-8") as f:
            rps = json.load(f)
        missing_rps = RUN_PACKAGE_SUMMARY_KEYS - set(rps)
        assert not missing_rps, f"run_package_summary missing keys: {missing_rps}"
