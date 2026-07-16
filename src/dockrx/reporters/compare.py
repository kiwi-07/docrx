"""Compare two DockRx analysis reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dockrx.reporters.presentation import aggregate_impact, grade_for_score, health_label

if TYPE_CHECKING:
    from dockrx.models import AnalysisReport


@dataclass
class CompareSummary:
    before_score: int
    after_score: int
    score_delta: int
    before_grade: str
    after_grade: str
    improved_rule_ids: list[str]
    new_rule_ids: list[str]


def build_compare_summary(before: AnalysisReport, after: AnalysisReport) -> CompareSummary:
    before_ids = {f.rule_id for f in before.findings}
    after_ids = {f.rule_id for f in after.findings}
    return CompareSummary(
        before_score=before.score.overall,
        after_score=after.score.overall,
        score_delta=after.score.overall - before.score.overall,
        before_grade=grade_for_score(before.score.overall)[0],
        after_grade=grade_for_score(after.score.overall)[0],
        improved_rule_ids=sorted(before_ids - after_ids),
        new_rule_ids=sorted(after_ids - before_ids),
    )


def render_compare(before: AnalysisReport, after: AnalysisReport, console: Console | None = None) -> None:
    console = console or Console()
    summary = build_compare_summary(before, after)
    before_health = health_label(before.score.overall)[0]
    after_health = health_label(after.score.overall)[0]

    console.print()
    console.print(
        Panel(
            "\n".join(
                [
                    f"[bold]Health[/bold]  {before.score.overall} → {after.score.overall}",
                    f"[dim]{before_health} ({summary.before_grade})[/dim] → [bold]{after_health} ({summary.after_grade})[/bold]",
                    f"[bold green]{summary.score_delta:+} points[/bold green]"
                    if summary.score_delta >= 0
                    else f"[bold red]{summary.score_delta} points[/bold red]",
                ]
            ),
            title="[bold]DockRx Compare[/bold]",
            subtitle=f"{before.path}  →  {after.path}",
            border_style="blue",
        )
    )
    console.print()

    category_table = Table(title="Category Delta", show_header=True, header_style="bold")
    category_table.add_column("Category")
    category_table.add_column("Before", justify="right")
    category_table.add_column("After", justify="right")
    category_table.add_column("Delta", justify="right")
    after_map = {c.name: c for c in after.score.categories}
    for before_cat in before.score.categories:
        after_cat = after_map[before_cat.name]
        delta = after_cat.score - before_cat.score
        delta_text = f"{delta:+}"
        if delta > 0:
            delta_text = f"[green]{delta_text}[/green]"
        elif delta < 0:
            delta_text = f"[red]{delta_text}[/red]"
        category_table.add_row(
            before_cat.name.value.replace("_", " ").title(),
            f"{before_cat.score}/{before_cat.max_points}",
            f"{after_cat.score}/{after_cat.max_points}",
            delta_text,
        )
    console.print(category_table)
    console.print()

    before_impact = aggregate_impact(before.findings)
    after_impact = aggregate_impact(after.findings)
    impact_table = Table(title="Estimated Outcome Delta", show_header=True, header_style="bold")
    impact_table.add_column("Metric")
    impact_table.add_column("Before")
    impact_table.add_column("After")
    impact_table.add_row("Image", before_impact.image_size or "n/a", after_impact.image_size or "n/a")
    impact_table.add_row("Build", before_impact.build_speed or "n/a", after_impact.build_speed or "n/a")
    impact_table.add_row("Security risks", str(before_impact.security_risks), str(after_impact.security_risks))
    impact_table.add_row("Best practices", str(before_impact.best_practices), str(after_impact.best_practices))
    console.print(impact_table)
    console.print()

    if summary.improved_rule_ids:
        console.print(
            Panel(
                "\n".join(f"• {rule_id}" for rule_id in summary.improved_rule_ids[:10]),
                title="[bold green]Resolved Findings[/bold green]",
                border_style="green",
            )
        )
        console.print()
    if summary.new_rule_ids:
        console.print(
            Panel(
                "\n".join(f"• {rule_id}" for rule_id in summary.new_rule_ids[:10]),
                title="[bold yellow]New Findings[/bold yellow]",
                border_style="yellow",
            )
        )


def render_compare_json(before: AnalysisReport, after: AnalysisReport) -> str:
    summary = build_compare_summary(before, after)
    after_map = {c.name: c for c in after.score.categories}
    payload = {
        "before": {
            "path": before.path,
            "score": before.score.overall,
            "grade": summary.before_grade,
        },
        "after": {
            "path": after.path,
            "score": after.score.overall,
            "grade": summary.after_grade,
        },
        "delta": {
            "score": summary.score_delta,
            "categories": {cat.name.value: after_map[cat.name].score - cat.score for cat in before.score.categories},
            "resolved_rule_ids": summary.improved_rule_ids,
            "new_rule_ids": summary.new_rule_ids,
        },
    }
    return json.dumps(payload, indent=2)
