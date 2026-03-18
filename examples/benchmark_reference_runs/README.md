# Benchmark reference runs (comparison suite)

Portable **summary statistics** for three scenarios. Full raw **`benchmark_summary.json`** from a run can be **megabytes** (per-event timestamps); committed files here keep only **aggregates** for diffing and documentation.

## Bundles

| Directory | Scenario | How to regenerate |
|-----------|----------|-------------------|
| `synthetic_baseline/` | Default synthetic proof-run, minimal degradation | `python -m looplab proof-run --backend synthetic --duration 3 --out-dir /tmp/out --seed 42` → copy stats from `benchmark_summary.json` |
| `synthetic_degraded/` | `examples/synthetic_scenario/config.yaml` (noise, dropouts, ack delay, etc.) | `python -m looplab proof-run --backend synthetic --config examples/synthetic_scenario/config.yaml --duration 3 --out-dir /tmp/out --seed 42` |
| `psychopy_e2e/` | Real PsychoPy task + IT→R | Run `examples/psychopy_e2e/run_demo.py --out-dir /tmp/psy --duration 4` (requires PsychoPy); see `REGENERATE.md` |

## Version

These summaries were exported for **LoopLab 0.3.x** (see `summary_stats.json` → `looplab_version` when present). Re-run the suite after changing hooks, `latency_report`, or default proof-run duration.

## Export portable stats

From any run directory:

```bash
python examples/benchmark_reference_runs/export_summary_stats.py /path/to/run_dir --out summary_stats.json
```

## Files

- **`expected_ranges_synthetic.yaml`** — Indicative upper bounds for sanity checks (not contractual SLOs).
- Each scenario folder: **`summary_stats.json`** (e2e_stats, stage stats, window counts; no raw `by_label` arrays).
