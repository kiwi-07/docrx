"""DRX016 — Multiple consecutive RUN instructions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dockrx.plugins.base import finding_from_meta

if TYPE_CHECKING:
    from dockrx.context import AnalysisContext
    from dockrx.models import Finding

RULE = {
    "id": "DRX016",
    "title": "Multiple consecutive RUN instructions",
    "severity": "MEDIUM",
    "category": "size",
    "tags": ["layers", "run"],
    "applies_to": ["dockerfile"],
    "recommendation": (
        "Combine related RUN commands with && so package install and "
        "cleanup happen in one layer. Separate RUNs leave cache and "
        "temporary files in earlier layers even if removed later."
    ),
    "estimated_saving": {
        "image_size": "~20-100 MB",
        "confidence": "heuristic",
    },
    "reason": "Each RUN creates a layer; cleanup in a later RUN cannot shrink earlier layers.",
    "references": [
        "https://docs.docker.com/build/building/best-practices/#apt-get",
    ],
    "pack": "builtin@0.1",
}


def check(ctx: AnalysisContext) -> list[Finding]:
    findings: list[Finding] = []
    prev = None
    for instr in ctx.graph.instructions:
        if instr.instruction != "RUN":
            prev = None
            continue
        if prev is not None and prev.stage == instr.stage:
            findings.append(
                finding_from_meta(
                    RULE,
                    message=f"Consecutive RUN at lines {prev.line} and {instr.line}",
                    line=instr.line,
                    stage=instr.stage,
                )
            )
            break  # one finding per analysis is enough
        prev = instr
    return findings
