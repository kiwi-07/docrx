"""Dockerfile formatter — normalize instruction style, whitespace, and stage layout.

The formatter preserves comments, blank lines within stages, and
continuation lines. It normalizes:

- Instruction casing (→ UPPERCASE)
- Trailing whitespace (removed)
- Blank lines between stages (exactly 1)
- Continuation-line indentation (aligned with first arg)
- Leading/trailing blank lines (removed)
"""

from __future__ import annotations

import difflib
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Instructions ordered by conventional grouping within a stage.
_INSTRUCTION_GROUPS: dict[str, int] = {
    "FROM": 0,
    "ARG": 1,
    "LABEL": 2,
    "ENV": 3,
    "EXPOSE": 4,
    "WORKDIR": 5,
    "USER": 6,
    "VOLUME": 7,
    "STOPSIGNAL": 8,
    "HEALTHCHECK": 9,
    "SHELL": 10,
    "COPY": 11,
    "ADD": 12,
    "RUN": 13,
    "ENTRYPOINT": 14,
    "CMD": 15,
    "ONBUILD": 16,
    "MAINTAINER": 17,
    "CROSS_BUILD": 18,
}

# Instructions that start a new stage (always uppercase for matching).
_STAGE_STARTERS = frozenset({"FROM"})

# Instructions that are "header" / metadata for a stage.
_HEADER_INSTRUCTIONS = frozenset({"FROM", "ARG", "LABEL", "ENV", "EXPOSE", "VOLUME", "STOPSIGNAL", "MAINTAINER"})

_ESTABLISHED_INSTRUCTIONS: set[str] = set(_INSTRUCTION_GROUPS.keys())

_INSTRUCTION_RE = re.compile(r"^\s*(?P<instr>[A-Za-z]+)\b")
_TRAILING_WS_RE = re.compile(r"[ \t]+$")


