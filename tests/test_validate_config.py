"""validate-config CLI and validate_config_file."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import yaml

REPO = Path(__file__).resolve().parents[1]


def test_validate_config_ok_builtin(tmp_path: Path):
    cfg = {
        "lsl": {"name": "X", "chunk_size": 8},
        "buffer": {"max_samples": 100, "n_channels": 2},
        "preprocess": "none",
        "feature_extractor": "simple",
        "feature_extractor_config": {},
        "model": "identity",
        "model_config": {},
        "policy": "identity",
        "policy_config": {},
        "task_adapter": "psychopy",
        "log_path": "e.jsonl",
    }
    p = tmp_path / "c.yaml"
    p.write_text(yaml.dump(cfg), encoding="utf-8")
    from looplab.runner import validate_config_file

    r = validate_config_file(p)
    assert r["ok"] is True
    assert not r["errors"]


def test_validate_config_unknown_model(tmp_path: Path):
    cfg = {
        "lsl": {"chunk_size": 8},
        "buffer": {"max_samples": 100, "n_channels": 2},
        "preprocess": "none",
        "feature_extractor": "simple",
        "model": "no_such_model_xyz",
        "policy": "identity",
        "log_path": "e.jsonl",
    }
    p = tmp_path / "c.yaml"
    p.write_text(yaml.dump(cfg), encoding="utf-8")
    from looplab.runner import validate_config_file

    r = validate_config_file(p)
    assert r["ok"] is False
    assert any("Unknown model" in e for e in r["errors"])


def test_validate_config_bad_model_kwargs(tmp_path: Path):
    cfg = {
        "lsl": {"chunk_size": 8},
        "buffer": {"max_samples": 100, "n_channels": 2},
        "preprocess": "none",
        "feature_extractor": "simple",
        "model": "identity",
        "model_config": {"bogus_kwarg": 123},
        "policy": "identity",
        "log_path": "e.jsonl",
    }
    p = tmp_path / "c.yaml"
    p.write_text(yaml.dump(cfg), encoding="utf-8")
    from looplab.runner import validate_config_file

    r = validate_config_file(p)
    assert r["ok"] is False
    assert any("identity" in e and "failed" in e for e in r["errors"])


def test_validate_config_preprocess_warning(tmp_path: Path):
    cfg = {
        "lsl": {"chunk_size": 8},
        "buffer": {"max_samples": 100, "n_channels": 2},
        "preprocess": "unknown_pipeline",
        "feature_extractor": "simple",
        "model": "identity",
        "policy": "identity",
        "log_path": "e.jsonl",
    }
    p = tmp_path / "c.yaml"
    p.write_text(yaml.dump(cfg), encoding="utf-8")
    from looplab.runner import validate_config_file

    r = validate_config_file(p, strict=False)
    assert r["ok"] is True
    assert r["warnings"]

    r2 = validate_config_file(p, strict=True)
    assert r2["ok"] is False


def test_validate_config_cli_subprocess():
    with tempfile.TemporaryDirectory() as d:
        cfg = {
            "lsl": {"chunk_size": 8},
            "buffer": {"max_samples": 100, "n_channels": 2},
            "preprocess": "none",
            "feature_extractor": "simple",
            "model": "identity",
            "policy": "identity",
            "log_path": "e.jsonl",
        }
        p = Path(d) / "c.yaml"
        p.write_text(yaml.dump(cfg), encoding="utf-8")
        out = subprocess.run(
            [sys.executable, "-m", "looplab", "validate-config", "--config", str(p)],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        assert out.returncode == 0, out.stderr


def test_list_components_json():
    out = subprocess.run(
        [sys.executable, "-m", "looplab", "list-components", "--json"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0
    data = json.loads(out.stdout)
    assert "models" in data
    assert "identity" in data["models"]
    assert "class" in data["models"]["identity"]


def test_build_components_manifest():
    from looplab.config.schema import RunConfig, LSLStreamConfig, BufferConfig
    from looplab.runner import build_components_manifest

    c = RunConfig(
        lsl=LSLStreamConfig(chunk_size=8),
        buffer=BufferConfig(max_samples=100, n_channels=2),
        feature_extractor="simple",
        model="identity",
        policy="identity",
    )
    m = build_components_manifest(c)
    assert m["looplab_version"]
    assert m["model"]["name"] == "identity"
    assert m["model"]["registered"] is True
    assert m["model"]["effective_config"] == {}
