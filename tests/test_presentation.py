"""Presentation layer tests."""

from pathlib import Path

from dockrx.engine import analyze
from dockrx.reporters.presentation import (
    build_diagnosis,
    enrich_findings,
    health_label,
    quick_wins,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_health_label_bands():
    assert health_label(95)[0] == "Excellent"
    assert health_label(80)[0] == "Good"
    assert health_label(65)[0] == "Fair"
    assert health_label(52)[0] == "Needs Attention"
    assert health_label(30)[0] == "Poor"


def test_enrich_sorts_by_roi():
    _, findings = analyze(EXAMPLES / "test")
    enriched = enrich_findings(findings)
    assert enriched[0].rank == 1
    assert enriched[0].roi_score >= enriched[-1].roi_score


def test_diagnosis_summary_counts():
    _, findings = analyze(EXAMPLES / "test")
    diag = build_diagnosis(findings)
    assert diag.total == len(findings)
    assert diag.high >= 1
    assert len(diag.top_opportunities) <= 3


def test_quick_wins_are_easy():
    _, findings = analyze(EXAMPLES / "test")
    enriched = enrich_findings(findings)
    wins = quick_wins(enriched)
    assert all(w.presentation.difficulty == "Easy" for w in wins)
