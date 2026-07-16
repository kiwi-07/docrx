"""YAML DSL matcher tests."""

from dockrx.engine.matcher import evaluate_detect
from dockrx.models import DetectCondition, DetectSpec
from dockrx.parser import parse_dockerfile_text


def test_copy_before_npm_install():
    graph = parse_dockerfile_text(
        """\
FROM node:22
COPY . .
RUN npm install
"""
    )
    spec = DetectSpec(
        all=[
            DetectCondition(
                instruction="COPY",
                args_match=r"^(?:--\S+\s+)*\.(?:/\S*)?(?:\s|$)",
                before=DetectCondition(
                    instruction="RUN",
                    args_match=r"(npm|yarn|pnpm)\s+(ci|install)",
                ),
            )
        ]
    )
    matched, instr = evaluate_detect(graph, spec)
    assert matched
    assert instr is not None and instr.instruction == "COPY"


def test_requirements_copy_not_full_tree():
    graph = parse_dockerfile_text(
        """\
FROM python:3.13-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
"""
    )
    spec = DetectSpec(
        all=[
            DetectCondition(
                instruction="COPY",
                args_match=r"^(?:--\S+\s+)*\.(?:/\S*)?(?:\s|$)",
                before=DetectCondition(
                    instruction="RUN",
                    args_match=r"pip(\d*)\s+install",
                ),
            )
        ]
    )
    matched, _ = evaluate_detect(graph, spec)
    assert not matched


def test_missing_user():
    graph = parse_dockerfile_text('FROM alpine\nCMD ["/bin/sh"]\n')
    spec = DetectSpec(all=[DetectCondition(instruction="USER", missing=True)])
    matched, _ = evaluate_detect(graph, spec)
    assert matched
