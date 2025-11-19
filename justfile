default:
    @just --list

clean:
    @echo "Cleaning space-os..."
    @rm -rf dist build .pytest_cache .ruff_cache __pycache__ .venv
    @find . -type d -name "__pycache__" -exec rm -rf {} +
    @cd web && just clean

install:
    @poetry lock
    @poetry install
    @cd web && pnpm install

ci:
    @poetry run ruff format .
    @poetry run ruff check . --fix --unsafe-fixes
    @python -m pytest tests -q
    @poetry build
    @cd web && just ci

test:
    @python -m pytest tests
    @cd web && pnpm test

format:
    @poetry run ruff format .
    @cd web && pnpm format

lint:
    @poetry run ruff check .
    @cd web && pnpm lint

fix:
    @poetry run ruff check . --fix --unsafe-fixes

build:
    @poetry build
    @cd web && pnpm build

dev:
    @echo "Starting API server and web UI..."
    @poetry run space-api & cd web && pnpm dev

commits:
    @git --no-pager log --pretty=format:"%h | %ar | %s"
