"""Explain command tests."""

from io import StringIO

from rich.console import Console

from dockrx.reporters.explain import render_explain


def test_explain_known_rule():
    out = StringIO()
    console = Console(file=out, width=120, force_terminal=True)
    ok = render_explain("DRX018", console=console)
    assert ok
    text = out.getvalue()
    assert "DRX018" in text
    assert "JRE" in text or "JDK" in text


def test_explain_unknown_rule():
    out = StringIO()
    console = Console(file=out, width=80)
    ok = render_explain("DRX999", console=console)
    assert not ok
