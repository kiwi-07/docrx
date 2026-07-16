"""Enrich findings with ROI, fixes, and presentation metadata."""

from __future__ import annotations

from dataclasses import dataclass, field

from dockrx.models import Category, Finding, Severity
from dockrx.scoring import SEVERITY_PENALTY
from dockrx.utils import parse_effort_seconds, parse_mb_hint, parse_pct_hint

_DEFAULT_HEALTH_THRESHOLDS: dict[str, int] = {
    "excellent": 90,
    "good": 75,
    "fair": 60,
    "needs-attention": 40,
}


def _health_bands(thresholds: dict[str, int] | None = None) -> list[tuple[int, str, str, str]]:
    t = {**_DEFAULT_HEALTH_THRESHOLDS, **(thresholds or {})}
    return [
        (int(t["excellent"]), "Excellent", "🟢", "green"),
        (int(t["good"]), "Good", "🟢", "green"),
        (int(t["fair"]), "Fair", "🟡", "yellow"),
        (int(t["needs-attention"]), "Needs Attention", "🟠", "bright_yellow"),
        (0, "Poor", "🔴", "red"),
    ]


# Backwards-compatible default bands used by tests and callers that don't pass config.
HEALTH_BANDS: list[tuple[int, str, str, str]] = _health_bands()

SEVERITY_ORDER = {
    Severity.HIGH: 0,
    Severity.MEDIUM: 1,
    Severity.LOW: 2,
    Severity.INFO: 3,
}

SEVERITY_WEIGHT = {
    Severity.HIGH: 40,
    Severity.MEDIUM: 25,
    Severity.LOW: 10,
    Severity.INFO: 5,
}


@dataclass
class RulePresentation:
    short_title: str
    effort: str
    difficulty: str
    impact: str
    risk: str | None = None
    roi_boost: int = 0
    suggested_fix: str | None = None


