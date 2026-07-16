"""DRX003 — Missing USER in the final stage."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dockrx.plugins.base import finding_from_meta

if TYPE_CHECKING:
    from dockrx.context import AnalysisContext
    from dockrx.models import Finding

RULE = {
    "id": "DRX003",
    "title": "Missing USER instruction",
    "severity": "HIGH",
    "category": "security",
    "tags": ["user", "root"],
    "applies_to": ["dockerfile"],
    "recommendation": (
        "Add a non-root USER in the final stage before CMD/ENTRYPOINT. "
        "Running as root increases the blast radius of container compromises.\n\n"
        "A USER in a builder stage does not harden the runtime image."
    ),
    "estimated_saving": {
        "confidence": "heuristic",
    },
    "reason": "Containers default to root when the final stage omits USER.",
    "references": [
        "https://docs.docker.com/engine/security/#protect-the-docker-daemon-socket",
    ],
    "pack": "builtin@0.1",
}


def check(ctx: AnalysisContext) -> list[Finding]:
    final = ctx.graph.final_stage
    if final is None:
        return []

    has_user = any(i.stage == final and i.instruction == "USER" for i in ctx.graph.instructions)
    if has_user:
        return []

    return [
        finding_from_meta(
            RULE,
            message=f"final stage '{final}' has no USER instruction",
            stage=final,
        )
    ]
