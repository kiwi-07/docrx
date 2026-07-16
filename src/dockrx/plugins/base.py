"""Plugin helpers."""

from __future__ import annotations

from dockrx.models import Category, EstimatedSaving, Finding, Severity


def finding_from_meta(
    meta: dict,
    *,
    message: str | None = None,
    line: int | None = None,
    stage: str | None = None,
) -> Finding:
    saving = meta.get("estimated_saving")
    return Finding(
        rule_id=meta["id"],
        title=meta["title"],
        severity=Severity(meta["severity"]),
        category=Category(meta["category"]),
        recommendation=meta["recommendation"].strip(),
        pack=meta.get("pack", "builtin@0.1"),
        message=message,
        reason=meta.get("reason"),
        estimated_saving=EstimatedSaving(**saving) if saving else None,
        references=meta.get("references", []),
        stage=stage,
        line=line,
        tags=meta.get("tags", []),
    )
