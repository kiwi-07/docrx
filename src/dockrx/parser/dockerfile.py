"""Parsed Dockerfile instruction graph."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

INSTRUCTION_RE = re.compile(
    r"^(?P<instruction>[A-Za-z]+)\s+(?P<args>.*)$",
    re.DOTALL,
)
FROM_RE = re.compile(
    r"^FROM\s+(?:--platform=\S+\s+)?(?P<image>\S+)(?:\s+[Aa][Ss]\s+(?P<stage>\S+))?",
    re.IGNORECASE,
)


@dataclass
class Instruction:
    index: int
    line: int
    instruction: str
    args: str
    raw: str
    stage: str
    stage_index: int


@dataclass
class DockerfileGraph:
    path: Path
    instructions: list[Instruction] = field(default_factory=list)
    stages: list[str] = field(default_factory=list)
    syntax: str | None = None

    @property
    def final_stage(self) -> str | None:
        return self.stages[-1] if self.stages else None

    def by_instruction(self, name: str) -> list[Instruction]:
        upper = name.upper()
        return [i for i in self.instructions if i.instruction == upper]


def _normalize_continuation(text: str) -> list[tuple[int, str]]:
    """Join backslash-continued lines; return (start_line, logical_line)."""
    lines = text.splitlines()
    result: list[tuple[int, str]] = []
    buf: list[str] = []
    start_line = 1

    for lineno, line in enumerate(lines, start=1):
        stripped = line.rstrip()
        if not buf:
            start_line = lineno
        if stripped.endswith("\\") and not stripped.lstrip().startswith("#"):
            buf.append(stripped[:-1].rstrip())
            continue
        buf.append(stripped)
        result.append((start_line, " ".join(buf)))
        buf = []

    if buf:
        result.append((start_line, " ".join(buf)))
    return result


def parse_dockerfile(path: Path | str) -> DockerfileGraph:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    return parse_dockerfile_text(text, path=path)


def parse_dockerfile_text(text: str, path: Path | str | None = None) -> DockerfileGraph:
    path = Path(path) if path else Path("<stdin>")
    graph = DockerfileGraph(path=path)

    current_stage = "default"
    stage_index = 0
    index = 0

    for start_line, logical in _normalize_continuation(text):
        line = logical.strip()
        if not line:
            continue
        if line.startswith("#"):
            if line.lower().startswith("# syntax="):
                graph.syntax = line.split("=", 1)[1].strip()
            continue

        match = INSTRUCTION_RE.match(line)
        if not match:
            continue

        instruction = match.group("instruction").upper()
        args = match.group("args").strip()

        if instruction == "FROM":
            from_match = FROM_RE.match(line)
            stage_name = None
            if from_match:
                stage_name = from_match.group("stage")
            if stage_name:
                current_stage = stage_name
            else:
                stage_index += 1 if graph.stages else 0
                current_stage = f"stage{len(graph.stages)}"
            if current_stage not in graph.stages:
                graph.stages.append(current_stage)
            stage_index = graph.stages.index(current_stage)

        instr = Instruction(
            index=index,
            line=start_line,
            instruction=instruction,
            args=args,
            raw=line,
            stage=current_stage,
            stage_index=stage_index,
        )
        graph.instructions.append(instr)
        index += 1

        if instruction == "FROM" and not graph.stages:
            graph.stages.append(current_stage)

    if not graph.stages and graph.instructions:
        graph.stages = ["default"]

    return graph
