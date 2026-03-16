"""LSL stream ingestion and clock utilities."""

from looplab.streams.clock import lsl_clock
from looplab.streams.lsl_client import LSLInletClient, discover_stream, create_inlet
from looplab.streams.synthetic import run_synthetic_outlet, start_synthetic_outlet_thread

__all__ = [
    "lsl_clock",
    "LSLInletClient",
    "discover_stream",
    "create_inlet",
    "run_synthetic_outlet",
    "start_synthetic_outlet_thread",
]
