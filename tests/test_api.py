"""Web API tests for the /api/analyze playground endpoint."""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.index import app  # noqa: E402

client = TestClient(app)

GOOD = "FROM alpine:3.20\nUSER nobody\nHEALTHCHECK CMD true\nLABEL org.opencontainers.image.title=x\nCMD [\"true\"]\n"


def _ids(payload: dict) -> set[str]:
    return {r["id"] for r in payload["recommendations"]}


def test_has_dockerignore_suppresses_drx005():
    without = client.post("/api/analyze", json={"dockerfile": GOOD}).json()
    with_di = client.post("/api/analyze", json={"dockerfile": GOOD, "has_dockerignore": True}).json()

    assert "DRX005" in _ids(without)
    assert "DRX005" not in _ids(with_di)
    assert with_di["score"] >= without["score"]


def test_invalid_dockerfile_rejected():
    res = client.post("/api/analyze", json={"dockerfile": "hello world\nnot a dockerfile\n"})
    assert res.status_code == 422


def test_blank_dockerfile_rejected():
    res = client.post("/api/analyze", json={"dockerfile": "   "})
    assert res.status_code == 422


def test_health_ok():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_cors_headers_present():
    res = client.get("/api/health", headers={"Origin": "https://example.com"})
    assert res.headers.get("access-control-allow-origin") in {"*", "https://example.com"}


def test_fix_preview_returns_downloadable_dockerfile():
    source = "FROM alpine:3.20\nCMD [\"true\"]\n"
    res = client.post("/api/fix", json={"dockerfile": source, "rule_ids": ["DRX004"]})
    assert res.status_code == 200
    payload = res.json()
    assert "DRX004" in payload["applied_rule_ids"]
    assert payload["dockerfile"] != source
    assert payload["diff"]


def test_fix_preview_respects_selected_rules():
    source = "FROM alpine:3.20\nCMD [\"true\"]\n"
    res = client.post("/api/fix", json={"dockerfile": source, "rule_ids": []})
    assert res.status_code == 200
    assert res.json()["applied_rule_ids"] == []
    assert res.json()["dockerfile"] == source


def test_format_preview():
    res = client.post("/api/format", json={"dockerfile": "from alpine:3.20  \n"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["changed"] is True
    assert payload["dockerfile"] == "FROM alpine:3.20\n"
    assert payload["diff"]


def test_compare_preview():
    before = "FROM python:latest\nCOPY . .\n"
    after = "FROM python:3.12-slim\nUSER nobody\nHEALTHCHECK CMD true\n"
    res = client.post(
        "/api/compare",
        json={
            "before": before,
            "after": after,
            "before_has_dockerignore": True,
            "after_has_dockerignore": True,
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["before"]["score"] != payload["after"]["score"]
    assert "resolved_rule_ids" in payload["delta"]


def test_badge_preview():
    res = client.post(
        "/api/badge",
        json={
            "dockerfile": GOOD,
            "has_dockerignore": True,
            "label": "Example",
            "style": "flat-square",
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["svg"].startswith("<svg")
    assert payload["markdown"].startswith("![Dockerfile Health:")
    assert payload["url"].startswith("https://img.shields.io/")
