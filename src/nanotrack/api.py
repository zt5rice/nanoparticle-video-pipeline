"""FastAPI application: /health, /analyze, /metrics, /tracking."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field, field_validator

from . import metrics
from .config import BACKENDS, PipelineConfig
from .pipeline import run
from .synth import generate

app = FastAPI(title="nanotrack", version="0.1.0")


class AnalyzeRequest(BaseModel):
    n_frames: int = Field(60, ge=10, le=500)
    backend: str = "numpy"
    image_size: int = 512
    seed: int | None = None

    @field_validator("backend")
    @classmethod
    def _check_backend(cls, value: str) -> str:
        if value not in BACKENDS:
            raise ValueError(f"backend must be one of {BACKENDS}")
        return value


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    start = time.perf_counter()
    try:
        cfg = PipelineConfig(
            n_frames=req.n_frames,
            backend=req.backend,
            image_size=req.image_size,
            seed=req.seed if req.seed is not None else 0,
        )
        frames, _ = generate(cfg)
        result = run(frames, cfg)
        metrics.observe(result["n_frames"], time.perf_counter() - start)
    except Exception as exc:
        metrics.count_error()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    s = result["summary"]
    tracks = (
        [
            {
                "track_id": s["track_id"],
                "length_mean": s["length_mean"],
                "length_std": s["length_std"],
                "angle_std": s["angle_std"],
                "eccentricity_mean": s["eccentricity_mean"],
                "diffusion_coefficient_px2_per_s": s["diffusion_coefficient_px2_per_s"],
                "rotational_diffusion_coefficient_rad2_per_s": s[
                    "rotational_diffusion_coefficient_rad2_per_s"
                ],
            }
        ]
        if result["n_tracks"]
        else []
    )
    return {
        "n_frames": result["n_frames"],
        "n_tracks": result["n_tracks"],
        "n_detections": result["n_detections"],
        "quality_pass_rate": result["quality"]["pass_rate"],
        "tracks": tracks,
    }


@app.get("/metrics")
def metrics_endpoint() -> Response:
    return Response(
        content=metrics.render(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/tracking")
def tracking_page(out: str = "output") -> Response:
    """Serve the tracking-QC HTML report for a run directory."""
    path = Path(out) / "tracking_report.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{path} not found")
    return FileResponse(path, media_type="text/html")

