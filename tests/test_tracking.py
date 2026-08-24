"""SPT tracking tests: continuity, gap-fill interpolation, max_disp, track validity."""

from itertools import pairwise

from nanotrack.config import PipelineConfig
from nanotrack.tracking import track


def _blob(x, y, angle=10.0):
    """Build a minimal blob dict (the only/largest detection of a frame)."""
    return {
        "id": 1,
        "x": float(x),
        "y": float(y),
        "angle": float(angle),
        "length": 40.0,
        "width": 6.0,
        "area": 200.0,
        "eccentricity": 0.9,
    }


def test_continuous_track():
    """A blob moving 1 px/frame stays continuously tracked (x_px == frame index)."""
    cfg = PipelineConfig(n_frames=10, min_track_len=5, max_disp=10, memory=3)
    bpf = [[_blob(t, 50)] for t in range(10)]
    trk = track(bpf, cfg)
    assert trk["present_frames"] == 10
    assert trk["valid"] is True
    assert trk["frames"][5]["x_px"] == 5.0


def test_gap_fill_interpolates():
    """A missing frame within memory is back-filled by linear interpolation (1->3 = 2)."""
    cfg = PipelineConfig(n_frames=5, min_track_len=2, max_disp=10, memory=3)
    bpf = [[_blob(0, 50)], [_blob(1, 50)], [], [_blob(3, 50)], [_blob(4, 50)]]
    trk = track(bpf, cfg)
    f2 = trk["frames"][2]
    assert f2["missing"] is False
    assert abs(f2["x_px"] - 2.0) < 1e-6


def test_too_far_is_missing():
    """A blob jumping beyond max_disp is treated as a missing frame, not linked."""
    cfg = PipelineConfig(n_frames=3, min_track_len=2, max_disp=5, memory=0)
    bpf = [[_blob(0, 50)], [_blob(100, 50)], [_blob(101, 50)]]
    trk = track(bpf, cfg)
    assert trk["frames"][1]["missing"] is True
    assert trk["frames"][2]["missing"] is True
    assert trk["present_frames"] == 1


def test_short_track_invalid():
    """A track shorter than min_track_len is marked invalid."""
    cfg = PipelineConfig(n_frames=3, min_track_len=5, max_disp=10, memory=0)
    bpf = [[_blob(t, 50)] for t in range(3)]
    assert track(bpf, cfg)["valid"] is False


def test_vertical_rod_orientation_unwrapped():
    """Detection angles near ±90 deg must be unwrapped into a continuous series."""
    cfg = PipelineConfig(n_frames=5, min_track_len=2, max_disp=10, memory=0)
    raw_angles = [89.0, 90.0, -89.0, -88.0, 88.0]  # vertical rod vibrating
    bpf = [[_blob(t, 50, angle=a)] for t, a in enumerate(raw_angles)]
    trk = track(bpf, cfg)
    angles = [f["angle"] for f in trk["frames"]]
    steps = [abs(b - a) for a, b in pairwise(angles)]
    assert max(steps) < 10.0, f"fake orientation jump: {max(steps):.1f} deg"
