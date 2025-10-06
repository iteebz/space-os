default:
    @just --list

install:
    @poetry install

test:
    @poetry run python -m pytest tests -v

format:
    @poetry run ruff format .

lint:
    @poetry run ruff check .

fix:
    @poetry run ruff check . --fix --unsafe-fixes

build:
    @poetry build

clean:
    @rm -rf dist build .pytest_cache .ruff_cache __pycache__
    @find . -type d -name "__pycache__" -exec rm -rf {} +
    @rm -f .space/apps/*.db

ci: format fix test build