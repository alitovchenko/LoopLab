"""Render plugin stub files from bundled templates (`looplab new`)."""

from __future__ import annotations

from importlib import resources


def render_plugin_stub(kind: str, name: str) -> str:
    """Return Python source for a registered plugin stub (feature | model | policy)."""
    class_name = "".join(p.capitalize() for p in name.replace("-", "_").split("_"))
    fn = {"feature": "feature_extractor", "model": "model", "policy": "policy"}[kind]
    raw = resources.files("looplab.plugin_templates").joinpath(f"{fn}.py.example").read_text(encoding="utf-8")
    if kind == "feature":
        return raw.replace("MyFeatureExtractor", class_name).replace('"my_feature"', repr(name))
    if kind == "model":
        return raw.replace("MyModel", class_name).replace('"my_model"', repr(name))
    return raw.replace("MyPolicy", class_name).replace('"my_policy"', repr(name))


def minimal_config_yaml_for_plugin(name: str, kind: str) -> str:
    """Minimal RunConfig YAML referencing the new plugin in the right slot."""
    fe, mo, po = "simple", "identity", "identity"
    if kind == "feature":
        fe = name
    elif kind == "model":
        mo = name
    else:
        po = name

    return f"""# Minimal config for custom plugin {name!r} ({kind}).
# Validate: python -m looplab validate-config --config {name}_config.yaml --plugin {name}.py
# Before run/replay, load the plugin (e.g. --plugin {name}.py or import the module).

lsl:
  name: "FakeEEG"
  type: "EEG"
  chunk_size: 8
  max_buffered: 360.0
  timeout: 5.0

buffer:
  max_samples: 500
  n_channels: 2

preprocess: "none"
feature_extractor: "{fe}"
feature_extractor_config: {{}}
model: "{mo}"
model_config: {{}}
policy: "{po}"
policy_config:
  validity_seconds: 1.0

task_adapter: "psychopy"
log_path: "{name}_events.jsonl"
record_stream_path: "{name}_stream.jsonl"
benchmark: true
"""


def plugin_readme_md(name: str, kind: str) -> str:
    return f"""# Plugin: {name} ({kind})

1. **Validate** (after implementing the stub):

   ```bash
   python -m looplab validate-config --config {name}_config.yaml --plugin {name}.py
   ```

2. **Discover** registered names and defaults:

   ```bash
   python -m looplab list-components
   ```

3. **Load before run**: pass `--plugin {name}.py` to commands that accept it, or `import {name}` in your driver script so registration runs before `create_runner`.

See the LoopLab repository **docs/extensions/** guides (Add a model / feature / policy) for full steps.
"""
