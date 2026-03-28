.PHONY: install dev test run dry-run clean

install:
	python3 -m pip install -e .

dev:
	python3 -m pip install -e .[dev]

test:
	python3 -m pytest

run:
	python3 scripts/main.py

dry-run:
	python3 scripts/main.py --dry-run

clean:
	rm -f data/radar.db
	rm -f data/raw/*.json
	rm -f data/processed/*.json
	rm -f output/*.md
	rm -f logs/*.log
