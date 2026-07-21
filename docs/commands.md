# Commands

DockRx currently ships **seven commands** plus a global `--version` flag.

| Command | Purpose |
|---------|---------|
| [`dockrx analyze`](#dockrx-analyze) | Analyze a Dockerfile and print a health report |
| [`dockrx explain`](#dockrx-explain) | Explain a rule by ID |
| [`dockrx fix`](#dockrx-fix) | Preview and apply deterministic fixes |
| [`dockrx compare`](#dockrx-compare) | Compare two Dockerfiles before/after |
| [`dockrx badge`](#dockrx-badge) | Generate a health-grade badge |
| [`dockrx suggest`](#dockrx-suggest) | Walk through fixes interactively |
| [`dockrx format`](#dockrx-format) | Format a Dockerfile for consistent style |
| [`dockrx --version`](#dockrx---version) | Print the installed version |

---

## `dockrx analyze`

Analyze a Dockerfile path or project directory.

```bash
dockrx analyze .
dockrx analyze Dockerfile
dockrx analyze services/api/
dockrx analyze . --json
dockrx analyze . --score-only
dockrx analyze . --badge
```

Options:

| Flag | Description |
|------|-------------|
| `--json` | Emit a machine-readable JSON report |
| `--score-only` | Print only the overall score (integer) |
| `--badge` | Print an SVG health badge instead of the full report |

`--json`, `--score-only`, and `--badge` are **mutually exclusive** — passing more than one exits with code `2`.

What it prints (default mode):

- overall health gauge and grade
- quick wins
- lost points
- estimated results
- treatment plan
- category breakdown
- detailed findings sorted by ROI

Exit behavior (applies to **all** output modes, including `--score-only` and `--badge`):

- exits with code `1` when findings meet `[tool.dockrx] fail-on-severity` (default: `HIGH`)
- exits with code `2` when the Dockerfile path cannot be resolved, is empty, or is not a valid Dockerfile (no `FROM` instruction)
- exits with code `0` otherwise

When a directory contains more than one Dockerfile, DockRx analyzes the primary one and prints a warning to stderr listing the others.

Size/build estimates in the report are heuristic (not measured from builds).

## `dockrx explain`

Explain a rule id and show why it matters, estimated impact, references, and a suggested fix.

```bash
dockrx explain DRX018
dockrx explain DRX003
dockrx explain DRX018 --path .
```

Options:

| Flag | Description |
|------|-------------|
| `--path`, `-p` | Project path for loading local rule overrides |

Exit behavior:

- exits with code `1` when the rule id is unknown
- exits with code `0` when the rule is found and explained

## `dockrx fix`

Preview and apply a small set of deterministic fixes. DockRx never overwrites the original Dockerfile; it writes `Dockerfile.fixed`.

Only a **subset** of rules have auto-fix handlers today. Other findings remain recommendations.

```bash
dockrx fix .
dockrx fix . --dry-run --yes
dockrx fix . --yes
dockrx fix . --limit 5
```

Options:

| Flag | Description |
|------|-------------|
| `--limit` | Max number of fixes to apply (default: config `default-fix-limit` or `3`) |
| `--yes` | Apply changes without prompting |
| `--dry-run` | Show preview only; do not write any files |

In a non-interactive environment (no TTY, e.g. CI or a pipe), `fix` requires `--yes` or `--dry-run`; without one it refuses to prompt and exits with code `2`.

Current fix support includes:

- JDK runtime -> JRE runtime
- adding non-root `USER`
- removing debug networking packages from runtime images
- converting shell `ENTRYPOINT exec ...` into a safer wrapper
- adding `HEALTHCHECK`
- creating `.dockerignore` when missing

## `dockrx compare`

Compare two Dockerfiles or project directories and show score, grade, category, and finding deltas.

```bash
dockrx compare before/ after/
dockrx compare before.Dockerfile after.Dockerfile
dockrx compare before/ after/ --json
```

Options:

| Flag | Description |
|------|-------------|
| `--json` | Emit a machine-readable JSON comparison |

What it prints:

- score delta
- grade delta
- category delta table
- estimated outcome delta
- resolved findings
- newly introduced findings

## `dockrx badge`

Generate a health-grade badge for a Dockerfile.

```bash
dockrx badge .
dockrx badge Dockerfile --output badge.svg
dockrx badge . --format markdown
dockrx badge . --format url --style for-the-badge
dockrx badge . --label MyProject
```

Options:

| Flag | Description |
|------|-------------|
| `--output`, `-o` | Write badge to file instead of stdout |
| `--format`, `-f` | Output format: `svg`, `markdown`, `url` (alias: `shield-url`; default: `svg`) |
| `--style`, `-s` | Badge style: `flat`, `flat-square`, `plastic`, `for-the-badge` |
| `--label`, `-l` | Left-side label text (default: `DockRx`) |

## `dockrx suggest`

Walk through fix suggestions interactively (same fix handlers as `dockrx fix`).

```bash
dockrx suggest .
dockrx suggest . --yes
```

Options:

| Flag | Description |
|------|-------------|
| `--yes` | Apply all suggestions and write `Dockerfile.fixed` without prompting |

Without `--yes`, for each fixable finding you can apply, skip, or quit, then confirm writing `Dockerfile.fixed`. In a non-interactive environment (no TTY), `suggest` requires `--yes`; without it, it refuses to prompt and exits with code `2`.

## `dockrx format`

Format a Dockerfile for consistent style (instruction casing, whitespace, stage spacing).

```bash
dockrx format Dockerfile
dockrx format . --write
dockrx format Dockerfile --check
dockrx format Dockerfile --diff
```

Options:

| Flag | Description |
|------|-------------|
| `--write`, `-w` | **Overwrite the Dockerfile in place** (destructive — unlike `fix`) |
| `--check` | Exit with code `1` if formatting is needed (CI-friendly) |
| `--diff` | Show a unified diff of changes |

`--check`, `--write`, and `--diff` are **mutually exclusive** — passing more than one exits with code `2`. With no mode flag, `format` prints the formatted Dockerfile to stdout.

Prefer `--check` / `--diff` in CI. Use `--write` only when you intend to modify the original file.

## `dockrx --version`

Print the installed DockRx version.

```bash
dockrx --version
```

## Exit Codes

Exit codes are a stable public contract intended for scripting and CI:

| Code | Meaning |
|------|---------|
| `0` | Success — no failing findings, or a non-analyze command completed normally |
| `1` | Analysis threshold reached (`analyze` found issues at/above `fail-on-severity`), formatting needed (`format --check`), or an unknown rule id (`explain`) |
| `2` | Usage or input error — path not found, empty/invalid Dockerfile (no `FROM`), mutually-exclusive flags combined, or an interactive command run without a TTY and without `--yes`/`--dry-run` |

Per-command specifics are noted in each section above.

## Configuration

Optional settings in the analyzed project's `pyproject.toml`:

```toml
[tool.dockrx]
log-level = "WARNING"
fail-on-severity = "HIGH"    # HIGH | MEDIUM | LOW | INFO | none
default-fix-limit = 3
health-thresholds = { excellent = 90, good = 75, fair = 60, needs-attention = 40 }
```

## JSON Output

Use JSON output for CI, dashboards, or scripting:

```bash
dockrx analyze . --json
dockrx compare before/ after/ --json
```

`analyze --json` includes:

- score and health label
- diagnosis summary
- category breakdown with explanations
- ranked recommendations
- suggested fixes
- estimated savings

`compare --json` includes:

- before/after score and grade
- category deltas
- resolved rule IDs
- newly introduced rule IDs

## Web API

DockRx also exposes an HTTP API (the same engine as the CLI) that powers the live playground at
[dockrx.vercel.app](https://dockrx.vercel.app). See [`web-api.md`](web-api.md) for endpoints,
request/response shapes, limits, and the `DOCKRX_CORS_ORIGINS` setting.
