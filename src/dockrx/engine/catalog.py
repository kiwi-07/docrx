"""Load rule catalog for explain command."""

from __future__ import annotations

from pathlib import Path

from dockrx.engine.loader import load_all_rules
from dockrx.models import RuleMeta


def load_rule_catalog(project_root: Path | None = None) -> dict[str, RuleMeta]:
    """Return all known rules by id (builtin + optional project overrides)."""
    root = project_root or Path.cwd()
    yaml_rules, plugins = load_all_rules(root)
    catalog: dict[str, RuleMeta] = {}
    for rule in yaml_rules:
        catalog[rule.id] = RuleMeta.model_validate(rule.model_dump(exclude={"detect"}))
    for plugin in plugins:
        catalog[plugin.id] = RuleMeta.model_validate(plugin.meta)
    return catalog


def get_rule(rule_id: str, project_root: Path | None = None) -> RuleMeta | None:
    return load_rule_catalog(project_root).get(rule_id.upper())