# Curated presentation per rule — snippets users can paste.
RULE_PRESENTATION: dict[str, RulePresentation] = {
    "DRX001": RulePresentation(
        short_title="Reorder COPY for npm cache",
        effort="2 min",
        difficulty="Easy",
        impact="Build speed",
        suggested_fix="""COPY package.json package-lock.json ./
RUN npm ci
COPY . .""",
    ),
    "DRX003": RulePresentation(
        short_title="Run as non-root",
        effort="30 sec",
        difficulty="Easy",
        impact="Security",
        risk="High",
        roi_boost=30,
        suggested_fix="""RUN adduser --system --no-create-home appuser
USER appuser""",
    ),
    "DRX004": RulePresentation(
        short_title="Add HEALTHCHECK",
        effort="1 min",
        difficulty="Easy",
        impact="Reliability",
        suggested_fix="HEALTHCHECK CMD curl -f http://localhost:8080/health || exit 1",
    ),
    "DRX005": RulePresentation(
        short_title="Add .dockerignore",
        effort="30 sec",
        difficulty="Easy",
        impact="Build speed",
        roi_boost=50,
        suggested_fix=""".git
node_modules
dist
target
.venv
.env
*.log""",
    ),
    "DRX006": RulePresentation(
        short_title="Add LABEL metadata",
        effort="1 min",
        difficulty="Easy",
        impact="Maintainability",
        suggested_fix="""LABEL org.opencontainers.image.title="my-app"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.description="My service\"""",
    ),
    "DRX007": RulePresentation(
        short_title="Clean APT cache",
        effort="30 sec",
        difficulty="Easy",
        impact="Image size",
        suggested_fix="""RUN apt-get update \\
    && apt-get install -y --no-install-recommends curl \\
    && rm -rf /var/lib/apt/lists/*""",
    ),
    "DRX008": RulePresentation(
        short_title="Use COPY instead of ADD",
        effort="30 sec",
        difficulty="Easy",
        impact="Maintainability",
        suggested_fix="COPY app.tar.gz /app/",
    ),
    "DRX009": RulePresentation(
        short_title="Remove secrets from ENV",
        effort="5 min",
        difficulty="Medium",
        impact="Security",
        risk="Critical",
        suggested_fix="# Use runtime secrets or BuildKit:\n# RUN --mount=type=secret,id=api_key ...",
    ),
    "DRX010": RulePresentation(
        short_title="Disable pip cache",
        effort="30 sec",
        difficulty="Easy",
        impact="Image size",
        suggested_fix="RUN pip install --no-cache-dir -r requirements.txt",
    ),
    "DRX011": RulePresentation(
        short_title="Clean npm cache",
        effort="30 sec",
        difficulty="Easy",
        impact="Image size",
        suggested_fix="RUN npm ci && npm cache clean --force",
    ),
    "DRX012": RulePresentation(
        short_title="Use apk --no-cache",
        effort="30 sec",
        difficulty="Easy",
        impact="Image size",
        suggested_fix="RUN apk add --no-cache curl",
    ),
    "DRX013": RulePresentation(
        short_title="Switch to slim base image",
        effort="2 min",
        difficulty="Easy",
        impact="Image size",
        roi_boost=40,
        suggested_fix="FROM python:3.13-slim",
    ),
    "DRX014": RulePresentation(
        short_title="Stop running as root",
        effort="30 sec",
        difficulty="Easy",
        impact="Security",
        risk="High",
        suggested_fix="USER appuser",
    ),
    "DRX015": RulePresentation(
        short_title="Narrow COPY paths",
        effort="2 min",
        difficulty="Easy",
        impact="Build speed",
        suggested_fix="COPY src/ ./src/",
    ),
    "DRX016": RulePresentation(
        short_title="Combine RUN layers",
        effort="1 min",
        difficulty="Easy",
        impact="Image size",
        suggested_fix="RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*",
    ),
    "DRX017": RulePresentation(
        short_title="Reorder COPY for pip cache",
        effort="2 min",
        difficulty="Easy",
        impact="Build speed",
        suggested_fix="""COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .""",
    ),
    "DRX018": RulePresentation(
        short_title="Switch JDK → JRE runtime",
        effort="2 min",
        difficulty="Easy",
        impact="Image size",
        roi_boost=60,
        suggested_fix="""-FROM eclipse-temurin:21-jdk-jammy
+FROM eclipse-temurin:21-jre-jammy""",
    ),
    "DRX019": RulePresentation(
        short_title="Remove debug networking tools",
        effort="1 min",
        difficulty="Easy",
        impact="Security",
        risk="Medium",
        suggested_fix="# Remove from apt-get install:\n# iputils-ping telnet traceroute netcat net-tools",
    ),
    "DRX020": RulePresentation(
        short_title="Copy POMs before Maven build",
        effort="5 min",
        difficulty="Medium",
        impact="Build speed",
        suggested_fix="""COPY pom.xml .
COPY module/pom.xml module/pom.xml
RUN mvn dependency:go-offline
COPY module/src module/src
RUN mvn package""",
    ),
    "DRX021": RulePresentation(
        short_title="Copy Gradle files before build",
        effort="5 min",
        difficulty="Medium",
        impact="Build speed",
        suggested_fix="""COPY gradlew settings.gradle build.gradle ./
COPY gradle gradle
RUN ./gradlew dependencies --no-daemon
COPY src src""",
    ),
    "DRX022": RulePresentation(
        short_title="Copy go.mod before go build",
        effort="2 min",
        difficulty="Easy",
        impact="Build speed",
        suggested_fix="""COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o /app .""",
    ),
    "DRX023": RulePresentation(
        short_title="Use exec-form ENTRYPOINT",
        effort="2 min",
        difficulty="Easy",
        impact="Maintainability",
        suggested_fix='ENTRYPOINT ["java", "-jar", "/app/app.jar"]',
    ),
    "DRX024": RulePresentation(
        short_title="Move build tools to builder stage",
        effort="10 min",
        difficulty="Medium",
        impact="Image size",
        roi_boost=45,
        suggested_fix="""FROM maven:3.9 AS builder
RUN mvn package

FROM eclipse-temurin:21-jre
COPY --from=builder /app/target/app.jar /app.jar""",
    ),
    "DRX025": RulePresentation(
        short_title="Add Maven POM layer",
        effort="5 min",
        difficulty="Medium",
        impact="Build speed",
        suggested_fix="COPY pom.xml .\nRUN mvn dependency:go-offline",
    ),
    "DRX026": RulePresentation(
        short_title="Move compilers to builder stage",
        effort="5 min",
        difficulty="Medium",
        impact="Image size",
        suggested_fix="# Install gcc/make in a builder stage, not the final runtime image",
    ),
    "DRX027": RulePresentation(
        short_title="Copy Cargo manifests first",
        effort="3 min",
        difficulty="Medium",
        impact="Build speed",
        suggested_fix="""COPY Cargo.toml Cargo.lock ./
RUN cargo fetch
COPY src src
RUN cargo build --release""",
    ),
}


@dataclass
class DiagnosisSummary:
    total: int
    critical: int
    high: int
    medium: int
    low: int
    info: int
    top_opportunities: list[str] = field(default_factory=list)
    potential_image_mb: str | None = None
    potential_build_pct: str | None = None
    security_level: str | None = None
    maintainability_level: str | None = None


@dataclass
class AggregateImpact:
    image_size: str | None = None
    build_speed: str | None = None
    security_risks: int = 0
    best_practices: int = 0
    confidence: str | None = None
    confidence_reason: str | None = None


@dataclass
class EnrichedFinding:
    finding: Finding
    presentation: RulePresentation
    roi_score: float
    rank: int = 0


