"""CLI: python -m looplab run|replay|benchmark."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(prog="looplab", description="LoopLab closed-loop experiment SDK")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run experiment from config")
    run_p.add_argument("--config", "-c", required=True, help="Config file (YAML or JSON)")
    run_p.add_argument("--duration", "-d", type=float, default=60.0, help="Run duration in seconds (default 60)")
    run_p.add_argument("--tick-hz", type=float, default=10.0, help="Controller tick rate (default 10)")

    replay_p = sub.add_parser("replay", help="Replay session from log and recorded stream")
    replay_p.add_argument("--log", required=True, help="Event log JSONL path")
    replay_p.add_argument("--stream", help="Recorded stream path (optional)")
    replay_p.add_argument("--seed", type=int, default=42, help="Random seed for replay")
    replay_p.add_argument("--strict", action="store_true", help="Exit with code 1 if replay diverges from log")

    bench_p = sub.add_parser("benchmark", help="Print benchmark report from log")
    bench_p.add_argument("--log", required=True, help="Event log JSONL path")
    bench_p.add_argument("--human", action="store_true", help="Print only human-readable summary (no JSON)")

    proof_p = sub.add_parser("proof-run", help="Canonical proof run: synthetic LSL, record, replay, benchmark (no hardware)")
    proof_p.add_argument("--duration", "-d", type=float, default=4.0, help="Session duration in seconds (default 4)")
    proof_p.add_argument("--out-dir", type=str, default="proof_run_output", help="Output directory for log and stream (default proof_run_output)")
    proof_p.add_argument("--seed", type=int, default=42, help="Random seed for replay (default 42)")
    proof_p.add_argument("--strict", action="store_true", help="Exit with code 1 if replay diverges from log")

    args = parser.parse_args()

    if args.command == "run":
        from looplab.config.schema import load_config
        from looplab.runner import create_runner
        from looplab.streams.lsl_client import LSLInletClient
        from looplab.streams.clock import lsl_clock
        from looplab.replay.stream_recorder import StreamRecorder

        config = load_config(args.config)
        components = create_runner(config)
        loop = components["loop"]
        buffer = components["buffer"]
        writer = components["writer"]
        hooks = components.get("hooks")
        recorder = components.get("recorder")

        client = LSLInletClient(
            name=config.lsl.name,
            type_=config.lsl.type,
            source_id=config.lsl.source_id,
            chunk_size=config.lsl.chunk_size or 32,
            max_buffered=config.lsl.max_buffered,
            timeout=config.lsl.timeout,
        )
        client.connect()
        writer.open()

        if recorder:
            recorder.open()

        start = lsl_clock()
        tick_interval = 1.0 / args.tick_hz
        next_tick = start
        try:
            while lsl_clock() - start < args.duration:
                data, timestamps = client.pull_chunk(timeout=0.1, max_samples=256)
                if data.size > 0:
                    buffer.append(data, timestamps)
                    if hooks:
                        hooks.record_pull_chunk(lsl_clock())
                    if recorder and timestamps:
                        recorder.record(data, timestamps)
                now = lsl_clock()
                if now >= next_tick:
                    if hooks:
                        hooks.record_preprocess_done(now)
                    c = loop.tick()
                    if hooks and c:
                        hooks.record_policy_done(now)
                    next_tick = now + tick_interval
        finally:
            client.close()
            writer.close()
            if recorder:
                recorder.close()
        print("Run finished.", file=sys.stderr)

    elif args.command == "replay":
        from looplab.replay.engine import ReplayEngine
        from looplab.replay.runner import ReplayRunner
        from looplab.replay.divergence import compute_divergence, format_divergence_report
        from looplab.buffer.ring_buffer import RingBuffer
        from looplab.preprocess.pipeline import noop_preprocess
        from looplab.features.simple import SimpleFeatureExtractor
        from looplab.model.base import create_model
        from looplab.controller.policy import IdentityPolicy

        engine = ReplayEngine(args.log, args.stream)
        engine.load()
        chunks = engine.get_chunks()
        logged = engine.get_control_sequence()
        if not chunks:
            print("No stream chunks to replay; only log loaded.", file=sys.stderr)
            if args.strict and logged:
                sys.exit(1)
        else:
            n_samples, n_channels = chunks[0][0].shape[0], chunks[0][0].shape[1]
            buffer = RingBuffer(max_samples=n_samples * 10, n_channels=n_channels)
            model = create_model("identity", {})
            policy = IdentityPolicy()
            runner = ReplayRunner(
                engine,
                buffer,
                noop_preprocess,
                SimpleFeatureExtractor(),
                model,
                policy,
            )
            replayed = runner.run(seed=args.seed)
            report = compute_divergence(logged, replayed)
            msg = format_divergence_report(report)
            print(msg, file=sys.stderr)
            if args.strict and not report["matches"]:
                sys.exit(1)

    elif args.command == "benchmark":
        from looplab.logging.schema import LogEvent
        from looplab.benchmark.report import latency_report, format_report_human
        import json

        points = []
        with open(args.log, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ev = LogEvent.from_dict(json.loads(line))
                if getattr(ev.event_type, "value", ev.event_type) == "benchmark_latency":
                    label = ev.payload.get("label", "?")
                    points.append((label, ev.lsl_time))
        report = latency_report(points)
        human = format_report_human(report)
        print(human, file=sys.stderr)
        if not args.human:
            print(json.dumps(report, indent=2))

    elif args.command == "proof-run":
        import json as _json
        import time as _time
        from pathlib import Path as _Path

        from datetime import datetime as _datetime
        from looplab.config.schema import RunConfig, LSLStreamConfig, BufferConfig, config_to_dict
        from looplab.runner import create_runner
        from looplab.streams.lsl_client import LSLInletClient
        from looplab.streams.clock import lsl_clock
        from looplab.streams.synthetic import start_synthetic_outlet_thread
        from looplab.replay.engine import ReplayEngine
        from looplab.replay.runner import ReplayRunner
        from looplab.replay.divergence import compute_divergence, format_divergence_report
        from looplab.replay.stream_recorder import StreamRecorder
        from looplab.buffer.ring_buffer import RingBuffer
        from looplab.preprocess.pipeline import noop_preprocess
        from looplab.features.simple import SimpleFeatureExtractor
        from looplab.model.base import create_model
        from looplab.controller.policy import IdentityPolicy
        from looplab.logging.schema import LogEvent
        from looplab.benchmark.report import latency_report, format_report_human

        out_dir = _Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        log_path = out_dir / "events.jsonl"
        stream_path = out_dir / "stream.jsonl"

        config = RunConfig(
            lsl=LSLStreamConfig(name="FakeEEG", type="EEG", chunk_size=8, timeout=5.0),
            buffer=BufferConfig(max_samples=500, n_channels=2),
            preprocess="none",
            feature_extractor="simple",
            model="identity",
            policy="identity",
            task_adapter="psychopy",
            log_path=str(log_path),
            record_stream_path=str(stream_path),
            benchmark=True,
        )
        with open(out_dir / "config_snapshot.json", "w", encoding="utf-8") as f:
            _json.dump(config_to_dict(config), f, indent=2)

        duration = args.duration
        thread = start_synthetic_outlet_thread(duration + 1.0, n_channels=2, srate=50.0, stream_name="FakeEEG")
        _time.sleep(0.8)

        try:
            client = LSLInletClient(name="FakeEEG", timeout=5.0, chunk_size=8)
            client.connect()
        except RuntimeError as e:
            if "No LSL stream" in str(e):
                print("Proof-run skipped: LSL stream discovery failed (e.g. network/sandbox).", file=sys.stderr)
                session_fail = {
                    "lsl_available": False,
                    "error": "LSL stream discovery failed (e.g. network/sandbox)",
                    "out_dir": str(out_dir),
                }
                with open(out_dir / "session_summary.json", "w", encoding="utf-8") as f:
                    _json.dump(session_fail, f, indent=2)
                sys.exit(2)
            raise

        components = create_runner(config)
        loop = components["loop"]
        buffer = components["buffer"]
        writer = components["writer"]
        hooks = components.get("hooks")
        recorder = components.get("recorder")
        writer.open()
        if recorder:
            recorder.open()

        start = lsl_clock()
        tick_interval = 1.0 / 10.0
        next_tick = start
        try:
            while lsl_clock() - start < duration:
                data, timestamps = client.pull_chunk(timeout=0.1, max_samples=32)
                if data.size > 0:
                    buffer.append(data, timestamps)
                    if hooks:
                        hooks.record_pull_chunk(lsl_clock())
                    if recorder and timestamps:
                        recorder.record(data, timestamps)
                now = lsl_clock()
                if now >= next_tick:
                    if hooks:
                        hooks.record_preprocess_done(now)
                    c = loop.tick()
                    if hooks and c:
                        hooks.record_policy_done(now)
                    next_tick = now + tick_interval
        finally:
            client.close()
            writer.close()
            if recorder:
                recorder.close()
        thread.join(timeout=10)

        print("Proof-run: session recorded.", file=sys.stderr)

        # Replay
        engine = ReplayEngine(str(log_path), str(stream_path))
        engine.load()
        chunks = engine.get_chunks()
        logged = engine.get_control_sequence()
        if not chunks:
            print("Replay: no stream chunks (replay skipped).", file=sys.stderr)
            replay_ok = not args.strict
            replay_result = {
                "match_count": 0,
                "mismatch_count": len(logged),
                "total_logged": len(logged),
                "total_replayed": 0,
                "matches": False,
                "divergences": [],
            }
        else:
            r_buffer = RingBuffer(max_samples=500, n_channels=2)
            runner = ReplayRunner(
                engine, r_buffer, noop_preprocess,
                SimpleFeatureExtractor(), create_model("identity", {}), IdentityPolicy(),
            )
            replayed = runner.run(seed=args.seed)
            report = compute_divergence(logged, replayed)
            replay_result = report
            print(format_divergence_report(report), file=sys.stderr)
            replay_ok = report["matches"] or not args.strict
        with open(out_dir / "replay_result.json", "w", encoding="utf-8") as f:
            _json.dump(replay_result, f, indent=2)

        # Benchmark
        points = []
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ev = LogEvent.from_dict(_json.loads(line))
                if getattr(ev.event_type, "value", ev.event_type) == "benchmark_latency":
                    points.append((ev.payload.get("label", "?"), ev.lsl_time))
        bench_report = latency_report(points)
        print(format_report_human(bench_report), file=sys.stderr)
        with open(out_dir / "benchmark_summary.json", "w", encoding="utf-8") as f:
            _json.dump(bench_report, f, indent=2)

        # Artifacts
        artifacts_ok = log_path.exists() and log_path.stat().st_size > 0
        artifacts_ok = artifacts_ok and stream_path.exists() and stream_path.stat().st_size > 0
        session_summary = {
            "duration_sec": duration,
            "seed": args.seed,
            "out_dir": str(out_dir),
            "artifacts_ok": artifacts_ok,
            "replay_ok": replay_ok,
            "lsl_available": True,
            "timestamp": _datetime.utcnow().isoformat() + "Z",
        }
        with open(out_dir / "session_summary.json", "w", encoding="utf-8") as f:
            _json.dump(session_summary, f, indent=2)
        if not artifacts_ok:
            print("Proof-run: artifact check failed (log or stream missing/empty).", file=sys.stderr)
            sys.exit(1)
        if not replay_ok:
            sys.exit(1)
        print("Proof-run: all checks passed.", file=sys.stderr)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
