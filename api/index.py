"""DockRx web API — analyze a Dockerfile from text (Vercel / local)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel, Field

# Allow importing the local package when deployed from the monorepo root.
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
_STATIC = Path(__file__).resolve().parent / "static"
_PUBLIC = _ROOT / "public"

if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dockrx.engine import analyze  # noqa: E402
from dockrx.models import AnalysisReport  # noqa: E402
from dockrx.reporters.json_report import render_json  # noqa: E402
from dockrx.scoring import score_findings  # noqa: E402

MAX_DOCKERFILE_CHARS = 200_000

app = FastAPI(title="DockRx", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    dockerfile: str = Field(..., min_length=1, max_length=MAX_DOCKERFILE_CHARS)
    filename: str = Field(default="Dockerfile", max_length=128)


def _asset(*names: str) -> Path | None:
    # Prefer the function-local copy (filled by Vercel build script from public/).
    for base in (_STATIC, _PUBLIC):
        path = base.joinpath(*names)
        if path.is_file():
            return path
    return None


@app.get("/", response_class=HTMLResponse)
def home() -> Response:
    path = _asset("index.html")
    if path is None:
        raise HTTPException(status_code=404, detail="UI not found")
    return FileResponse(path, media_type="text/html; charset=utf-8")


@app.get("/app.js")
def script() -> Response:
    path = _asset("app.js")
    if path is None:
        raise HTTPException(status_code=404, detail="app.js not found")
    return FileResponse(path, media_type="text/javascript; charset=utf-8")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "dockrx"}


@app.post("/api/analyze")
def analyze_dockerfile(body: AnalyzeRequest) -> dict:
    text = body.dockerfile.replace("\r\n", "\n")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Dockerfile is empty.")

    name = Path(body.filename).name or "Dockerfile"

    try:
        with tempfile.TemporaryDirectory(prefix="dockrx-") as tmp:
            root = Path(tmp)
            path = root / name
            path.write_text(text, encoding="utf-8")
            ctx, findings = analyze(path)
            report = AnalysisReport(
                path=name,
                score=score_findings(findings),
                findings=findings,
                instruction_count=len(ctx.graph.instructions),
                stage_count=len(ctx.graph.stages),
            )
            return json.loads(render_json(report))
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — surface as API error for the UI
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc
