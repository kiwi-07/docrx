"""DRX025 — Maven stage missing POM layer before mvn."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from dockrx.plugins.base import finding_from_meta

if TYPE_CHECKING:
    from dockrx.context import AnalysisContext
    from dockrx.models import Finding

RULE = {
    "id": "DRX025",
    "title": "Maven build without POM layer in stage",
    "severity": "HIGH",
    "category": "cache",
    "tags": ["maven", "java", "pom"],
    "applies_to": ["dockerfile"],
    "recommendation": (
        "Before running mvn in a stage, copy pom.xml files (or COPY --from "
        "a dependency stage that already resolved them). Building without a "
        "POM layer forces dependency downloads on every source change."
    ),
    "estimated_saving": {
        "build_time": "30-80%",
        "confidence": "heuristic",
    },
    "reason": "Maven cannot cache dependency resolution without POM manifests in an earlier layer.",
    "references": [
        "https://docs.docker.com/build/cache/",
    ],
    "pack": "builtin@0.1",
}

MVN_RE = re.compile(r"\bmvn\b", re.IGNORECASE)
POM_COPY_RE = re.compile(r"pom\.xml", re.IGNORECASE)
FROM_COPY_RE = re.compile(r"^--from=", re.IGNORECASE)


def _stage_instructions(ctx: AnalysisContext, stage: str) -> list:
    return [i for i in ctx.graph.instructions if i.stage == stage]


def check(ctx: AnalysisContext) -> list[Finding]:
    findings: list[Finding] = []
    seen_stages: set[str] = set()

    for instr in ctx.graph.instructions:
        if instr.instruction != "RUN" or not MVN_RE.search(instr.args):
            continue
        if instr.stage in seen_stages:
            continue
        seen_stages.add(instr.stage)

        prior = [i for i in _stage_instructions(ctx, instr.stage) if i.index < instr.index]
        has_pom_layer = any(
            i.instruction == "COPY" and (POM_COPY_RE.search(i.args) or FROM_COPY_RE.search(i.args.strip()))
            for i in prior
        )
        if has_pom_layer:
            continue

        findings.append(
            finding_from_meta(
                RULE,
                message=f"mvn at line {instr.line} without prior pom.xml or COPY --from= layer",
                line=instr.line,
                stage=instr.stage,
            )
        )

    return findings
