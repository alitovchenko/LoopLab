"""Config-driven runner: LSL inlets, buffer, pipeline, loop, adapter, logger, optional recorder."""

from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path
from typing import Any

from looplab.buffer.ring_buffer import RingBuffer
from looplab.config.schema import RunConfig, load_config
from looplab.controller.loop import ControllerLoop
from looplab.controller.policy import create_policy, get_policy_registry
from looplab.exceptions import UnknownComponentError
from looplab.features.base import create_feature_extractor, get_feature_extractor_registry
from looplab.logging.event_logger import EventLogger
from looplab.logging.writers import JSONLWriter
from looplab.model.base import create_model, get_model_registry
from looplab.preprocess.pipeline import PreprocessPipeline, noop_preprocess
from looplab.task.psychopy_adapter import PsychoPyTaskAdapter
from looplab.replay.stream_recorder import StreamRecorder
from looplab.benchmark.hooks import BenchmarkHooks


def _ensure_plugin_registries_loaded() -> None:
    """Import modules that register built-in plugins so registries are populated."""
    import looplab.model.example_models  # noqa: F401
    import looplab.features.simple  # noqa: F401
    import looplab.controller.policy  # noqa: F401


def validate_plugin_names(config: RunConfig) -> None:
    """Check that config feature_extractor, model, and policy names are registered. Raise UnknownComponentError on first invalid name."""
    _ensure_plugin_registries_loaded()
    fe = get_feature_extractor_registry()
    if config.feature_extractor not in fe:
        raise UnknownComponentError("feature_extractor", config.feature_extractor, list(fe))
    mo = get_model_registry()
    if config.model not in mo:
        raise UnknownComponentError("model", config.model, list(mo))
    po = get_policy_registry()
    if config.policy not in po:
        raise UnknownComponentError("policy", config.policy, list(po))


def _unpack_reg(entry: tuple[Any, ...]) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    if len(entry) == 2:
        return entry[0], entry[1], {}
    return entry[0], entry[1], entry[2]


def _class_qualname(obj: Any) -> str:
    if isinstance(obj, type):
        return f"{obj.__module__}.{obj.__qualname__}"
    mod = getattr(obj, "__module__", "")
    name = getattr(obj, "__qualname__", getattr(obj, "__name__", repr(obj)))
    return f"{mod}.{name}" if mod else name


def build_components_manifest(config: RunConfig) -> dict[str, Any]:
    """Snapshot of resolved pipeline components for run artifacts."""
    try:
        from importlib.metadata import version

        looplab_ver = version("looplab")
    except Exception:
        looplab_ver = "unknown"
    _ensure_plugin_registries_loaded()
    fe_reg = get_feature_extractor_registry()
    mo_reg = get_model_registry()
    po_reg = get_policy_registry()

    def describe(
        reg: dict[str, tuple],
        name: str,
        user_cfg: dict[str, Any],
    ) -> dict[str, Any]:
        if name not in reg:
            return {"name": name, "registered": False}
        cls, defaults, meta = _unpack_reg(reg[name])
        return {
            "name": name,
            "registered": True,
            "class": _class_qualname(cls),
            "default_config": dict(defaults),
            "effective_config": {**defaults, **user_cfg},
            "component_version": meta.get("version"),
        }

    return {
        "looplab_version": looplab_ver,
        "feature_extractor": describe(fe_reg, config.feature_extractor, config.feature_extractor_config),
        "model": describe(mo_reg, config.model, config.model_config),
        "policy": describe(po_reg, config.policy, config.policy_config),
    }


def load_plugin_modules(paths: list[str | Path]) -> None:
    """Import plugin files so they register components (same pattern as demos)."""
    for p in paths:
        path = Path(p)
        if not path.is_file():
            raise FileNotFoundError(f"Plugin file not found: {path}")
        mod_name = f"_looplab_validate_plugin_{hash(path) % 10_000_000}"
        spec = importlib.util.spec_from_file_location(mod_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load plugin: {path}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)


def validate_config_file(
    config_path: str | Path,
    plugin_paths: list[str | Path] | None = None,
    *,
    strict: bool = False,
) -> dict[str, Any]:
    """
    Validate config: registered names, preprocess/task_adapter warnings, dry-run instantiate.
    Returns dict with ok, errors, warnings. Raises nothing; exit code from caller.
    """
    plugin_paths = plugin_paths or []
    errors: list[str] = []
    warnings: list[str] = []

    for p in plugin_paths:
        try:
            load_plugin_modules([p])
        except Exception as e:
            errors.append(f"plugin {p}: {e}")

    if errors:
        return {"ok": False, "errors": errors, "warnings": warnings}

    config = load_config(config_path)

    try:
        validate_plugin_names(config)
    except UnknownComponentError as e:
        errors.append(str(e))
        return {"ok": False, "errors": errors, "warnings": warnings}

    pp = (config.preprocess or "").lower()
    if pp != "none" and "detrend" not in pp and "zscore" not in pp:
        msg = f"preprocess {config.preprocess!r} has no recognized steps (expected 'none' or tokens: detrend, zscore)"
        if strict:
            errors.append(msg)
        else:
            warnings.append(msg)

    if config.task_adapter != "psychopy":
        warnings.append(
            f"task_adapter {config.task_adapter!r} is not a known built-in (only 'psychopy' is standard)."
        )

    try:
        create_feature_extractor(config.feature_extractor, config.feature_extractor_config)
    except (TypeError, ValueError) as e:
        errors.append(f"feature_extractor {config.feature_extractor!r} instantiation failed: {e}")
    try:
        create_model(config.model, config.model_config)
    except (TypeError, ValueError) as e:
        errors.append(f"model {config.model!r} instantiation failed: {e}")
    try:
        create_policy(config.policy, config.policy_config)
    except (TypeError, ValueError) as e:
        errors.append(f"policy {config.policy!r} instantiation failed: {e}")

    if errors:
        return {"ok": False, "errors": errors, "warnings": warnings}
    return {"ok": True, "errors": [], "warnings": warnings}


def create_runner(config: RunConfig) -> dict[str, Any]:
    """Build buffer, preprocess, features, model, policy, adapter, logger from config."""
    validate_plugin_names(config)
    cfg = config
    buffer = RingBuffer(cfg.buffer.max_samples, cfg.buffer.n_channels)

    if cfg.preprocess == "none":
        preprocess = noop_preprocess
    else:
        pipe = PreprocessPipeline()
        if "detrend" in cfg.preprocess.lower():
            from looplab.preprocess.pipeline import detrend_window
            pipe.add_step(detrend_window)
        if "zscore" in cfg.preprocess.lower():
            from looplab.preprocess.pipeline import zscore_window
            pipe.add_step(zscore_window)
        preprocess = pipe

    try:
        feature_extractor = create_feature_extractor(cfg.feature_extractor, cfg.feature_extractor_config)
        model = create_model(cfg.model, cfg.model_config)
        policy = create_policy(cfg.policy, cfg.policy_config)
    except (TypeError, ValueError) as e:
        raise RuntimeError(
            f"Pipeline component instantiation failed: {e}. "
            "Check model_config / policy_config / feature_extractor_config against the component's __init__. "
            "Run: python -m looplab validate-config --config <your-config> [--plugin path/to/plugins.py]"
        ) from e
    adapter = PsychoPyTaskAdapter()

    writer = JSONLWriter(Path(cfg.log_path))
    logger = EventLogger(writer)
    adapter.set_logger(logger)

    loop = ControllerLoop(
        buffer=buffer,
        preprocess=preprocess,
        feature_extractor=feature_extractor,
        model=model,
        policy=policy,
        adapter=adapter,
        logger=logger,
        min_samples=10,
    )

    hooks = BenchmarkHooks() if cfg.benchmark else None
    if hooks and cfg.benchmark:
        hooks.set_logger(logger)
        loop.set_hooks(hooks)

    recorder = StreamRecorder(cfg.record_stream_path) if cfg.record_stream_path else None

    return {
        "config": cfg,
        "buffer": buffer,
        "preprocess": preprocess,
        "feature_extractor": feature_extractor,
        "model": model,
        "policy": policy,
        "adapter": adapter,
        "logger": logger,
        "loop": loop,
        "writer": writer,
        "hooks": hooks,
        "recorder": recorder,
    }