def health_label(score: int, thresholds: dict[str, int] | None = None) -> tuple[str, str, str]:
    """Return (label, emoji, color) for a score.

    When thresholds is omitted, loads `[tool.dockrx].health-thresholds` if present.
    """
    if thresholds is None:
        try:
            from dockrx.config import get_config_value

            cfg_t = get_config_value("health-thresholds")
            if isinstance(cfg_t, dict):
                thresholds = cfg_t
        except Exception:
            thresholds = None
    bands = _health_bands(thresholds)
    for threshold, label, emoji, color in bands:
        if score >= threshold:
            return label, emoji, color
    return "Poor", "🔴", "red"


def grade_for_score(score: int) -> tuple[str, str]:
    """Return (grade_letter, grade_name)."""
    if score >= 90:
        return "A", "Excellent"
    if score >= 80:
        return "B", "Great"
    if score >= 70:
        return "C", "Fair"
    if score >= 60:
        return "D", "Needs Attention"
    return "F", "Poor"


# Re-export shared helpers for backwards compatibility
_parse_mb_hint = parse_mb_hint
_parse_pct_hint = parse_pct_hint
_effort_seconds = parse_effort_seconds


def presentation_for(finding: Finding) -> RulePresentation:
    if finding.rule_id in RULE_PRESENTATION:
        return RULE_PRESENTATION[finding.rule_id]
    return RulePresentation(
        short_title=finding.title,
        effort="2 min",
        difficulty="Medium",
        impact=finding.category.value.replace("_", " ").title(),
    )


def roi_score(finding: Finding, pres: RulePresentation) -> float:
    score = float(SEVERITY_WEIGHT[finding.severity])
    if finding.estimated_saving:
        score += _parse_mb_hint(finding.estimated_saving.image_size) * 1.5
        score += _parse_pct_hint(finding.estimated_saving.build_time) * 0.8
    score += pres.roi_boost
    # Quick wins: high impact, low effort
    score += max(0, 120 - _effort_seconds(pres.effort)) / 10
    return score


def enrich_findings(findings: list[Finding]) -> list[EnrichedFinding]:
    enriched = []
    for f in findings:
        pres = presentation_for(f)
        enriched.append(EnrichedFinding(finding=f, presentation=pres, roi_score=roi_score(f, pres)))
    enriched.sort(key=lambda e: (-e.roi_score, SEVERITY_ORDER[e.finding.severity], e.finding.rule_id))
    for i, item in enumerate(enriched, start=1):
        item.rank = i
    return enriched


def quick_wins(enriched: list[EnrichedFinding], limit: int = 4) -> list[EnrichedFinding]:
    """Findings that are easy and fast."""
    candidates = [
        e for e in enriched if e.presentation.difficulty == "Easy" and _effort_seconds(e.presentation.effort) <= 120
    ]
    candidates.sort(key=lambda e: (-e.roi_score, _effort_seconds(e.presentation.effort)))
    return candidates[:limit]


def category_assessment(
    category: Category,
    score: int,
    max_points: int,
    findings: list[Finding],
) -> str:
    if score == max_points:
        return "Excellent"
    cat_findings = [f for f in findings if f.category == category]
    if not cat_findings:
        return "Room to improve"
    titles = [presentation_for(f).short_title for f in cat_findings[:2]]
    return "; ".join(titles)


def build_diagnosis(findings: list[Finding]) -> DiagnosisSummary:
    counts = {s: 0 for s in Severity}
    for f in findings:
        counts[f.severity] += 1

    enriched = enrich_findings(findings)
    top_opportunities = [e.presentation.short_title for e in enriched[:3]]

    image_vals = [_parse_mb_hint(f.estimated_saving.image_size if f.estimated_saving else None) for f in findings]
    image_vals = [v for v in image_vals if v > 0]
    potential_image = None
    if image_vals:
        lo = int(min(image_vals))
        hi = int(sum(image_vals))
        potential_image = f"↓ {lo}-{hi} MB"

    build_vals = [_parse_pct_hint(f.estimated_saving.build_time if f.estimated_saving else None) for f in findings]
    build_vals = [v for v in build_vals if v > 0]
    potential_build = None
    if build_vals:
        potential_build = f"↑ {int(min(build_vals))}-{int(max(build_vals))}%"

    sec_high = sum(1 for f in findings if f.category == Category.SECURITY and f.severity == Severity.HIGH)
    security_level = "High" if sec_high >= 2 else "Medium" if sec_high == 1 else "Low" if findings else None

    maint = [f for f in findings if f.category == Category.MAINTAINABILITY]
    maintainability_level = "Medium" if maint else None

    return DiagnosisSummary(
        total=len(findings),
        critical=0,  # reserved for future CRITICAL severity
        high=counts[Severity.HIGH],
        medium=counts[Severity.MEDIUM],
        low=counts[Severity.LOW],
        info=counts[Severity.INFO],
        top_opportunities=top_opportunities,
        potential_image_mb=potential_image,
        potential_build_pct=potential_build,
        security_level=security_level,
        maintainability_level=maintainability_level,
    )


