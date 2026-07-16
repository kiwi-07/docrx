# Real-world DockRx results

Analyzed 18 Dockerfiles from popular open-source projects
(see [SOURCES.md](SOURCES.md)). Scores include each project's
`.dockerignore` when one exists upstream.

## Scoreboard (post pre-release fixes)

| Project | Score | Notable rules | Notes |
|---------|------:|---------------|-------|
| filebrowser | **99** | DRX006 | Near-perfect |
| outline | **88** | DRX002 | Untagged ARG default (true positive) |
| prometheus | **85** | DRX002, DRX004 | `:latest` still flagged |
| argocd | **80** | DRX016, DRX011, … | FP cleared for DRX002/DRX014 |
| watchtower | **78** | DRX005, DRX003 | Scratch final — no DRX004 noise |
| nextjs | **72** | DRX013, DRX016, … | Official example, actionable Mediums |
| gitea | **70** | DRX016, DRX003, … | DRX022 FP cleared |
| meilisearch | **73** | DRX027 | Real Cargo cache issue |

## Pre-release rule fixes validated here

- DRX022 / DRX002 / DRX014 false positives cleared on Gitea / Argo CD
- DRX003 now requires `USER` in the **final** stage only
- DRX004 skips scratch/distroless finals

## How to re-run

```bash
for d in examples/realworld/*/; do
  printf "%-14s " "$(basename "$d")"
  DOCKRX_LOG_LEVEL=ERROR uv run dockrx analyze "$d" --score-only
done
```
