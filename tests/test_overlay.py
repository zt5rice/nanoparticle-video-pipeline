"""Overlay tests: tracking result drawn on the input video (mp4/gif/png)."""

import cv2

from nanotrack.config import PipelineConfig
from nanotrack.overlay import overlay_tracks
from nanotrack.pipeline import run
from nanotrack.synth import generate


def _setup():
    cfg = PipelineConfig(image_size=128, n_frames=30, seed=0, min_track_len=10)
    frames, _ = generate(cfg)
    result = run(frames, cfg, raw=True)
    assert result["n_tracks"] == 1
    return cfg, frames, result


def test_overlay_mp4(tmp_path):
    cfg, frames, result = _setup()
    out = overlay_tracks(frames, result["track"], tmp_path / "ov.mp4", cfg)
    assert out.exists() and out.stat().st_size > 0
    cap = cv2.VideoCapture(str(out))
    assert cap.isOpened()
    assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 30
    cap.release()


def test_overlay_gif(tmp_path):
    cfg, frames, result = _setup()
    out = overlay_tracks(frames, result["track"], tmp_path / "ov.gif", cfg)
    assert out.exists() and out.stat().st_size > 0


def test_overlay_png_still(tmp_path):
    cfg, frames, result = _setup()
    out = overlay_tracks(frames, result["track"], tmp_path / "ov.png", cfg)
    assert out.exists() and out.stat().st_size > 0
    img = cv2.imread(str(out))
    assert img is not None and img.ndim == 3


def test_overlay_unsupported_format(tmp_path):
    cfg, frames, result = _setup()
    try:
        overlay_tracks(frames, result["track"], tmp_path / "ov.xyz", cfg)
    except ValueError:
        return
    raise AssertionError("expected ValueError for unsupported format")

