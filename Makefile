.PHONY: install dev test run dry-run clean setup docker-build docker-run

install:
	python3 -m pip install -e .

dev:
	python3 -m pip install -e .[dev]

setup:
	bash bootstrap.sh

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

docker-build:
	docker build -t paper-radar .

docker-run:
	docker run --rm -v $(PWD)/output:/app/output -v $(PWD)/data:/app/data paper-radar
