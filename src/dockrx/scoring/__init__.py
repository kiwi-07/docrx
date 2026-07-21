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
    # Accumulate the full penalty per category (no per-category flooring here) so
    # that the overall score reflects every finding. Flooring only at the category
    # level would silently discard penalties once a small category (e.g.
    # best_practices, max 10) is exhausted, making fixes appear to change nothing.
    penalties = {cat: 0 for cat in WEIGHTS}
    for finding in findings:
        penalties[finding.category] += SEVERITY_PENALTY[finding.severity]

    categories = [
        CategoryScore(
            name=cat,
            score=max(0, weight - penalties[cat]),
            max_points=weight,
            weight=weight,
        )
        for cat, weight in WEIGHTS.items()
    ]

    total_weight = sum(WEIGHTS.values())
    total_penalty = sum(penalties.values())
    overall = max(0, total_weight - total_penalty)
    return ScoreReport(overall=overall, categories=categories)
