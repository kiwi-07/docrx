"""Smoke tests for the rich terminal reporter.

`render_rich` is the primary human-facing CLI output. These tests render into a
recording Console and assert on the captured text so the render path stays covered
without asserting exact layout.
"""

from pathlib import Path

from rich.console import Console

from dockrx.cli import _build_report
from dockrx.reporters.rich_report import render_rich

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _render(path: Path) -> str:
    console = Console(record=True, width=100, force_terminal=True)
    render_rich(_build_report(path), console=console)
    return console.export_text()


def test_render_rich_report_with_findings():
    out = _render(EXAMPLES / "test")
    assert "Overall Health" in out
    assert "/ 100" in out
    assert "Prioritized by ROI" in out
    # Category breakdown is always rendered.
    assert "Category Breakdown" in out


def test_render_rich_report_clean_dockerfile():
    out = _render(EXAMPLES / "good")
    assert "Overall Health" in out
    # A clean Dockerfile has no ROI section and shows the all-clear message.
    assert "No issues found" in out
    assert "Prioritized by ROI" not in out


def test_render_rich_accepts_default_console(capsys):
    # Should not raise when no console is supplied (covers the default branch).
    render_rich(_build_report(EXAMPLES / "test"))
    assert "Overall Health" in capsys.readouterr().out
