# nanotrack

Single-molecule nanoparticle video tracking pipeline (SPT), reimplemented from the
author's MATLAB methodology (see `docs/implementation-plan.md` for the decision-complete
spec).

> Status: Phase 1 in progress — core NumPy pipeline. `ref/` (papers + MATLAB source) is
> local-only and not part of the repository.

## Quick start

```bash
make venv && make install   # create .venv and install dependencies
make smoke                  # end-to-end smoke test (40 frames, 1 molecule)
make sample && make run     # write sample data and run the pipeline
```

## Layout

```
src/nanotrack/   core package
scripts/         CLI entrypoints
tests/           pytest suite
docs/            implementation plan + system design
```
