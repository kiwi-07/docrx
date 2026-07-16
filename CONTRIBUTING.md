# Contributing

Thank you for considering contributing to DockRx!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/kiwi-07/docrx.git
cd dockrx

# Sync dependencies
uv sync --group dev

# Install pre-commit hooks
uv run pre-commit install
```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage (soft gate at 60%; richer coverage is ongoing)
uv run pytest --cov=dockrx --cov-report=term-missing

# Run a specific test
uv run pytest tests/test_parser.py -v
```

## Code Quality

We use ruff for linting and formatting:

```bash
# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Type-check
uv run pyright src/ tests/
```

## Project Structure

```
src/dockrx/
  cli.py              — CLI entry point (typer)
  context.py          — Analysis context builder
  config.py           — [tool.dockrx] config loading
  log.py              — logging setup
  models.py           — Pydantic data models
  fixer.py            — Non-destructive fix logic
  formatter.py        — Dockerfile formatter
  parser/             — Dockerfile → instruction graph
  engine/             — Rule engine + matcher
  rules/builtin/      — YAML rule definitions
  plugins/            — Python plugin checks
  scoring/            — Severity-based scoring
  reporters/          — Terminal, JSON, compare, explain, badge
```

## Adding a Rule

See [docs/extending.md](docs/extending.md) for the full guide.

Quick summary:

1. **YAML rule**: add `src/dockrx/rules/builtin/DRXNNN_name.yaml`
2. **Python plugin**: add `src/dockrx/plugins/name.py`
3. Write tests in `tests/`
4. Add presentation entry in `src/dockrx/reporters/presentation.py`

## Pull Request Guidelines

- Write clear commit messages
- Add tests for new rules or fixes
- Run `ruff check` and `pytest` before pushing
- Keep PRs focused on a single concern
