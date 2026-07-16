"""DRX027 — Cargo build after full source COPY without manifest layer."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from dockrx.plugins.base import finding_from_meta

if TYPE_CHECKING:
    from dockrx.context import AnalysisContext
    from dockrx.models import Finding

RULE = {
    "id": "DRX027",
    "title": "Cargo build without manifest layer",
    "severity": "HIGH",
    "category": "cache",
    "tags": ["rust", "cargo", "caching"],
    "applies_to": ["dockerfile"],
    "recommendation": (
        "Copy Cargo.toml and Cargo.lock (and any workspace manifests) before "
        "source trees, fetch dependencies, then copy src:\n\n"
        "  COPY Cargo.toml Cargo.lock ./\n"
        "  RUN cargo fetch\n"
        "  COPY src src\n"
        "  RUN cargo build --release"
    ),
    "estimated_saving": {
        "build_time": "30-80%",
        "confidence": "heuristic",
    },
    "reason": "Cargo dependency layers need manifests copied before full source trees.",
    "references": [
        "https://docs.docker.com/build/cache/",
    ],
    "pack": "builtin@0.1",
}

CARGO_RUN_RE = re.compile(r"\bcargo\s+(build|install|test)\b", re.IGNORECASE)
CARGO_MANIFEST_RE = re.compile(r"Cargo\.(toml|lock)", re.IGNORECASE)
FULL_COPY_RE = re.compile(r"^(?:--\S+\s+)*\.(?:/\S*)?(?:\s|$)")


def check(ctx: AnalysisContext) -> list[Finding]:
    findings: list[Finding] = []

    for instr in ctx.graph.instructions:
        if instr.instruction != "RUN" or not CARGO_RUN_RE.search(instr.args):
            continue

        stage_instrs = [i for i in ctx.graph.instructions if i.stage == instr.stage and i.index < instr.index]
        has_manifest = any(i.instruction == "COPY" and CARGO_MANIFEST_RE.search(i.args) for i in stage_instrs)
        has_full_copy_before = any(
            i.instruction == "COPY" and FULL_COPY_RE.search(i.args.strip()) for i in stage_instrs
        )

        if has_full_copy_before and not has_manifest:
            findings.append(
                finding_from_meta(
                    RULE,
                    message=f"cargo build at line {instr.line} after COPY . without manifest layer",
                    line=instr.line,
                    stage=instr.stage,
                )
            )

    return findings
