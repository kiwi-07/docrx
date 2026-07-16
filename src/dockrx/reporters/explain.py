"""Explain a single rule by id."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from dockrx.engine.catalog import get_rule
from dockrx.models import Finding
from dockrx.reporters.presentation import presentation_for


def render_explain(rule_id: str, console: Console | None = None, project_root=None) -> bool:
    """Print rule documentation. Returns False if rule not found."""
    console = console or Console()
    rule = get_rule(rule_id, project_root=project_root)
    if rule is None:
        return False

    # Build a synthetic finding for presentation lookup
    finding = Finding(
        rule_id=rule.id,
        title=rule.title,
        severity=rule.severity,
        category=rule.category,
        recommendation=rule.recommendation,
        pack=rule.pack,
        reason=rule.reason,
        estimated_saving=rule.estimated_saving,
        references=rule.references,
        tags=rule.tags,
    )
    pres = presentation_for(finding)

    console.print()
    console.print(Panel(f"[bold]{rule.id}[/bold]\n{rule.title}", title="DockRx Rule", border_style="blue"))
    console.print()

    if rule.reason:
        console.print("[bold]Why this matters[/bold]")
        console.print(rule.reason)
        console.print()

    if rule.estimated_saving:
        console.print("[bold]Typical savings[/bold]")
        if rule.estimated_saving.image_size:
            console.print(f"  Image: {rule.estimated_saving.image_size}")
        if rule.estimated_saving.build_time:
            console.print(f"  Build: {rule.estimated_saving.build_time}")
        console.print(f"  Confidence: {rule.estimated_saving.confidence}")
        console.print()

    console.print("[bold]Recommendation[/bold]")
    console.print(rule.recommendation.strip())
    console.print()

    if pres.suggested_fix:
        console.print("[bold]Suggested fix[/bold]")
        lang = "diff" if pres.suggested_fix.strip().startswith(("-", "+")) else "dockerfile"
        console.print(Syntax(pres.suggested_fix, lang, theme="monokai", padding=1))
        console.print()

    meta = Table(show_header=False, box=None)
    meta.add_column("k", style="dim")
    meta.add_column("v")
    meta.add_row("Severity", rule.severity.value)
    meta.add_row("Category", rule.category.value)
    meta.add_row("Pack", rule.pack)
    meta.add_row("Effort", pres.effort)
    meta.add_row("Difficulty", pres.difficulty)
    console.print(meta)

    if rule.references:
        console.print()
        console.print("[bold]References[/bold]")
        for ref in rule.references:
            console.print(f"  • {ref}")

    return True
