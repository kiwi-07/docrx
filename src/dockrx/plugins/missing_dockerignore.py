"""DRX005 — Missing .dockerignore (project context plugin)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dockrx.plugins.base import finding_from_meta

if TYPE_CHECKING:
    from dockrx.context import AnalysisContext
    from dockrx.models import Finding

RULE = {
    "id": "DRX005",
    "title": "Missing .dockerignore",
    "severity": "HIGH",
    "category": "best_practices",
    "tags": ["context", "dockerignore"],
    "applies_to": ["dockerfile", "project"],
    "recommendation": (
        "Add a .dockerignore file next to your Dockerfile to exclude "
        ".git, node_modules, virtualenvs, build artifacts, and secrets "
        "from the build context."
    ),
    "estimated_saving": {
        "build_time": "20-70%",
        "image_size": "context upload often 100MB-1GB+",
        "confidence": "heuristic",
    },
    "reason": "Large build contexts slow every build and risk leaking secrets.",
    "references": [
        "https://docs.docker.com/build/building/context/#dockerignore-files",
    ],
    "pack": "builtin@0.1",
}


def check(ctx: AnalysisContext) -> list[Finding]:
    if ctx.has_dockerignore:
        return []
    return [finding_from_meta(RULE, message="No .dockerignore found in project root")]
