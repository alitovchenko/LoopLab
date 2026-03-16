"""Compare logged vs replayed control sequences and report divergence.

Replay agreement contract:
- Action sequence equality: logged and replayed sequences are equal iff they have the same
  length and, for each index, action matches and params match (with numeric tolerance for floats).
- Controller decision equality: we compare action and params only; valid_until_lsl_time is
  ignored (timing can differ slightly).
- Tolerance: float params are compared with absolute tolerance (default 1e-9), configurable
  via compute_divergence(..., float_tolerance=...).
- Divergence report fields: the returned dict has match_count, mismatch_count, total_logged,
  total_replayed, matches (bool), and divergences (list of {index, logged, replayed}).
"""

from __future__ import annotations

from typing import Any


def _params_match(
    logged: dict,
    replayed: dict,
    float_tolerance: float = 1e-9,
) -> bool:
    """Compare action and params; ignore valid_until_lsl_time (timing can differ slightly)."""
    if logged.get("action") != replayed.get("action"):
        return False
    lp = logged.get("params") or {}
    rp = replayed.get("params") or {}
    if set(lp.keys()) != set(rp.keys()):
        return False
    for k in lp:
        a, b = lp[k], rp[k]
        if isinstance(a, float) and isinstance(b, float):
            if abs(a - b) > float_tolerance:
                return False
        elif a != b:
            return False
    return True


def compute_divergence(
    logged: list[dict[str, Any]],
    replayed: list[dict[str, Any]],
    float_tolerance: float = 1e-9,
) -> dict[str, Any]:
    """
    Compare logged vs replayed control signal sequences.

    Returns a dict with: match_count, mismatch_count, total_logged, total_replayed,
    matches (bool), and divergences (list of {index, logged, replayed}).
    """
    total_logged = len(logged)
    total_replayed = len(replayed)
    divergences: list[dict[str, Any]] = []
    match_count = 0
    for i in range(min(total_logged, total_replayed)):
        if _params_match(logged[i], replayed[i], float_tolerance):
            match_count += 1
        else:
            divergences.append({
                "index": i,
                "logged": logged[i],
                "replayed": replayed[i],
            })
    mismatch_count = len(divergences)
    if total_logged != total_replayed:
        mismatch_count += abs(total_logged - total_replayed)
    return {
        "match_count": match_count,
        "mismatch_count": mismatch_count,
        "total_logged": total_logged,
        "total_replayed": total_replayed,
        "matches": mismatch_count == 0 and total_logged == total_replayed,
        "divergences": divergences,
    }


def format_divergence_report(report: dict[str, Any]) -> str:
    """Human-readable one-line or short summary of divergence report."""
    if report["matches"]:
        n = report["match_count"]
        return f"Replay: {n}/{n} control signals matched (determinism OK)."
    lines = [
        f"Replay: {report['match_count']} matched, {report['mismatch_count']} divergence(s).",
        f"  Logged: {report['total_logged']}, Replayed: {report['total_replayed']}.",
    ]
    for d in report["divergences"][:5]:
        lines.append(f"  Index {d['index']}: logged action={d['logged'].get('action')} params={d['logged'].get('params')} vs replayed action={d['replayed'].get('action')} params={d['replayed'].get('params')}")
    if len(report["divergences"]) > 5:
        lines.append(f"  ... and {len(report['divergences']) - 5} more.")
    return "\n".join(lines)
