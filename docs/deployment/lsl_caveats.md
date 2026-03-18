# LSL caveats and support expectations

**Same mapping as README/quickstart:** **Supported** = synthetic core → **`synthetic_supported`**. **Best effort** = native LSL → **`native_lsl_functional`** \| **`native_lsl_unavailable`**. **Monitoring-only** = **`test-lsl`** lane. Field **`lsl_support_tier`** is stable. Examples: **[LSL compatibility matrix](lsl_compatibility_matrix.md)**. Probe: `python -m looplab check-lsl` / `--json`.

## What LSL gives you

- Discovery of streams by name/type/source_id.
- Chunks of multichannel data with timestamps in **LSL local clock**—aligned with `lsl_clock()` in the same process.

## Caveats

- **Discovery can fail** in restricted environments (containers, no Bonjour/mDNS, firewall). **`proof-run --backend lsl`** may exit non-zero; **`--backend synthetic`** remains the reliable default for CI and onboarding.
- **Stream identity:** Name collisions or multiple sources require careful `source_id` / type filters.
- **Chunk timing:** Network jitter and device rates affect effective windows per second; cite **actual** `benchmark_summary` / `run_report` timing, not only nominal tick rate.

## Support expectations

- LoopLab assumes **pylsl** and a working LSL runtime for live acquisition. Environment-specific LSL issues are outside core LoopLab guarantees; synthetic backend exercises the same **pipeline and replay** logic.

## Suggested practice

1. Develop with **synthetic** proof-run and run reports.
2. Validate on **live LSL** in the lab with a short run and compare **`run_report.md`** (window rate, health, replay if recording stream).

See [Concepts: Streams](../concepts/streams.md), main README testing section for optional `RUN_LSL_TESTS`.
