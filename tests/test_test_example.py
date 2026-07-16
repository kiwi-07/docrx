"""Tests for examples/test Dockerfile and new gap-closing rules."""

from pathlib import Path

from dockrx.engine import analyze

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_analyze_test_example_flags_java_runtime_gaps():
    _, findings = analyze(EXAMPLES / "test")
    ids = {f.rule_id for f in findings}
    assert "DRX003" in ids  # missing USER
    assert "DRX005" in ids  # missing dockerignore
    assert "DRX018" in ids  # JDK runtime
    assert "DRX019" in ids  # debug networking tools
    assert "DRX023" in ids  # shell ENTRYPOINT exec
    # Good Maven layering — should not flag cache mistakes
    assert "DRX020" not in ids
    assert "DRX025" not in ids


def test_maven_bad_copy_triggers_drx020():
    dockerfile = EXAMPLES / "test" / "Dockerfile.maven-bad"
    _, findings = analyze(dockerfile)
    assert "DRX020" in {f.rule_id for f in findings}
