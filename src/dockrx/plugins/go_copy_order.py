"""DRX022 — Go build after full source COPY without go.mod layer."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from dockrx.plugins.base import finding_from_meta

if TYPE_CHECKING:
    from dockrx.context import AnalysisContext
    from dockrx.models import Finding

RULE = {
    "id": "DRX022",
    "title": "COPY before Go module download",
    "severity": "HIGH",
    "category": "cache",
    "tags": ["golang", "go", "caching"],
    "applies_to": ["dockerfile"],
    "recommendation": (
        "Copy go.mod and go.sum before the full source tree:\n\n"
        "  COPY go.mod go.sum ./\n"
        "  RUN go mod download\n"
        "  COPY . .\n"
        "  RUN go build -o /app ."
    ),
    "estimated_saving": {
        "build_time": "30-80%",
        "confidence": "heuristic",
    },
    "reason": "Full-tree COPY before go mod download busts module cache every build.",
    "references": [
        "https://docs.docker.com/build/cache/",
    ],
    "pack": "builtin@0.1",
}

GO_RUN_RE = re.compile(r"\bgo\s+(mod\s+download|get|build|install)\b", re.IGNORECASE)
GO_MANIFEST_RE = re.compile(r"go\.(mod|sum)", re.IGNORECASE)
FULL_COPY_RE = re.compile(r"^(?:--\S+\s+)*\.(?:/\S*)?(?:\s|$)")


def check(ctx: AnalysisContext) -> list[Finding]:
    findings: list[Finding] = []
    seen_stages: set[str] = set()

    for instr in ctx.graph.instructions:
        if instr.instruction != "RUN" or not GO_RUN_RE.search(instr.args):
            continue
        if instr.stage in seen_stages:
            continue

        stage_instrs = [i for i in ctx.graph.instructions if i.stage == instr.stage and i.index < instr.index]
        has_manifest = any(i.instruction == "COPY" and GO_MANIFEST_RE.search(i.args) for i in stage_instrs)
        has_full_copy_before = any(
            i.instruction == "COPY" and FULL_COPY_RE.search(i.args.strip()) for i in stage_instrs
        )

        if has_full_copy_before and not has_manifest:
            seen_stages.add(instr.stage)
            findings.append(
                finding_from_meta(
                    RULE,
                    message=f"go command at line {instr.line} after COPY . without go.mod layer",
                    line=instr.line,
                    stage=instr.stage,
                )
            )

    return findings
