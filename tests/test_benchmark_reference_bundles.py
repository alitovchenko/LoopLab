"""Reference benchmark bundles stay valid JSON with expected keys."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "examples" / "benchmark_reference_runs"


@pytest.mark.parametrize(
    "rel",
    [
        "synthetic_baseline/summary_stats.json",
        "synthetic_degraded/summary_stats.json",
    ],
)
def test_reference_summary_stats_schema(rel: str) -> None:
    p = REF / rel
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("e2e_stats", {}).get("p95") is not None
    assert d.get("n_pull_chunk", 0) > 0
    assert "preprocess_latency_stats" in d


def test_expected_ranges_yaml_exists() -> None:
    assert (REF / "expected_ranges_synthetic.yaml").is_file()
