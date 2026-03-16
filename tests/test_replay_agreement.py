"""Unit tests for replay agreement: action sequence equality, tolerance, divergence report fields."""

import pytest

from looplab.replay.divergence import compute_divergence


EXPECTED_KEYS = {"match_count", "mismatch_count", "total_logged", "total_replayed", "matches", "divergences"}
DIVERGENCE_KEYS = {"index", "logged", "replayed"}


def test_action_sequence_equality_identical():
    """Two identical control sequences produce matches=True, match_count=N, no divergences."""
    logged = [
        {"action": "set_value", "params": {"value": 0.5}},
        {"action": "set_value", "params": {"value": 0.3}},
    ]
    replayed = [
        {"action": "set_value", "params": {"value": 0.5}},
        {"action": "set_value", "params": {"value": 0.3}},
    ]
    report = compute_divergence(logged, replayed)
    assert report["matches"] is True
    assert report["match_count"] == 2
    assert report["mismatch_count"] == 0
    assert report["divergences"] == []


def test_controller_decision_equality():
    """Full agreement on action and params (controller decision equality)."""
    logged = [{"action": "set_value", "params": {"value": 1.0}, "valid_until_lsl_time": 100.0}]
    replayed = [{"action": "set_value", "params": {"value": 1.0}, "valid_until_lsl_time": 200.0}]
    report = compute_divergence(logged, replayed)
    assert report["matches"] is True
    assert report["match_count"] == 1


def test_tolerance_within():
    """Float param within tolerance still produces matches=True."""
    logged = [{"action": "set_value", "params": {"value": 0.5}}]
    replayed = [{"action": "set_value", "params": {"value": 0.5 + 1e-10}}]
    report = compute_divergence(logged, replayed, float_tolerance=1e-9)
    assert report["matches"] is True
    assert report["match_count"] == 1


def test_tolerance_outside():
    """Float param outside tolerance produces matches=False and one divergence."""
    logged = [{"action": "set_value", "params": {"value": 0.5}}]
    replayed = [{"action": "set_value", "params": {"value": 0.6}}]
    report = compute_divergence(logged, replayed, float_tolerance=1e-9)
    assert report["matches"] is False
    assert report["match_count"] == 0
    assert report["mismatch_count"] == 1
    assert len(report["divergences"]) == 1
    assert report["divergences"][0]["index"] == 0


def test_divergence_report_fields():
    """Returned dict has exactly the expected keys; each divergence has index, logged, replayed."""
    logged = [{"action": "a", "params": {}}]
    replayed = [{"action": "b", "params": {}}]
    report = compute_divergence(logged, replayed)
    assert set(report.keys()) == EXPECTED_KEYS
    assert len(report["divergences"]) == 1
    for d in report["divergences"]:
        assert set(d.keys()) == DIVERGENCE_KEYS
        assert "index" in d
        assert "logged" in d
        assert "replayed" in d


def test_length_mismatch():
    """Different sequence lengths produce matches=False and correct counts."""
    logged = [{"action": "set_value", "params": {"value": 0.5}}] * 2
    replayed = [{"action": "set_value", "params": {"value": 0.5}}] * 3
    report = compute_divergence(logged, replayed)
    assert report["matches"] is False
    assert report["total_logged"] == 2
    assert report["total_replayed"] == 3
    assert report["mismatch_count"] == 1
