# Architecture

```text
Parser -> Instruction graph -> Rule engine -> Findings -> Scoring -> Reporters / Fixers
```

```text
src/dockrx/
  cli.py
  context.py
  config.py
  parser/
  engine/
  rules/builtin/
  plugins/
  scoring/
  reporters/
  fixer.py
  formatter.py
```

## Current Scope

DockRx focuses on **static Dockerfile analysis**.

Included now:

- Dockerfile parsing into an instruction graph
- Hybrid rule engine (YAML + Python plugins)
- Health scoring with ROI-prioritized findings
- `analyze` / `explain` / `fix` / `compare` / `badge` / `suggest` / `format`
- JSON output for CI
- GitHub Action with PR commenting
- Project-local rule/plugin overrides via `.dockrx/`

Planned later:

- image inspection and layer-size analysis
- measured (not heuristic) size deltas
- richer auto-fix coverage
- remote rule packs / HTML reports

## Limitations

- Size and build-time estimates are **heuristic**, not measured from builds
- `dockrx fix` / `suggest` only auto-fix a **subset** of rules (others are recommendations)
- `dockrx compare` compares DockRx reports, not real built image sizes
- `dockrx format --write` **overwrites** the Dockerfile in place (unlike `fix`, which writes `Dockerfile.fixed`)
- Not a vulnerability scanner, CVE database, or Hadolint replacement
