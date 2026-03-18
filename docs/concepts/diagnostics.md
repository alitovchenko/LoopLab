# Diagnostics

**Role:** After a run, **diagnostics.json** (and merged session summary fields) summarize **run health**: healthy / degraded / unhealthy, plus **findings** (info / warning / critical) from checks on event rates, replay, benchmarks, etc.

- Used by **`run_report.md`** under “Diagnostics” and in **`methods.warning_status`**.
- Helps collaborators see at a glance whether the log is trustworthy for methods claims.

Regenerate with `python -m looplab report --run-dir <dir> --write` if you fix logs and re-analyze.

See: [Reports](reports.md).
