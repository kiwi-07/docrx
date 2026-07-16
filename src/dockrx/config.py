"""Configuration loading for DockRx.

Settings are loaded from the user's pyproject.toml under [tool.dockrx].

Supports:
  - log-level: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
  - fail-on-severity: "HIGH" | "MEDIUM" | "LOW" | "INFO" | null
  - default-fix-limit: int
  - health-thresholds: dict[str, int]

Example pyproject.toml:

    [tool.dockrx]
    log-level = "INFO"
    fail-on-severity = "MEDIUM"
    default-fix-limit = 5
"""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path
from typing import Any

logger = logging.getLogger("dockrx.config")


_DEFAULT_CONFIG: dict[str, Any] = {
    "log-level": "WARNING",
    "fail-on-severity": "HIGH",
    "default-fix-limit": 3,
    "health-thresholds": {
        "excellent": 90,
        "good": 75,
        "fair": 60,
        "needs-attention": 40,
    },
}


def _find_project_root(start: Path | None = None) -> Path:
    """Walk up from start (or CWD) to find the project root containing pyproject.toml."""
    current = (start or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    return current


def _load_pyproject_toml(path: Path) -> dict[str, Any] | None:
    """Load and parse a pyproject.toml file."""
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except (FileNotFoundError, PermissionError, tomllib.TOMLDecodeError) as exc:
        logger.debug("Could not load %s: %s", path, exc)
        return None


def load_config(project_root: Path | None = None) -> dict[str, Any]:
    """Load DockRx configuration from pyproject.toml near the project root.

    Falls back to defaults if no config section is found.
    """
    root = project_root or _find_project_root()
    pyproject_path = root / "pyproject.toml"

    data = _load_pyproject_toml(pyproject_path)
    if data is None:
        return dict(_DEFAULT_CONFIG)

    dockrx_config = data.get("tool", {}).get("dockrx", {})
    if not isinstance(dockrx_config, dict):
        return dict(_DEFAULT_CONFIG)

    merged = dict(_DEFAULT_CONFIG)
    merged.update(dockrx_config)
    return merged


def get_config_value(key: str, default: Any = None, project_root: Path | None = None) -> Any:
    """Get a single config value by key, falling back to default."""
    cfg = load_config(project_root)
    return cfg.get(key, default)
