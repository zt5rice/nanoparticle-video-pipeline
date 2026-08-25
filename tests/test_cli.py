"""CLI tests: run_pipeline.py --input processes a real video file."""

import json
import subprocess
import sys
from pathlib import Path

from nanotrack.config import PipelineConfig
from nanotrack.io import save_video
from nanotrack.synth import generate

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "scripts" / "run_pipeline.py"


def _run_cli(*args: str | Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *[str(a) for a in args]],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    )


def test_cli_input_writes_result(tmp_path):
    """A real TIFF input produces output/result.json with a valid track."""
    frames, _ = generate(PipelineConfig(image_size=128, n_frames=30, seed=0))
    video = tmp_path / "input.tif"
    save_video(video, frames)
    out = tmp_path / "out"

    proc = _run_cli("--input", video, "--out", out)
    assert proc.returncode == 0, proc.stderr
    result = json.loads((out / "result.json").read_text(encoding="utf-8"))
    assert result["n_frames"] == 30
    assert result["n_tracks"] == 1


def test_cli_input_missing_file_fails(tmp_path):
    """A missing input file must fail with a clear error and non-zero exit."""
    proc = _run_cli("--input", tmp_path / "nope.tif", "--out", tmp_path / "out")
    assert proc.returncode != 0
    assert "error:" in proc.stderr


def test_cli_resume_reuses_detections(tmp_path):
    """--resume rebuilds result/tracks from detections.csv without image analysis."""
    frames, _ = generate(PipelineConfig(image_size=128, n_frames=30, seed=0))
    video = tmp_path / "input.tif"
    save_video(video, frames)
    out = tmp_path / "out"

    proc1 = _run_cli("--input", video, "--out", out)
    assert proc1.returncode == 0, proc1.stderr
    assert (out / "detections.csv").exists()
    assert (out / "tracks.csv").exists()
    first = json.loads((out / "result.json").read_text(encoding="utf-8"))

    # Simulate interrupted post-processing: keep detections, delete derived outputs.
    (out / "result.json").unlink()
    (out / "tracks.csv").unlink()

    proc2 = _run_cli("--input", video, "--out", out, "--resume")
    assert proc2.returncode == 0, proc2.stderr
    second = json.loads((out / "result.json").read_text(encoding="utf-8"))
    assert second["n_detections"] == first["n_detections"]
    assert second["n_tracks"] == first["n_tracks"]


def test_cli_n_frames_slices_input(tmp_path):
    """--n-frames N must actually analyze only the first N frames."""
    frames, _ = generate(PipelineConfig(image_size=128, n_frames=40, seed=0))
    video = tmp_path / "input.tif"
    save_video(video, frames)
    out = tmp_path / "out"

    proc = _run_cli("--input", video, "--n-frames", "10", "--out", out)
    assert proc.returncode == 0, proc.stderr
    result = json.loads((out / "result.json").read_text(encoding="utf-8"))
    assert result["n_frames"] == 10
    assert result["n_detections"] == 10
