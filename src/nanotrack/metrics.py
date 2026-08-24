"""Guarded Prometheus metrics for the nanotrack API."""

from __future__ import annotations

import os

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

# Disable metrics with NANOTRACK_METRICS_ENABLED=false (e.g. in tests).
ENABLED = os.environ.get("NANOTRACK_METRICS_ENABLED", "true").strip().lower() not in (
    "0",
    "false",
    "no",
)

_frames = Counter("nanotrack_frames_total", "Total number of analyzed frames.")
_errors = Counter("nanotrack_errors_total", "Total number of pipeline/API errors.")
_runtime = Histogram(
    "nanotrack_runtime_seconds",
    "Pipeline runtime in seconds.",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 60.0),
)


def observe(frames: int, runtime: float) -> None:
    """Record a successful analysis (frames analyzed + runtime)."""
    if ENABLED:
        _frames.inc(frames)
        _runtime.observe(runtime)


def count_error() -> None:
    """Record a failed analysis."""
    if ENABLED:
        _errors.inc()


def render() -> bytes:
    """Return the Prometheus exposition text (empty when metrics are disabled)."""
    return generate_latest() if ENABLED else b""


__all__ = ["CONTENT_TYPE_LATEST", "ENABLED", "count_error", "observe", "render"]

