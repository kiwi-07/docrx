"""Tests for the shield-style health badge generator."""

from __future__ import annotations

import pytest

from dockrx.reporters.badge import (
    GRADE_COLOURS,
    SHIELD_STYLES,
    _grade_for_score_extended,
    render_badge,
    render_badge_markdown,
    render_badge_shields_url,
    render_badge_svg,
)


def test_grade_for_score_extended() -> None:
    assert _grade_for_score_extended(100) == "A+"
    assert _grade_for_score_extended(95) == "A+"
    assert _grade_for_score_extended(94) == "A"
    assert _grade_for_score_extended(90) == "A"
    assert _grade_for_score_extended(85) == "B"
    assert _grade_for_score_extended(75) == "C"
    assert _grade_for_score_extended(65) == "D"
    assert _grade_for_score_extended(55) == "F"
    assert _grade_for_score_extended(0) == "F"


def test_render_badge_svg_is_valid_svg() -> None:
    svg = render_badge_svg(85, label="DockRx", style="flat")
    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    assert 'width="' in svg
    assert 'height="' in svg
    assert 'role="img"' in svg
    assert "DockRx" in svg
    assert "B" in svg  # grade for 85


def test_render_badge_svg_includes_findings() -> None:
    svg = render_badge_svg(72, findings_count=5)
    assert "5 findings" in svg


def test_render_badge_svg_includes_tooltip() -> None:
    svg = render_badge_svg(95)
    assert "title" in svg
    assert "Dockerfile Health" in svg
    assert "Excellent" in svg  # grade name for 95


def test_render_badge_svg_styles() -> None:
    for style in ("flat", "flat-square", "plastic", "for-the-badge"):
        svg = render_badge_svg(80, style=style)
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")
        assert f'height="{SHIELD_STYLES[style].height}"' in svg


def test_render_badge_svg_colours() -> None:
    for score, expected_grade in [(95, "A+"), (90, "A"), (80, "B"), (70, "C"), (60, "D"), (50, "F")]:
        svg = render_badge_svg(score)
        colour = GRADE_COLOURS[expected_grade]
        assert colour in svg, f"Expected colour {colour} for grade {expected_grade} at score {score}"


def test_render_badge_svg_aria() -> None:
    svg = render_badge_svg(100)
    assert 'aria-label="DockRx: A+"' in svg


def test_render_badge_markdown() -> None:
    md = render_badge_markdown(88)
    assert md.startswith("![Dockerfile Health:")
    assert "data:image/svg+xml;base64," in md
    assert md.endswith(")")


def test_render_badge_shields_url() -> None:
    url = render_badge_shields_url(92, label="DockRx", style="flat")
    assert url.startswith("https://img.shields.io/badge/")
    assert "DockRx" in url
    assert "A" in url  # grade for 92
    assert "style=flat" in url


def test_render_badge_svg() -> None:
    svg = render_badge(85, format="svg")
    assert svg.startswith("<svg")


def test_render_badge_markdown_via_format() -> None:
    result = render_badge(75, format="markdown")
    assert result.startswith("![Dockerfile Health:")


def test_render_badge_url() -> None:
    url = render_badge(65, format="url")
    assert url.startswith("https://img.shields.io/badge/")


def test_render_badge_shield_url() -> None:
    url = render_badge(55, format="shield-url")
    assert url.startswith("https://img.shields.io/badge/")


def test_render_badge_custom_label() -> None:
    svg = render_badge_svg(80, label="MyProject")
    assert "MyProject" in svg


def test_render_badge_invalid_format() -> None:
    with pytest.raises(ValueError, match="pdf"):
        render_badge(80, format="pdf")


def test_render_badge_all_grades_svg() -> None:
    """All grade letters should produce valid SVG."""
    for score in [100, 95, 90, 80, 70, 60, 50, 0]:
        svg = render_badge_svg(score)
        assert "xmlns" in svg
        assert svg.count("<svg") == 1
        assert svg.count("</svg>") == 1
