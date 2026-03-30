# Quickstart

Goal: install LoopLab, confirm your config is valid, run a **synthetic** proof-run (no EEG hardware), and read a **methods-ready run report**.

## 1. Install

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -e ".[dev,yaml]"   # dev: pytest + PyYAML; yaml: config files
```

Minimum without YAML tests: `pip install -e .` plus `pip install pyyaml` if you use `.yaml` configs.

**One-liner (install → proof-run → human report, no hardware):** default proof-run uses the **synthetic** backend.

```bash
python -m venv .venv && source .venv/bin/activate && pip install --upgrade pip && pip install -e ".[yaml]" && python -m looplab proof-run && python -m looplab report --run-dir proof_run_output --human
```

Or combine proof + report: `python -m looplab proof-run --with-report`. Use **`-v`** / **`-vv`** on `run`, `replay`, or `proof-run` for stderr diagnostics (JSONL remains the analysis source).

Optional: `pip install -e ".[psychopy]"` for PsychoPy demos.

## 2. Validate config

Use a small config that matches the closed-loop demo (works for proof-run with synthetic backend):

```bash
python -m looplab validate-config --config examples/closed_loop_demo/config.yaml
```

- Exit **0**: `feature_extractor`, `model`, and `policy` names are registered and `*_config` can instantiate each component.
- Custom plugins: load the module that registers them first:

```bash
python -m looplab validate-config --config path/to/config.yaml --plugin path/to/plugins.py
```

Discover names and defaults:

```bash
python -m looplab list-components
```

## 3. Run synthetic proof-run

**LSL:** **Supported** → `synthetic_supported`; **Best effort** (native) → `native_lsl_functional` \| `native_lsl_unavailable`; **Monitoring-only** → CI `test-lsl`. Probe: `python -m looplab check-lsl` (see [matrix](deployment/lsl_compatibility_matrix.md) for sample human/JSON output and run-report line).

No LSL stream required for the steps below:

```bash
python -m looplab proof-run --backend synthetic --duration 4 --out-dir proof_out
```

You should see replay match counts and a final success line. Artifacts land under `proof_out/` (or your `--out-dir`).

## 4. Read run report

**Human-readable one-pager:**

```bash
python -m looplab report --run-dir proof_out --human
```

**JSON** (default without `--human`):

```bash
python -m looplab report --run-dir proof_out --json
```

**Refresh written files** (run package summary + run report on disk):

```bash
python -m looplab report --run-dir proof_out --write
```

Then open **`proof_out/run_report.md`**: citable window size, model/policy/feature names, adaptation target, timing stats, replay agreement, diagnostics, artifact checklist. See [Concepts: Reports](concepts/reports.md) for field meanings.

---

**Next:** [Concepts overview](concepts/index.md) or a [tutorial](tutorials/index.md).
