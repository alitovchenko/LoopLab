# Add a feature extractor

1. Implement **`FeatureExtractor`** (`extract(data, t_start, t_end, context)` returning a feature array or vector).
2. **`register_feature_extractor("my_fe", MyFE, default_config_dict)`**.
3. Config:

   ```yaml
   feature_extractor: "my_fe"
   feature_extractor_config: {}
   ```

4. Validate with `--plugin` if registrations live in a standalone module.

See `src/looplab/features/simple.py`, [Concepts: Features](../concepts/features.md).
