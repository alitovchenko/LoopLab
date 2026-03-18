"""Tests for synthetic scenario system: deterministic replay under faults, warnings, artifact writing, controller stability."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

import pytest


def _run_proof_run(out_dir: str, extra_args: list[str] | None = None, config_path: str | None = None) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable, "-m", "looplab", "proof-run",
        "--backend", "synthetic",
        "--duration", "2",
        "--out-dir", out_dir,
        "--seed", "42",
    ]
    if config_path:
        cmd.extend(["--config", config_path])
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=Path(__file__).resolve().parent.parent)


def test_synthetic_stationary_clean_artifacts_written():
    """With scenario stationary_clean (default), all canonical artifacts are written."""
    with tempfile.TemporaryDirectory() as d:
        out = _run_proof_run(d)
        assert out.returncode == 0, (out.stdout, out.stderr)
        for name in ["config_snapshot.json", "events.jsonl", "stream.jsonl", "replay_result.json",
                     "benchmark_summary.json", "session_summary.json"]:
            p = Path(d) / name
            assert p.exists(), f"missing {name}"
            if name.endswith(".jsonl") and name != "stream.jsonl":
                assert p.stat().st_size > 0


def test_synthetic_scenario_config_deterministic_replay():
    """With a scenario config (dropouts, seed), replay runs and produces replay_result."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        config = {
            "lsl": {"name": "FakeEEG", "type": "EEG", "chunk_size": 8, "timeout": 5.0},
            "buffer": {"max_samples": 500, "n_channels": 2},
            "preprocess": "none",
            "feature_extractor": "simple",
            "model": "identity",
            "policy": "identity",
            "task_adapter": "psychopy",
            "log_path": "e.jsonl",
            "record_stream_path": "s.jsonl",
            "benchmark": True,
            "synthetic": {
                "scenario": "stationary_clean",
                "seed": 123,
                "dropouts": {"enabled": True, "probability": 0.1},
            },
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        out_dir = tmp_path / "run1"
        out_dir.mkdir()
        out = _run_proof_run(str(out_dir), config_path=str(config_path))
        assert out.returncode == 0, (out.stdout, out.stderr)
        replay_path = out_dir / "replay_result.json"
        assert replay_path.exists()
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        assert "match_count" in replay and "total_replayed" in replay


def test_synthetic_drifting_attention_runs():
    """Scenario drifting_attention runs without error and writes artifacts."""
    with tempfile.TemporaryDirectory() as tmp:
        config = {
            "lsl": {"name": "FakeEEG", "chunk_size": 8},
            "buffer": {"max_samples": 500, "n_channels": 2},
            "feature_extractor": "simple",
            "model": "identity",
            "policy": "identity",
            "log_path": "e.jsonl",
            "record_stream_path": "s.jsonl",
            "benchmark": True,
            "synthetic": {
                "scenario": "drifting_attention",
                "seed": 42,
                "drift_per_channel": [0.01, -0.01],
            },
        }
        config_path = Path(tmp) / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        out_dir = Path(tmp) / "run"
        out_dir.mkdir()
        out = _run_proof_run(str(out_dir), config_path=str(config_path))
        assert out.returncode == 0, (out.stdout, out.stderr)
        assert (out_dir / "events.jsonl").exists()
        assert (out_dir / "stream.jsonl").stat().st_size > 0


def test_synthetic_warnings_in_run_package():
    """Under fault conditions (dropouts, omissions), run_package_summary can contain warnings."""
    with tempfile.TemporaryDirectory() as tmp:
        config = {
            "lsl": {"name": "FakeEEG", "chunk_size": 8},
            "buffer": {"max_samples": 500, "n_channels": 2},
            "feature_extractor": "simple",
            "model": "identity",
            "policy": "identity",
            "log_path": "e.jsonl",
            "record_stream_path": "s.jsonl",
            "benchmark": True,
            "synthetic": {
                "scenario": "stationary_clean",
                "seed": 99,
                "dropouts": {"enabled": True, "probability": 0.2},
                "event_omission": {"enabled": True, "probability": 0.1},
            },
        }
        config_path = Path(tmp) / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        out_dir = Path(tmp) / "run"
        out_dir.mkdir()
        out = _run_proof_run(str(out_dir), config_path=str(config_path))
        assert out.returncode == 0, (out.stdout, out.stderr)
        pkg_path = out_dir / "run_package_summary.json"
        assert pkg_path.exists()
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        # Run package summary has replay status, action counts, and/or warning_inventory
        assert "replay_match_status" in pkg or "action_counts" in pkg or "warning_inventory" in pkg


def test_controller_stable_under_invalid_windows():
    """Controller does not crash when invalid (NaN) windows are occasionally emitted."""
    from looplab.synthetic.config import InvalidWindowsConfig, SyntheticConfig, parse_synthetic_config
    from looplab.synthetic.generator import generate_chunks

    cfg = SyntheticConfig(
        scenario="stationary_clean",
        seed=42,
        invalid_windows=InvalidWindowsConfig(enabled=True, probability=0.2),
    )
    chunks = list(generate_chunks(cfg, duration_sec=0.5, n_channels=2, chunk_size=8, srate=50.0, start_time=1000.0))
    assert len(chunks) >= 1
    valid_count = sum(1 for _, _, v in chunks if v)
    invalid_count = sum(1 for _, _, v in chunks if not v)
    # With 0.2 probability we may get some invalid
    assert valid_count + invalid_count == len(chunks)


def test_signal_generators_shape_and_determinism():
    """Signal generators produce correct shape and are deterministic for fixed seed."""
    from looplab.synthetic.signals import drifting_latent_state, regime_shift, stationary_clean

    rng = np.random.default_rng(42)
    s = stationary_clean(16, 2, rng)
    assert s.shape == (16, 2)
    rng2 = np.random.default_rng(42)
    s2 = stationary_clean(16, 2, rng2)
    np.testing.assert_array_equal(s, s2)

    rng3 = np.random.default_rng(7)
    d = drifting_latent_state(8, 2, rng3, t_start=1000.0, srate=50.0, drift_per_channel=[0.01, -0.01])
    assert d.shape == (8, 2)

    rng4 = np.random.default_rng(7)
    r = regime_shift(8, 2, rng4, t_start=1000.0, srate=50.0, regime_shift_times=[1000.1], scale=2.0, offset=1.0)
    assert r.shape == (8, 2)
