"""Shared Pydantic models for rules, findings, and reports."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Severity(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class Category(StrEnum):
    CACHE = "cache"
    SIZE = "size"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"
    BEST_PRACTICES = "best_practices"


class EstimatedSaving(BaseModel):
    build_time: str | None = None
    image_size: str | None = None
    confidence: str = "heuristic"


class DetectCondition(BaseModel):
    """A single instruction-matching condition in the YAML DSL."""

    instruction: str
    args_match: str | None = None
    stage: str | None = None  # "final" | "any" | stage name
    before: DetectCondition | None = None
    after: DetectCondition | None = None
    missing: bool = False  # true => instruction must NOT exist


class DetectSpec(BaseModel):
    """Boolean composition of detect conditions."""

    all: list[DetectCondition | DetectSpec] | None = None
    any: list[DetectCondition | DetectSpec] | None = None
    not_: DetectCondition | DetectSpec | None = Field(default=None, alias="not")

    model_config = {"populate_by_name": True, "extra": "forbid"}

    def model_post_init(self, __context: Any) -> None:
        if self.all is None and self.any is None and self.not_ is None:
            raise ValueError("DetectSpec requires one of: all, any, not")


class RuleMeta(BaseModel):
    """Metadata shared by YAML rules and Python plugins."""

    id: str
    title: str
    severity: Severity
    category: Category
    tags: list[str] = Field(default_factory=list)
    applies_to: list[str] = Field(default_factory=lambda: ["dockerfile"])
    recommendation: str
    estimated_saving: EstimatedSaving | None = None
    references: list[str] = Field(default_factory=list)
    pack: str = "builtin@0.1"
    reason: str | None = None


class YamlRule(RuleMeta):
    """Declarative rule loaded from YAML."""

    detect: DetectSpec


class Finding(BaseModel):
    rule_id: str
    title: str
    severity: Severity
    category: Category
    recommendation: str
    pack: str
    message: str | None = None
    reason: str | None = None
    estimated_saving: EstimatedSaving | None = None
    references: list[str] = Field(default_factory=list)
    stage: str | None = None
    line: int | None = None
    tags: list[str] = Field(default_factory=list)


class CategoryScore(BaseModel):
    name: Category
    score: int
    max_points: int
    weight: int


class ScoreReport(BaseModel):
    overall: int
    categories: list[CategoryScore]


class AnalysisReport(BaseModel):
    path: str
    score: ScoreReport
    findings: list[Finding]
    instruction_count: int = 0
    stage_count: int = 0
    meta: dict[str, Any] = Field(default_factory=dict)
