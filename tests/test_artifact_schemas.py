"""Regression tests for run artifact JSON contracts (see docs/artifact_schemas.md)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "artifact_contracts"
SCHEMAS = Path(__file__).resolve().parent.parent / "schemas"

ARTIFACTS = [
    "session_summary",
    "benchmark_summary",
    "diagnostics",
    "replay_result",
    "components_manifest",
    "run_report",
]


def _load_fixture(name: str) -> dict:
    path = FIXTURES / f"{name}.minimal.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_session_summary_contract():
    d = _load_fixture("session_summary")
    assert isinstance(d["duration_sec"], (int, float))
    assert d["backend"] == "synthetic"
    assert isinstance(d["artifacts_ok"], bool)
    assert isinstance(d["replay_ok"], bool)
    assert "run_health" in d
    assert d.get("lsl_support_tier") == "synthetic_supported"
    assert isinstance(d["diagnostic_findings"], list)
    assert isinstance(d["warning_messages"], list)


def test_benchmark_summary_contract():
    d = _load_fixture("benchmark_summary")
    assert isinstance(d["by_label"], dict)
    assert "e2e_mean" in d or "e2e_stats" in d
    assert isinstance(d.get("e2e_latency_seconds", []), list)


def test_diagnostics_contract():
    d = _load_fixture("diagnostics")
    assert d["health"] in ("healthy", "degraded", "unhealthy")
    assert isinstance(d["findings"], list)
    for f in d["findings"]:
        assert "level" in f and "code" in f and "message" in f


def test_replay_result_contract():
    d = _load_fixture("replay_result")
    assert isinstance(d["match_count"], int)
    assert isinstance(d["matches"], bool)
    assert isinstance(d["divergences"], list)
    assert d["total_logged"] >= 0


def test_components_manifest_contract():
    d = _load_fixture("components_manifest")
    assert isinstance(d["looplab_version"], str)
    for key in ("feature_extractor", "model", "policy"):
        comp = d[key]
        assert "name" in comp
        assert comp["registered"] is True
        assert "class" in comp


def test_run_report_contract():
    d = _load_fixture("run_report")
    m = d["methods"]
    assert "feature_extractor_name" in m
    assert "pipeline" in d
    assert d["pipeline"].get("source")
    assert isinstance(d["artifact_inventory"], list)
    assert d["artifact_inventory"]
    inv = d["artifact_inventory"][0]
    assert inv["name"].endswith(".json")
    assert "present" in inv


def test_fixtures_validate_against_json_schema():
    """Validates minimal fixtures against schemas/ (jsonschema is a core dependency)."""
    for name in ARTIFACTS:
        schema_path = SCHEMAS / f"{name}.schema.json"
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
        instance = _load_fixture(name)
        jsonschema.validate(instance=instance, schema=schema)
