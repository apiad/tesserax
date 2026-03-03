.PHONY: all test lint format docs

all: format lint test

test:
	uv run pytest --cov=src/tesserax tests/

lint:
	uv run ruff check .

format:
	uv run ruff format .

docs:
	quarto publish gh-pages docs/
