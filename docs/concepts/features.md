# Feature extractors

**Role:** Turn a **preprocessed** slice of the ring buffer into a **feature vector** (or structured features) for the model.

- Registered by name (`feature_extractor` in config).
- Receive window context: data array, `t_start` / `t_end` in LSL time, optional context dict.
- Examples: `"simple"` rolling statistics; custom plugins via `register_feature_extractor`.

**Config:** `feature_extractor` + optional `feature_extractor_config` merged with registry defaults.

**Methods tip:** Cite extractor name and effective config from `components_manifest.json` or `run_report.json` → `methods` / `pipeline`.

See: [Add a feature extractor](../extensions/add_feature_extractor.md), `python -m looplab list-components --features`.
