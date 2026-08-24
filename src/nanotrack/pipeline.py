"""Pipeline orchestrator: preprocess -> detect -> track -> features -> validate -> export."""

from __future__ import annotations

import numpy as np

from . import validation
from .config import PipelineConfig
from .detection import detect
from .features import summarize
from .preprocessing import preprocess
from .tracking import track


def _analyze_frame(frame: np.ndarray, cfg: PipelineConfig) -> list[dict]:
    mask = preprocess(frame, cfg.backend, cfg)
    return detect(mask, cfg)


def run_from_detections(
    blobs_per_frame: list[list[dict]],
    cfg: PipelineConfig,
    ground_truth: dict | None = None,
    raw: bool = False,
) -> dict:
    """Run tracking -> features -> validation on pre-computed detections.

    This is the resume/post-processing entry point: image analysis (the expensive
    stage) can be skipped when ``detections.csv`` is already available.
    """
    trk = track(blobs_per_frame, cfg)
    summary = summarize(trk, cfg)
    trk["summary"] = summary
    quality = validation.report(trk, blobs_per_frame, cfg)
    result = {
        "version": "0.1.0",
        "config": cfg.to_dict(),
        "n_frames": int(cfg.n_frames),
        "n_detections": int(trk["present_frames"]),
        "n_tracks": 1 if trk["valid"] else 0,
        "summary": summary,
        "quality": quality,
    }
    if raw:
        result["detections"] = blobs_per_frame
        result["track"] = trk
        result["ground_truth"] = ground_truth
    return result


def run(
    frames: np.ndarray,
    cfg: PipelineConfig,
    ground_truth: dict | None = None,
    raw: bool = False,
) -> dict:
    """Run the full pipeline on a video stack (preprocess -> detect -> ... -> validate)."""
    blobs_per_frame = [_analyze_frame(f, cfg) for f in frames]
    return run_from_detections(blobs_per_frame, cfg, ground_truth=ground_truth, raw=raw)
