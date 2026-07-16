"""JSON reporter."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from dockrx.reporters.presentation import (
    build_diagnosis,
    category_assessment,
    enrich_findings,
    health_label,
)

if TYPE_CHECKING:
    from dockrx.models import AnalysisReport


def render_json(report: AnalysisReport) -> str:
    label, emoji, _ = health_label(report.score.overall)
    diag = build_diagnosis(report.findings)
    enriched = enrich_findings(report.findings)

    payload = {
        "score": report.score.overall,
        "health": {"label": label, "emoji": emoji},
        "diagnosis": {
            "total": diag.total,
            "critical": diag.critical,
            "high": diag.high,
            "medium": diag.medium,
            "low": diag.low,
            "info": diag.info,
            "top_opportunities": diag.top_opportunities,
            "potential_image_mb": diag.potential_image_mb,
            "potential_build_pct": diag.potential_build_pct,
        },
        "categories": {
            c.name.value: {
                "score": c.score,
                "max": c.max_points,
                "weight": c.weight,
                "why": category_assessment(c.name, c.score, c.max_points, report.findings),
            }
            for c in report.score.categories
        },
        "path": report.path,
        "instruction_count": report.instruction_count,
        "stage_count": report.stage_count,
        "recommendations": [
            {
                "rank": e.rank,
                "roi_score": round(e.roi_score, 1),
                "id": f.rule_id,
                "severity": f.severity.value,
                "category": f.category.value,
                "title": f.title,
                "short_title": e.presentation.short_title,
                "recommendation": f.recommendation,
                "pack": f.pack,
                "line": f.line,
                "stage": f.stage,
                "impact": e.presentation.impact,
                "effort": e.presentation.effort,
                "difficulty": e.presentation.difficulty,
                "suggested_fix": e.presentation.suggested_fix,
                "estimated_saving": (f.estimated_saving.model_dump(exclude_none=True) if f.estimated_saving else None),
                "references": f.references,
                "tags": f.tags,
            }
            for e in enriched
            for f in [e.finding]
        ],
    }
    return json.dumps(payload, indent=2)
