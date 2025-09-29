.PHONY: install dev test format

install:
pip install -e .[dev]

dev:
uvicorn api.main:app --reload --port 8000

test:
pytest

format:
ruff format

