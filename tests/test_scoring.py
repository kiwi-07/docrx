"""Scoring model tests: the overall score must reflect every finding."""

from dockrx.models import Category, Finding, Severity
from dockrx.scoring import score_findings


def _finding(rule_id: str, severity: Severity, category: Category) -> Finding:
    return Finding(
        rule_id=rule_id,
        title=rule_id,
        severity=severity,
        category=category,
        recommendation="do the thing",
        pack="test",
    )


def test_fixing_a_finding_in_a_floored_category_moves_overall():
    # best_practices max is 10, but two HIGH findings (-12 each) exceed it.
    # Removing one must still raise the overall score even though the category
    # score stays floored at 0.
    two_highs = [
        _finding("A", Severity.HIGH, Category.BEST_PRACTICES),
        _finding("B", Severity.HIGH, Category.BEST_PRACTICES),
    ]
    one_high = two_highs[:1]

    score_two = score_findings(two_highs).overall
    score_one = score_findings(one_high).overall

    assert score_one > score_two


def test_category_score_is_still_floored_for_display():
    findings = [
        _finding("A", Severity.HIGH, Category.BEST_PRACTICES),
        _finding("B", Severity.HIGH, Category.BEST_PRACTICES),
    ]
    report = score_findings(findings)
    best = next(c for c in report.categories if c.name == Category.BEST_PRACTICES)
    assert best.score == 0  # never negative in the breakdown


def test_clean_dockerfile_scores_100():
    assert score_findings([]).overall == 100


def test_overall_never_negative():
    findings = [_finding(str(i), Severity.HIGH, Category.SECURITY) for i in range(20)]
    assert score_findings(findings).overall == 0
