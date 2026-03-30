# Benchmarking protocol

For **BIDS / MNE export** of the same run’s `stream.jsonl` (continuous EEG) and mapped events, see [Export formats](export_formats.md).

LoopLab records **timing in LSL local time** (or the process **synthetic clock** override). This page defines what each measure means, how it is computed, and how to interpret **synthetic**, **PsychoPy**, and **native LSL** runs.

## Three timing layers (do not conflate)

| Layer | What it measures | Typical run type |
|-------|-------------------|------------------|
| **A. Pipeline (synthetic clock)** | Python pipeline only: chunk arrival → policy output. Same clock as hook timestamps. | `proof-run --backend synthetic` |
| **B. Task-level realized** | **Stimulus intended** (logged when control signal is dispatched) → **stimulus realized** (`report_realized` after `win.flip()`). Includes display/OS jitter and task scheduling. | PsychoPy e2e, any run where the task calls `report_realized` |
| **C. Native LSL wall alignment** | Chunk timestamps come from the **LSL inlet**; hooks use `lsl_clock()`. Pipeline latencies are still “in LSL time,” but chunk spacing reflects **device/network**. | `proof-run --backend lsl`, `run --config` with live stream |

**Methods writing:** State explicitly which layer you report. **A** is ideal for “software pipeline latency under controlled conditions.” **B** is appropriate for “stimulus update latency from control decision to pixels.” **C** adds acquisition variability; cite **effective windows/s** from `run_report` when claiming throughput.

---

## What each measure means

### End-to-end (E2E) latency

- **Definition:** Time from **`pull_chunk`** (chunk received for this window) to **`policy_done`** (policy has emitted a control decision for that window).
- **Computation:** For aligned indices `i`, `e2e[i] = policy_done[i] - pull_chunk[i]`. Summary: mean, std, p50, p95 over samples.
- **Represents:** Preprocess + features + model + policy + dispatch bookkeeping for one controller tick—not display latency.

### Per-stage latencies

Aligned by **window index** (`window_ready` length):

| Stage | Delta | Meaning |
|-------|-------|---------|
| acquisition → window | `window_ready - acquisition` | Only meaningful when **acquisition** is the window’s end timestamp in the same clock as hooks; can be **negative or huge** if semantics differ (common on synthetic). **Do not cite for methods** unless you validate alignment. |
| preprocess | `preprocess_done - window_ready` | Preprocessing duration |
| features | `features_done - preprocess_done` | Feature extraction |
| model | `model_done - features_done` | Model forward |
| policy | `policy_done - model_done` | Policy decision |
| task_dispatch | `task_dispatch - policy_done` | Adapter / intended-event path |

Implementation: `latency_report()` in [`src/looplab/benchmark/report.py`](../src/looplab/benchmark/report.py).

### Intended → realized (IT→R)

- **Definition:** **`stimulus_realized[i] - stimulus_intended[i]`** for aligned pairs (same index order in the log).
- **Computation:** Same as E2E pairing: first intended with first realized, etc., per `latency_report`.
- **Represents:** **Task-level** delay: queue + stimulus update + **flip** + optional synthetic **ack_delay** in degraded scenarios. This is the right quantity for “how long until the participant sees the update.”
- **Requires:** Logger + task that calls `report_realized` after flip. **Synthetic proof-run** without a consuming task often has **no** IT→R samples. **PsychoPy e2e** populates them.

---

## How benchmarks are recorded

1. **`benchmark: true`** in config enables **BenchmarkHooks** in the controller loop.
2. Hooks append `(label, lsl_clock())` at: pull_chunk, window_ready, acquisition, preprocess_done, features_done, model_done, policy_done, task_dispatch, stimulus_intended, stimulus_realized.
3. After the run, **`benchmark_summary.json`** is produced from **`benchmark_latency`** events in `events.jsonl` via `latency_report`.

---

## Synthetic vs PsychoPy vs LSL

| Mode | E2E | IT→R | Notes |
|------|-----|------|-------|
| **Synthetic proof-run** | Yes | Usually **no** (no task flip) | Controlled; best for regression and “pipeline only.” |
| **Synthetic + degraded scenario** | Similar order of magnitude | May appear if wrapper simulates delay | `ack_delay_ms` etc. inflate IT→R in scenario configs that omit realized events—check event counts. |
| **PsychoPy e2e** | Yes | **Yes** | Full bridge; cite IT→R for display path. |
| **Live LSL** | Yes | If task reports realized | E2E includes real chunk timing; compare to synthetic for acquisition effects. |

---

## Reference bundles and healthy ranges

Versioned **summary statistics** (no raw timestamp arrays) live under **`examples/benchmark_reference_runs/`**. Regenerate after major pipeline changes; bump the folder version in the README.

**Expected healthy ranges (synthetic baseline, indicative—not SLOs):**

- **E2E p95:** typically **&lt; 5 ms** on a modern CPU for identity/simple pipeline; allow **&lt; 20 ms** for CI/noisy hosts.
- **E2E mean:** often **sub-ms to a few ms** depending on tick rate and chunk processing.
- **Per-stage p95:** each stage usually **&lt; 1 ms** for built-in simple components; much higher if you add heavy models.

If E2E explodes while stages stay small, suspect **threading**, **GIL contention**, or **clock** issues. If IT→R is large on PsychoPy, suspect **missed flips**, **heavy draw**, or **main-thread blocking**.

See **[examples/benchmark_reference_runs/README.md](../examples/benchmark_reference_runs/README.md)** for the comparison suite (baseline vs degraded vs PsychoPy instructions).

---

## Interpretation checklist (for collaborators)

1. Open **`benchmark_summary.json`** or **`run_report.md`** → timing section.
2. Confirm **`has_e2e_data`** / event counts for IT→R.
3. Note **backend** (synthetic vs LSL) and **paradigm** (e.g. psychopy_e2e).
4. For methods: report **mean ± std or p95**, sample count **N**, and **machine/OS** if citing pipeline latency.
5. Do not mix **synthetic E2E** numbers with **lab IT→R** in the same sentence without labeling.

---

## Related

- [Concepts: Reports](concepts/reports.md), [Replay](concepts/replay.md)
- [Quickstart](quickstart.md) — proof-run + report
- [Deployment: LSL](deployment/lsl_caveats.md)
