"""Implement `dockrx fix`.

MVP strategy:
- Select top ROI findings that have a concrete fix handler.
- Apply a small set of deterministic, text-based transformations (no full AST rewrite).
- Show a unified diff preview and ask for confirmation.
- Never overwrite the original Dockerfile; write `Dockerfile.fixed`.
"""

from __future__ import annotations

import difflib
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from dockrx.engine import analyze
from dockrx.reporters.presentation import enrich_findings

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from dockrx.context import AnalysisContext

logger = logging.getLogger("dockrx.fixer")


@dataclass
class FixPlan:
    dockerfile_path: Path
    fixed_path: Path
    applied_rule_ids: list[str]
    dockerfile_before: str
    dockerfile_after: str
    dockerfile_diff: str
    dockerignore_added: bool
    dockerignore_before: str | None
    dockerignore_after: str | None


DEBUG_PACKAGES = {
    "iputils-ping",
    "telnet",
    "traceroute",
    "netcat",
    "netcat-openbsd",
    "net-tools",
    "dnsutils",
    "bind9-dnsutils",
    "nmap",
    "tcpdump",
}


def _split_lines(text: str) -> list[str]:
    # Keep without line endings; re-join with '\n'.
    return text.splitlines()


def _join_lines(lines: list[str]) -> str:
    return "\n".join(lines) + ("\n" if lines and not lines[-1].endswith("\n") else "")


def _find_last_from_index(lines: list[str]) -> int:
    from_re = re.compile(r"^\s*FROM\s+", re.IGNORECASE)
    last = -1
    for i, line in enumerate(lines):
        if from_re.search(line):
            last = i
    return max(0, last)


def _final_stage_slice(lines: list[str]) -> tuple[int, list[str]]:
    start = _find_last_from_index(lines)
    return start, lines[start:]


def _final_has_instruction(lines: list[str], start: int, instr: str) -> bool:
    pat = re.compile(rf"^\s*{re.escape(instr)}\b", re.IGNORECASE)
    return any(pat.search(line) for line in lines[start:])


def _get_final_workdir(lines: list[str], start: int) -> str:
    pat = re.compile(r"^\s*WORKDIR\s+(?P<path>\S+)\s*$", re.IGNORECASE)
    last = "/opt/app"
    for line in lines[start:]:
        m = pat.search(line)
        if m:
            last = m.group("path")
    return last


def _get_final_expose_port(lines: list[str], start: int) -> str | None:
    pat = re.compile(r"^\s*EXPOSE\s+(?P<port>\d+)\b", re.IGNORECASE)
    for line in reversed(lines[start:]):
        m = pat.search(line)
        if m:
            return m.group("port")
    return None


def _find_first_final_entrypoint_or_cmd(lines: list[str], start: int) -> int | None:
    ep_pat = re.compile(r"^\s*(ENTRYPOINT|CMD)\b", re.IGNORECASE)
    for i in range(start, len(lines)):
        if ep_pat.search(lines[i]):
            return i
    return None


def _fix_drx018_jdk_to_jre(text: str, ctx: AnalysisContext) -> str:
    lines = _split_lines(text)
    start, _ = _final_stage_slice(lines)
    # Replace on the final FROM line.
    if start >= len(lines):
        return text
    line = lines[start]
    if re.search(r"\bjdk\b", line, re.IGNORECASE):
        lines[start] = re.sub(r"-jdk-", "-jre-", line, flags=re.IGNORECASE)
        # Also handle cases like ":21-jdk-jammy" without "-jdk-" tokenization.
        lines[start] = re.sub(r":(\d+)[-]jdk([-\w]*)", r":\1-jre\2", lines[start], flags=re.IGNORECASE)
    return _join_lines(lines)


def _fix_drx003_insert_user(text: str, ctx: AnalysisContext) -> str:
    lines = _split_lines(text)
    start, _ = _final_stage_slice(lines)

    if _final_has_instruction(lines, start, "USER"):
        return text

    workdir = _get_final_workdir(lines, start)
    insert_at = _find_first_final_entrypoint_or_cmd(lines, start)
    if insert_at is None:
        insert_at = len(lines)

    indent = ""
    # Use indentation from the entrypoint/cmd line if possible.
    if insert_at < len(lines):
        m = re.match(r"^(\s*)", lines[insert_at])
        indent = m.group(1) if m else ""

    user_lines = [
        f"{indent}RUN useradd --system --create-home appuser && chown -R appuser:appuser {workdir}",
        f"{indent}USER appuser",
    ]

    # Insert with a blank line for readability.
    lines[insert_at:insert_at] = ["", *user_lines, ""]
    return _join_lines(lines)


