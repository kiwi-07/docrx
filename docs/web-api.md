# Web API

DockRx ships a small HTTP API (FastAPI) that powers the live playground at
[dockrx.vercel.app](https://dockrx.vercel.app) and can be called directly by external clients.

It analyzes Dockerfile **text** — nothing is written to your project. Each request runs in a
throwaway temporary directory that is deleted afterward.

## Running it locally

```bash
uv sync --group dev
uv run uvicorn api.index:app --reload
# open http://127.0.0.1:8000  (UI)  ·  http://127.0.0.1:8000/api/docs  (OpenAPI)
```

Interactive OpenAPI docs are served at `/api/docs` unless disabled with
`DOCKRX_ENABLE_DOCS=0`.

## Conventions

- All analyze-style endpoints accept a `dockerfile` string (1–200,000 chars) and an optional
  `filename` (defaults to `Dockerfile`; unsafe names are coerced back to `Dockerfile`).
- `has_dockerignore: true` tells the analyzer the project already ships a `.dockerignore`, which
  suppresses `DRX005`.
- Text that does not contain a `FROM` instruction returns **422**.
- Blank/oversized input returns **422** (Pydantic validation).
- Unexpected server errors return **500** with a generic message.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET`  | `/api/health` | Liveness probe (`{"status":"ok",...}`) |
| `POST` | `/api/analyze` | Full JSON health report (same shape as `analyze --json`) |
| `POST` | `/api/fix` | Preview deterministic fixes (available fixes, applied rules, fixed Dockerfile, diff) |
| `POST` | `/api/format` | Format the Dockerfile text and return the result + diff |
| `POST` | `/api/compare` | Compare two Dockerfiles (same shape as `compare --json`) |
| `POST` | `/api/badge` | Return `svg`, `markdown`, and shields.io `url` badge outputs |

> The current web UI only calls `/api/analyze`. The other endpoints are a supported programmatic
> surface (covered by `tests/test_api.py`); the browser playground intentionally stays analyze-only.

### `POST /api/analyze`

```jsonc
// request
{ "dockerfile": "FROM python:3.12\n...", "filename": "Dockerfile", "has_dockerignore": false }
```

Returns the same JSON document as `dockrx analyze --json` (score, health label, category
breakdown, ranked recommendations, suggested fixes, estimated savings).

### `POST /api/fix`

```jsonc
// request
{ "dockerfile": "FROM alpine:3.20\nCMD [\"true\"]\n", "rule_ids": ["DRX004"] }
```

`rule_ids` is optional; omit it to apply every available deterministic fix. Only IDs matching
`DRX\d{3}` are honored. Response includes `available_fixes`, `applied_rule_ids`, `dockerfile`
(fixed text), `diff`, and `.dockerignore` details.

### `POST /api/compare`

```jsonc
// request
{ "before": "FROM ...", "after": "FROM ...",
  "before_has_dockerignore": false, "after_has_dockerignore": false }
```

### `POST /api/badge`

```jsonc
// request
{ "dockerfile": "FROM ...", "label": "DockRx", "style": "flat" }
```

`style` is one of `flat`, `flat-square`, `plastic`, `for-the-badge`.

## CORS

CORS is enabled so the API can be called from other origins and to answer `OPTIONS` preflight.
It defaults to `*` (fine for a public analyze API). To lock it down, set a comma-separated
allowlist:

```bash
export DOCKRX_CORS_ORIGINS="https://example.com,https://app.example.com"
```

## Limits

- Max Dockerfile size: 200,000 characters per field.
- `filename` max length 128; only `Dockerfile`, `Containerfile`, or `*.dockerfile` names are kept.
- `rule_ids` max 30 entries.
