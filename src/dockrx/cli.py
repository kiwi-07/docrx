"""DockRx CLI."""

from __future__ import annotations

import difflib
import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from dockrx.config import get_config_value, load_config
from dockrx.engine import analyze
from dockrx.fixer import apply_fix_plan, build_fix_plan
from dockrx.models import AnalysisReport, Severity
from dockrx.reporters import (
    render_badge,
    render_compare,
    render_compare_json,
    render_explain,
    render_json,
    render_rich,
)
from dockrx.scoring import score_findings

logger = logging.getLogger("dockrx.cli")

_SEVERITY_RANK: dict[str, int] = {
    "HIGH": 0,
    "MEDIUM": 1,
    "LOW": 2,
    "INFO": 3,
}


_SEVERITY_STYLE: dict[Severity, str] = {
    Severity.HIGH: "bold red",
    Severity.MEDIUM: "yellow",
    Severity.LOW: "cyan",
    Severity.INFO: "dim",
}


def _severity_style(severity: Severity) -> str:
    """Return a Rich markup style string for the given severity."""
    return _SEVERITY_STYLE.get(severity, "dim")


def _config_root_for(path: Path) -> Path:
    return path if path.is_dir() else path.parent


def _should_fail_on_severity(findings: list, threshold: str | None) -> bool:
    if threshold is None:
        return False
    normalized = str(threshold).strip().upper()
    if normalized in {"", "NONE", "NULL", "FALSE", "0"}:
        return False
    rank = _SEVERITY_RANK.get(normalized)
    if rank is None:
        return False
    return any(_SEVERITY_RANK.get(f.severity.value, 99) <= rank for f in findings)


