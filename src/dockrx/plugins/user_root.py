"""DRX014 — Final stage ends as USER root."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from dockrx.plugins.base import finding_from_meta

if TYPE_CHECKING:
    from dockrx.context import AnalysisContext
    from dockrx.models import Finding

RULE = {
    "id": "DRX014",
    "title": "Explicit root USER",
    "severity": "HIGH",
    "category": "security",
    "tags": ["user", "root"],
    "applies_to": ["dockerfile"],
    "recommendation": (
        "Avoid ending the final stage as USER root. Create and switch to a "
        "non-privileged user before CMD/ENTRYPOINT.\n\n"
        "Temporary USER root for install steps is fine if the last USER is non-root."
    ),
    "reason": "Ending as root undoes earlier USER hardening.",
    "references": [
        "https://docs.docker.com/engine/security/",
    ],
    "pack": "builtin@0.1",
}

ROOT_USER_RE = re.compile(r"^(root|0)(?:\s|$)", re.IGNORECASE)


def check(ctx: AnalysisContext) -> list[Finding]:
    final = ctx.graph.final_stage
    users = [i for i in ctx.graph.instructions if i.stage == final and i.instruction == "USER"]
    if not users:
        return []

    last = users[-1]
    if not ROOT_USER_RE.search(last.args.strip()):
        return []

    return [
        finding_from_meta(
            RULE,
            message=f"final stage ends as USER {last.args.strip()} at line {last.line}",
            line=last.line,
            stage=last.stage,
        )
    ]
