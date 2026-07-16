"""Rich terminal reporter — diagnosis-oriented output."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from dockrx.models import AnalysisReport, Severity
from dockrx.reporters.presentation import (
    EnrichedFinding,
    aggregate_impact,
    build_diagnosis,
    category_assessment,
    enrich_findings,
    grade_for_score,
    grouped_treatment_plan,
    health_bar,
    health_label,
    lost_points_detailed,
    quick_wins,
    summary_sentence,
)
from dockrx.utils import parse_effort_seconds, stars_from_effort_seconds

SEVERITY_STYLE = {
    Severity.HIGH: "bold red",
    Severity.MEDIUM: "yellow",
    Severity.LOW: "cyan",
    Severity.INFO: "dim",
}

CATEGORY_ICONS = {
    "cache": "🟢",
    "size": "🟠",
    "security": "🔴",
    "maintainability": "🔵",
    "best_practices": "🟣",
}


def _render_compact_header(report: AnalysisReport, enriched: list[EnrichedFinding]) -> Panel:
    score = report.score.overall
    label, emoji, color = health_label(score)
    grade_letter, grade_name = grade_for_score(score)
    diag = build_diagnosis(report.findings)
    wins = quick_wins(enriched, limit=3)

    bar = health_bar(score)
    gauge_lines = [
        "[bold]Overall Health[/bold]",
        "",
        f"{bar}",
        f"{score} / 100",
        f"{emoji} {label}  ·  Grade: {grade_letter} ({grade_name})",
    ]

    counts_line = f"{diag.total} findings  ·  {diag.high} High  ·  {diag.medium} Medium  ·  {diag.low} Low"

    lines = [
        "\n".join(gauge_lines),
        "",
        counts_line,
    ]
    if wins:
        lines.extend(["", "[bold]Quick Wins[/bold]"])
        for idx, win in enumerate(wins, start=1):
            lines.append(
                f"{idx}. {win.presentation.short_title}  "
                f"[green]{_impact_hint(win)}[/green]  "
                f"[dim]{win.presentation.effort}[/dim]"
            )
    return Panel("\n".join(lines), title="[bold]DockRx[/bold]", subtitle=str(report.path), border_style=color)


def _impact_hint(item: EnrichedFinding) -> str:
    finding = item.finding
    if finding.estimated_saving:
        if finding.estimated_saving.image_size and "context upload" not in finding.estimated_saving.image_size.lower():
            return f"↓ {finding.estimated_saving.image_size}"
        if finding.estimated_saving.build_time:
            return f"↑ {finding.estimated_saving.build_time}"
    if item.presentation.risk:
        return item.presentation.impact
    return item.presentation.impact


def _render_categories(report: AnalysisReport) -> Table:
    table = Table(title="Category Breakdown", show_header=True, header_style="bold")
    table.add_column("Category", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Why")
    for cat in report.score.categories:
        why = category_assessment(cat.name, cat.score, cat.max_points, report.findings)
        icon = CATEGORY_ICONS.get(cat.name.value, "•")
        table.add_row(
            f"{icon} {cat.name.value.replace('_', ' ').title()}",
            f"{cat.score}/{cat.max_points}",
            why,
        )
    return table


def _render_score_breakdown(report: AnalysisReport) -> Panel | None:
    deductions = lost_points_detailed(report.findings, limit=6)
    if not deductions:
        return None
    lines = []
    for title, points, _category, severity, reason, group in deductions:
        lines.append(f"-{points:>2}  {title}")
        if reason:
            lines.append(f"   Reason: {reason}")
        lines.append(f"   Category: {group}")
        lines.append(f"   Weight: {severity.value} (-{points} points)")
        lines.append("")
    # Trim last empty line.
    if lines and lines[-1] == "":
        lines.pop()
    return Panel("\n".join(lines), title="[bold]Lost Points[/bold]", border_style="red")


# Re-export shared helpers for backwards compatibility
_parse_effort_seconds = parse_effort_seconds
_stars_from_seconds = stars_from_effort_seconds


def _render_overall_goal(report: AnalysisReport, enriched: list[EnrichedFinding]) -> Panel | None:
    if not enriched:
        return None

    # MVP estimate: apply top findings by ROI.
    selected = enriched[:5]
    total_penalty = sum(
        {Severity.HIGH: 12, Severity.MEDIUM: 7, Severity.LOW: 3, Severity.INFO: 1}[i.finding.severity] for i in selected
    )
    # Penalties are an upper bound (Milestone 1 is heuristic), so we scale down.
    effective_penalty = round(total_penalty * 0.6)
    predicted = min(100, report.score.overall + effective_penalty)

    total_seconds = sum(_parse_effort_seconds(i.presentation.effort) for i in selected)
    stars = _stars_from_seconds(total_seconds)
    minutes = max(1, round(total_seconds / 60))

    return Panel(
        "\n".join(
            [
                "[bold]Overall[/bold]",
                f"Estimated effort: {minutes} minutes {stars}",
                f"Expected score improvement: {report.score.overall} → {predicted}",
            ]
        ),
        border_style="green",
    )


def _render_estimated_results(report: AnalysisReport) -> Panel | None:
    impact = aggregate_impact(report.findings)
    rows = []
    if impact.image_size:
        rows.append(f"[green]{impact.image_size}[/green] image size")
    if impact.build_speed:
        rows.append(f"[green]{impact.build_speed}[/green] faster builds")
    if impact.security_risks:
        rows.append(f"[red]↓ {impact.security_risks}[/red] security risks")
    if impact.best_practices:
        rows.append(f"[blue]+{impact.best_practices}[/blue] best-practice fixes")
    if impact.confidence:
        rows.append(f"[dim]Confidence: {impact.confidence}[/dim]")
    if impact.confidence_reason:
        rows.append(f"[dim]{impact.confidence_reason}[/dim]")
    if not rows:
        return None
    return Panel("\n".join(rows), title="[bold]Estimated Results[/bold]", border_style="green")


def _render_treatment_plan(enriched: list[EnrichedFinding]) -> Panel | None:
    groups = grouped_treatment_plan(enriched)
    if not groups:
        return None
    lines: list[str] = []
    for idx, (group_name, items) in enumerate(groups):
        if idx:
            lines.append("")
        lines.append(f"[bold]{group_name}[/bold]")
        for item in items[:3]:
            lines.append(f"✓ {item.presentation.short_title}")
    return Panel("\n".join(lines), title="[bold]Treatment Plan[/bold]", border_style="magenta")


def _render_summary(report: AnalysisReport) -> Panel:
    return Panel(summary_sentence(report.findings), title="[bold]Summary[/bold]", border_style="blue")


def _render_finding(console: Console, item: EnrichedFinding) -> None:
    f = item.finding
    pres = item.presentation
    style = SEVERITY_STYLE[f.severity]

    console.print(f"[bold]#{item.rank}[/bold]  [{style}]{f.severity.value}[/{style}]  [bold]{pres.short_title}[/bold]")
    console.print(f"  Rule: {f.rule_id} · pack: {f.pack}")
    if f.line:
        console.print(f"  [dim]Dockerfile:{f.line}[/dim]")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("key", style="dim")
    table.add_column("val")
    table.add_row("Impact", pres.impact)
    if pres.risk:
        table.add_row("Risk", pres.risk)
    table.add_row("Difficulty", pres.difficulty)
    table.add_row("Time", pres.effort)
    if f.estimated_saving:
        if f.estimated_saving.image_size:
            table.add_row("Estimated", f"↓ {f.estimated_saving.image_size}")
        if f.estimated_saving.build_time:
            table.add_row("Build gain", f"↑ {f.estimated_saving.build_time}")
    console.print(table)

    if f.reason:
        console.print(f"  [dim]Why:[/dim] {f.reason}")

    if pres.suggested_fix:
        console.print("  [bold]Suggested fix[/bold]")
        lang = (
            "diff"
            if pres.suggested_fix.strip().startswith("-") or pres.suggested_fix.strip().startswith("+")
            else "dockerfile"
        )
        console.print(
            Panel(
                Syntax(pres.suggested_fix, lang, theme="monokai", padding=1),
                title="[bold]Copy & Paste[/bold]",
                border_style="blue",
            )
        )

    console.print()


def render_rich(report: AnalysisReport, console: Console | None = None) -> None:
    console = console or Console()
    enriched = enrich_findings(report.findings)

    console.print()
    console.print(_render_compact_header(report, enriched))
    console.print()

    score_breakdown = _render_score_breakdown(report)
    if score_breakdown:
        console.print(score_breakdown)
        console.print()

    estimated = _render_estimated_results(report)
    if estimated:
        console.print(estimated)
        console.print()

    console.print(_render_summary(report))
    console.print()

    treatment = _render_treatment_plan(enriched)
    if treatment:
        console.print(treatment)
        console.print()

    goal = _render_overall_goal(report, enriched)
    if goal:
        console.print(goal)
        console.print()

    console.print(_render_categories(report))
    console.print()

    if not enriched:
        console.print("[green]No issues found. Looking good.[/green]")
        return

    console.print("[bold]Prioritized by ROI[/bold]")
    console.print()
    for item in enriched:
        _render_finding(console, item)
