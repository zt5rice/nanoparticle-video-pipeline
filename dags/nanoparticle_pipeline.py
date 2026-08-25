"""Airflow DAG: generate -> preprocess -> detect_track -> features_validate -> export."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from airflow import DAG
from airflow.operators.python import PythonOperator

from nanotrack.config import PipelineConfig
from nanotrack.export import detections_to_rows, read_detections_rows, write_csv
from nanotrack.pipeline import run, run_from_detections
from nanotrack.synth import generate

OUT = Path(__file__).resolve().parents[1] / "output"
INTER = OUT / "intermediates"

default_args = {
    "owner": "nanotrack",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}


def _generate() -> dict:
    INTER.mkdir(parents=True, exist_ok=True)
    cfg = PipelineConfig(n_frames=40, seed=0, backend="numpy")
    frames, gt = generate(cfg)
    np.save(INTER / "frames.npy", frames)
    (INTER / "ground_truth.json").write_text(json.dumps(gt), encoding="utf-8")
    return {"n_frames": int(cfg.n_frames)}


def _preprocess() -> dict:
    # Preprocessing is fused into detection inside the nanotrack core; this task
    # records the boundary so the DAG matches the generate -> preprocess ->
    # detect_track -> features_validate -> export structure.
    frames = np.load(INTER / "frames.npy")
    return {"frames_ready": int(frames.shape[0])}


def _detect_track() -> dict:
    frames = np.load(INTER / "frames.npy")
    cfg = PipelineConfig(n_frames=int(frames.shape[0]), seed=0, backend="numpy")
    result_raw = run(frames, cfg, raw=True)
    write_csv(
        INTER / "detections.csv",
        detections_to_rows(result_raw["detections"]),
        columns=["frame", "blob_id", "x_px", "y_px", "angle_deg", "angle_rad",
                 "length_px", "width_px", "area", "eccentricity"],
    )
    return {"n_detections": result_raw["n_detections"]}


def _features_validate() -> dict:
    blobs = read_detections_rows(INTER / "detections.csv")
    cfg = PipelineConfig(n_frames=len(blobs), seed=0, backend="numpy")
    result = run_from_detections(blobs, cfg, raw=True)
    (INTER / "result.json").write_text(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("detections", "track")},
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"pass_rate": result["quality"]["pass_rate"]}


def _export() -> dict:
    INTER.mkdir(parents=True, exist_ok=True)
    data = (INTER / "result.json").read_text(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "latest_result.json").write_text(data, encoding="utf-8")
    return {"exported": str(OUT / "latest_result.json")}


with DAG(
    dag_id="nanoparticle_video_pipeline",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2026, 8, 24, tzinfo=UTC),
    catchup=False,
    description="Single-molecule nanoparticle video tracking pipeline",
) as dag:
    generate_task = PythonOperator(task_id="generate", python_callable=_generate)
    preprocess_task = PythonOperator(task_id="preprocess", python_callable=_preprocess)
    detect_track_task = PythonOperator(task_id="detect_track", python_callable=_detect_track)
    features_validate_task = PythonOperator(task_id="features_validate", python_callable=_features_validate)
    export_task = PythonOperator(task_id="export", python_callable=_export)

    (
        generate_task
        >> preprocess_task
        >> detect_track_task
        >> features_validate_task
        >> export_task
    )
