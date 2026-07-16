"""Tests for the Dockerfile formatter."""

from __future__ import annotations

from pathlib import Path

from dockrx.formatter import (
    format_dockerfile,
    format_dockerfile_diff,
    format_dockerfile_file,
    is_formatted,
)


def test_uppercases_instructions() -> None:
    raw = 'from alpine:3.19\nrun echo hello\ncmd ["echo", "hi"]\n'
    result = format_dockerfile(raw)
    assert result == 'FROM alpine:3.19\nRUN echo hello\nCMD ["echo", "hi"]\n'


def test_uppercases_mixed_case() -> None:
    raw = "From alpine:3.19\nrUn echo hello\n"
    result = format_dockerfile(raw)
    assert result == "FROM alpine:3.19\nRUN echo hello\n"


def test_removes_trailing_whitespace() -> None:
    raw = "FROM alpine:3.19   \nRUN echo hello  \n"
    result = format_dockerfile(raw)
    assert result == "FROM alpine:3.19\nRUN echo hello\n"


def test_preserves_comments() -> None:
    raw = "# This is a comment\nFROM alpine:3.19\n# Another comment\nRUN echo hello\n"
    result = format_dockerfile(raw)
    assert "# This is a comment" in result
    assert "# Another comment" in result


def test_normalizes_stage_spacing() -> None:
    raw = """FROM alpine:3.19 AS builder
RUN echo build



FROM alpine:3.19
RUN echo run
"""
    result = format_dockerfile(raw)
    # Verify: exactly two stages, one blank line separating them,
    # no double or triple blank lines
    assert result.count("\n\n") <= 1  # only the stage separation
    assert "\n\n\n" not in result  # no triple blank lines
    assert "FROM alpine:3.19 AS builder" in result
    assert "FROM alpine:3.19" in result
    assert "RUN echo build" in result
    assert "RUN echo run" in result


def test_handles_empty_file() -> None:
    assert format_dockerfile("") == "\n"


def test_handles_whitespace_only() -> None:
    assert format_dockerfile("   \n\n  \n") == "\n"


def test_strips_leading_trailing_empty_lines() -> None:
    raw = "\n\n\nFROM alpine\nRUN echo hi\n\n\n"
    result = format_dockerfile(raw)
    assert result == "FROM alpine\nRUN echo hi\n"
    assert not result.startswith("\n")


def test_preserves_complex_multistage() -> None:
    raw = """FROM node:22 AS builder
WORKDIR /app
COPY package.json .
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD [\"nginx\", \"-g\", \"daemon off;\"]
"""
    result = format_dockerfile(raw)
    # Should still have two stages with one blank line between
    assert "FROM node:22 AS builder" in result
    assert "FROM nginx:alpine" in result
    # Check single blank line between stages
    lines = result.splitlines()
    from_indices = [i for i, line in enumerate(lines) if line.startswith("FROM")]
    assert len(from_indices) == 2
    assert "\n\n\n" not in result


def test_preserves_continuation_lines() -> None:
    raw = """FROM alpine
RUN apk add --no-cache \
    curl \
    git \
    bash
"""
    result = format_dockerfile(raw)
    assert "RUN apk add --no-cache" in result
    assert "curl" in result
    assert "git" in result
    assert "bash" in result


def test_is_formatted_returns_true() -> None:
    raw = "FROM alpine:3.19\nRUN echo hello\n"
    formatted = format_dockerfile(raw)
    # Write it to a temp file and check
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix="Dockerfile", delete=False) as f:
        f.write(formatted)
        p = Path(f.name)
    try:
        assert is_formatted(p)
    finally:
        p.unlink()


def test_is_formatted_returns_false() -> None:
    raw = "from alpine:3.19\n"
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix="Dockerfile", delete=False) as f:
        f.write(raw)
        p = Path(f.name)
    try:
        assert not is_formatted(p)
    finally:
        p.unlink()


def test_format_dockerfile_diff_shows_changes() -> None:
    raw = "from alpine:3.19\n"
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix="Dockerfile", delete=False) as f:
        f.write(raw)
        p = Path(f.name)
    try:
        diff = format_dockerfile_diff(p)
        assert diff
        assert "FROM" in diff
        assert "from" in diff
    finally:
        p.unlink()


def test_format_dockerfile_diff_empty_when_formatted() -> None:
    raw = "FROM alpine:3.19\n"
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix="Dockerfile", delete=False) as f:
        f.write(raw)
        p = Path(f.name)
    try:
        diff = format_dockerfile_diff(p)
        assert diff == ""
    finally:
        p.unlink()


def test_uppercases_from_with_as() -> None:
    raw = "from ubuntu:22.04 as base\n"
    result = format_dockerfile(raw)
    assert result == "FROM ubuntu:22.04 as base\n"


def test_uppercases_expose_healthcheck() -> None:
    raw = "expose 8080\nhealthcheck cmd curl || exit 1\n"
    result = format_dockerfile(raw)
    assert result == "EXPOSE 8080\nHEALTHCHECK cmd curl || exit 1\n"


def test_handles_windows_line_endings() -> None:
    raw = "from alpine:3.19\r\nrun echo hello\r\n"
    result = format_dockerfile(raw)
    assert result == "FROM alpine:3.19\nRUN echo hello\n"
    assert "\r\n" not in result


def test_preserves_label_values() -> None:
    raw = 'LABEL org.opencontainers.image.title="my-app"\n'
    result = format_dockerfile(raw)
    assert result == 'LABEL org.opencontainers.image.title="my-app"\n'


def test_does_not_change_already_formatted() -> None:
    raw = "FROM alpine:3.19\nRUN echo hello\n"
    result = format_dockerfile(raw)
    assert result == raw + ""  # it already ends with newline? let's check
    # Actually our function adds a trailing newline if missing
    # raw already has a trailing newline
    assert result == raw


def test_print_versions_and_alpine() -> None:
    raw = """FROM python:3.12-slim
RUN pip install -r requirements.txt
COPY . /app
CMD ["python", "/app/main.py"]
"""
    result = format_dockerfile(raw)
    assert "FROM python:3.12-slim" in result
    assert 'CMD ["python", "/app/main.py"]' in result


def test_format_dockerfile_file(tmp_path: Path) -> None:
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("from alpine\n")
    result = format_dockerfile_file(dockerfile)
    assert result == "FROM alpine\n"