app = typer.Typer(
    name="dockrx",
    help="DockRx — analyze Dockerfiles for size, cache, and security issues.",
    no_args_is_help=True,
    invoke_without_command=False,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        from dockrx import __version__

        console.print(f"dockrx {__version__}")
        raise typer.Exit()


def _build_report(path: Path) -> AnalysisReport:
    logger.debug("Building report for %s", path)
    ctx, findings = analyze(path)
    return AnalysisReport(
        path=str(ctx.dockerfile_path),
        score=score_findings(findings),
        findings=findings,
        instruction_count=len(ctx.graph.instructions),
        stage_count=len(ctx.graph.stages),
    )


@app.callback()
def _root(
    version: bool | None = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """DockRx CLI."""


@app.command("analyze")
def analyze_cmd(
    path: Path = typer.Argument(
        Path("."),
        help="Dockerfile path or project directory",
        exists=True,
        readable=True,
        resolve_path=True,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit JSON report",
    ),
    score_only: bool = typer.Option(
        False,
        "--score-only",
        help="Print only the overall score",
    ),
    badge: bool = typer.Option(
        False,
        "--badge",
        help="Output a health-grade SVG badge instead of the full report",
    ),
) -> None:
    """Analyze a Dockerfile and print recommendations."""
    try:
        report = _build_report(path)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    if badge:
        badge_svg = render_badge(
            report.score.overall,
            format="svg",
            findings_count=len(report.findings),
        )
        typer.echo(badge_svg)
        raise typer.Exit(code=0)

    if score_only:
        typer.echo(report.score.overall)
        raise typer.Exit(code=0)

    if json_output:
        typer.echo(render_json(report))
    else:
        render_rich(report, console=console)

    cfg = load_config(_config_root_for(path))
    threshold = cfg.get("fail-on-severity", "HIGH")
    if _should_fail_on_severity(report.findings, threshold):
        raise typer.Exit(code=1)


@app.command("explain")
def explain_cmd(
    rule_id: str = typer.Argument(..., help="Rule id, e.g. DRX018"),
    path: Path = typer.Option(
        Path("."),
        "--path",
        "-p",
        help="Project path for loading local rule overrides",
        exists=True,
        resolve_path=True,
    ),
) -> None:
    """Explain a rule and show suggested fixes."""
    project_root = path if path.is_dir() else path.parent
    if not render_explain(rule_id, console=console, project_root=project_root):
        console.print(f"[red]Unknown rule: {rule_id}[/red]")
        raise typer.Exit(code=2)


@app.command("compare")
def compare_cmd(
    before: Path = typer.Argument(
        ...,
        help="Original Dockerfile path or project directory",
        exists=True,
        readable=True,
        resolve_path=True,
    ),
    after: Path = typer.Argument(
        ...,
        help="Updated Dockerfile path or project directory",
        exists=True,
        readable=True,
        resolve_path=True,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit JSON comparison",
    ),
) -> None:
    """Compare two Dockerfiles or project directories."""
    try:
        before_report = _build_report(before)
        after_report = _build_report(after)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    if json_output:
        typer.echo(render_compare_json(before_report, after_report))
    else:
        render_compare(before_report, after_report, console=console)


@app.command("fix")
def fix_cmd(
    path: Path = typer.Argument(
        Path("."),
        help="Project path containing a Dockerfile",
        exists=True,
        readable=True,
        resolve_path=True,
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        help="Max number of changes to apply (default: config default-fix-limit or 3)",
        min=1,
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Apply changes without prompting",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show preview only; do not write any files",
    ),
) -> None:
    """Rewrite the Dockerfile into a non-destructive fixed version."""
    if limit is None:
        limit = int(get_config_value("default-fix-limit", 3, _config_root_for(path)))
    plan = build_fix_plan(path, limit=limit)
    applied = plan.applied_rule_ids

    if not applied:
        console.print("[green]No supported fixes found.[/green]")
        raise typer.Exit(code=0)

    console.print()
    console.print(
        Panel(
            "\n".join([f"• {rid}" for rid in applied]),
            title="[bold]Planned fixes[/bold]",
            border_style="blue",
        )
    )
    console.print()

    if plan.dockerignore_added:
        console.print("[bold]Will create .dockerignore[/bold]")
        console.print(Syntax(plan.dockerignore_after or "", "dockerfile", theme="monokai"))
        console.print()

    console.print("[bold]Dockerfile diff preview[/bold]")
    console.print(Syntax(plan.dockerfile_diff or "", "diff", theme="monokai"))
    console.print()

    if dry_run:
        console.print("[yellow]Dry run: nothing was written.[/yellow]")
        raise typer.Exit(code=0)

    if yes:
        apply_fix_plan(plan)
        console.print(f"[green]Wrote {plan.fixed_path}[/green]")
        raise typer.Exit(code=0)

    prompt = f"Apply {len(applied)} changes? [y/N] "
    ans = input(prompt).strip().lower()
    if ans not in {"y", "yes"}:
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit(code=0)

    apply_fix_plan(plan)
    console.print(f"[green]Wrote {plan.fixed_path}[/green]")
    raise typer.Exit(code=0)


@app.command("badge")
def badge_cmd(
    path: Path = typer.Argument(
        Path("."),
        help="Dockerfile path or project directory",
        exists=True,
        readable=True,
        resolve_path=True,
    ),
    output_path: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Write SVG badge to file instead of stdout",
    ),
    format: str = typer.Option(
        "svg",
        "--format",
        "-f",
        help="Output format: svg, markdown, url",
    ),
    style: str = typer.Option(
        "flat",
        "--style",
        "-s",
        help="Badge style: flat, flat-square, plastic, for-the-badge",
    ),
    label: str = typer.Option(
        "DockRx",
        "--label",
        "-l",
        help="Label text on the left side of the badge",
    ),
) -> None:
    """Generate a health-grade badge for a Dockerfile.

    Outputs a shield.io-style SVG badge showing the Dockerfile's
    health grade (A+, A, B, C, D, F). Use --format markdown to get
    an embeddable markdown image tag, or --format url for a shields.io URL.

    Examples:
        dockrx badge . --output badge.svg
        dockrx badge Dockerfile --format markdown
        dockrx badge . --format url --style for-the-badge
    """
    try:
        report = _build_report(path)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    score = report.score.overall
    findings_count = len(report.findings)

    try:
        result = render_badge(
            score,
            format=format,
            style=style,
            label=label,
            findings_count=findings_count,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    if output_path:
        output_file = Path(output_path)
        output_file.write_text(result, encoding="utf-8")
        console.print(f"[green]Badge written to {output_file}[/green]")
    else:
        typer.echo(result)


@app.command("suggest")
def suggest_cmd(
    path: Path = typer.Argument(
        Path("."),
        help="Project path containing a Dockerfile",
        exists=True,
        readable=True,
        resolve_path=True,
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Apply all suggestions without prompting",
    ),
) -> None:
    """Walk through fix suggestions one by one.

    Interactively preview and apply each suggested fix.
    For each finding, you can:
      - [a]pply the fix
      - [s]kip this finding
      - [q]uit the session

    Examples:
        dockrx suggest .
        dockrx suggest Dockerfile --yes
    """
    from dockrx.fixer import FIX_HANDLERS
    from dockrx.reporters.presentation import enrich_findings, presentation_for

    ctx, findings = analyze(path)

    if not findings:
        console.print("[green]No issues found. Looking good![/green]")
        raise typer.Exit(code=0)

    enriched = enrich_findings(findings)
    supported_ids = {h.rule_id for h in FIX_HANDLERS}

    # Filter to fixable findings, sorted by ROI
    fixable = [e for e in enriched if e.finding.rule_id in supported_ids]

    if not fixable:
        console.print("[yellow]No auto-fixable issues found (try 'dockrx analyze' for recommendations).[/yellow]")
        raise typer.Exit(code=0)

    console.print(f"[bold]DockRx Suggest[/bold] — {len(fixable)} fixable issues found")
    console.print()

    # Read original file content for diff previews
    dockerfile = ctx.dockerfile_path
    dockerfile_before = dockerfile.read_text(encoding="utf-8-sig")
    dockerfile_after = dockerfile_before
    applied_ids: list[str] = []
    skipped_ids: list[str] = []

    for idx, item in enumerate(fixable, start=1):
        finding = item.finding
        pres = presentation_for(finding)
        rid = finding.rule_id
        handler = next((h for h in FIX_HANDLERS if h.rule_id == rid), None)
        if not handler:
            skipped_ids.append(rid)
            continue

        console.print()
        console.print(
            f"[bold]#{idx}/{len(fixable)}[/bold]  [{_severity_style(finding.severity)}]{finding.severity.value}[/]  [bold]{finding.title}[/bold]"
        )
        console.print(f"  Rule: {rid}  ·  {pres.effort}  ·  {pres.difficulty}")
        if pres.impact:
            console.print(f"  Impact: {pres.impact}")
        if finding.recommendation:
            console.print(f"  [dim]→ {finding.recommendation.strip()}[/dim]")

        # Compute diff for this specific fix
        dockerfile_after = handler.handler(dockerfile_after, ctx)

        diff_lines = list(
            difflib.unified_diff(
                dockerfile_before.splitlines(keepends=False),
                dockerfile_after.splitlines(keepends=False),
                fromfile=str(dockerfile.name),
                tofile=str(dockerfile.name),
                lineterm="",
                n=2,
            )
        )
        diff_text = "\n".join(diff_lines)

        if diff_text:
            console.print()
            console.print("  [bold]Changes:[/bold]")
            for line in diff_lines:
                if line.startswith("+"):
                    console.print(f"  [green]{line}[/green]")
                elif line.startswith("-"):
                    console.print(f"  [red]{line}[/red]")
                elif line.startswith("@"):
                    console.print(f"  [dim]{line}[/dim]")
                else:
                    console.print(f"  {line}")

        if yes:
            applied_ids.append(rid)
            console.print("  [green]✓ Applied[/green]")
            dockerfile_before = dockerfile_after
            continue

        console.print()
        ans = input("  Apply this fix? [a]pply / [s]kip / [q]uit [a]: ").strip().lower()

        if ans in ("", "a", "apply"):
            applied_ids.append(rid)
            console.print("  [green]✓ Applied[/green]")
            dockerfile_before = dockerfile_after
        elif ans in ("q", "quit"):
            console.print("  [yellow]Quit[/yellow]")
            break
        else:
            skipped_ids.append(rid)
            console.print("  [dim]Skipped[/dim]")
            # Roll back the after content
            dockerfile_after = dockerfile_before

    # Summary
    console.print()
    console.print("═" * 40)
    console.print("[bold]Summary[/bold]")
    console.print(f"  Applied: {len(applied_ids)} fix(es)")
    console.print(f"  Skipped: {len(skipped_ids)}")
    if applied_ids:
        for rid in applied_ids:
            console.print(f"    [green]✓ {rid}[/green]")
    if skipped_ids:
        for rid in skipped_ids:
            console.print(f"    [dim]— {rid}[/dim]")

    if not applied_ids:
        console.print("[yellow]No fixes applied.[/yellow]")
        raise typer.Exit(code=0)

    fixed_path = dockerfile.with_name(f"{dockerfile.name}.fixed")
    if yes:
        fixed_path.write_text(dockerfile_before, encoding="utf-8")
        console.print(f"[green]Written to {fixed_path}[/green]")
        raise typer.Exit(code=0)

    console.print()
    write_ans = input(f"Write changes to {dockerfile.name}.fixed? [y/N]: ").strip().lower()
    if write_ans in ("y", "yes"):
        fixed_path.write_text(dockerfile_before, encoding="utf-8")
        console.print(f"[green]Written to {fixed_path}[/green]")
    else:
        console.print("[yellow]Changes not saved.[/yellow]")


@app.command("format")
def format_cmd(
    path: Path = typer.Argument(
        Path("."),
        help="Dockerfile path or project directory",
        exists=True,
        readable=True,
        resolve_path=True,
    ),
    write: bool = typer.Option(
        False,
        "--write",
        "-w",
        help="Overwrite the Dockerfile in place with formatted version",
    ),
    check: bool = typer.Option(
        False,
        "--check",
        help="Exit with code 1 if the Dockerfile is not formatted (CI-mode)",
    ),
    diff: bool = typer.Option(
        False,
        "--diff",
        help="Show a unified diff of changes",
    ),
) -> None:
    """Format a Dockerfile for consistent style.

    Normalizes instruction casing (→ UPPERCASE), trailing whitespace,
    blank lines between stages, and continuation-line indentation.

    Examples:
        dockrx format Dockerfile              # Print formatted version
        dockrx format . --write               # Overwrite in place
        dockrx format Dockerfile --check       # CI check (exit 1 if unformatted)
        dockrx format Dockerfile --diff        # Show unified diff
    """
    from dockrx.formatter import format_dockerfile_diff, format_dockerfile_file, is_formatted

    dockerfile = path if path.is_file() else (path / "Dockerfile")
    if not dockerfile.is_file():
        candidates = [path / n for n in ("Dockerfile", "dockerfile", "Containerfile")]
        dockerfile = next((c for c in candidates if c.is_file()), None)
        if dockerfile is None:
            console.print("[red]Dockerfile not found[/red]")
            raise typer.Exit(code=2)

    if check:
        if is_formatted(dockerfile):
            console.print(f"[green]{dockerfile} is correctly formatted[/green]")
            raise typer.Exit(code=0)
        else:
            console.print(f"[red]{dockerfile} needs formatting — run 'dockrx format --write'[/red]")
            raise typer.Exit(code=1)

    if diff:
        dif = format_dockerfile_diff(dockerfile)
        if dif:
            typer.echo(dif)
        else:
            console.print(f"[green]{dockerfile} is already formatted[/green]")
        raise typer.Exit(code=0)

    formatted = format_dockerfile_file(dockerfile)

    if write:
        dockerfile.write_text(formatted, encoding="utf-8")
        console.print(f"[green]Formatted {dockerfile}[/green]")
    else:
        typer.echo(formatted)
