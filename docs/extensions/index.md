# Extension guides

LoopLab extensions are **registered Python callables** referenced by name from YAML/JSON config.

| Guide | You add |
|-------|---------|
| [Add a model](add_model.md) | `Model` implementation + `register_model` |
| [Add a feature extractor](add_feature_extractor.md) | `FeatureExtractor` + `register_feature_extractor` |
| [Add a policy](add_policy.md) | `Policy` + `register_policy` |
| [Add a synthetic scenario](add_synthetic_scenario.md) | `synthetic:` config for proof-run (no new Python for basic cases) |

**Before coding:** `python -m looplab list-components` and `looplab new model|feature|policy <name>` for stubs under `examples/plugin_templates/`.

**After coding:** `python -m looplab validate-config --config yours.yaml --plugin your_plugins.py`.
