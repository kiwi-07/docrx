"""Shield-style SVG badge generator for Dockerfile health scores.

Usage from CLI:
    dockrx badge .                          # Print SVG to stdout
    dockrx badge Dockerfile --output badge.svg
    dockrx badge . --format markdown        # Print markdown image link
    dockrx badge . --format url             # Print shield.io URL

The badge shows the DockRx health grade (A+, A, B, C, D, F)
with appropriate colour coding, matching shield.io conventions.
"""

from __future__ import annotations

from dataclasses import dataclass

from dockrx.reporters.presentation import grade_for_score

# ═══════════════════════════════════════════════════════════════════════════════
# Shield.io colour palette (hex)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class BadgeStyle:
    """Visual configuration for a badge."""

    label_colour: str = "#555555"
    message_colour: str = "#4c1"
    label_text_colour: str = "#ffffff"
    message_text_colour: str = "#ffffff"
    height: int = 20
    font_size: int = 11
    label_padding: int = 6
    message_padding: int = 6
    corner_radius: int = 3


GRADE_COLOURS: dict[str, str] = {
    "A+": "#4c1",  # brightgreen
    "A": "#97ca00",  # green
    "B": "#a4a61d",  # yellowgreen
    "C": "#dfb317",  # yellow
    "D": "#fe7d37",  # orange
    "F": "#e05d44",  # red
}

SHIELD_STYLES: dict[str, BadgeStyle] = {
    "flat": BadgeStyle(corner_radius=3, height=20, font_size=11, label_padding=6, message_padding=6),
    "flat-square": BadgeStyle(corner_radius=0, height=20, font_size=11, label_padding=6, message_padding=6),
    "plastic": BadgeStyle(
        corner_radius=3,
        height=20,
        font_size=11,
        label_padding=6,
        message_padding=6,
        label_colour="#555555",
    ),
    "for-the-badge": BadgeStyle(
        corner_radius=4,
        height=28,
        font_size=12,
        label_padding=10,
        message_padding=10,
        label_colour="#555555",
        label_text_colour="#ffffff",
        message_text_colour="#ffffff",
    ),
}


def _grade_for_score_extended(score: int) -> str:
    """Return grade letter with optional plus for the badge.

    A+ at 95+ for that extra dopamine hit.
    """
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _escape_svg(text: str) -> str:
    """Escape text for safe embedding in SVG XML."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def render_badge_svg(
    score: int,
    *,
    label: str = "DockRx",
    style: str = "flat",
    findings_count: int | None = None,
) -> str:
    """Generate an SVG badge string for the given health score.

    Args:
        score: Overall health score (0-100).
        label: Text shown on the left side of the badge.
        style: Badge style — 'flat', 'flat-square', 'plastic', or 'for-the-badge'.
        findings_count: Optional number of findings to show in subtitle.

    Returns:
        SVG XML string.
    """
    style_cfg = SHIELD_STYLES.get(style, SHIELD_STYLES["flat"])
    grade = _grade_for_score_extended(score)
    grade_colour = GRADE_COLOURS.get(grade, "#555")

    # Calculate widths
    label_text = _escape_svg(label)
    grade_text = _escape_svg(grade)
    _, grade_name = grade_for_score(score)

    # Approximate character widths (monospace-ish for small fonts)
    char_width = 7
    label_width = max(len(label), 4) * char_width + style_cfg.label_padding * 2
    grade_width = max(len(grade_text), 1) * char_width + style_cfg.message_padding * 2

    total_width = label_width + grade_width
    h = style_cfg.height
    r = style_cfg.corner_radius

    # Title tooltip
    subtitle = f"  · {findings_count} findings" if findings_count is not None else ""
    tooltip = f"Dockerfile Health: {grade} ({grade_name}){subtitle}"

    # Build SVG
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{total_width}" height="{h}" role="img" aria-label="{label}: {grade}">
  <title>{_escape_svg(tooltip)}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#fff" stop-opacity=".7"/>
    <stop offset="100%" stop-color="#fff" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_width}" height="{h}" rx="{r}" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="{h}" fill="{style_cfg.label_colour}"/>
    <rect x="{label_width}" width="{grade_width}" height="{h}" fill="{grade_colour}"/>
    <rect width="{total_width}" height="{h}" fill="url(#s)"/>
  </g>
  <g fill="{style_cfg.label_text_colour}" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="{style_cfg.font_size}">
    <text x="{style_cfg.label_padding}" y="{h // 2 + 1}" textLength="{label_width - style_cfg.label_padding * 2}" lengthAdjust="spacingAndGlyphs">{label_text}</text>
    <text x="{label_width + style_cfg.message_padding}" y="{h // 2 + 1}" font-weight="bold" textLength="{grade_width - style_cfg.message_padding * 2}" lengthAdjust="spacingAndGlyphs" fill="{style_cfg.message_text_colour}">{grade_text}</text>
  </g>
</svg>"""

    return svg


def render_badge_markdown(score: int, *, style: str = "flat") -> str:
    """Render a markdown image tag for the badge.

    Uses an embedded data: URI so it works without hosting.
    """
    svg = render_badge_svg(score, style=style)
    import base64

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"![Dockerfile Health: {_grade_for_score_extended(score)}](data:image/svg+xml;base64,{encoded})"


def render_badge_shields_url(score: int, *, label: str = "DockRx", style: str = "flat") -> str:
    """Generate a shield.io dynamic badge URL.

    Useful for users who want to host their badge via shields.io.
    """
    from urllib.parse import quote

    grade = _grade_for_score_extended(score)
    colour = GRADE_COLOURS.get(grade, "#555").lstrip("#")
    return f"https://img.shields.io/badge/{quote(label)}-{grade}-{colour}?style={quote(style)}"


def render_badge(
    score: int,
    *,
    format: str = "svg",
    style: str = "flat",
    label: str = "DockRx",
    findings_count: int | None = None,
) -> str:
    """Render a health badge in the requested format.

    Args:
        score: Overall health score (0-100).
        format: Output format — 'svg', 'markdown', 'url', or 'shield-url'.
        style: Badge visual style.
        label: Label text on the left side of the badge.
        findings_count: Optional finding count for tooltip.

    Returns:
        String representation of the badge.

    Raises:
        ValueError: If an unsupported format is given.
    """
    valid_formats = {"svg", "markdown", "url", "shield-url"}
    if format not in valid_formats:
        raise ValueError(f"Unsupported badge format: {format!r}. Choose from: {', '.join(sorted(valid_formats))}")

    if format == "markdown":
        return render_badge_markdown(score, style=style)
    elif format in ("url", "shield-url"):
        return render_badge_shields_url(score, label=label, style=style)
    else:  # svg
        return render_badge_svg(score, label=label, style=style, findings_count=findings_count)