def _filter_packages_in_line(line: str) -> str:
    """Remove known debug packages from a single line (best-effort)."""
    stripped = line.rstrip()
    indent_m = re.match(r"^(\s*)", line)
    indent = indent_m.group(1) if indent_m else ""

    has_backslash = stripped.endswith("\\")
    if has_backslash:
        stripped = stripped[:-1].rstrip()

    before_and_after = stripped.split("&&", 1)
    left = before_and_after[0].strip()
    right = ("&&" + before_and_after[1]) if len(before_and_after) == 2 else ""

    tokens = left.split()
    kept = [t for t in tokens if t not in DEBUG_PACKAGES]

    # If the line only contained removable packages, drop the whole line.
    # This avoids leaving behind dangling "\" continuation tokens.
    if not kept and not right.strip():
        return ""

    rebuilt = indent + (" ".join(kept) if kept else "")
    if right:
        rebuilt += (" " if rebuilt.strip() else "") + right.strip()
    if has_backslash:
        rebuilt = rebuilt.rstrip() + " \\"

    return rebuilt


def _fix_drx019_remove_debug_tools(text: str, ctx: AnalysisContext) -> str:
    lines = _split_lines(text)
    start, _ = _final_stage_slice(lines)

    run_re = re.compile(r"^\s*RUN\b", re.IGNORECASE)
    apt_install_re = re.compile(r"\bapt-get\s+install\b", re.IGNORECASE)

    in_install_block = False
    saw_start = False

    for i in range(start, len(lines)):
        line = lines[i]
        if run_re.search(line) and apt_install_re.search(line):
            # Next lines usually list packages until rm -rf /var/lib/apt/lists/*
            in_install_block = True
            saw_start = True
            lines[i] = _filter_packages_in_line(line)
            continue

        if not in_install_block:
            continue

        # Still inside the package list.
        lines[i] = _filter_packages_in_line(line)

        if "rm -rf" in line and "/var/lib/apt/lists" in line:
            in_install_block = False
            continue

    # If we didn't find an apt-get install block, don't touch.
    if not saw_start:
        return text
    return _join_lines(lines)


def _fix_drx023_shell_entrypoint_exec_to_script(text: str, ctx: AnalysisContext) -> str:
    lines = _split_lines(text)
    start, _ = _final_stage_slice(lines)

    entrypoint_re = re.compile(r"^\s*ENTRYPOINT\s+exec\s+java\b", re.IGNORECASE)
    jar_re = re.compile(r"-jar\s+(?P<jar>\S+)", re.IGNORECASE)

    for i in range(start, len(lines)):
        if not entrypoint_re.search(lines[i]):
            continue

        jar_m = jar_re.search(lines[i])
        if not jar_m:
            return text

        jar_path = jar_m.group("jar").strip().strip('"')
        has_java_opts = "$JAVA_OPTS" in lines[i]
        indent_m = re.match(r"^(\s*)", lines[i])
        indent = indent_m.group(1) if indent_m else ""

        exec_line = f"exec java $JAVA_OPTS -jar {jar_path}" if has_java_opts else f"exec java -jar {jar_path}"
        script_run = f"{indent}RUN printf '%s\\n' '#!/bin/sh' '{exec_line}' > /entrypoint.sh && chmod +x /entrypoint.sh"
        lines.insert(i, script_run)
        lines[i + 1] = f'{indent}ENTRYPOINT ["/entrypoint.sh"]'
        return _join_lines(lines)

    return text


def _fix_drx004_add_healthcheck(text: str, ctx: AnalysisContext) -> str:
    lines = _split_lines(text)
    start, _ = _final_stage_slice(lines)

    if _final_has_instruction(lines, start, "HEALTHCHECK"):
        return text

    port = _get_final_expose_port(lines, start) or "8080"
    hc_line = f"HEALTHCHECK CMD curl -f http://localhost:{port}/health || exit 1"

    # Prefer insertion after the last EXPOSE.
    expose_idx = None
    expose_pat = re.compile(r"^\s*EXPOSE\b", re.IGNORECASE)
    for i in range(start, len(lines)):
        if expose_pat.search(lines[i]):
            expose_idx = i

    insert_at = None
    if expose_idx is not None:
        insert_at = expose_idx + 1
    else:
        insert_at = _find_first_final_entrypoint_or_cmd(lines, start)
        if insert_at is None:
            insert_at = len(lines)

    lines[insert_at:insert_at] = ["", hc_line, ""]
    return _join_lines(lines)


