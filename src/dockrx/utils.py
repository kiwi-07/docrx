"""Shared utility functions used across DockRx modules."""

from __future__ import annotations

import re


def parse_effort_seconds(effort: str) -> int:
    """Parse a human-readable effort string into approximate seconds.

    Examples:
        "30 sec"  -> 30
        "2 min"   -> 120
        "5 min"   -> 300
        "10 min"  -> 600
    """
    if not effort:
        return 120
    effort_lower = effort.lower()
    m = re.search(r"(\d+)", effort_lower)
    if not m:
        return 120
    value = int(m.group(1))
    if "sec" in effort_lower:
        return value
    if "min" in effort_lower:
        return value * 60
    return 120


def stars_from_effort_seconds(seconds: int) -> str:
    """Convert effort seconds to a star-rating indicator.

    Short tasks get more stars.
    """
    minutes = seconds / 60
    if minutes <= 2:
        return "⭐⭐☆☆☆"
    if minutes <= 5:
        return "⭐⭐⭐☆☆"
    if minutes <= 10:
        return "⭐⭐☆☆☆"
    return "⭐☆☆☆☆"


def parse_mb_hint(text: str | None) -> float:
    """Parse a text hint that may contain MB values.

    Examples:
        "~100 MB" -> 100.0
        "~50-200 MB" -> 125.0
        "context upload often 100MB-1GB+" -> 0.0  (context upload, not image)
    """
    if not text:
        return 0.0
    if "context upload" in text.lower():
        return 0.0
    numbers = [int(n) for n in re.findall(r"\d+", text.replace(",", ""))]
    if not numbers:
        return 0.0
    if len(numbers) >= 2:
        return (numbers[0] + numbers[1]) / 2.0
    return float(numbers[0])


def parse_pct_hint(text: str | None) -> float:
    """Parse a text hint that may contain percentage values.

    Examples:
        "30-80%" -> 55.0
        "20-70%" -> 45.0
    """
    if not text:
        return 0.0
    numbers = [int(n) for n in re.findall(r"\d+", text)]
    if not numbers:
        return 0.0
    if len(numbers) >= 2:
        return (numbers[0] + numbers[1]) / 2.0
    return float(numbers[0])


def severity_weight(severity_value: str) -> int:
    """Return a numeric weight for sorting by severity."""
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}
    return order.get(severity_value, 99)
