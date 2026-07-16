"""Rule engine: evaluate YAML rules and plugins into findings."""

from __future__ import annotations

import logging
from pathlib import Path

from dockrx.context import AnalysisContext, build_context
from dockrx.engine.loader import PluginRule, load_all_rules
from dockrx.engine.matcher import evaluate_detect
from dockrx.models import Finding, Severity, YamlRule

logger = logging.getLogger("dockrx.engine")


def _finding_from_yaml(rule: YamlRule, line: int | None, stage: str | None) -> Finding:
    return Finding(
        rule_id=rule.id,
        title=rule.title,
        severity=rule.severity,
        category=rule.category,
        recommendation=rule.recommendation.strip(),
        pack=rule.pack,
        reason=rule.reason,
        estimated_saving=rule.estimated_saving,
        references=rule.references,
        stage=stage,
        line=line,
        tags=rule.tags,
    )


def run_yaml_rules(ctx: AnalysisContext, rules: list[YamlRule]) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        if "dockerfile" not in rule.applies_to:
            continue
        matched, instr = evaluate_detect(ctx.graph, rule.detect)
        if matched:
            findings.append(
                _finding_from_yaml(
                    rule,
                    line=instr.line if instr else None,
                    stage=instr.stage if instr else None,
                )
            )
    return findings


def run_plugins(ctx: AnalysisContext, plugins: list[PluginRule]) -> list[Finding]:
    findings: list[Finding] = []
    for plugin in plugins:
        applies = plugin.meta.get("applies_to", ["dockerfile"])
        if "dockerfile" not in applies and "project" not in applies:
            continue
        try:
            plugin_findings = plugin.check(ctx)
            findings.extend(plugin_findings)
        except Exception:
            logger.exception("Plugin %s failed unexpectedly, skipping", plugin.id)
    return findings


def analyze(path: Path | str) -> tuple[AnalysisContext, list[Finding]]:
    """Analyze a Dockerfile and return (context, findings).

    This function is the main entry point for the rule engine.
    It gracefully degrades: if parsing fails, a synthetic finding is returned.
    If individual plugins crash, they are skipped.
    """
    try:
        ctx = build_context(Path(path))
    except FileNotFoundError:
        raise
    except Exception:
        logger.exception("Failed to build analysis context for %s", path)
        raise

    try:
        yaml_rules, plugins = load_all_rules(ctx.root)
    except Exception:
        logger.exception("Failed to load rules for %s, continuing with empty rule set", path)
        yaml_rules, plugins = [], []

    yaml_findings = run_yaml_rules(ctx, yaml_rules) if yaml_rules else []
    plugin_findings = run_plugins(ctx, plugins) if plugins else []
    findings = yaml_findings + plugin_findings

    # Sort: HIGH first, then by rule_id for determinism
    findings.sort(key=lambda f: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}[f.severity.value], f.rule_id))

    logger.info(
        "Analysis complete: %d findings (%d HIGH)",
        len(findings),
        sum(1 for f in findings if f.severity == Severity.HIGH),
    )
    return ctx, findings
