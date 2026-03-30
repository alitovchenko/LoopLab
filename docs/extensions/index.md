# Extension guides

LoopLab extensions are **registered Python callables** referenced by name from YAML/JSON config.

| Guide | You add |
|-------|---------|
| [**Custom component in five minutes**](custom_component_walkthrough.md) | `new` → validate → import/`--plugin` → run |
| [Add a model](add_model.md) | `Model` implementation + `register_model` |
| [Add a feature extractor](add_feature_extractor.md) | `FeatureExtractor` + `register_feature_extractor` |
| [Add a policy](add_policy.md) | `Policy` + `register_policy` |
| [Add a synthetic scenario](add_synthetic_scenario.md) | `synthetic:` config for proof-run (no new Python for basic cases) |

**Before coding:** `python -m looplab list-components` and `python -m looplab new model|feature|policy <name>` (stubs match `examples/plugin_templates/` and the bundled `looplab.plugin_templates` package).

**After coding:** `python -m looplab validate-config --config yours.yaml --plugin your_plugins.py`.
