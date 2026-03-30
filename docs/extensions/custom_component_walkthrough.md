# Custom component in five minutes

This is the shortest path from zero to a validated, registered plugin that behaves like built-ins.

## 1. Generate a stub

From your project directory (or anywhere you keep code):

```bash
python -m looplab new model my_alpha --out-dir . --with-config --with-readme
```

Use `feature` or `policy` instead of `model` if you need those slots. Flags:

- **`--with-config`** — writes `my_alpha_config.yaml` with a minimal `RunConfig` that references your plugin.
- **`--with-readme`** — writes `README_my_alpha.md` with copy-paste commands.

The stub matches the bundled templates under `examples/plugin_templates/` (same content as the `looplab.plugin_templates` package data used by `new`).

## 2. Implement the class

Edit `my_alpha.py`: replace the placeholder body of `run()`, `extract()`, or `__call__()` with your logic. Keep the `register_*("my_alpha", ...)` line aligned with the name you use in YAML.

## 3. Validate

```bash
python -m looplab validate-config --config my_alpha_config.yaml --plugin my_alpha.py
```

You should see **Plugin load order**, **Resolved components** (name → class), and **Config OK.** Fix any **Error** lines before continuing.

Discover built-ins and defaults anytime:

```bash
python -m looplab list-components
```

## 4. Load before running

Registration runs at **import** time. Either:

- pass **`--plugin my_alpha.py`** to commands that support it (`validate-config`, and patterns that mirror [examples/closed_loop_demo/](https://github.com/alitovchenko/LoopLab/tree/main/examples/closed_loop_demo)), or  
- `import my_alpha` at the top of your driver script **before** `create_runner`.

## 5. Run or proof-run

Point a config at `model: "my_alpha"` (or the appropriate key) after loading the plugin module. For a full adaptive pipeline example with custom model + policy, see **`examples/model_feedback_demo/`** in the repo.

---

**Related:** [Extension guides index](index.md) · [Add a model](add_model.md) · [Add a feature extractor](add_feature_extractor.md) · [Add a policy](add_policy.md)
