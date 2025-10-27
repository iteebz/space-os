default:
    @just --list

clean:
    @echo "Cleaning space-os..."
    @rm -rf dist build .pytest_cache .ruff_cache __pycache__ .venv
    @find . -type d -name "__pycache__" -exec rm -rf {} +

install:
    @poetry lock
    @poetry install

ci: format fix test build

test:
    @PYTHONPATH=$(pwd) poetry run python -m pytest tests -q

format:
    @poetry run ruff format .

lint:
    @poetry run ruff check .

fix:
    @poetry run ruff check . --fix --unsafe-fixes

build:
    @poetry build

commits:
    @git --no-pager log --pretty=format:"%h | %ar | %s"