def lost_points(findings: list[Finding]) -> list[tuple[str, int]]:
    """Aggregate the score deductions by user-facing cause."""
    totals: dict[str, int] = {}
    for finding in findings:
        label = presentation_for(finding).short_title
        totals[label] = totals.get(label, 0) + SEVERITY_PENALTY[finding.severity]
    return sorted(totals.items(), key=lambda item: (-item[1], item[0]))


def lost_points_detailed(
    findings: list[Finding],
    *,
    limit: int = 8,
) -> list[tuple[str, int, Category, Severity, str, str]]:
    """Return detailed lost points rows.

    Tuple fields:
      (title, points_lost, category, severity, reason, impact_group)
    """
    rows = []
    for f in findings:
        pres = presentation_for(f)
        points = SEVERITY_PENALTY[f.severity]
        impact_group = "Build Performance"
        if pres.impact.lower() == "security":
            impact_group = "Security"
        elif pres.impact.lower() == "reliability":
            impact_group = "Reliability"
        elif pres.impact.lower() == "maintainability":
            impact_group = "Maintainability"
        rows.append(
            (
                pres.short_title,
                points,
                f.category,
                f.severity,
                f.reason or "",
                impact_group,
            )
        )

    rows.sort(key=lambda r: (-r[1], SEVERITY_ORDER[r[3]], r[0]))
    return rows[:limit]


def aggregate_impact(findings: list[Finding]) -> AggregateImpact:
    image_total = 0.0
    build_total = 0.0
    security_count = 0
    best_practices = 0
    confidence_values: set[str] = set()

    for finding in findings:
        if finding.estimated_saving:
            image_total += _parse_mb_hint(finding.estimated_saving.image_size)
            build_total += _parse_pct_hint(finding.estimated_saving.build_time)
            confidence_values.add(finding.estimated_saving.confidence)
        if finding.category == Category.SECURITY:
            security_count += 1
        if finding.category == Category.BEST_PRACTICES:
            best_practices += 1

    image_size = f"↓ ~{int(image_total)} MB" if image_total else None
    build_speed = f"↑ ~{int(build_total)}%" if build_total else None

    confidence = None
    confidence_reason = None
    if confidence_values:
        if confidence_values == {"heuristic"}:
            confidence = "Heuristic"
            confidence_reason = "All estimates are heuristic in Milestone 1."
        else:
            confidence = "Mixed"
            confidence_reason = "Some estimates are measured/stronger than heuristic."

    return AggregateImpact(
        image_size=image_size,
        build_speed=build_speed,
        security_risks=security_count,
        best_practices=best_practices,
        confidence=confidence,
        confidence_reason=confidence_reason,
    )


def grouped_treatment_plan(enriched: list[EnrichedFinding]) -> list[tuple[str, list[EnrichedFinding]]]:
    groups: list[tuple[str, list[EnrichedFinding]]] = []
    buckets: dict[str, list[EnrichedFinding]] = {
        "Performance": [],
        "Security": [],
        "Reliability": [],
        "Maintainability": [],
    }
    for item in enriched:
        impact = item.presentation.impact.lower()
        if impact in {"image size", "build speed"}:
            buckets["Performance"].append(item)
        elif impact == "security":
            buckets["Security"].append(item)
        elif impact == "reliability":
            buckets["Reliability"].append(item)
        else:
            buckets["Maintainability"].append(item)
    for name in ("Performance", "Security", "Reliability", "Maintainability"):
        if buckets[name]:
            groups.append((name, buckets[name]))
    return groups


def summary_sentence(findings: list[Finding]) -> str:
    if not findings:
        return "This Dockerfile already looks healthy. No major improvement areas were detected."

    enriched = enrich_findings(findings)
    impact = aggregate_impact(findings)
    top = [item.presentation.short_title for item in enriched[:2]]

    parts = ["This Dockerfile is primarily held back by " + " and ".join(top).lower() + "."]
    improvements: list[str] = []
    if impact.image_size:
        improvements.append(f"reduce image size by {impact.image_size.replace('↓ ', '')}")
    if impact.build_speed:
        improvements.append(f"improve build performance by {impact.build_speed.replace('↑ ', '')}")
    if improvements:
        parts.append("Applying the top recommendations should " + " and ".join(improvements) + ".")
    return " ".join(parts)


def prescription_items(enriched: list[EnrichedFinding], limit: int = 5) -> list[str]:
    return [e.presentation.short_title for e in enriched[:limit]]


def health_bar(score: int, width: int = 20) -> str:
    filled = round(score / 100 * width)
    return "█" * filled + "░" * (width - filled)
