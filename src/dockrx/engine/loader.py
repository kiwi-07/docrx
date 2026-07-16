"""Load YAML rules and Python plugins from builtin and project packs."""

from __future__ import annotations

import importlib.util
import logging
import sys
import uuid
from collections.abc import Callable
from pathlib import Path

import yaml

from dockrx.context import AnalysisContext
from dockrx.models import Finding, YamlRule

logger = logging.getLogger("dockrx.loader")

PluginCheck = Callable[[AnalysisContext], list[Finding]]


class PluginRule:
    """Python plugin with the same metadata surface as YAML rules."""

    def __init__(self, meta: dict, check: PluginCheck) -> None:
        self.meta = meta
        self.check = check
        self.id = meta["id"]


def builtin_rules_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "rules" / "builtin"


def builtin_plugins_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "plugins"


def project_dockrx_dir(root: Path) -> Path:
    return root / ".dockrx"


def load_yaml_rules(directory: Path, pack: str | None = None) -> list[YamlRule]:
    if not directory.is_dir():
        return []
    rules: list[YamlRule] = []
    for path in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not data:
            continue
        if pack and "pack" not in data:
            data["pack"] = pack
        rules.append(YamlRule.model_validate(data))
    for path in sorted(directory.glob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not data:
            continue
        if pack and "pack" not in data:
            data["pack"] = pack
        rules.append(YamlRule.model_validate(data))
    return rules


def _plugin_module_uuid(path: Path) -> str:
    """Generate a deterministic module name for a plugin path."""
    return f"dockrx_plugin_{path.stem}_{uuid.uuid5(uuid.NAMESPACE_URL, str(path.resolve()))}"


def _load_plugin_module(path: Path) -> object | None:
    """Load a Python plugin module, returning None on failure."""
    module_name = _plugin_module_uuid(path)
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            logger.error("Cannot create spec for plugin: %s", path)
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception:
        logger.exception("Failed to load plugin: %s", path)
        return None


def load_plugins(directory: Path, pack: str | None = None) -> list[PluginRule]:
    if not directory.is_dir():
        return []
    plugins: list[PluginRule] = []
    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_") or path.name == "base.py":
            continue
        module = _load_plugin_module(path)
        if module is None:
            continue
        rule_attr = getattr(module, "RULE", None)
        check_attr = getattr(module, "check", None)
        if rule_attr is None or check_attr is None:
            logger.warning("Plugin %s missing RULE or check attribute, skipping", path.name)
            continue
        meta = dict(rule_attr)
        if pack and "pack" not in meta:
            meta["pack"] = pack
        plugins.append(PluginRule(meta=meta, check=check_attr))
    return plugins


def load_all_rules(project_root: Path) -> tuple[list[YamlRule], list[PluginRule]]:
    """
    Load order:
      1. Built-in YAML rules
      2. Built-in Python plugins
      3. ./.dockrx/rules/*.yaml
      4. ./.dockrx/plugins/*.py
    Later rules with the same id override earlier ones.
    """
    yaml_rules = load_yaml_rules(builtin_rules_dir(), pack="builtin@0.1")
    plugins = load_plugins(builtin_plugins_dir(), pack="builtin@0.1")

    local = project_dockrx_dir(project_root)
    yaml_rules.extend(load_yaml_rules(local / "rules", pack="project@local"))
    plugins.extend(load_plugins(local / "plugins", pack="project@local"))

    # Deduplicate by id (last wins)
    yaml_by_id = {r.id: r for r in yaml_rules}
    plugin_by_id = {p.id: p for p in plugins}
    # If a project YAML overrides a builtin plugin id, drop the plugin
    for rid in yaml_by_id:
        plugin_by_id.pop(rid, None)
    for rid in list(plugin_by_id):
        if rid in yaml_by_id and yaml_by_id[rid].pack.startswith("project"):
            pass

    return list(yaml_by_id.values()), list(plugin_by_id.values())
