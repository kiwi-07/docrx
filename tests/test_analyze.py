"""Engine and scoring tests."""

from pathlib import Path

from dockrx.engine import analyze
from dockrx.scoring import score_findings

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_analyze_bad_example_finds_high_severity():
    _, findings = analyze(EXAMPLES / "bad")
    ids = {f.rule_id for f in findings}
    assert "DRX001" in ids or "DRX017" in ids  # copy before deps
    assert "DRX003" in ids  # missing USER
    assert "DRX005" in ids  # missing dockerignore
    assert "DRX009" in ids  # secret in ENV
    score = score_findings(findings)
    assert score.overall < 80


def test_analyze_good_example_scores_higher():
    _, bad_findings = analyze(EXAMPLES / "bad")
    _, good_findings = analyze(EXAMPLES / "good")
    assert score_findings(good_findings).overall > score_findings(bad_findings).overall
    good_ids = {f.rule_id for f in good_findings}
    assert "DRX003" not in good_ids
    assert "DRX005" not in good_ids
