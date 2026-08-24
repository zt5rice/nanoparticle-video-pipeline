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
