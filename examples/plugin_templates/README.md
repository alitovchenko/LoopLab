# Plugin templates

Minimal stub files for custom LoopLab plugins. Copy the file for the component type you need, rename the class and the registration name, then implement the required methods.

1. **Copy** the `.example` file (e.g. `feature_extractor.py.example`) into your project and rename (e.g. `my_extractor.py`).
2. **Implement** the abstract methods: `extract` (feature extractor), `run` (model), or `__call__` (policy).
3. **Register** by calling `register_feature_extractor`, `register_model`, or `register_policy` at module bottom with your plugin name.
4. **Import** your module before building the runner (e.g. in your main script or via entry points) so the registration runs.
5. **Reference** the name in your config (e.g. `feature_extractor: my_feature` in YAML) or pass it to `create_*`.
6. Run `looplab list` to confirm your plugin appears.

Alternatively, use the CLI to generate a stub from the same templates bundled in the package: `python -m looplab new feature my_extractor --out-dir .` (same for `model` or `policy`). Optional: `--with-config` / `--with-readme`.