@dataclass
class _FixHandler:
    rule_id: str
    title: str
    handler: Callable[[str, AnalysisContext], str]


FIX_HANDLERS: list[_FixHandler] = [
    _FixHandler("DRX018", "Switch JDK → JRE runtime", _fix_drx018_jdk_to_jre),
    _FixHandler("DRX003", "Run as non-root", _fix_drx003_insert_user),
    _FixHandler("DRX019", "Remove debug networking tools", _fix_drx019_remove_debug_tools),
    _FixHandler("DRX023", "Use exec-form ENTRYPOINT (script wrapper)", _fix_drx023_shell_entrypoint_exec_to_script),
    _FixHandler("DRX004", "Add HEALTHCHECK", _fix_drx004_add_healthcheck),
]


def _dockerignore_default_content() -> str:
    # Keep this aligned with RULE_PRESENTATION[DRX005]. Suggested fix patterns.
    return "\n".join(
        [
            ".git",
            "node_modules",
            "dist",
            "target",
            ".venv",
            ".env",
            "*.log",
            "",
        ]
    )


def _render_diff(original: str, modified: str, from_path: str, to_path: str) -> str:
    original_lines = original.splitlines(keepends=False)
    modified_lines = modified.splitlines(keepends=False)
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=from_path,
        tofile=to_path,
        lineterm="",
    )
    return "\n".join(diff)


def build_fix_plan(path: Path | str, limit: int = 3) -> FixPlan:
    ctx, findings = analyze(path)

    enriched = enrich_findings(findings)
    supported = {h.rule_id: h for h in FIX_HANDLERS}

    selected: list[str] = []
    for e in enriched:
        rid = e.finding.rule_id
        if rid == "DRX005":
            # dockerignore is outside Dockerfile, handled separately
            if "DRX005" not in selected:
                selected.append("DRX005")
        elif rid in supported and rid not in selected:
            selected.append(rid)
        if len(selected) >= limit:
            break

    try:
        dockerfile_before = ctx.dockerfile_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        logger.error("Failed to read Dockerfile %s: %s", ctx.dockerfile_path, exc)
        raise FileNotFoundError(f"Cannot read Dockerfile: {ctx.dockerfile_path}") from exc
    dockerfile_after = dockerfile_before

    for rid in selected:
        if rid == "DRX005":
            continue
        handler = supported.get(rid)
        if not handler:
            continue
        dockerfile_after = handler.handler(dockerfile_after, ctx)

    dockerfile_diff = _render_diff(
        dockerfile_before,
        dockerfile_after,
        from_path=str(ctx.dockerfile_path.name),
        to_path=f"{ctx.dockerfile_path.name}.fixed",
    )

    dockerignore_path = ctx.root / ".dockerignore"
    dockerignore_before = None
    dockerignore_after = None
    dockerignore_added = False
    if "DRX005" in selected and not dockerignore_path.exists():
        dockerignore_added = True
        dockerignore_before = None
        dockerignore_after = _dockerignore_default_content()

    return FixPlan(
        dockerfile_path=ctx.dockerfile_path,
        fixed_path=ctx.dockerfile_path.with_name(f"{ctx.dockerfile_path.name}.fixed"),
        applied_rule_ids=selected,
        dockerfile_before=dockerfile_before,
        dockerfile_after=dockerfile_after,
        dockerfile_diff=dockerfile_diff,
        dockerignore_added=dockerignore_added,
        dockerignore_before=dockerignore_before,
        dockerignore_after=dockerignore_after,
    )


def apply_fix_plan(plan: FixPlan) -> None:
    """Write the fixed Dockerfile and optional .dockerignore to disk."""
    try:
        plan.fixed_path.write_text(plan.dockerfile_after, encoding="utf-8")
        logger.info("Wrote fixed Dockerfile to %s", plan.fixed_path)
    except OSError as exc:
        logger.error("Failed to write fixed Dockerfile %s: %s", plan.fixed_path, exc)
        raise

    if plan.dockerignore_added and plan.dockerignore_after is not None:
        # Safe: only create when missing.
        root = plan.dockerfile_path.parent
        dockerignore_path = root / ".dockerignore"
        if not dockerignore_path.exists():
            try:
                dockerignore_path.write_text(plan.dockerignore_after, encoding="utf-8")
                logger.info("Created .dockerignore at %s", dockerignore_path)
            except OSError as exc:
                logger.error("Failed to create .dockerignore: %s", exc)
                # Non-fatal: the main fix was already written
