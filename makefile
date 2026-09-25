.PHONY: all test lint format docs

all: format lint test

test:
	uv run pytest --cov=src/tesserax tests/

lint:
	uv run ruff check .
	@command -v rift >/dev/null 2>&1 && rift check || echo "rift not installed — skipping the agent-docs checks"

format:
	uv run ruff format .

docs:
	uv run quarto publish gh-pages docs/
