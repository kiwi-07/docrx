# Changelog

All notable changes to DockRx are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-07-16

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
