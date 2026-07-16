from __future__ import annotations

import shutil
from pathlib import Path

from dockrx.fixer import apply_fix_plan, build_fix_plan


def test_fix_plan_applies_jdk_to_jre_and_dockerignore_and_removes_debug_tools(tmp_path: Path) -> None:
    src = Path(__file__).resolve().parents[1] / "examples" / "test"
    dst = tmp_path / "test"
    shutil.copytree(src, dst)

    plan = build_fix_plan(dst, limit=3)
    assert "DRX018" in plan.applied_rule_ids
    assert "DRX005" in plan.applied_rule_ids
    assert "DRX019" in plan.applied_rule_ids

    apply_fix_plan(plan)

    fixed = (dst / "Dockerfile.fixed").read_text(encoding="utf-8")
    assert "eclipse-temurin:21-jre-jammy" in fixed
    assert "iputils-ping" not in fixed
    assert "telnet" not in fixed
    assert "traceroute" not in fixed
    assert "dnsutils" not in fixed
    # Keep curl for HEALTHCHECK support.
    assert "curl" in fixed

    dockerignore = (dst / ".dockerignore").read_text(encoding="utf-8")
    assert ".git" in dockerignore
    assert "node_modules" in dockerignore
