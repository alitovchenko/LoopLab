# Add a synthetic scenario

Synthetic behavior is configured in YAML under **`synthetic:`** when using **`proof-run --backend synthetic`**. You do **not** need new Python for many cases.

## Minimal recipe

1. Copy `examples/synthetic_scenario/config.yaml`.
2. Set **`synthetic.scenario`**: e.g. `stationary_clean`, `drifting_attention`, `regime_shift`, etc.
3. Toggle schedules: **`dropouts`**, **`noise_bursts`**, **`ack_delay_ms`**, **`event_omission`**, **`policy_noop`**, **`low_confidence`**, **`irregular_timing`**, **`invalid_windows`**.

Example:

```bash
python -m looplab proof-run --config examples/synthetic_scenario/config.yaml \
  --out-dir scenario_out --duration 4
```

4. Compare **`run_report.md`** timing and diagnostics across scenarios.

## Deeper changes

New scenario **names** or generator logic live in `src/looplab/synthetic/` (generator, config dataclasses). That is advanced; start by mixing existing scenario + schedules.

See `src/looplab/synthetic/config.py`, [Concepts: Streams](../concepts/streams.md), [Deployment: Synthetic](../deployment/local_synthetic_development.md).
