"""DRX004 — Missing HEALTHCHECK (skipped for scratch/distroless finals)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from dockrx.plugins.base import finding_from_meta

if TYPE_CHECKING:
    from dockrx.context import AnalysisContext
    from dockrx.models import Finding

RULE = {
    "id": "DRX004",
    "title": "Missing HEALTHCHECK",
    "severity": "LOW",
    "category": "best_practices",
    "tags": ["healthcheck"],
    "applies_to": ["dockerfile"],
    "recommendation": (
        "Add a HEALTHCHECK so orchestrators can detect unhealthy containers.\n"
        "Example: HEALTHCHECK CMD curl -f http://localhost:8080/health || exit 1"
    ),
    "reason": "Without HEALTHCHECK, failed services may keep receiving traffic.",
    "references": [
        "https://docs.docker.com/reference/dockerfile/#healthcheck",
    ],
    "pack": "builtin@0.1",
}

_FROM_AS_RE = re.compile(r"\s+[Aa][Ss]\s+(\S+)\s*$")
_PLATFORM_RE = re.compile(r"^--platform=\S+\s+", re.IGNORECASE)
_VAR_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}|^\$([A-Za-z_][A-Za-z0-9_]*)")
_ARG_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
_SKIP_BASE_RE = re.compile(
    r"(?:^|/)(?:scratch)$|distroless",
    re.IGNORECASE,
)


def _strip_from_args(args: str) -> str:
    text = args.strip()
    as_match = _FROM_AS_RE.search(text)
    if as_match:
        text = text[: as_match.start()].rstrip()
    while True:
        platform = _PLATFORM_RE.match(text)
        if not platform:
            break
        text = text[platform.end() :]
    return text.strip()


def _arg_defaults(ctx: AnalysisContext) -> dict[str, str]:
    defaults: dict[str, str] = {}
    for instr in ctx.graph.instructions:
        if instr.instruction != "ARG":
            continue
        match = _ARG_RE.match(instr.args.strip())
        if match:
            defaults[match.group(1)] = match.group(2).strip().strip("\"'")
    return defaults


def _resolve_image(ref: str, arg_defaults: dict[str, str]) -> str:
    match = _VAR_RE.match(ref)
    if not match:
        return ref
    name = match.group(1) or match.group(2)
    default = arg_defaults.get(name)
    return default if default is not None else ref


def _final_base_image(ctx: AnalysisContext) -> str:
    """Resolve the final stage's FROM image, walking stage aliases once."""
    final = ctx.graph.final_stage
    if final is None:
        return ""

    stage_from: dict[str, str] = {}
    arg_defaults = _arg_defaults(ctx)
    for instr in ctx.graph.instructions:
        if instr.instruction != "FROM":
            continue
        ref = _resolve_image(_strip_from_args(instr.args), arg_defaults)
        stage_from[instr.stage] = ref

    image = stage_from.get(final, "")
    # One-hop stage alias: FROM builder → resolve builder's image
    if image and "/" not in image and ":" not in image and "@" not in image:
        image = stage_from.get(image, image)
    return image


def check(ctx: AnalysisContext) -> list[Finding]:
    if any(i.instruction == "HEALTHCHECK" for i in ctx.graph.instructions):
        return []

    base = _final_base_image(ctx)
    if base and _SKIP_BASE_RE.search(base):
        return []

    return [
        finding_from_meta(
            RULE,
            message="no HEALTHCHECK instruction found",
            stage=ctx.graph.final_stage,
        )
    ]
