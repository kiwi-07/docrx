"""Analysis context shared by YAML rules and Python plugins."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from dockrx.parser.dockerfile import DockerfileGraph


@dataclass
class AnalysisContext:
    """Context providers for rules. Image/layer fields reserved for M2."""

    root: Path
    dockerfile_path: Path
    graph: DockerfileGraph
    has_dockerignore: bool = False
    dockerignore_path: Path | None = None
    # Reserved for Milestone 2 context providers:
    image: object | None = None
    layers: object | None = None
    history: object | None = None
    build_context: object | None = None
    meta: dict = field(default_factory=dict)


def build_context(path: Path) -> AnalysisContext:
    """Resolve a Dockerfile path or project directory into an analysis context."""
    path = path.resolve()

    if path.is_dir():
        root = path
        candidates = [
            root / "Dockerfile",
            root / "dockerfile",
            root / "Containerfile",
        ]
        dockerfile = next((c for c in candidates if c.is_file()), None)
        if dockerfile is None:
            raise FileNotFoundError(f"No Dockerfile found in {root}")
    elif path.is_file():
        dockerfile = path
        root = path.parent
    else:
        raise FileNotFoundError(f"Path not found: {path}")

    dockerignore = root / ".dockerignore"
    from dockrx.parser import parse_dockerfile

    return AnalysisContext(
        root=root,
        dockerfile_path=dockerfile,
        graph=parse_dockerfile(dockerfile),
        has_dockerignore=dockerignore.is_file(),
        dockerignore_path=dockerignore if dockerignore.is_file() else None,
    )
