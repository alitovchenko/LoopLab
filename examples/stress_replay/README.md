# Stress replay (Workstream F)

Run replay with optional **stream stressors** (missing chunks, noise) to see how the pipeline and divergence report behave under fault conditions.

## Usage

From repo root (with `pip install -e .` or `PYTHONPATH=src`):

```bash
python examples/stress_replay/run_stress_replay.py --log proof_run_output/events.jsonl --stream proof_run_output/stream.jsonl
```

With stressors:

```bash
python examples/stress_replay/run_stress_replay.py --log proof_run_output/events.jsonl --stream proof_run_output/stream.jsonl --drop-ratio 0.2 --seed 42
python examples/stress_replay/run_stress_replay.py --log X --stream Y --noise-scale 0.5 --noise-t-start 1000 --noise-t-end 1002
```

- `--drop-ratio`: fraction of chunks to drop (0–1); replay will see fewer ticks and control sequence length will differ from log.
- `--noise-scale`, `--noise-t-start`, `--noise-t-end`: add Gaussian noise to chunks in the given time range.
- Output: divergence report (match count, mismatches) and a stressed stream file `*_stressed.jsonl`.

## Library usage

Use `looplab.replay.stressors` directly: `drop_chunks`, `add_noise`, `add_drift`, `add_abrupt_change`, `delay_realized_events`, `drop_realized_events`. Apply to chunk lists or event lists, then run replay or benchmark as usual.
