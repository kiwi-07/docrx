"""DockRx web API — analyze a Dockerfile from text (Vercel / local)."""

from __future__ import annotations

import difflib
import json
import logging
import os
import re
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel, Field, field_validator

# Allow importing the local package when deployed from the monorepo root.
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
_STATIC = Path(__file__).resolve().parent / "static"
_PUBLIC = _ROOT / "public"

if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dockrx.engine import analyze  # noqa: E402
from dockrx.fixer import FIX_HANDLERS, build_fix_plan  # noqa: E402
from dockrx.formatter import format_dockerfile  # noqa: E402
from dockrx.models import AnalysisReport  # noqa: E402
from dockrx.reporters.badge import render_badge  # noqa: E402
from dockrx.reporters.compare import render_compare_json  # noqa: E402
from dockrx.reporters.json_report import render_json  # noqa: E402
from dockrx.scoring import score_findings  # noqa: E402

logger = logging.getLogger("dockrx.api")

MAX_DOCKERFILE_CHARS = 200_000
_SAFE_FILENAME = re.compile(r"^(Dockerfile|Containerfile|[A-Za-z0-9._-]+\.dockerfile)$", re.IGNORECASE)
_STATIC_HEADERS = {"Cache-Control": "public, max-age=300"}

_enable_docs = os.getenv("DOCKRX_ENABLE_DOCS", "1").lower() not in {"0", "false", "no"}

app = FastAPI(
    title="DockRx",
    version="0.1.1",
    docs_url="/api/docs" if _enable_docs else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if _enable_docs else None,
)

# CORS: same-origin browser calls don't need this, but re-enabling it keeps the
# /api/analyze endpoint usable from external clients and answers OPTIONS preflight.
# Restrict via DOCKRX_CORS_ORIGINS (comma-separated) or default to "*".
_cors_origins = [o.strip() for o in os.getenv("DOCKRX_CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    dockerfile: str = Field(..., min_length=1, max_length=MAX_DOCKERFILE_CHARS)
    filename: str = Field(default="Dockerfile", max_length=128)
    has_dockerignore: bool = Field(
        default=False,
        description="Set true if the project already ships a .dockerignore (suppresses DRX005).",
    )

    @field_validator("dockerfile")
    @classmethod
    def dockerfile_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Dockerfile is empty.")
        return value

    @field_validator("filename")
    @classmethod
    def filename_safe(cls, value: str) -> str:
        name = Path(value).name
        if not name or not _SAFE_FILENAME.match(name):
            return "Dockerfile"
        return name


class FixRequest(AnalyzeRequest):
    rule_ids: list[str] | None = Field(
        default=None,
        max_length=30,
        description="Optional deterministic rule IDs to apply. Omit to apply every available fix.",
    )

    @field_validator("rule_ids")
    @classmethod
    def rule_ids_safe(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [rid.upper() for rid in value if re.fullmatch(r"DRX\d{3}", rid.upper())]


class CompareRequest(BaseModel):
    before: str = Field(..., min_length=1, max_length=MAX_DOCKERFILE_CHARS)
    after: str = Field(..., min_length=1, max_length=MAX_DOCKERFILE_CHARS)
    before_has_dockerignore: bool = False
    after_has_dockerignore: bool = False

    @field_validator("before", "after")
    @classmethod
    def dockerfile_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Dockerfile is empty.")
        return value


class BadgeRequest(AnalyzeRequest):
    label: str = Field(default="DockRx", min_length=1, max_length=40)
    style: str = Field(default="flat", pattern=r"^(flat|flat-square|plastic|for-the-badge)$")


def _report_for_text(
    text: str,
    name: str,
    root: Path,
    *,
    has_dockerignore: bool,
) -> AnalysisReport:
    path = root / name
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8")
    if has_dockerignore:
        (root / ".dockerignore").write_text("# provided via API\n", encoding="utf-8")
    ctx, findings = analyze(path)
    if not ctx.graph.has_from:
        raise HTTPException(
            status_code=422,
            detail="This does not look like a Dockerfile (no FROM instruction found).",
        )
    return AnalysisReport(
        path=name,
        score=score_findings(findings),
        findings=findings,
        instruction_count=len(ctx.graph.instructions),
        stage_count=len(ctx.graph.stages),
    )


def _unified_diff(before: str, after: str, after_name: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile="Dockerfile",
            tofile=after_name,
            lineterm="",
        )
    )


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
    return FileResponse(path, media_type="text/html; charset=utf-8", headers=_STATIC_HEADERS)


@app.get("/app.js")
def script() -> Response:
    path = _asset("app.js")
    if path is None:
        raise HTTPException(status_code=404, detail="app.js not found")
    return FileResponse(path, media_type="text/javascript; charset=utf-8", headers=_STATIC_HEADERS)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "dockrx", "version": "0.1.1"}


@app.post("/api/analyze")
def analyze_dockerfile(body: AnalyzeRequest) -> dict:
    try:
        with tempfile.TemporaryDirectory(prefix="dockrx-") as tmp:
            report = _report_for_text(
                body.dockerfile,
                body.filename,
                Path(tmp),
                has_dockerignore=body.has_dockerignore,
            )
            return json.loads(render_json(report))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail="Analysis failed. Please try again.") from None


