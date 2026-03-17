"""Config-driven runner: LSL inlets, buffer, pipeline, loop, adapter, logger, optional recorder."""

from __future__ import annotations

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

    feature_extractor = create_feature_extractor(cfg.feature_extractor, cfg.feature_extractor_config)
    model = create_model(cfg.model, cfg.model_config)
    policy = create_policy(cfg.policy, cfg.policy_config)
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
