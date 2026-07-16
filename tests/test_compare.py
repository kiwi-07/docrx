from __future__ import annotations

from io import StringIO
from pathlib import Path

from rich.console import Console

from dockrx.engine import analyze
from dockrx.models import AnalysisReport
from dockrx.reporters.compare import build_compare_summary, render_compare, render_compare_json
from dockrx.scoring import score_findings

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _report(path: Path) -> AnalysisReport:
    ctx, findings = analyze(path)
    return AnalysisReport(
        path=str(ctx.dockerfile_path),
        score=score_findings(findings),
        findings=findings,
        instruction_count=len(ctx.graph.instructions),
        stage_count=len(ctx.graph.stages),
    )


def test_compare_summary_bad_to_good_improves_score() -> None:
    before = _report(EXAMPLES / "bad")
    after = _report(EXAMPLES / "good")
    summary = build_compare_summary(before, after)
    assert summary.score_delta > 0
    assert "DRX003" in summary.improved_rule_ids
    assert "DRX005" in summary.improved_rule_ids


def test_render_compare_outputs_health_delta() -> None:
    before = _report(EXAMPLES / "bad")
    after = _report(EXAMPLES / "good")
    out = StringIO()
    console = Console(file=out, width=120, force_terminal=True)
    render_compare(before, after, console=console)
    text = out.getvalue()
    assert "DockRx Compare" in text
    assert "Health" in text
    assert "Resolved Findings" in text


def test_render_compare_json_contains_delta() -> None:
    before = _report(EXAMPLES / "bad")
    after = _report(EXAMPLES / "good")
    payload = render_compare_json(before, after)
    assert '"score"' in payload
    assert '"resolved_rule_ids"' in payload
