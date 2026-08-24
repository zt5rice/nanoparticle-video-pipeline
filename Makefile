PY := .venv/bin/python

.PHONY: venv install sample run smoke test lint clean

venv:
	python3.11 -m venv .venv

install:
	$(PY) -m pip install -r requirements-dev.txt

sample:
	$(PY) scripts/make_sample_data.py

run:
	$(PY) scripts/run_pipeline.py --config sample_data/config.yaml --out output

smoke:
	$(PY) scripts/smoke_test.py

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check src tests

clean:
	rm -rf output sample_data .pytest_cache .ruff_cache

