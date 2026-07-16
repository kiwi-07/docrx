"""Regression tests for real-world false-positive fixes."""

from pathlib import Path

from dockrx.context import AnalysisContext
from dockrx.engine import analyze
from dockrx.parser import parse_dockerfile_text
from dockrx.plugins.go_copy_order import check as check_go
from dockrx.plugins.unpinned_latest import check as check_latest
from dockrx.plugins.user_root import check as check_user_root

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _ctx_from_text(text: str, name: str = "Dockerfile") -> AnalysisContext:
    graph = parse_dockerfile_text(text)
    root = EXAMPLES / "good"
    return AnalysisContext(
        root=root,
        dockerfile_path=root / name,
        graph=graph,
        has_dockerignore=True,
    )


def test_go_copy_order_ok_when_gomod_first():
    ctx = _ctx_from_text(
        """\
FROM golang:1.22 AS build
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o /app .
FROM alpine
COPY --from=build /app /app
"""
    )
    assert check_go(ctx) == []


def test_go_copy_order_flags_full_copy_before_mod():
    ctx = _ctx_from_text(
        """\
FROM golang:1.22
COPY . .
RUN go mod download
RUN go build -o /app .
"""
    )
    findings = check_go(ctx)
    assert len(findings) == 1
    assert findings[0].rule_id == "DRX022"


def test_go_copy_order_ignores_other_stages():
    """Node stage COPY . must not trigger Go rule via a later Go stage."""
    ctx = _ctx_from_text(
        """\
FROM node:22 AS frontend
COPY . .
RUN npm ci
FROM golang:1.22 AS build
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o /app .
"""
    )
    assert check_go(ctx) == []


def test_user_root_ignores_temporary_root():
    ctx = _ctx_from_text(
        """\
FROM ubuntu:24.04
USER root
RUN apt-get update
USER app
CMD ["./app"]
"""
    )
    assert check_user_root(ctx) == []


def test_user_root_flags_final_root():
    ctx = _ctx_from_text(
        """\
FROM ubuntu:24.04
USER app
USER root
CMD ["./app"]
"""
    )
    findings = check_user_root(ctx)
    assert len(findings) == 1
    assert findings[0].rule_id == "DRX014"


def test_latest_ignores_resolved_pinned_arg():
    ctx = _ctx_from_text(
        """\
ARG BASE_IMAGE=ubuntu:24.04@sha256:abc123
FROM $BASE_IMAGE AS base
COPY app /app
"""
    )
    assert check_latest(ctx) == []


def test_latest_flags_explicit_latest():
    ctx = _ctx_from_text('FROM alpine:latest\nCMD ["/bin/sh"]\n')
    findings = check_latest(ctx)
    assert len(findings) == 1
    assert findings[0].rule_id == "DRX002"


def test_latest_flags_untagged_arg_default():
    ctx = _ctx_from_text(
        """\
ARG BASE_IMAGE=outlinewiki/outline-base
FROM ${BASE_IMAGE} AS base
"""
    )
    findings = check_latest(ctx)
    assert len(findings) == 1


def test_latest_skips_stage_alias():
    ctx = _ctx_from_text(
        """\
FROM golang:1.22 AS builder
RUN go build -o /app .
FROM builder
COPY --from=builder /app /app
"""
    )
    assert check_latest(ctx) == []


def test_latest_skips_unresolvable_variable():
    ctx = _ctx_from_text('FROM $RUNTIME_IMAGE\nCMD ["/bin/sh"]\n')
    assert check_latest(ctx) == []


def test_realworld_gitea_no_drx022():
    _, findings = analyze(EXAMPLES / "realworld" / "gitea")
    assert "DRX022" not in {f.rule_id for f in findings}


def test_realworld_argocd_no_drx014_or_false_drx002():
    _, findings = analyze(EXAMPLES / "realworld" / "argocd")
    ids = {f.rule_id for f in findings}
    assert "DRX014" not in ids
    # $BASE_IMAGE resolves to a digest-pinned ubuntu — should not flag DRX002
    assert "DRX002" not in ids


def test_missing_user_requires_final_stage():
    """USER in a builder stage must not satisfy DRX003 for the runtime stage."""
    from dockrx.plugins.missing_user import check as check_user

    ctx = _ctx_from_text(
        """\
FROM golang:1.22 AS build
USER nobody
RUN go build -o /app .
FROM alpine
COPY --from=build /app /app
CMD ["/app"]
"""
    )
    findings = check_user(ctx)
    assert len(findings) == 1
    assert findings[0].rule_id == "DRX003"


def test_missing_user_ok_when_final_has_user():
    from dockrx.plugins.missing_user import check as check_user

    ctx = _ctx_from_text(
        """\
FROM alpine
USER nobody
CMD ["/bin/sh"]
"""
    )
    assert check_user(ctx) == []


def test_healthcheck_skipped_for_scratch():
    from dockrx.plugins.missing_healthcheck import check as check_hc

    ctx = _ctx_from_text(
        """\
FROM alpine AS build
RUN echo ok
FROM scratch
COPY --from=build /bin/app /app
ENTRYPOINT ["/app"]
"""
    )
    assert check_hc(ctx) == []


def test_healthcheck_flags_normal_runtime():
    from dockrx.plugins.missing_healthcheck import check as check_hc

    ctx = _ctx_from_text(
        """\
FROM alpine
CMD ["/bin/sh"]
"""
    )
    findings = check_hc(ctx)
    assert len(findings) == 1
    assert findings[0].rule_id == "DRX004"
