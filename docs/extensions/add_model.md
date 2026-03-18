# Add a model

1. Implement the **`Model`** protocol (`forward` / `__call__` as defined in `looplab.model.base`).
2. **`register_model("my_model", MyModelClass, {"default": "config"})`** at import time.
3. Config:

   ```yaml
   model: "my_model"
   model_config:
     your_param: value
   ```

4. **`python -m looplab validate-config -c config.yaml --plugin path/to/plugins.py`**

See `src/looplab/model/example_models.py`, `examples/plugin_templates/`, and [Concepts: Models](../concepts/models.md).
