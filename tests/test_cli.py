"""CLI behavior tests: exit codes, flag validation, and input validation."""

from pathlib import Path

from typer.testing import CliRunner

from dockrx.cli import app

runner = CliRunner()
EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_score_only_honors_fail_on_severity():
    # examples/bad has HIGH findings; --score-only must still exit 1.
    result = runner.invoke(app, ["analyze", str(EXAMPLES / "bad"), "--score-only"])
    assert result.exit_code == 1
    assert result.stdout.strip().splitlines()[-1].isdigit()


def test_badge_honors_fail_on_severity():
    result = runner.invoke(app, ["analyze", str(EXAMPLES / "bad"), "--badge"])
    assert result.exit_code == 1


def test_good_example_score_only_exits_zero():
    result = runner.invoke(app, ["analyze", str(EXAMPLES / "good"), "--score-only"])
    assert result.exit_code == 0


def test_analyze_output_flags_mutually_exclusive():
    result = runner.invoke(app, ["analyze", str(EXAMPLES / "bad"), "--json", "--score-only"])
    assert result.exit_code == 2


def test_explain_unknown_rule_exits_one():
    result = runner.invoke(app, ["explain", "DRX999"])
    assert result.exit_code == 1


def test_analyze_rejects_non_dockerfile(tmp_path: Path):
    (tmp_path / "Dockerfile").write_text("this is not a dockerfile\n")
    result = runner.invoke(app, ["analyze", str(tmp_path)])
    assert result.exit_code == 2


def test_analyze_rejects_empty_dockerfile(tmp_path: Path):
    (tmp_path / "Dockerfile").write_text("")
    result = runner.invoke(app, ["analyze", str(tmp_path)])
    assert result.exit_code == 2


def test_format_check_and_write_are_mutually_exclusive(tmp_path: Path):
    df = tmp_path / "Dockerfile"
    df.write_text("from alpine:3.20\n")
    result = runner.invoke(app, ["format", str(df), "--check", "--write"])
    assert result.exit_code == 2


def test_fix_refuses_prompt_in_non_interactive(tmp_path: Path):
    df = tmp_path / "Dockerfile"
    df.write_text("FROM openjdk:17\nCMD [\"java\"]\n")
    # No --yes and no TTY: must refuse instead of aborting on EOF.
    result = runner.invoke(app, ["fix", str(tmp_path)])
    assert result.exit_code == 2
