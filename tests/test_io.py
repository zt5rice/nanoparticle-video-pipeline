"""I/O tests: TIFF roundtrip, ND2 dependency error, and the real Artificial8bit sample."""

import builtins
import zipfile
from pathlib import Path

import numpy as np
import pytest

from nanotrack.config import PipelineConfig
from nanotrack.io import load_video, save_video
from nanotrack.pipeline import run

ARCHIVE = Path(__file__).resolve().parents[1] / "ref" / "SWNTs trackingV3.zip"
ART8_ENTRY = "SWNTs trackingV3/sample data/Artificial8bit/Artificial8bit.tif"


def test_tiff_roundtrip(tmp_path):
    """A synthetic uint8 stack survives save -> load unchanged."""
    frames = np.arange(5 * 64 * 64, dtype=np.uint8).reshape(5, 64, 64)
    path = tmp_path / "stack.tif"
    save_video(path, frames)
    loaded, meta = load_video(path)
    np.testing.assert_array_equal(loaded, frames)
    assert meta["format"] == "tiff"
    assert meta["n_frames"] == 5


def test_nd2_missing_dependency_raises_clear_error(tmp_path, monkeypatch):
    """Blocking the optional nd2 import must raise an actionable ImportError."""

    def fake_import(name, *args, **kwargs):
        if name == "nd2":
            raise ImportError("No module named 'nd2'")
        return original_import(name, *args, **kwargs)

    original_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError, match="pip install nd2"):
        load_video(tmp_path / "movie.nd2")


@pytest.mark.skipif(not ARCHIVE.exists(), reason="local ref/ archive not present")
def test_artificial8bit_read_and_pipeline(tmp_path):
    """The real 8-bit sample loads as a uint8 stack and the pipeline runs on it."""
    with zipfile.ZipFile(ARCHIVE) as z:
        z.extract(ART8_ENTRY, tmp_path)
    frames, meta = load_video(tmp_path / ART8_ENTRY)
    assert frames.ndim == 3
    assert frames.dtype == np.uint8
    assert frames.shape[0] > 0
    assert meta["format"] == "tiff"

    # Single-molecule SPT on a short prefix: pipeline must run end-to-end.
    cfg = PipelineConfig(n_frames=min(10, frames.shape[0]), min_track_len=3, seed=0)
    result = run(frames[: cfg.n_frames], cfg)
    assert result["n_frames"] == cfg.n_frames
    assert "quality" in result and "pass_rate" in result["quality"]
