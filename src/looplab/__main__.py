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

    proof_p = sub.add_parser("proof-run", help="Canonical proof run: record, replay, benchmark (no hardware)")
    proof_p.add_argument("--backend", choices=["synthetic", "lsl"], default="synthetic", help="synthetic: pure Python, no LSL (CI-safe). lsl: real LSL discovery (default synthetic)")
    proof_p.add_argument("--config", type=str, default=None, help="Optional config file (YAML/JSON); if set, use its settings and synthetic scenario when present")
    proof_p.add_argument("--duration", "-d", type=float, default=4.0, help="Session duration in seconds (default 4)")
    proof_p.add_argument("--out-dir", type=str, default="proof_run_output", help="Output directory for log and stream (default proof_run_output)")
    proof_p.add_argument("--seed", type=int, default=42, help="Random seed for replay (default 42)")
    proof_p.add_argument("--strict", action="store_true", help="Exit with code 1 if replay diverges from log")

    report_p = sub.add_parser("report", help="Unified run report from log or run directory")
    report_p.add_argument("--log", help="Event log JSONL path")
    report_p.add_argument("--run-dir", help="Run directory (expects events.jsonl, optional benchmark_summary.json)")
    report_p.add_argument("--human", action="store_true", help="Print only human-readable one-page summary")
    report_p.add_argument("--json", action="store_true", help="Print JSON run report (default if no --human)")
    report_p.add_argument(
        "--write",
        action="store_true",
        help="Write run_package_summary.json, RUN_SUMMARY.md, run_report.json, run_report.md into --run-dir",
    )

    list_p = sub.add_parser("list", help="List registered plugins (short form; see list-components for detail)")
    list_p.add_argument("--features", action="store_true", help="List only feature extractors")
    list_p.add_argument("--models", action="store_true", help="List only models")
    list_p.add_argument("--policies", action="store_true", help="List only policies")
    list_p.add_argument("--json", action="store_true", help="Output as JSON")

    lc_p = sub.add_parser(
        "list-components",
        help="List feature extractors, models, policies with class, defaults, and descriptions",
    )
    lc_p.add_argument("--features", action="store_true", help="List only feature extractors")
    lc_p.add_argument("--models", action="store_true", help="List only models")
    lc_p.add_argument("--policies", action="store_true", help="List only policies")
    lc_p.add_argument("--json", action="store_true", help="Output as JSON")

    vc_p = sub.add_parser("validate-config", help="Validate config: registered names and component instantiation")
    vc_p.add_argument("--config", "-c", required=True, help="Config YAML or JSON")
    vc_p.add_argument(
        "--plugin",
        action="append",
        default=[],
        help="Python file to load first (register custom components); repeat for multiple",
    )
    vc_p.add_argument("--strict", action="store_true", help="Treat unrecognized preprocess as error")
    vc_p.add_argument("--json", action="store_true", help="Print result as JSON")

    check_lsl_p = sub.add_parser(
        "check-lsl",
        help="Probe native LSL discovery (see docs/deployment/lsl_compatibility_matrix.md)",
    )
    check_lsl_p.add_argument("--json", action="store_true", help="Machine-readable result and exit code")

    export_bids_p = sub.add_parser(
        "export-bids",
        help="Export run dir to BIDS + FIF (requires: pip install -e \".[mne]\"; docs/export_formats.md)",
    )
    export_bids_p.add_argument("--run-dir", required=True, help="LoopLab run directory (stream.jsonl, events.jsonl)")
    export_bids_p.add_argument("--bids-root", required=True, help="BIDS dataset root directory")
    export_bids_p.add_argument("--sub", required=True, help="BIDS subject label (e.g. 01 → sub-01)")
    export_bids_p.add_argument("--task", default="closedloop", help="BIDS task label")
    export_bids_p.add_argument("--ses", default=None, help="Optional session label")
    export_bids_p.add_argument("--run", type=int, default=1, help="Run index (default 1)")
    export_bids_p.add_argument("--overwrite", action="store_true", help="Overwrite existing export files")
    export_bids_p.add_argument(
        "--include-all-events",
        action="store_true",
        help="Include stream_chunk and features rows in events.tsv (can be large)",
    )

    new_p = sub.add_parser("new", help="Generate a starter plugin file (feature, model, or policy)")
    new_p.add_argument("kind", choices=["feature", "model", "policy"], help="Plugin type")
    new_p.add_argument("name", help="Plugin name (used for registration and file name)")
    new_p.add_argument("--out-dir", type=str, default=".", help="Directory to write the file (default: current)")

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
                    loop.tick()
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
        from looplab.features.base import create_feature_extractor
        from looplab.model.base import create_model
        from looplab.controller.policy import create_policy

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
            policy = create_policy("identity", {})
            runner = ReplayRunner(
                engine,
                buffer,
                noop_preprocess,
                create_feature_extractor("simple", {}),
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

        import numpy as _np
        from datetime import datetime as _datetime, timezone as _timezone
        from looplab.config.schema import RunConfig, LSLStreamConfig, BufferConfig, config_to_dict
        from looplab.replay.engine import ReplayEngine
        from looplab.replay.runner import ReplayRunner
        from looplab.replay.divergence import compute_divergence, format_divergence_report
        from looplab.replay.stream_recorder import StreamRecorder
        from looplab.buffer.ring_buffer import RingBuffer
        from looplab.preprocess.pipeline import noop_preprocess
        from looplab.features.base import create_feature_extractor
        from looplab.model.base import create_model
        from looplab.controller.policy import create_policy
        from looplab.logging.schema import LogEvent
        from looplab.benchmark.report import latency_report, format_report_human

        out_dir = _Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        log_path = out_dir / "events.jsonl"
        stream_path = out_dir / "stream.jsonl"

        if getattr(args, "config", None):
            from looplab.config.schema import load_config
            config = load_config(args.config)
            config.log_path = str(log_path)
            config.record_stream_path = str(stream_path)
        else:
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
        from looplab.runner import build_components_manifest

        with open(out_dir / "components_manifest.json", "w", encoding="utf-8") as f:
            _json.dump(build_components_manifest(config), f, indent=2)

        duration = args.duration
        backend = getattr(args, "backend", "synthetic")

        if backend == "synthetic":
            # Pure Python path: no pylsl. Set synthetic clock before any code that calls lsl_clock().
            _t0_wall = _time.monotonic()
            _base_time = 1000.0

            def _synthetic_clock() -> float:
                return _base_time + (_time.monotonic() - _t0_wall)

            from looplab.streams import clock as _clock_mod
            _clock_mod.set_clock(_synthetic_clock)
            lsl_clock = _clock_mod.lsl_clock
            start = lsl_clock()

            from looplab.runner import create_runner
            from looplab.controller.loop import ControllerLoop
            components = create_runner(config)
            adapter = components["adapter"]
            model = components["model"]
            policy = components["policy"]
            syn_cfg = None
            if getattr(config, "synthetic", None):
                from looplab.synthetic.config import parse_synthetic_config
                syn_cfg = parse_synthetic_config(config.synthetic)
            if syn_cfg:
                if syn_cfg.ack_delay_ms.enabled or syn_cfg.event_omission.enabled:
                    from looplab.synthetic.wrappers import SyntheticTaskAdapterWrapper
                    adapter = SyntheticTaskAdapterWrapper(
                        adapter, syn_cfg.ack_delay_ms, syn_cfg.event_omission, syn_cfg.seed
                    )
                    adapter.set_logger(components["logger"])
                if syn_cfg.low_confidence.enabled:
                    from looplab.synthetic.wrappers import LowConfidenceModelWrapper
                    model = LowConfidenceModelWrapper(
                        model, syn_cfg.low_confidence, start, lsl_clock
                    )
                if syn_cfg.policy_noop.enabled:
                    from looplab.synthetic.wrappers import NoopPolicyWrapper
                    policy = NoopPolicyWrapper(
                        policy, syn_cfg.policy_noop, start, lsl_clock
                    )
            loop = ControllerLoop(
                buffer=components["buffer"],
                preprocess=components["preprocess"],
                feature_extractor=components["feature_extractor"],
                model=model,
                policy=policy,
                adapter=adapter,
                logger=components["logger"],
                min_samples=8,
            )
            buffer = components["buffer"]
            writer = components["writer"]
            hooks = components.get("hooks")
            if hooks:
                loop.set_hooks(hooks)
            recorder = components.get("recorder")
            writer.open()
            if recorder:
                recorder.open()

            chunk_interval = 0.02
            n_channels = getattr(config.buffer, "n_channels", 2)
            chunk_size = getattr(config.lsl, "chunk_size", 8) or 8
            srate = 50.0
            try:
                if syn_cfg:
                    from looplab.synthetic.generator import generate_chunks
                    for data, timestamps, _valid in generate_chunks(
                        syn_cfg, duration, n_channels, chunk_size, srate, start, chunk_interval
                    ):
                        buffer.append(data, timestamps)
                        if hooks:
                            hooks.record_pull_chunk(lsl_clock())
                        if recorder:
                            recorder.record(data, timestamps)
                        loop.tick()
                        sig = adapter.pop_pending()
                        if sig is not None:
                            adapter.report_realized(sig, lsl_clock())
                        _time.sleep(chunk_interval)
                else:
                    rng = _np.random.default_rng(args.seed)
                    _np.random.seed(args.seed)
                    sample_idx = 0
                    while lsl_clock() - start < duration:
                        data = rng.standard_normal((chunk_size, n_channels)).astype(_np.float64)
                        ts_start = start + sample_idx / srate
                        timestamps = [ts_start + j / srate for j in range(chunk_size)]
                        sample_idx += chunk_size
                        buffer.append(data, timestamps)
                        if hooks:
                            hooks.record_pull_chunk(lsl_clock())
                        if recorder:
                            recorder.record(data, timestamps)
                        loop.tick()
                        _time.sleep(chunk_interval)
            finally:
                writer.close()
                if recorder:
                    recorder.close()
            print("Proof-run: session recorded (synthetic backend).", file=sys.stderr)
        else:
            # LSL backend: real stream discovery (may segfault in CI).
            from looplab.streams import clock as _clock_mod
            _clock_mod.set_clock(None)
            from looplab.runner import create_runner
            from looplab.streams.lsl_client import LSLInletClient
            from looplab.streams.clock import lsl_clock
            from looplab.streams.synthetic import start_synthetic_outlet_thread

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
                        "lsl_support_tier": "native_lsl_unavailable",
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
                        loop.tick()
                        next_tick = now + tick_interval
            finally:
                client.close()
                writer.close()
                if recorder:
                    recorder.close()
            thread.join(timeout=10)
            print("Proof-run: session recorded (LSL backend).", file=sys.stderr)

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
                create_feature_extractor("simple", {}), create_model("identity", {}), create_policy("identity", {}),
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
        event_counts = {}
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ev = LogEvent.from_dict(_json.loads(line))
                t = getattr(ev.event_type, "value", ev.event_type)
                event_counts[t] = event_counts.get(t, 0) + 1
                if t == "benchmark_latency":
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
            "lsl_available": (backend == "lsl"),
            "lsl_support_tier": (
                "native_lsl_functional" if backend == "lsl" else "synthetic_supported"
            ),
            "backend": backend,
            "timestamp": _datetime.now(_timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        run_warnings = []
        if not points:
            run_warnings.append("no_benchmark_events")
        if not chunks:
            run_warnings.append("replay_skipped_no_chunks")
        from looplab.benchmark.diagnostics import write_run_diagnostics_artifacts
        from looplab.benchmark.run_summary import build_run_package_summary, format_run_summary_markdown

        diag, warning_inv = write_run_diagnostics_artifacts(
            out_dir,
            event_counts,
            bench_report,
            replay_result,
            out_dir / "events.jsonl",
            out_dir / "stream.jsonl",
            session_summary,
            run_warnings,
        )
        with open(out_dir / "session_summary.json", "w", encoding="utf-8") as f:
            _json.dump(session_summary, f, indent=2)

        config_snap = _json.loads((out_dir / "config_snapshot.json").read_text(encoding="utf-8"))
        run_package_summary = build_run_package_summary(
            event_counts,
            bench_report,
            run_dir=out_dir,
            session_summary=session_summary,
            replay_result=replay_result,
            config_snapshot=config_snap,
            backend=backend,
            warnings=warning_inv,
            diagnostics=diag,
        )
        with open(out_dir / "run_package_summary.json", "w", encoding="utf-8") as f:
            _json.dump(run_package_summary, f, indent=2)
        with open(out_dir / "RUN_SUMMARY.md", "w", encoding="utf-8") as f:
            f.write(format_run_summary_markdown(run_package_summary))
        from looplab.benchmark.run_report import write_run_report_artifacts

        write_run_report_artifacts(out_dir)

        if not artifacts_ok:
            print("Proof-run: artifact check failed (log or stream missing/empty).", file=sys.stderr)
            sys.exit(1)
        if not replay_ok:
            sys.exit(1)
        print("Proof-run: all checks passed.", file=sys.stderr)

    elif args.command == "report":
        import json as _json
        from pathlib import Path as _Path
        from looplab.logging.schema import LogEvent
        from looplab.benchmark.report import latency_report, format_report_human

        run_dir = _Path(args.run_dir) if getattr(args, "run_dir", None) else None
        log_path = getattr(args, "log", None)
        if run_dir and run_dir.is_dir():
            log_path = str(run_dir / "events.jsonl")
        if not log_path or not _Path(log_path).exists():
            print("report: provide --log <path> or --run-dir <dir> with events.jsonl", file=sys.stderr)
            sys.exit(1)
        path = _Path(log_path)

        events = []
        points = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ev = LogEvent.from_dict(_json.loads(line))
                events.append(ev)
                if getattr(ev.event_type, "value", ev.event_type) == "benchmark_latency":
                    points.append((ev.payload.get("label", "?"), ev.lsl_time))

        by_type = {}
        for e in events:
            t = getattr(e.event_type, "value", e.event_type)
            by_type[t] = by_type.get(t, 0) + 1

        bench = latency_report(points)
        report = {
            "log_path": str(path),
            "event_counts": by_type,
            "n_events": len(events),
            "benchmark": bench,
        }
        if run_dir:
            session_file = run_dir / "session_summary.json"
            if session_file.exists():
                with open(session_file, encoding="utf-8") as f:
                    report["session_summary"] = _json.load(f)
            for name in ("replay_result.json", "config_snapshot.json"):
                p = run_dir / name
                if p.exists():
                    report[name.replace(".json", "_path")] = str(p)

        report_warnings = []
        if not points:
            report_warnings.append("no_benchmark_events")
        from looplab.benchmark.run_summary import build_run_package_summary, format_run_summary_markdown

        bench_for_diag = bench
        replay_for_summary = None
        if run_dir:
            bp = run_dir / "benchmark_summary.json"
            if bp.exists():
                with open(bp, encoding="utf-8") as f:
                    bench_for_diag = _json.load(f)
            rp = run_dir / "replay_result.json"
            if rp.exists():
                with open(rp, encoding="utf-8") as f:
                    replay_for_summary = _json.load(f)

        diag = None
        warning_inv = list(report_warnings)
        if run_dir and getattr(args, "write", False) and path.resolve().parent == run_dir.resolve():
            from looplab.benchmark.diagnostics import write_run_diagnostics_artifacts

            session_for_summary = dict(report.get("session_summary") or {})
            diag, warning_inv = write_run_diagnostics_artifacts(
                run_dir,
                report["event_counts"],
                bench_for_diag,
                replay_for_summary,
                path,
                run_dir / "stream.jsonl",
                session_for_summary,
                report_warnings,
            )
            report["session_summary"] = session_for_summary
            with open(run_dir / "session_summary.json", "w", encoding="utf-8") as f:
                _json.dump(session_for_summary, f, indent=2)
        elif run_dir:
            dp = run_dir / "diagnostics.json"
            if dp.exists():
                with open(dp, encoding="utf-8") as f:
                    diag = _json.load(f)
                for item in diag.get("findings", []):
                    if item.get("level") in ("warning", "critical"):
                        warning_inv.append(f"{item['level']}: {item.get('code', '')} — {item.get('message', '')}")

        run_package_summary = build_run_package_summary(
            report["event_counts"],
            bench_for_diag,
            run_dir=run_dir,
            session_summary=report.get("session_summary"),
            replay_result=replay_for_summary,
            warnings=warning_inv,
            diagnostics=diag,
        )
        report["run_package_summary"] = run_package_summary
        if run_dir and getattr(args, "write", False):
            with open(run_dir / "run_package_summary.json", "w", encoding="utf-8") as f:
                _json.dump(run_package_summary, f, indent=2)
            with open(run_dir / "RUN_SUMMARY.md", "w", encoding="utf-8") as f:
                f.write(format_run_summary_markdown(run_package_summary))
            from looplab.benchmark.run_report import write_run_report_artifacts

            write_run_report_artifacts(run_dir)

        if getattr(args, "human", False):
            lines = [
                f"Run report: {report['log_path']}",
                f"  Events: {report['n_events']} total",
                "  By type: " + ", ".join(f"{k}={v}" for k, v in sorted(report["event_counts"].items())),
                "",
                format_report_human(bench),
                "",
                format_run_summary_markdown(run_package_summary),
            ]
            print("\n".join(lines))
        else:
            print(_json.dumps(report, indent=2))

    elif args.command == "new":
        out_dir = Path(getattr(args, "out_dir", "."))
        out_dir.mkdir(parents=True, exist_ok=True)
        kind = getattr(args, "kind")
        name = getattr(args, "name")
        class_name = "".join(p.capitalize() for p in name.replace("-", "_").split("_"))
        if kind == "feature":
            content = f'''"""Custom feature extractor: {name}. Implement extract() and reference as feature_extractor: {name!r} in config."""

from __future__ import annotations

from typing import Any

import numpy as np

from looplab.features.base import FeatureExtractor, register_feature_extractor


class {class_name}(FeatureExtractor):
    def __init__(self, use_variance: bool = True):
        self._use_variance = use_variance

    def extract(
        self,
        data: np.ndarray,
        t_start: float,
        t_end: float,
        context: dict[str, Any] | None = None,
    ) -> np.ndarray | dict[str, np.ndarray]:
        data = np.asarray(data, dtype=np.float64)
        # TODO: your implementation
        return data.mean(axis=1)


register_feature_extractor({name!r}, {class_name}, {{"use_variance": True}})
'''
        elif kind == "model":
            content = f'''"""Custom model: {name}. Implement run() and reference as model: {name!r} in config."""

from __future__ import annotations

from typing import Any

import numpy as np

from looplab.controller.signals import ModelOutput
from looplab.model.base import Model, register_model


class {class_name}(Model):
    def run(
        self,
        features: np.ndarray,
        context: dict[str, Any] | None = None,
    ) -> ModelOutput:
        # TODO: your implementation
        f = np.asarray(features).ravel()
        return ModelOutput(value=float(np.mean(f)), confidence=1.0)


register_model({name!r}, {class_name}, {{}})
'''
        else:  # policy
            content = f'''"""Custom policy: {name}. Implement __call__() and reference as policy: {name!r} in config."""

from __future__ import annotations

from typing import Any

from looplab.controller.signals import ControlSignal, ModelOutput
from looplab.controller.policy import Policy, register_policy
from looplab.streams.clock import lsl_clock


class {class_name}(Policy):
    def __init__(self, validity_seconds: float = 1.0):
        self._validity_seconds = validity_seconds

    def __call__(
        self,
        model_output: ModelOutput,
        context: dict[str, Any],
    ) -> ControlSignal:
        now = lsl_clock()
        # TODO: your implementation
        return ControlSignal(
            action="set_value",
            params={{"value": model_output.value}},
            valid_until_lsl_time=now + self._validity_seconds,
        )


register_policy({name!r}, {class_name}, {{"validity_seconds": 1.0}})
'''
        path = out_dir / f"{name}.py"
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path}", file=sys.stderr)

    elif args.command == "validate-config":
        import json as _json
        from looplab.runner import validate_config_file

        result = validate_config_file(args.config, list(args.plugin or []), strict=getattr(args, "strict", False))
        if getattr(args, "json", False):
            print(_json.dumps(result, indent=2))
        else:
            for w in result.get("warnings", []):
                print(f"Warning: {w}", file=sys.stderr)
            for e in result.get("errors", []):
                print(f"Error: {e}", file=sys.stderr)
            if result.get("ok"):
                print("Config OK.", file=sys.stderr)
            else:
                print("Validation failed.", file=sys.stderr)
        sys.exit(0 if result.get("ok") else 1)

    elif args.command == "check-lsl":
        import json as _json

        from looplab.streams.lsl_support import (
            LSL_MATRIX_BLURB,
            build_check_lsl_json_report,
            check_lsl_exit_code,
            check_lsl_human_message,
            probe_native_lsl_discovery,
        )

        r = probe_native_lsl_discovery()
        if getattr(args, "json", False):
            print(_json.dumps(build_check_lsl_json_report(r), indent=2))
        else:
            print(LSL_MATRIX_BLURB, file=sys.stderr)
            print("", file=sys.stderr)
            print(check_lsl_human_message(r), file=sys.stderr)
            if r.get("error") and not r.get("discovery_ok") and r.get("pylsl_available"):
                print(f"  ({r['error']})", file=sys.stderr)
        sys.exit(check_lsl_exit_code(r))

    elif args.command == "export-bids":
        import json as _json

        try:
            from looplab.export.bids_export import export_run_to_bids
        except ImportError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        try:
            out = export_run_to_bids(
                args.run_dir,
                args.bids_root,
                sub=args.sub,
                task=args.task,
                ses=getattr(args, "ses", None) or None,
                run=int(args.run),
                overwrite=bool(getattr(args, "overwrite", False)),
                include_all_events=bool(getattr(args, "include_all_events", False)),
            )
        except Exception as e:
            print(f"export-bids failed: {e}", file=sys.stderr)
            sys.exit(1)
        print(_json.dumps(out, indent=2))
        sys.exit(0)

    elif args.command == "list-components":
        import json as _json
        from looplab.introspection import build_component_catalog, format_component_catalog_text

        cat = build_component_catalog()
        show_all = not (
            getattr(args, "features", False)
            or getattr(args, "models", False)
            or getattr(args, "policies", False)
        )
        if getattr(args, "json", False):
            out: dict = {}
            if show_all or getattr(args, "features", False):
                out["feature_extractors"] = cat["feature_extractors"]
            if show_all or getattr(args, "models", False):
                out["models"] = cat["models"]
            if show_all or getattr(args, "policies", False):
                out["policies"] = cat["policies"]
            print(_json.dumps(out, indent=2))
        else:
            text = format_component_catalog_text(
                cat,
                features=show_all or getattr(args, "features", False),
                models=show_all or getattr(args, "models", False),
                policies=show_all or getattr(args, "policies", False),
            )
            print(text)

    elif args.command == "list":
        import json as _json
        # Ensure built-ins are registered
        import looplab.model.example_models  # noqa: F401
        import looplab.features.simple  # noqa: F401
        import looplab.controller.policy  # noqa: F401
        from looplab.features.base import get_feature_extractor_registry
        from looplab.model.base import get_model_registry
        from looplab.controller.policy import get_policy_registry

        def _defaults(entry: tuple) -> dict:
            return entry[1] if len(entry) >= 2 else {}

        show_all = not (getattr(args, "features", False) or getattr(args, "models", False) or getattr(args, "policies", False))
        out = {}
        if getattr(args, "json", False):
            if show_all or getattr(args, "features", False):
                fe = get_feature_extractor_registry()
                out["features"] = {name: list(_defaults(t)) for name, t in fe.items()}
            if show_all or getattr(args, "models", False):
                mo = get_model_registry()
                out["models"] = {name: list(_defaults(t)) for name, t in mo.items()}
            if show_all or getattr(args, "policies", False):
                po = get_policy_registry()
                out["policies"] = {name: list(_defaults(t)) for name, t in po.items()}
            print(_json.dumps(out, indent=2))
        else:
            lines = []
            if show_all or getattr(args, "features", False):
                fe = get_feature_extractor_registry()
                lines.append("Feature extractors:")
                for name, t in sorted(fe.items()):
                    defaults = _defaults(t)
                    keys = list(defaults) if defaults else []
                    lines.append(f"  {name}" + (f"  (default config keys: {', '.join(keys)})" if keys else ""))
                lines.append("")
            if show_all or getattr(args, "models", False):
                mo = get_model_registry()
                lines.append("Models:")
                for name, t in sorted(mo.items()):
                    defaults = _defaults(t)
                    keys = list(defaults) if defaults else []
                    lines.append(f"  {name}" + (f"  (default config keys: {', '.join(keys)})" if keys else ""))
                lines.append("")
            if show_all or getattr(args, "policies", False):
                po = get_policy_registry()
                lines.append("Policies:")
                for name, t in sorted(po.items()):
                    defaults = _defaults(t)
                    keys = list(defaults) if defaults else []
                    lines.append(f"  {name}" + (f"  (default config keys: {', '.join(keys)})" if keys else ""))
            if lines and lines[-1] == "":
                lines.pop()
            print("\n".join(lines))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
