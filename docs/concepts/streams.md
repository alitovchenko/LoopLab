# Streams

**Role:** Deliver **chunks** of multichannel samples into LoopLab on a timeline aligned with **LSL local clock** (or a synthetic substitute).

- **LSL path:** An inlet resolves a named stream (`lsl.name`, `lsl.type`, optional `source_id`). Each pull returns a chunk of shape `(n_samples, n_channels)` with timestamps.
- **Synthetic path (`proof-run --backend synthetic`):** An in-process generator produces chunks with the same interface; no hardware or LSL discovery. Optional **`synthetic:`** in config shapes signal type and degradations (dropouts, noise, delayed acknowledgments, etc.).

**Config knobs (typical):**

- `lsl.chunk_size` — samples per window the buffer sees per tick (often equals “window size” in methods text).
- `buffer.max_samples`, `buffer.n_channels` — ring buffer capacity and expected channel count.

**Why it matters:** All later stages (preprocess → features → model → policy) run **per chunk/window**. Chunk timing drives effective loop rate and latency.

See also: [Deployment: LSL](../deployment/lsl_caveats.md), [Synthetic scenario extension](../extensions/add_synthetic_scenario.md).
