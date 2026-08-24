"""Connected-component detection with moment-based ellipse features.

Ports ``localmaxFlow`` semantics: hole fill, 8-connected components, masscut filter,
binary centroid, second-moment orientation, MajorAxisLength / MinorAxisLength /
Eccentricity (regionprops formulas).
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import binary_fill_holes

from .config import PipelineConfig


def label_components(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """Two-pass union-find connected-component labeling (8-connectivity)."""
    h, w = mask.shape
    lab = np.zeros((h, w), dtype=np.int32)
    parent: dict[int, int] = {}

    # Union-find helpers (with path compression) used to merge adjacent labels.
    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # Pass 1: assign provisional labels; union any label that is 8-connected to a
    # previously assigned neighbor (top-left, top, top-right, left).
    nxt = 1
    for y in range(h):
        for x in range(w):
            if not mask[y, x]:
                continue
            nbrs: list[int] = []
            for dy, dx in ((-1, -1), (-1, 0), (-1, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if ny >= 0 and nx >= 0 and ny < h and nx < w and lab[ny, nx] > 0:
                    nbrs.append(lab[ny, nx])
            if nbrs:
                m = min(nbrs)
                lab[y, x] = m
                for nb in nbrs:
                    union(m, nb)
            else:
                parent[nxt] = nxt
                lab[y, x] = nxt
                nxt += 1

    # Pass 2: collapse provisional labels to consecutive roots 1..K via union-find.
    roots: dict[int, int] = {}
    out = np.zeros_like(lab)
    k = 1
    for y in range(h):
        for x in range(w):
            if lab[y, x]:
                r = find(lab[y, x])
                if r not in roots:
                    roots[r] = k
                    k += 1
                out[y, x] = roots[r]
    return out, k - 1


def detect(mask: np.ndarray, cfg: PipelineConfig) -> list[dict]:
    """Return blob dicts sorted by area descending (largest first = primary)."""

    # Step 1 — Fill holes in the binary mask (port of MATLAB ``imfill``).
    filled = binary_fill_holes(mask)

    # Step 2 — Label 8-connected components (port of MATLAB ``bwlabel``).
    labels, n = label_components(filled)
    blobs: list[dict] = []

    # Step 3 — Extract moment-based ellipse features per component.
    for comp in range(1, n + 1):
        ys, xs = np.nonzero(labels == comp)
        if len(ys) == 0:
            continue

        # Area = number of foreground pixels in the component.
        area = float(len(ys))

        # Masscut filter (localmaxFlow): reject tiny components whose bounding-box
        # extent (max-min in x plus max-min in y) is not larger than min_feature_size.
        extent = float(xs.max() - xs.min() + ys.max() - ys.min())
        if extent <= cfg.min_feature_size:
            continue

        # Centroid = mean of the bright-pixel coordinates (binary center of mass).
        cx = float(xs.mean())
        cy = float(ys.mean())

        # Second central moments of the pixel distribution (regionprops semantics).
        Mxx = float(np.mean((xs - cx) ** 2))
        Myy = float(np.mean((ys - cy) ** 2))
        Mxy = float(np.mean((xs - cx) * (ys - cy)))

        # Orientation (deg) from the moment matrix: 0.5 * atan2(2*Mxy, Mxx - Myy).
        angle = float(np.degrees(0.5 * np.arctan2(2.0 * Mxy, Mxx - Myy)))

        # Major/minor axis lengths from covariance eigenvalues
        # (regionprops: axis length = 4 * sqrt(eigenvalue)).
        disc = np.sqrt(max(0.0, ((Mxx - Myy) / 2.0) ** 2 + Mxy * Mxy))
        tr = Mxx + Myy
        l1 = max(tr / 2.0 + disc, 0.0)
        l2 = max(tr / 2.0 - disc, 1e-12)
        major = 4.0 * np.sqrt(l1)
        minor = 4.0 * np.sqrt(l2)

        # Eccentricity from the eigenvalue ratio (0 = circle, 1 = line).
        ecc = float(np.sqrt(1.0 - l2 / l1) if l1 > 0 else 0.0)
        blobs.append(
            {
                "id": comp,
                "x": cx,
                "y": cy,
                "angle": angle,
                "length": float(major),
                "width": float(minor),
                "area": area,
                "eccentricity": ecc,
            }
        )

    # Step 4 — Sort by area descending so blobs[0] is the primary object (SPT).
    blobs.sort(key=lambda b: b["area"], reverse=True)
    return blobs
