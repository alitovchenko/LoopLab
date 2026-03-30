"""Proof-run success banner and failure hints (stderr)."""

from __future__ import annotations

import sys
from pathlib import Path


def print_proof_success_banner(out_dir: Path) -> None:
    """After all checks pass: copy-pasteable success criteria and next steps."""
    od = str(out_dir.resolve())
    rr = out_dir / "replay_result.json"
    ev = out_dir / "events.jsonl"
    sm = out_dir / "RUN_SUMMARY.md"
    print("", file=sys.stderr)
    print("--- Proof-run success ---", file=sys.stderr)
    print("Exit code: 0 (all checks passed).", file=sys.stderr)
    print(f"Output directory: {od}", file=sys.stderr)
    print("Quick checks (copy-paste):", file=sys.stderr)
    print(f'  test -f "{rr}" && test -f "{ev}" && test -f "{sm}"', file=sys.stderr)
    print(f'  grep -q \'"matches": true\' "{rr}" 2>/dev/null || grep -q "matches" "{rr}"', file=sys.stderr)
    print(f'  test -s "{ev}"', file=sys.stderr)
    print("Next:", file=sys.stderr)
    print(f"  python -m looplab report --run-dir {od} --human", file=sys.stderr)
    print(f"  Open: {out_dir / 'run_report.md'} or {sm}", file=sys.stderr)
    print("-------------------------", file=sys.stderr)


def print_proof_replay_failure(out_dir: Path, replay_result: dict, *, strict: bool) -> None:
    print("", file=sys.stderr)
    print("Proof-run: replay check failed.", file=sys.stderr)
    if strict:
        print("  Cause: replay diverged from the logged control sequence (--strict is on).", file=sys.stderr)
    else:
        print("  Cause: replay did not match the logged control sequence.", file=sys.stderr)
    print("  Inspect:", file=sys.stderr)
    print(f"    {out_dir / 'replay_result.json'}  (matches, divergences)", file=sys.stderr)
    print(f"    {out_dir / 'events.jsonl'}", file=sys.stderr)
    print("  Try: re-run with a fixed --seed, simplify --config / synthetic scenario, or report a bug if", file=sys.stderr)
    print("       deterministic replay should hold for this setup.", file=sys.stderr)
    if replay_result.get("divergences"):
        n = len(replay_result["divergences"])
        print(f"  Note: {n} divergence record(s) in replay_result.json.", file=sys.stderr)


def print_proof_lsl_discovery_failed_hint() -> None:
    print("", file=sys.stderr)
    print("What to do next:", file=sys.stderr)
    print("  • CI-safe path (no native LSL):  python -m looplab proof-run --backend synthetic", file=sys.stderr)
    print("  • Diagnose native LSL:           python -m looplab check-lsl", file=sys.stderr)
    print("  • See: docs/deployment/lsl_compatibility_matrix.md", file=sys.stderr)
