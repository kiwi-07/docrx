"""Score findings into weighted category and overall scores."""

from __future__ import annotations

from dockrx.models import Category, CategoryScore, Finding, ScoreReport, Severity

WEIGHTS: dict[Category, int] = {
    Category.CACHE: 30,
    Category.SIZE: 25,
    Category.SECURITY: 20,
    Category.MAINTAINABILITY: 15,
    Category.BEST_PRACTICES: 10,
}

SEVERITY_PENALTY: dict[Severity, int] = {
    Severity.HIGH: 12,
    Severity.MEDIUM: 7,
    Severity.LOW: 3,
    Severity.INFO: 1,
}


def score_findings(findings: list[Finding]) -> ScoreReport:
    remaining = {cat: weight for cat, weight in WEIGHTS.items()}

    for finding in findings:
        penalty = SEVERITY_PENALTY[finding.severity]
        cat = finding.category
        remaining[cat] = max(0, remaining[cat] - penalty)

    categories = [
        CategoryScore(
            name=cat,
            score=remaining[cat],
            max_points=weight,
            weight=weight,
        )
        for cat, weight in WEIGHTS.items()
    ]
    overall = sum(remaining.values())
    return ScoreReport(overall=overall, categories=categories)
