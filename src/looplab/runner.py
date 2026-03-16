"""Config-driven runner: LSL inlets, buffer, pipeline, loop, adapter, logger, optional recorder."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from looplab.buffer.ring_buffer import RingBuffer
from looplab.config.schema import RunConfig, load_config
from looplab.controller.loop import ControllerLoop
from looplab.controller.policy import IdentityPolicy
from looplab.features.simple import SimpleFeatureExtractor
from looplab.logging.event_logger import EventLogger
from looplab.logging.writers import JSONLWriter
from looplab.model.base import create_model
from looplab.preprocess.pipeline import PreprocessPipeline, noop_preprocess
from looplab.streams.clock import lsl_clock
from looplab.streams.lsl_client import LSLInletClient
from looplab.task.psychopy_adapter import PsychoPyTaskAdapter
from looplab.replay.stream_recorder import StreamRecorder
from looplab.benchmark.hooks import BenchmarkHooks


def create_runner(config: RunConfig) -> dict[str, Any]:
    """Build buffer, preprocess, features, model, policy, adapter, logger from config."""
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

    feature_extractor = SimpleFeatureExtractor()
    model = create_model(cfg.model, cfg.model_config)
    policy = IdentityPolicy(**cfg.policy_config) if cfg.policy == "identity" else IdentityPolicy()
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
