"""Parser unit tests."""

from dockrx.parser import parse_dockerfile_text


def test_parses_multistage_and_lines():
    text = """\
# syntax=docker/dockerfile:1
FROM golang:1.22 AS builder
WORKDIR /src
COPY . .
RUN go build -o app

FROM gcr.io/distroless/static
COPY --from=builder /src/app /app
ENTRYPOINT ["/app"]
"""
    graph = parse_dockerfile_text(text)
    assert graph.syntax == "docker/dockerfile:1"
    assert graph.stages == ["builder", "stage1"]
    assert graph.final_stage == "stage1"
    assert graph.by_instruction("FROM")[0].line == 2
    assert any(i.instruction == "COPY" and "--from=builder" in i.args for i in graph.instructions)


def test_backslash_continuation():
    text = """\
FROM alpine
RUN apk add --no-cache \\
    curl \\
    git
"""
    graph = parse_dockerfile_text(text)
    runs = graph.by_instruction("RUN")
    assert len(runs) == 1
    assert "curl" in runs[0].args and "git" in runs[0].args
