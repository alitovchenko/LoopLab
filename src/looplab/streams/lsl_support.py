"""Native LSL environment probe (shared by `check-lsl` CLI and docs matrix).

Uses the same synthetic outlet name as proof-run LSL backend (`FakeEEG`).
"""

from __future__ import annotations

import platform
import sys
import time
from typing import Any

PROBE_STREAM_NAME = "FakeEEG"

EXIT_CODE_MEANINGS: dict[int, str] = {
    0: (
        "Native LSL discovery and basic runtime probing succeeded in this environment "
        "(pylsl + liblsl could resolve a test outlet). This is evidence of a working native "
        "stack here—not a guarantee that every live experiment, device, or use case will work."
    ),
    1: "pylsl could not be imported; native LSL is not usable from this Python environment.",
    2: (
        "pylsl loaded but resolving the probe stream failed (discovery/network/runtime). "
        "Treat native LSL as best-effort only on this machine until a probe succeeds."
    ),
}

# Canonical mapping (keep in sync with docs/deployment/lsl_compatibility_matrix.md).
LSL_MATRIX_BLURB = """LoopLab LSL — see docs/deployment/lsl_compatibility_matrix.md

  Supported        = synthetic/default core path     → artifact lsl_support_tier: synthetic_supported
  Best effort      = native LSL runtime path         → native_lsl_functional | native_lsl_unavailable
  Monitoring-only  = native LSL CI lane (test-lsl)  → not a release gate (no extra artifact value)

  check-lsl exit 0 = native LSL discovery + basic runtime probe OK here (not full live certification).
"""


def check_lsl_exit_code(probe_result: dict[str, Any]) -> int:
    """Exit code for `check-lsl`: 0 probe OK, 1 no pylsl, 2 discovery failed."""
    if not probe_result.get("pylsl_available"):
        return 1
    if not probe_result.get("discovery_ok"):
        return 2
    return 0


def pylsl_import_ok() -> bool:
    try:
        import pylsl  # noqa: F401
    except ImportError:
        return False
    return True


def gather_lsl_environment_metadata() -> dict[str, Any]:
    """OS, Python, arch, pylsl/liblsl versions when importable."""
    uname = platform.uname()
    meta: dict[str, Any] = {
        "os": uname.system,
        "os_release": uname.release,
        "os_version": getattr(uname, "version", "") or "",
        "python_version": sys.version.split()[0],
        "architecture": platform.machine(),
        "processor": uname.processor or None,
        "pylsl_version": None,
        "liblsl_library_version": None,
        "liblsl_build_info": None,
    }
    if not pylsl_import_ok():
        return meta
    try:
        from importlib.metadata import version

        meta["pylsl_version"] = version("pylsl")
    except Exception:
        pass
    try:
        import pylsl

        try:
            meta["liblsl_library_version"] = int(pylsl.library_version())
        except Exception:
            meta["liblsl_library_version"] = pylsl.library_version()
        try:
            meta["liblsl_build_info"] = str(pylsl.library_info())
        except Exception:
            pass
    except Exception:
        pass
    return meta


def probe_native_lsl_discovery(
    *,
    outlet_duration_sec: float = 3.0,
    settle_sec: float = 0.8,
    inlet_timeout: float = 5.0,
    chunk_size: int = 8,
) -> dict[str, Any]:
    """
    Start a short-lived synthetic LSL outlet and try to resolve it via LSLInletClient.

    Returns:
        pylsl_available: bool
        discovery_ok: bool
        error: str | None
        lsl_support_tier: native_lsl_functional | native_lsl_unavailable (aligned with session_summary)
    """
    if not pylsl_import_ok():
        return {
            "pylsl_available": False,
            "discovery_ok": False,
            "error": "pylsl import failed (install looplab deps / LSL Python bindings)",
            "lsl_support_tier": "native_lsl_unavailable",
        }

    from looplab.streams.lsl_client import LSLInletClient
    from looplab.streams.synthetic import start_synthetic_outlet_thread

    thread = start_synthetic_outlet_thread(
        outlet_duration_sec, n_channels=2, srate=50.0, stream_name=PROBE_STREAM_NAME
    )
    time.sleep(settle_sec)
    try:
        client = LSLInletClient(name=PROBE_STREAM_NAME, timeout=inlet_timeout, chunk_size=chunk_size)
        try:
            client.connect()
        except RuntimeError as e:
            if "No LSL stream" in str(e):
                return {
                    "pylsl_available": True,
                    "discovery_ok": False,
                    "error": str(e),
                    "lsl_support_tier": "native_lsl_unavailable",
                }
            raise
        client.close()
        return {
            "pylsl_available": True,
            "discovery_ok": True,
            "error": None,
            "lsl_support_tier": "native_lsl_functional",
        }
    finally:
        thread.join(timeout=15.0)


def build_check_lsl_json_report(probe: dict[str, Any]) -> dict[str, Any]:
    """Full `--json` payload: environment, probe, status, exit metadata."""
    exit_code = check_lsl_exit_code(probe)
    if not probe.get("pylsl_available"):
        status = "pylsl_missing"
        message = probe.get("error") or "pylsl not available"
    elif probe.get("discovery_ok"):
        status = "ok"
        message = (
            "Test outlet resolved: native LSL discovery and basic runtime probing succeeded "
            "in this environment. Not a guarantee for all hardware or live experiment paths."
        )
    else:
        status = "discovery_failed"
        message = probe.get("error") or "Could not resolve probe stream"

    return {
        "environment": gather_lsl_environment_metadata(),
        "probe": {
            "pylsl_available": probe["pylsl_available"],
            "discovery_ok": probe["discovery_ok"],
            "lsl_support_tier": probe.get("lsl_support_tier", "native_lsl_unavailable"),
            "error": probe.get("error"),
        },
        "status": status,
        "message": message,
        "exit_code": exit_code,
        "exit_code_meaning": EXIT_CODE_MEANINGS.get(exit_code, ""),
        "doc": "docs/deployment/lsl_compatibility_matrix.md",
    }


def check_lsl_human_message(probe: dict[str, Any]) -> str:
    """One block after matrix blurb; same claims as exit_code_meaning / matrix doc."""
    if not probe.get("pylsl_available"):
        return (
            "Result: exit 1 — pylsl not importable. "
            "lsl_support_tier (probe): native_lsl_unavailable."
        )
    if probe.get("discovery_ok"):
        return (
            "Result: exit 0 — native LSL discovery and basic runtime probing succeeded (test outlet resolved). "
            "lsl_support_tier (probe): native_lsl_functional. "
            "Not a guarantee for every live experiment path."
        )
    return (
        "Result: exit 2 — probe stream not resolved; native LSL best-effort only here. "
        "lsl_support_tier (probe): native_lsl_unavailable."
    )
