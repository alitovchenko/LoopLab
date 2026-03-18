# Run artifact schemas (contracts)

**As of LoopLab 0.3.x.** These JSON files are **public contracts** for tooling, methods text, and downstream analysis—not private implementation details.

**Machine-readable schemas:** [`schemas/`](../schemas/) (JSON Schema draft 2020-12).

---

## Compatibility policy

| Tag | Meaning |
|-----|---------|
| **Stable** | Field will not be removed or renamed in a minor release; new **optional** top-level keys may be added. External tools may depend on stable fields. |
| **Experimental** | May change name, shape, or disappear in a future minor. Use for display or best-effort parsing only. |

**No `schema_version` field yet** in artifacts; versioning is documented here and tied to LoopLab releases. A future release may add `"artifact_schema_version": "1.1"` to selected files.

---

## 1. `session_summary.json`

**Purpose:** High-level run outcome and session metadata; merged with diagnostics before write.

**JSON Schema:** [`schemas/session_summary.schema.json`](../schemas/session_summary.schema.json).

**Source of truth:** [`__main__.py`](../src/looplab/__main__.py) proof-run session dict (~459), then [`merge_diagnostics_into_session_summary`](../src/looplab/benchmark/diagnostics.py).

| Key | Type | Required | Stability | Meaning |
|-----|------|----------|-----------|---------|
| `duration_sec` | number | yes (proof-run) | stable | Wall duration of run |
| `seed` | number | yes (proof-run) | stable | Replay seed |
| `out_dir` | string | yes | stable | Output directory path |
| `artifacts_ok` | boolean | yes | stable | Log/stream present and non-empty |
| `replay_ok` | boolean | yes | stable | Replay passed (or non-strict) |
| `lsl_available` | boolean | yes | stable | Whether LSL backend was used |
| `lsl_support_tier` | string | proof-run | **stable** | One of **`synthetic_supported`** \| **`native_lsl_functional`** \| **`native_lsl_unavailable`** (frozen names). **Supported** policy → `synthetic_supported`; **Best effort** native path → `native_lsl_functional` or `native_lsl_unavailable`. Runtime classification for **this run** only—not a substitute for global policy; see [LSL matrix](deployment/lsl_compatibility_matrix.md). |
| `backend` | string | yes | stable | `synthetic` \| `lsl` (or demo-specific) |
| `timestamp` | string | yes | stable | ISO-8601 UTC |
| `run_health` | string | after diagnostics | stable | `healthy` \| `degraded` \| `unhealthy` |
| `diagnostics_summary` | string | after diagnostics | stable | Short human summary |
| `diagnostic_findings` | array | after diagnostics | stable | `{level, code, message}[]` (subset of findings) |
| `warning_messages` | array of string | after diagnostics | stable | Legacy + diagnostic warnings |
| `paradigm` | string | no | **experimental** | Demo tag, e.g. `psychopy_e2e`, `adaptive_difficulty` |
| `error` | string | no | experimental | e.g. LSL discovery failure |
| `degraded` | boolean | no | experimental | Session-level degraded flag (if set) |

---

## 2. `benchmark_summary.json`

**Purpose:** Latency aggregates from `benchmark_latency` events in `events.jsonl`.

**JSON Schema:** [`schemas/benchmark_summary.schema.json`](../schemas/benchmark_summary.schema.json).

**Source of truth:** [`latency_report`](../src/looplab/benchmark/report.py).

| Key | Type | Stability | Meaning |
|-----|------|-----------|---------|
| `by_label` | object | stable | Map label → array of LSL timestamps (e.g. `pull_chunk`, `policy_done`, `window_ready`, …) |
| `e2e_latency_seconds` | number[] | stable | Per-window chunk→policy deltas |
| `e2e_mean` | number | stable | Mean E2E |
| `e2e_stats` | object | stable | `{mean, std, p50, p95}` |
| `intended_to_realized_seconds` | number[] | stable | Paired IT→R deltas |
| `intended_to_realized_mean` | number | stable | |
| `intended_to_realized_stats` | object | stable | `{mean, std, p50, p95}` |
| `*_latency_seconds` | number[] | stable | preprocess, features, model, policy, task_dispatch |
| `*_latency_stats` | object | stable | Same stats shape |
| `acquisition_to_window_seconds` | number[] | **experimental** | Sensitive to acquisition timestamp semantics |
| `acquisition_to_window_stats` | object | experimental | |

Many keys are **absent** if insufficient benchmark events (e.g. no pull/policy alignment).

---

## 3. `diagnostics.json`

