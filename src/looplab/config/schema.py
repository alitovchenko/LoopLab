"""Configuration schema and loading (YAML/JSON)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LSLStreamConfig:
    name: str | None = None
    type: str | None = None
    source_id: str | None = None
    chunk_size: int = 0
    max_buffered: float = 360.0
    timeout: float = 5.0


@dataclass
class BufferConfig:
    max_samples: int = 10000
    n_channels: int = 32


@dataclass
class RunConfig:
    """Single config for run: LSL, buffer, preprocess, feature, model, policy, task, log, flags."""

    lsl: LSLStreamConfig = field(default_factory=LSLStreamConfig)
    buffer: BufferConfig = field(default_factory=BufferConfig)
    preprocess: str = "none"
    feature_extractor: str = "simple"
    model: str = "identity"
    model_config: dict[str, Any] = field(default_factory=dict)
    policy: str = "identity"
    policy_config: dict[str, Any] = field(default_factory=dict)
    task_adapter: str = "psychopy"
    log_path: str = "looplab_events.jsonl"
    record_stream_path: str | None = None
    benchmark: bool = False


def config_to_dict(config: RunConfig) -> dict[str, Any]:
    """Convert RunConfig (and nested LSLStreamConfig, BufferConfig) to a JSON-serializable dict."""
    return asdict(config)


def load_config(path: str | Path) -> RunConfig:
    """Load YAML or JSON config into RunConfig."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    raw = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
            data = yaml.safe_load(raw)
        except ImportError:
            raise ImportError("PyYAML required for YAML config: pip install pyyaml")
    else:
        import json
        data = json.loads(raw)
    return _dict_to_config(data)


def _dict_to_config(d: dict[str, Any]) -> RunConfig:
    lsl = d.get("lsl", {})
    buf = d.get("buffer", {})
    return RunConfig(
        lsl=LSLStreamConfig(
            name=lsl.get("name"),
            type=lsl.get("type"),
            source_id=lsl.get("source_id"),
            chunk_size=lsl.get("chunk_size", 0),
            max_buffered=lsl.get("max_buffered", 360.0),
            timeout=lsl.get("timeout", 5.0),
        ),
        buffer=BufferConfig(
            max_samples=buf.get("max_samples", 10000),
            n_channels=buf.get("n_channels", 32),
        ),
        preprocess=d.get("preprocess", "none"),
        feature_extractor=d.get("feature_extractor", "simple"),
        model=d.get("model", "identity"),
        model_config=d.get("model_config", {}),
        policy=d.get("policy", "identity"),
        policy_config=d.get("policy_config", {}),
        task_adapter=d.get("task_adapter", "psychopy"),
        log_path=d.get("log_path", "looplab_events.jsonl"),
        record_stream_path=d.get("record_stream_path"),
        benchmark=d.get("benchmark", False),
    )
