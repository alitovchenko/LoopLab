# LSL compatibility matrix

LoopLab interacts with **native LSL** (via `pylsl` / liblsl). The same mapping appears in README, quickstart, caveats, artifact docs, and `check-lsl` output.

## Canonical mapping (policy ↔ artifacts)

| Policy (prose) | Meaning | `lsl_support_tier` value |
|----------------|---------|--------------------------|
| **Supported** | Synthetic / default **core path** (`proof-run --backend synthetic`, main CI). | **`synthetic_supported`** |
| **Best effort** | **Native LSL runtime path** (discovery, inlets, timing vary by machine). | **`native_lsl_functional`** (native run completed) or **`native_lsl_unavailable`** (e.g. discovery failed) |
| **Monitoring-only** | **Native LSL CI lane** (`test-lsl`, `RUN_LSL_TESTS=1`); not a release gate. | *(no fourth value—runs still record one of the three tiers above)* |

Field name **`lsl_support_tier`** and the three values are **stable** (see [Artifact schemas](../artifact_schemas.md)). Values describe **this run** (or this probe), not a rewrite of global policy.

**`native_lsl_functional`:** native stack present, discovery succeeded for that run, session completed on LSL—not certification for all hardware or protocols.

**`check-lsl` exit 0:** native LSL **discovery and basic runtime probing** succeeded (test outlet resolved). Evidence of a working stack **here**, not proof that every live experiment path will work.

---

## Examples

### Human `check-lsl` (stderr)

Illustrative success case:

```text
$ python -m looplab check-lsl
LoopLab LSL — see docs/deployment/lsl_compatibility_matrix.md

  Supported        = synthetic/default core path     → artifact lsl_support_tier: synthetic_supported
  Best effort      = native LSL runtime path         → native_lsl_functional | native_lsl_unavailable
  Monitoring-only  = native LSL CI lane (test-lsl)  → not a release gate (no extra artifact value)

  check-lsl exit 0 = native LSL discovery + basic runtime probe OK here (not full live certification).

Result: exit 0 — native LSL discovery and basic runtime probing succeeded (test outlet resolved). lsl_support_tier (probe): native_lsl_functional. Not a guarantee for every live experiment path.
```

### `check-lsl --json` (abbreviated)

```json
{
  "environment": {
    "os": "Darwin",
    "os_release": "24.6.0",
    "python_version": "3.11.0",
    "architecture": "arm64",
    "pylsl_version": "1.16.2",
    "liblsl_library_version": 117,
    "liblsl_build_info": "git:.../branch:refs/tags/v1.17.4/..."
  },
  "probe": {
    "pylsl_available": true,
    "discovery_ok": true,
    "lsl_support_tier": "native_lsl_functional",
    "error": null
  },
  "status": "ok",
  "message": "Test outlet resolved: native LSL discovery and basic runtime probing succeeded...",
  "exit_code": 0,
  "exit_code_meaning": "Native LSL discovery and basic runtime probing succeeded...",
  "doc": "docs/deployment/lsl_compatibility_matrix.md"
}
```

### Run report line (`run_report.md`)

After synthetic proof-run, **Methods** includes:

```markdown
- **LSL support tier (this run):** `synthetic_supported` — see LSL matrix for policy vs artifact labels
```

(`native_lsl_functional` / `native_lsl_unavailable` appear for LSL or failed-LSL outcomes.)

---

## `--json` field reference

| Field | Content |
|-------|---------|
| `environment` | `os`, `os_release`, `python_version`, `architecture`, `pylsl_version`, `liblsl_library_version`, `liblsl_build_info` (when detectable) |
| `probe` | `pylsl_available`, `discovery_ok`, **`lsl_support_tier`**, `error` |
| `status` | `ok` \| `pylsl_missing` \| `discovery_failed` |
| `message` | Short summary |
| `exit_code` | 0 / 1 / 2 |
| `exit_code_meaning` | Same nuance as matrix (probe ≠ full live certification) |
| `doc` | Path to this page |

## Release language

- **LoopLab-validated** → Supported tier (synthetic proof-run, main CI).
- **Native LSL timing** → Best effort; cite your lab’s **`benchmark_summary`** / **`run_report`**.
- Red optional **test-lsl** job ≠ LoopLab regression.

## Related docs

- [LSL caveats](lsl_caveats.md)
- [Concepts: Streams](../concepts/streams.md)
- [Artifact schemas](../artifact_schemas.md) (`lsl_support_tier`)
