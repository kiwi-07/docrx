"""JSON reporter tests."""

import json
from pathlib import Path

from dockrx.cli import _build_report
from dockrx.reporters.json_report import render_json

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_render_json_is_valid_json():
    report = _build_report(EXAMPLES / "test")
    payload = json.loads(render_json(report))
    assert payload["score"] == report.score.overall
    assert payload["diagnosis"]["total"] == len(report.findings)
    assert len(payload["recommendations"]) == len(report.findings)
