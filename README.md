# nanotrack

[![CI](https://github.com/zt5rice/nanoparticle-video-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/zt5rice/nanoparticle-video-pipeline/actions)

Single-molecule nanoparticle video tracking pipeline (SPT), reimplemented from the
author's MATLAB methodology (see `docs/implementation-plan.md` for the decision-complete
spec).

## Overview

**nanotrack** is an end-to-end, single-molecule (SPT) nanoparticle video-tracking
pipeline, re-engineered from the author's MATLAB methodology into a modern Python
data-infrastructure stack — a working-experience project for a Software Development
Engineer specializing in data infrastructure.

- **Computer-vision core** — frame-accurate detection of fast-moving, flexible
  nanoparticles (nanorods, nanosheets, single-walled carbon nanotubes): connected
  components + moment-based ellipse features, three interchangeable preprocessing
  backends (NumPy reference / OpenCV / scikit-image), and mod-180° orientation
  unwrapping so vertical rods track stably without fake ±90° jumps.
- **Parallelism & HPC** — Dask chunked processing with a sequential fallback, plus a
  SLURM batch example that mirrors the original "15 hours → 30 minutes" cluster
  speedup for long (10k-frame) videos.
- **Serving & orchestration** — FastAPI REST API (`/analyze`, `/tracking`), an Airflow
  DAG (`generate → preprocess → detect_track → features_validate → export`), and a
  Docker Compose stack (API / Airflow / Postgres / Prometheus / Grafana).
- **Observability** — Prometheus metrics (frames analyzed, errors, runtime p95) with a
  provisioned Grafana `nanotrack-pipeline` dashboard.
- **Data engineering & reproducibility** — immutable per-run artifacts (raw per-frame
  `tracks.csv` / `detections.csv`, config + ground-truth provenance), checkpoint
  resume (`--resume`), self-contained tracking-QC HTML reports, and tracking-overlay
  videos for visual QA.
- **CI/CD & delivery** — GitHub Actions CI (ruff, pytest, smoke) plus a Docker
  end-to-end job that boots the full stack and validates the Airflow DAG.
- **Research impact** — methods support 12 peer-reviewed publications, including
  ACS Nano and Soft Matter.

The pipeline ships as the `nanotrack` Python package with a CLI, REST API, and
ImageJ-style preprocessing notebook — usable end-to-end on synthetic data or real
fluorescence videos (TIFF / ND2).

> `ref/` (papers + MATLAB source) is local-only and not part of the repository.

## System design

```mermaid
flowchart TB
    subgraph IN["Input"]
        A1["synth.py: 1 molecule/video"]
        A2["real video TIFF / ND2 (io.py)"]
    end
    subgraph CORE["Core pipeline (src/nanotrack)"]
        B1["preprocess (numpy | opencv | skimage)"]
        B2["detect (threshold + CC + ellipse moments)"]
        B3["track (SPT: nearest within max_disp + gap fill)"]
        B4["features (MSD / MSAD / Dt / Dr / shape fluct.)"]
        B5["validate (data-quality checks)"]
        B6["export (JSON / CSV / overlay / QC HTML)"]
    end
    subgraph OPS["Orchestration & serving"]
        C1["Airflow DAG"]
        C2["FastAPI /analyze + /tracking"]
        C3["Dask parallel chunk map"]
    end
    subgraph OBS["Observability"]
        D1["Prometheus"]
        D2["Grafana"]
    end
    A1 --> B1
    A2 --> B1
    B1 --> B2 --> B3 --> B4 --> B5 --> B6
    C3 -.-> B1
    C1 -.-> CORE
    C2 --> D1 --> D2
    B6 --> C2
```

See [`docs/system-design.md`](docs/system-design.md) for the component table and data flow.

## Quick start

```bash
make venv && make install   # create .venv and install dependencies
make smoke                  # end-to-end smoke test (40 frames, 1 molecule)
make sample && make run     # write sample data and run the pipeline
python scripts/run_pipeline.py --input video.tif --out output   # analyze a real video
python scripts/run_pipeline.py --out output --resume            # rebuild from detections.csv
python scripts/run_pipeline.py --input video.tif --out output --overlay  # + trajectory overlay video
```

Each run also writes `output/tracking_report.html` — a self-contained tracking-QC
dashboard (trajectory, x/y vs frame, angle vs frame, MSD). With the API up, open
`http://localhost:8000/tracking`.

### Docker stack (local)

```bash
mkdir -p output && chmod -R 777 output   # Airflow runs as a non-root user
docker compose up --build
```

Services: API `:8000`, Airflow `:8080`, Prometheus `:9090`, Grafana `:3000`.

## Example outputs

**Observability & orchestration stack** (simulated previews with sample data; see the
real stack via `docker compose up` — Airflow `:8080`, Prometheus `:9090`, Grafana
`:3000`):

![Grafana nanotrack-pipeline dashboard](docs/assets/grafana_preview.png)

![Apache Airflow DAG](docs/assets/airflow_preview.png)

![Prometheus targets & graph](docs/assets/prometheus_preview.png)

**Tracking QC report** — an interactive HTML report is written to
`output/tracking_report.html` after every run (trajectory overlaid on the first frame,
x/y vs frame, unwrapped angle in deg vs frame, MSD/MSAD vs lag on log-log (base 10)
axes, and a run summary). Static preview:

![Tracking QC report](docs/assets/tracking_qc_preview.png)

**Tracking QC report — 10,000-frame real video (parallel/perpendicular MSD trend)** —
the full 3×2 QC report from a 10,000-frame single-molecule SWCNT video
(`--max-lag 5000`). The MSD panel shows the Fakhri et al. (Science 2010)
parallel/perpendicular MSD regimes: anisotropic short-time `Δs² >> Δn²`, the
super-linear crossover `Δn² ~ D∥·D_r·t²`, and the onset of isotropic convergence
beyond `τ_r = 1/(2D_r)`. Demo video courtesy of Fakhri et al., Science 2010 —
please cite the source paper (see [Citation](#citation)):

![Tracking QC report — 10k-frame par/perp MSD trend](docs/assets/tracking_report_nt3_full.png)

**Tracking overlay video** — `--overlay` draws the tracked trajectory and orientation
onto the input video (`output/tracking_overlay.mp4`, or `.gif` / `.png` via
`--overlay-format`). Example on a single-molecule (vertical-rod) video:

![Tracking overlay on a single-molecule video](docs/assets/tracking_overlay.gif)

## Citation

If you use this tool in your work, please cite the methodology paper:

> Z. Tang, S. L. Eichmann, B. Lounis, L. Cognet, F. C. MacKintosh, M. Pasquali,
> *Single-walled carbon nanotube reptation dynamics in submicron sized pores from
> randomly packed mono-sized colloids*, Soft Matter **2022**.
> DOI: [10.1039/D2SM00305H](https://doi.org/10.1039/D2SM00305H)

The 10,000-frame demo video in the example outputs is from:

> N. Fakhri, F. C. MacKintosh, B. Lounis, L. Cognet, M. Pasquali,
> *Brownian Motion of Stiff Filaments in a Crowded Environment*, Science **2010**,
> 330 (6012), 1804–1807.
> DOI: [10.1126/science.1197321](https://doi.org/10.1126/science.1197321)

## Layout

```
src/nanotrack/   core package
scripts/         CLI entrypoints
tests/           pytest suite
docs/            implementation plan + system design
```
