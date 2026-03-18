"""Tests for native LSL probe (check-lsl / lsl_support)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

def test_probe_without_pylsl():
    with patch("looplab.streams.lsl_support.pylsl_import_ok", return_value=False):
        from looplab.streams.lsl_support import probe_native_lsl_discovery

        r = probe_native_lsl_discovery()
    assert r["pylsl_available"] is False
    assert r["discovery_ok"] is False
    assert r["lsl_support_tier"] == "native_lsl_unavailable"


@patch("looplab.streams.synthetic.start_synthetic_outlet_thread")
@patch("looplab.streams.lsl_support.pylsl_import_ok", return_value=True)
@patch("looplab.streams.lsl_support.time.sleep", lambda *_: None)
@patch("looplab.streams.lsl_client.LSLInletClient")
def test_probe_discovery_ok(mock_client_cls, _mock_pylsl, mock_start_thread):
    mock_start_thread.return_value.join = MagicMock()
    inst = MagicMock()
    mock_client_cls.return_value = inst
    from looplab.streams.lsl_support import probe_native_lsl_discovery

    r = probe_native_lsl_discovery(settle_sec=0)
    assert r["pylsl_available"] is True
    assert r["discovery_ok"] is True
    assert r["lsl_support_tier"] == "native_lsl_functional"
    inst.connect.assert_called_once()
    inst.close.assert_called_once()


@patch("looplab.streams.synthetic.start_synthetic_outlet_thread")
@patch("looplab.streams.lsl_support.pylsl_import_ok", return_value=True)
@patch("looplab.streams.lsl_support.time.sleep", lambda *_: None)
@patch("looplab.streams.lsl_client.LSLInletClient")
def test_probe_discovery_fails(mock_client_cls, _mock_pylsl, mock_start_thread):
    mock_start_thread.return_value.join = MagicMock()
    inst = MagicMock()
    inst.connect.side_effect = RuntimeError("No LSL stream matching name FakeEEG")
    mock_client_cls.return_value = inst
    from looplab.streams.lsl_support import probe_native_lsl_discovery

    r = probe_native_lsl_discovery(settle_sec=0)
    assert r["pylsl_available"] is True
    assert r["discovery_ok"] is False
    assert r["lsl_support_tier"] == "native_lsl_unavailable"


def test_check_lsl_exit_code():
    from looplab.streams.lsl_support import check_lsl_exit_code

    assert check_lsl_exit_code({"pylsl_available": False, "discovery_ok": False}) == 1
    assert check_lsl_exit_code({"pylsl_available": True, "discovery_ok": False}) == 2
    assert check_lsl_exit_code({"pylsl_available": True, "discovery_ok": True}) == 0


def test_build_check_lsl_json_report_shape():
    from looplab.streams.lsl_support import build_check_lsl_json_report

    r = build_check_lsl_json_report(
        {
            "pylsl_available": True,
            "discovery_ok": True,
            "error": None,
            "lsl_support_tier": "native_lsl_functional",
        }
    )
    assert r["exit_code"] == 0
    assert r["status"] == "ok"
    assert "environment" in r
    assert "python_version" in r["environment"]
    assert "exit_code_meaning" in r
    assert r["probe"]["lsl_support_tier"] == "native_lsl_functional"
