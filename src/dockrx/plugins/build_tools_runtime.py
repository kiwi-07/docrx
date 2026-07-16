"""DRX026 — Compilers and build toolchains in runtime stage."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from dockrx.plugins.base import finding_from_meta

if TYPE_CHECKING:
    from dockrx.context import AnalysisContext
    from dockrx.models import Finding

RULE = {
    "id": "DRX026",
    "title": "Compilers installed in runtime stage",
    "severity": "HIGH",
    "category": "size",
    "tags": ["apt", "build-tools", "gcc"],
    "applies_to": ["dockerfile"],
    "recommendation": (
        "Move gcc, g++, make, cmake, and similar build toolchains into a "
        "builder stage. Runtime images should only ship binaries and runtime "
        "libraries required to execute the application."
    ),
    "estimated_saving": {
        "image_size": "~50-200 MB",
        "confidence": "heuristic",
    },
    "reason": "Compilers belong in build stages, not production runtime layers.",
    "references": [
        "https://docs.docker.com/build/building/multi-stage/",
    ],
    "pack": "builtin@0.1",
}

BUILD_TOOL_RE = re.compile(
    r"apt(-get)?\s+install.*("
    r"\bgcc\b|\bg\+\+\b|\bmake\b|\bcmake\b|\bbuild-essential\b|"
    r"\bmaven\b|\bgradle\b|\bautoconf\b|\bautomake\b"
    r")",
    re.IGNORECASE,
)


def check(ctx: AnalysisContext) -> list[Finding]:
    final = ctx.graph.final_stage
    if not final:
        return []

    for instr in ctx.graph.instructions:
        if instr.stage != final or instr.instruction != "RUN":
            continue
        if BUILD_TOOL_RE.search(instr.args):
            return [
                finding_from_meta(
                    RULE,
                    message="Build toolchain packages installed via apt in final stage",
                    line=instr.line,
                    stage=instr.stage,
                )
            ]
    return []