def _is_instruction_line(line: str) -> bool:
    """Check if a line (stripped) looks like a Dockerfile instruction."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    m = _INSTRUCTION_RE.match(stripped)
    if m:
        instr = m.group("instr").upper()
        return instr in _ESTABLISHED_INSTRUCTIONS
    return False


def _normalize_line_continuation(text: str) -> str:
    """Normalize line continuation indentation.

    Lines ending with \\ get their continuation aligned with the argument start.
    This is a best-effort heuristic.
    """
    lines = text.splitlines(keepends=False)
    result: list[str] = []
    in_continuation = False
    continuation_indent = ""

    for line in lines:
        stripped = line.rstrip()
        if not in_continuation:
            if stripped.endswith("\\"):
                # Start of a continuation block
                m = _INSTRUCTION_RE.match(stripped)
                if m:
                    instr = m.group("instr")
                    # Calculate base indent from the instr + space
                    idx = stripped.index(instr) + len(instr) + 1
                    if idx > 0:
                        continuation_indent = " " * idx
                in_continuation = True
            result.append(stripped)
        else:
            if stripped.endswith("\\"):
                result.append(continuation_indent + stripped.lstrip())
            else:
                # Last line of continuation — use the same indent or less
                result.append(continuation_indent + stripped.lstrip())
                in_continuation = False

    return "\n".join(result)


def _uppercase_instructions(line: str) -> str:
    """Uppercase the instruction keyword in a line."""
    stripped = line.lstrip()
    if not stripped or stripped.startswith("#"):
        return line
    m = _INSTRUCTION_RE.match(stripped)
    if m:
        instr = m.group("instr")
        upper = instr.upper()
        if upper in _ESTABLISHED_INSTRUCTIONS:
            # Replace the instruction preserving case of the rest
            idx = stripped.index(instr)
            prefix = line[: len(line) - len(stripped)]  # leading whitespace
            rest = stripped[idx + len(instr) :]
            return prefix + upper + rest
    return line


def _remove_trailing_whitespace(line: str) -> str:
    """Remove trailing spaces and tabs from a line."""
    return _TRAILING_WS_RE.sub("", line)


def _strip_leading_empty_lines(text: str) -> str:
    """Remove blank lines at the start of the text."""
    return re.sub(r"^\s*\n+", "", text)


def _strip_trailing_empty_lines(text: str) -> str:
    """Remove blank lines at the end of the text."""
    return re.sub(r"\n\s*$", "\n", text)


def _normalize_stage_spacing(text: str) -> str:
    """Ensure exactly one blank line between stages.

    A stage starts with a FROM line. We collapse any block of
    blank lines before a FROM down to exactly one.
    """
    # Find all FROM lines and normalize preceding whitespace
    lines = text.splitlines(keepends=False)
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        m = _INSTRUCTION_RE.match(stripped)
        is_from = m and m.group("instr").upper() == "FROM"

        if is_from and i > 0:
            # Collapse preceding blank lines to exactly one
            # Walk backwards from current position
            j = len(result) - 1
            while j >= 0 and not result[j].strip():
                j -= 1
            # Remove blank lines from result
            result = result[: j + 1]
            # Add exactly one blank line before FROM (if not the first line)
            if result:
                result.append("")

        result.append(line)
        i += 1

    return "\n".join(result)


def format_dockerfile(text: str) -> str:
    """Format a Dockerfile according to DockRx conventions.

    Transformations applied (in order):
      1. Remove trailing whitespace
      2. Uppercase all instruction keywords
      3. Normalize line-continuation indentation
      4. Normalize blank lines between stages
      5. Strip leading/trailing empty lines

    Args:
        text: Raw Dockerfile content.

    Returns:
        Formatted Dockerfile content.
    """
    # Step 1: Normalize line endings
    text = text.replace("\r\n", "\n")

    # Step 2: Remove trailing whitespace
    lines = text.splitlines(keepends=False)
    lines = [_remove_trailing_whitespace(line) for line in lines]
    text = "\n".join(lines)

    # Step 3: Uppercase instructions
    lines = text.splitlines(keepends=False)
    lines = [_uppercase_instructions(line) for line in lines]
    text = "\n".join(lines)

    # Step 4: Normalize continuation indentation
    text = _normalize_line_continuation(text)

    # Step 5: Normalize stage spacing
    text = _normalize_stage_spacing(text)

    # Step 6: Strip leading/trailing empty lines
    text = _strip_leading_empty_lines(text)
    text = _strip_trailing_empty_lines(text)

    # Step 7: Ensure file ends with single newline
    if not text.endswith("\n"):
        text += "\n"

    return text


def format_dockerfile_file(path: Path) -> str:
    """Read a Dockerfile, format it, and return the formatted text.

    Args:
        path: Path to the Dockerfile.

    Returns:
        Formatted Dockerfile content.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    text = path.read_text(encoding="utf-8-sig")
    return format_dockerfile(text)


def format_dockerfile_diff(path: Path) -> str:
    """Generate a unified diff of original vs formatted Dockerfile.

    Args:
        path: Path to the Dockerfile.

    Returns:
        Unified diff string, or empty string if no changes.
    """
    original = path.read_text(encoding="utf-8-sig")
    formatted = format_dockerfile(original)
    if original == formatted:
        return ""

    original_lines = original.splitlines(keepends=False)
    formatted_lines = formatted.splitlines(keepends=False)

    diff = difflib.unified_diff(
        original_lines,
        formatted_lines,
        fromfile=str(path),
        tofile=str(path) + " (formatted)",
        lineterm="",
    )
    return "\n".join(diff)


def is_formatted(path: Path) -> bool:
    """Check whether a Dockerfile is already formatted.

    Args:
        path: Path to the Dockerfile.

    Returns:
        True if the file is already formatted, False otherwise.
    """
    original = path.read_text(encoding="utf-8-sig")
    formatted = format_dockerfile(original)
    return original == formatted
