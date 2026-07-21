# Changelog

All notable changes to DockRx are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.1] — 2026-07-21

### Changed
- Update package author metadata to Ankit Patil (`ankitiips@gmail.com`)
- Sanitize the bundled Java/Maven example and regenerate the README CLI demo
- Refresh installation and release documentation now that DockRx is available on PyPI

## [0.1.0] — 2026-07-21

First public release, published to [PyPI](https://pypi.org/project/dockrx/).

### Added
- Dockerfile parsing into an instruction graph
- Hybrid rule engine (YAML rules + Python plugins)
- Built-in rules covering cache, size, security, and best practices
- Rich terminal reporter with health gauge, ROI prioritization, quick wins
- JSON reporter for CI/automation
- `dockrx analyze` / `explain` / `fix` / `compare` / `badge` / `suggest` / `format`
- Project-local overrides via `.dockrx/rules` and `.dockrx/plugins`
- Project config via `[tool.dockrx]` (`log-level`, `fail-on-severity`, `default-fix-limit`, `health-thresholds`)
- GitHub Action with PR comment upsert and severity gate
- Logging infrastructure
- Web API + live playground ([dockrx.vercel.app](https://dockrx.vercel.app)): `/api/analyze`,
  `/api/fix`, `/api/format`, `/api/compare`, `/api/badge`, and `/api/health` (see `docs/web-api.md`)
- `DOCKRX_CORS_ORIGINS` to restrict CORS origins for the web API (defaults to `*`)
- `has_dockerignore` request field so the analyzer can suppress DRX005 when a `.dockerignore` exists
- Regression test suites for scoring, CLI exit codes, the web API, and the rich reporter

### Changed
- **Scoring:** overall score uses a "spill" model — every finding's penalty counts toward the
  overall score even when its category is already floored at 0, so fixing any finding always moves
  the overall number. Category scores are still displayed floored at 0.
- `analyze` applies `fail-on-severity` consistently across all output modes, including
  `--score-only` and `--badge`
- `analyze` warns (on stderr) when a directory contains more than one Dockerfile

### Fixed
- JSON output no longer corrupted by Rich terminal wrapping
- Plugin loader skips `base.py` helper module
- DRX022 no longer flags correct Go module layering
- DRX002 resolves `FROM $VAR` ARG defaults and skips stage aliases
- DRX003 only requires `USER` in the **final** stage
- DRX014 only flags when the final stage *ends* as root
- DRX004 skips scratch/distroless final images
- YAML `before`/`after` matching stays within the same build stage
- `dockrx suggest --yes` writes `Dockerfile.fixed` without a second prompt
- `analyze` rejects empty or invalid Dockerfiles (no `FROM`) with exit code `2`
- `analyze` treats `--json`, `--score-only`, and `--badge` as mutually exclusive (exit `2`)
- `format` treats `--check`, `--write`, and `--diff` as mutually exclusive (exit `2`)
- `explain` on an unknown rule id now exits `1` (was `2`)
- `fix` / `suggest` refuse to prompt in a non-interactive (no-TTY) environment; require
  `--yes`/`--dry-run`, otherwise exit `2`
