# Synthetic scenario example

Run proof-run with a **configurable synthetic scenario**: signal generator type plus optional degradation schedules (dropouts, noise bursts, ack delay, event omission, etc.) to stress the platform and support development under realistic conditions.

## Usage

From repo root (with the package installed):

```bash
python -m looplab proof-run --config examples/synthetic_scenario/config.yaml --out-dir scenario_out --duration 4
```

Or from this directory (with `PYTHONPATH=src` or `pip install -e .`):

```bash
python -m looplab proof-run --config config.yaml --out-dir scenario_out --duration 4
```

## Config

The `synthetic` section in `config.yaml` specifies:

- **scenario:** `stationary_clean` | `drifting_attention` | `drifting_latent_state` | `regime_shift`
- **seed:** for reproducible chunk and degradation generation
- **dropouts:** missing chunks (probability per chunk)
- **noise_bursts:** add Gaussian noise every N seconds
- **ack_delay_ms:** delay (mean, jitter in ms) for simulated task acknowledgments
- **event_omission:** probability of omitting realized events
- **policy_noop**, **low_confidence**, **irregular_timing**, **invalid_windows:** optional (see config comments)

## What to expect

- With dropouts, the stream has fewer chunks; replay may show fewer replayed than logged controls.
- With event_omission, there are fewer `stimulus_realized` than `stimulus_intended` events; benchmark intended→realized uses the shorter paired list.
- All canonical artifacts are still written; `run_package_summary.json` and `RUN_SUMMARY.md` reflect the run. Use `looplab report --run-dir scenario_out --human` for a one-page summary.
