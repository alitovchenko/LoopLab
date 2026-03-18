# PsychoPy e2e benchmark reference

This bundle is **not** committed with full stats by default (runs need a display and PsychoPy). Generate locally:

```bash
cd examples/psychopy_e2e
python run_demo.py --out-dir ../../benchmark_reference_runs/psychopy_e2e/run_output --duration 4 --seed 42
python ../export_summary_stats.py ../../benchmark_reference_runs/psychopy_e2e/run_output \
  --out ../../benchmark_reference_runs/psychopy_e2e/summary_stats.json
```

Expected in **`summary_stats.json`** after export:

- **`intended_to_realized_stats`** (mean, p95) — task-level display path
- **Large `n_stimulus_realized`** matching trials with control signals
- **E2E** similar order of magnitude to synthetic baseline (same pipeline)

Compare to **`../expected_ranges_synthetic.yaml`** → `psychopy_e2e` for IT→R.
