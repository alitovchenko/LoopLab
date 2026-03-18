# Tutorial: PsychoPy end-to-end

**Demo:** `examples/psychopy_e2e/`

The **canonical adaptive PsychoPy path**: controller loop in a background thread, **real PsychoPy window** on the main thread, same adapter and clock. Adaptation changes a **visible parameter** (circle radius); **`report_realized`** records timing; trial metadata lands in JSONL.

## Steps

1. `pip install -e ".[psychopy]"` (plus dev/yaml as needed).
2. From repo root or the example dir:

   ```bash
   python examples/psychopy_e2e/run_demo.py --out-dir demo_out --duration 4
   ```

3. Open **`demo_out/run_report.md`** — includes **Task-level summary (PsychoPy bridge)** because `session_summary` sets `paradigm: psychopy_e2e`.

## Read next

- Example README: **Canonical adaptive PsychoPy path** (numbered flow).
- [PsychoPy integration contract](../psychopy_integration.md)
- [Deployment: PsychoPy](../deployment/psychopy_task_integration.md)
