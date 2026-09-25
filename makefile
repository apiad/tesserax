.PHONY: all test lint format docs

all: format lint test

test:
# --extra export: two tests exercise the resvg-py/pillow rasterisation path
# and fail with an ImportError without it.
	uv run --extra export pytest --cov=src/tesserax tests/

lint:
	uv run ruff check .
	@command -v rift >/dev/null 2>&1 && rift check || echo "rift not installed — skipping the agent-docs checks"

format:
	uv run ruff format .

docs:
	uv run quarto publish gh-pages docs/