@app.post("/api/fix")
def fix_dockerfile(body: FixRequest) -> dict:
    """Preview deterministic fixes without mutating the user's project."""
    try:
        with tempfile.TemporaryDirectory(prefix="dockrx-fix-") as tmp:
            root = Path(tmp)
            report = _report_for_text(
                body.dockerfile,
                body.filename,
                root,
                has_dockerignore=body.has_dockerignore,
            )
            available_ids = {h.rule_id for h in FIX_HANDLERS} | {"DRX005"}
            available = [
                {
                    "id": finding.rule_id,
                    "title": finding.title,
                    "severity": finding.severity.value,
                }
                for finding in report.findings
                if finding.rule_id in available_ids
            ]
            plan = build_fix_plan(
                root / body.filename,
                limit=30,
                selected_rule_ids=body.rule_ids,
            )
            return {
                "available_fixes": available,
                "applied_rule_ids": plan.applied_rule_ids,
                "dockerfile": plan.dockerfile_after,
                "diff": plan.dockerfile_diff,
                "dockerignore": plan.dockerignore_after,
                "dockerignore_added": plan.dockerignore_added,
            }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Fix preview failed")
        raise HTTPException(status_code=500, detail="Fix preview failed. Please try again.") from None


@app.post("/api/format")
def format_dockerfile_api(body: AnalyzeRequest) -> dict:
    """Format Dockerfile text and return a preview."""
    with tempfile.TemporaryDirectory(prefix="dockrx-format-") as tmp:
        _report_for_text(
            body.dockerfile,
            body.filename,
            Path(tmp),
            has_dockerignore=body.has_dockerignore,
        )
    formatted = format_dockerfile(body.dockerfile)
    return {
        "changed": formatted != body.dockerfile,
        "dockerfile": formatted,
        "diff": _unified_diff(body.dockerfile, formatted, "Dockerfile.formatted"),
    }


@app.post("/api/compare")
def compare_dockerfiles(body: CompareRequest) -> dict:
    """Compare two pasted Dockerfiles using the same report model as the CLI."""
    with tempfile.TemporaryDirectory(prefix="dockrx-before-") as before_tmp:
        before = _report_for_text(
            body.before,
            "Dockerfile",
            Path(before_tmp),
            has_dockerignore=body.before_has_dockerignore,
        )
    with tempfile.TemporaryDirectory(prefix="dockrx-after-") as after_tmp:
        after = _report_for_text(
            body.after,
            "Dockerfile",
            Path(after_tmp),
            has_dockerignore=body.after_has_dockerignore,
        )
    return json.loads(render_compare_json(before, after))


@app.post("/api/badge")
def badge_dockerfile(body: BadgeRequest) -> dict:
    """Generate SVG, markdown, and shields.io badge outputs."""
    with tempfile.TemporaryDirectory(prefix="dockrx-badge-") as tmp:
        report = _report_for_text(
            body.dockerfile,
            body.filename,
            Path(tmp),
            has_dockerignore=body.has_dockerignore,
        )
    args = {
        "style": body.style,
        "label": body.label,
        "findings_count": len(report.findings),
    }
    return {
        "score": report.score.overall,
        "svg": render_badge(report.score.overall, format="svg", **args),
        "markdown": render_badge(report.score.overall, format="markdown", **args),
        "url": render_badge(report.score.overall, format="url", **args),
    }
