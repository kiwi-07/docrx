"""YAML detect DSL matcher against the instruction graph."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from dockrx.models import DetectCondition, DetectSpec

if TYPE_CHECKING:
    from dockrx.parser.dockerfile import DockerfileGraph, Instruction


@dataclass
class MatchHit:
    instruction: Instruction | None = None


def _stage_ok(instr: Instruction, stage: str | None, graph: DockerfileGraph) -> bool:
    if stage is None or stage == "any":
        return True
    if stage == "final":
        return instr.stage == graph.final_stage
    return instr.stage == stage


def _args_match(instr: Instruction, pattern: str | None) -> bool:
    if pattern is None:
        return True
    return re.search(pattern, instr.args, re.IGNORECASE) is not None


def _find_matches(
    graph: DockerfileGraph,
    condition: DetectCondition,
) -> list[Instruction]:
    if condition.missing:
        # missing is handled at evaluate level
        return []

    name = (condition.instruction or "").upper()
    candidates = [
        i
        for i in graph.instructions
        if (not name or i.instruction == name)
        and _stage_ok(i, condition.stage, graph)
        and _args_match(i, condition.args_match)
    ]
    return candidates


def _exists_missing(graph: DockerfileGraph, condition: DetectCondition) -> bool:
    """Return True when the targeted instruction does NOT exist (finding should fire)."""
    name = (condition.instruction or "").upper()
    for instr in graph.instructions:
        if name and instr.instruction != name:
            continue
        if not _stage_ok(instr, condition.stage, graph):
            continue
        if not _args_match(instr, condition.args_match):
            continue
        return False
    return True


def _match_condition(
    graph: DockerfileGraph,
    condition: DetectCondition,
) -> tuple[bool, Instruction | None]:
    if condition.missing:
        ok = _exists_missing(graph, condition)
        return ok, None

    candidates = _find_matches(graph, condition)
    if not candidates:
        return False, None

    if condition.before is None and condition.after is None:
        return True, candidates[0]

    for cand in candidates:
        if condition.before is not None:
            # Default: keep before/after relationships within the same stage so a
            # COPY in a Node builder stage cannot match a later Go RUN elsewhere.
            before_stage = condition.before.stage or condition.stage or cand.stage
            later = [
                i
                for i in graph.instructions
                if i.index > cand.index
                and (not condition.before.instruction or i.instruction == condition.before.instruction.upper())
                and _stage_ok(i, before_stage, graph)
                and _args_match(i, condition.before.args_match)
            ]
            # "before" means this instruction appears before a matching later one
            # and there should not be a better pattern — for COPY before npm install,
            # we want COPY . that appears before RUN npm install
            if not later:
                continue
            # Prefer when the COPY looks like a broad copy (caller constrains via args_match)
            return True, cand

        if condition.after is not None:
            after_stage = condition.after.stage or condition.stage or cand.stage
            earlier = [
                i
                for i in graph.instructions
                if i.index < cand.index
                and (not condition.after.instruction or i.instruction == condition.after.instruction.upper())
                and _stage_ok(i, after_stage, graph)
                and _args_match(i, condition.after.args_match)
            ]
            if earlier:
                return True, cand

    return False, None


def evaluate_detect(graph: DockerfileGraph, spec: DetectSpec | DetectCondition) -> tuple[bool, Instruction | None]:
    """Evaluate a detect tree. Returns (matched, primary_instruction)."""
    if isinstance(spec, DetectCondition):
        return _match_condition(graph, spec)

    if spec.not_ is not None:
        matched, _ = evaluate_detect(graph, spec.not_)
        return (not matched), None

    if spec.all is not None:
        hit: Instruction | None = None
        for child in spec.all:
            ok, instr = evaluate_detect(graph, child)
            if not ok:
                return False, None
            hit = hit or instr
        return True, hit

    if spec.any is not None:
        for child in spec.any:
            ok, instr = evaluate_detect(graph, child)
            if ok:
                return True, instr
        return False, None

    return False, None