**Purpose:** Run-quality rollup: health, findings, checks, thresholds.

**JSON Schema:** [`schemas/diagnostics.schema.json`](../schemas/diagnostics.schema.json).

**Source of truth:** [`build_run_diagnostics`](../src/looplab/benchmark/diagnostics.py).

| Key | Type | Stability | Meaning |
|-----|------|-----------|---------|
| `health` | string | stable | `healthy` \| `degraded` \| `unhealthy` |
| `findings` | array | stable | `{level, code, message, detail}` — **detail** object is experimental |
| `checks` | array | **experimental** | Named checks; entries and fields may grow |
| `thresholds` | object | experimental | Numeric thresholds used (may change) |
| `degraded_run_adjusted` | boolean | stable | Whether run was flagged degraded for diagnostics |

---

## 4. `replay_result.json`

**Purpose:** Determinism check: logged vs replayed control signals.

**JSON Schema:** [`schemas/replay_result.schema.json`](../schemas/replay_result.schema.json).

**Source of truth:** [`compute_divergence`](../src/looplab/replay/divergence.py); stub in `__main__` when no stream chunks.

| Key | Type | Stability | Meaning |
|-----|------|-----------|---------|
| `match_count` | integer | stable | Agreeing control signals |
| `mismatch_count` | integer | stable | Divergences + length mismatch penalty |
| `total_logged` | integer | stable | |
| `total_replayed` | integer | stable | |
| `matches` | boolean | stable | True iff no mismatches and same lengths |
| `divergences` | array | stable | `{index, logged, replayed}` per mismatch |

---

## 5. `components_manifest.json`

**Purpose:** Resolved pipeline components for reproducibility.

**JSON Schema:** [`schemas/components_manifest.schema.json`](../schemas/components_manifest.schema.json).

**Source of truth:** [`build_components_manifest`](../src/looplab/runner.py).

| Key | Type | Stability | Meaning |
|-----|------|-----------|---------|
| `looplab_version` | string | stable | Package version |
| `feature_extractor` | object | stable | See below |
| `model` | object | stable | |
| `policy` | object | stable | |

**Component object (each of feature_extractor, model, policy):**

| Key | Stability | Meaning |
|-----|-----------|---------|
| `name` | stable | Config name |
| `registered` | stable | Whether name was in registry |
| `class` | stable | Qualname when registered |
| `default_config` | stable | Registry defaults |
| `effective_config` | stable | Merged with user config |
| `component_version` | **experimental** | Optional registry metadata |

If not registered: `{name, registered: false}` only.

---

## 6. `run_report.json`

**Purpose:** Methods-ready aggregate (citable fields, inventory, highlights).

**JSON Schema:** [`schemas/run_report.schema.json`](../schemas/run_report.schema.json).

**Source of truth:** [`build_run_report`](../src/looplab/benchmark/run_report.py).

| Key | Type | Stability | Meaning |
|-----|------|-----------|---------|
| `run_dir` | string | stable | Absolute path |
| `methods` | object | stable | See below |
| `pipeline` | object | stable | From manifest or config snapshot |
| `backend` | string | stable | |
| `config_hash` | string | stable | SHA-256 of config_snapshot |
| `experiment_summary` | object | stable | Trial/block counts, flags |
| `adaptation` | object | stable | Counts, adaptation_target, first_control_action |
| `replay_agreement` | object \| null | stable | Subset of replay_result or null |
| `benchmark_highlights` | object | stable | Means/stats/window_count |
| `diagnostics_summary` | object | stable | health, findings_by_level, findings |
| `artifact_inventory` | array | stable | `{name, present, bytes}` |
| `event_counts_selected` | object | stable | Selected event type counts |
| `task_level_summary` | object | **experimental** | PsychoPy bridge / task-level stats |

**`methods` (stable keys):**

`window_size_samples`, `buffer_max_samples`, `n_channels`, `feature_extractor_name`, `model_name`, `policy_name`, `preprocess`, `adaptation_target`, `backend`, `duration_sec`, `effective_windows_per_sec`, `timing_summary`, `warning_status`, `looplab_version`.

**`timing_summary`:** optional nested `e2e_seconds`, `intended_to_realized_seconds` with mean/std/p50/p95.

---

## Changelog (documentation)

- **0.3.x:** `lsl_support_tier` and values `synthetic_supported`, `native_lsl_functional`, `native_lsl_unavailable` are **stable**; `check-lsl --json` uses the same `lsl_support_tier` in `probe`.
- **0.3.x:** Initial published contracts; `task_level_summary` on run_report marked experimental.
