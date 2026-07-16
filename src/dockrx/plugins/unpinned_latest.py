"""DRX002 — Unpinned :latest or implicit-latest base images."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from dockrx.plugins.base import finding_from_meta

if TYPE_CHECKING:
    from dockrx.context import AnalysisContext
    from dockrx.models import Finding

RULE = {
    "id": "DRX002",
    "title": "Unpinned latest tag",
    "severity": "HIGH",
    "category": "maintainability",
    "tags": ["base-image", "pinning"],
    "applies_to": ["dockerfile"],
    "recommendation": (
        "Pin base images to a specific version tag or digest instead of "
        "latest (or an implicit latest). Example: python:3.13-slim or "
        "python:3.13-slim@sha256:..."
    ),
    "estimated_saving": {
        "build_time": "reproducible builds",
        "confidence": "heuristic",
    },
    "reason": "latest moves underneath you and breaks reproducible builds.",
    "references": [
        "https://docs.docker.com/build/building/best-practices/#from",
    ],
    "pack": "builtin@0.1",
}

_FROM_AS_RE = re.compile(r"\s+[Aa][Ss]\s+(\S+)\s*$")
_PLATFORM_RE = re.compile(r"^--platform=\S+\s+", re.IGNORECASE)
_VAR_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}|^\$([A-Za-z_][A-Za-z0-9_]*)")
_ARG_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
_LATEST_RE = re.compile(r":latest(?:@|$|\s)", re.IGNORECASE)


def _strip_from_args(args: str) -> tuple[str, str | None]:
    """Return (image_ref, stage_alias) from a FROM instruction's args."""
    text = args.strip()
    alias = None
    as_match = _FROM_AS_RE.search(text)
    if as_match:
        alias = as_match.group(1)
        text = text[: as_match.start()].rstrip()
    while True:
        platform = _PLATFORM_RE.match(text)
        if not platform:
            break
        text = text[platform.end() :]
    return text.strip(), alias


def _resolve_image(ref: str, arg_defaults: dict[str, str]) -> str:
    """Resolve leading $VAR / ${VAR} using ARG defaults when available."""
    match = _VAR_RE.match(ref)
    if not match:
        return ref
    name = match.group(1) or match.group(2)
    default = arg_defaults.get(name)
    if default is None:
        # Unresolvable variable — do not flag (avoid false positives).
        return ""
    # Preserve any suffix after the variable (rare, but keep it).
    return default + ref[match.end() :]


def _is_unpinned(image: str) -> bool:
    if not image or image.upper() == "SCRATCH":
        return False
    if _LATEST_RE.search(image):
        return True
    # Digest-pinned without a tag is fine: name@sha256:...
    if "@" in image:
        return False
    # Tag present (anything after the last slash's colon)
    name = image.rsplit("/", 1)[-1]
    return ":" not in name


def check(ctx: AnalysisContext) -> list[Finding]:
    findings: list[Finding] = []
    stage_names: set[str] = set()
    # ARG defaults visible to subsequent FROM lines (Dockerfile global + reset per stage).
    global_args: dict[str, str] = {}
    stage_args: dict[str, str] = {}
    current_stage: str | None = None

    for instr in ctx.graph.instructions:
        if instr.instruction == "ARG":
            arg_match = _ARG_RE.match(instr.args.strip())
            if not arg_match:
                continue
            name, value = arg_match.group(1), arg_match.group(2).strip().strip("\"'")
            if current_stage is None:
                global_args[name] = value
            else:
                stage_args[name] = value
            continue

        if instr.instruction != "FROM":
            continue

        image_ref, alias = _strip_from_args(instr.args)
        if alias:
            stage_names.add(alias)

        # New stage begins — stage-scoped ARGs reset; globals still apply.
        current_stage = alias or instr.stage
        stage_args = {}

        # Merge: stage args empty at FROM time, so globals + any prior globals only.
        resolved = _resolve_image(image_ref, global_args)
        if not resolved:
            continue

        # Skip references to earlier named stages (multi-stage COPY bases).
        base_name = resolved.split("@", 1)[0].split(":", 1)[0]
        if resolved in stage_names or base_name in stage_names:
            continue

        if _is_unpinned(resolved):
            findings.append(
                finding_from_meta(
                    RULE,
                    message=f"unpinned base image at line {instr.line}: {resolved}",
                    line=instr.line,
                    stage=instr.stage,
                )
            )

    return findings
