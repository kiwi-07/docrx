# Real-world DockRx results

Analyzed 18 Dockerfiles from popular open-source projects
(see [SOURCES.md](SOURCES.md)). Scores include each project's
`.dockerignore` when one exists upstream.

> **Scoring note:** DockRx uses a "spill" scoring model where every finding's penalty counts
> toward the overall score (see `CHANGELOG.md`). Scores below reflect the 0.1.0 model — don't
> compare them directly against pre-release tables.

## Scoreboard

| Project | Score | Grade | Notable rules |
|---------|------:|:-----:|---------------|
| filebrowser | **99** | A | DRX006 |
| outline | **88** | B | DRX002 |
| prometheus | **85** | B | DRX002, DRX004 |
| traefik | **84** | B | DRX003, DRX004, DRX006 |
| argocd | **80** | B | DRX004, DRX011, DRX015, DRX016 |
| netdata | **78** | C | DRX003, DRX015, DRX016 |
| watchtower | **76** | C | DRX003, DRX005 |
| homeassistant | **75** | C | DRX003, DRX004, DRX010, DRX015 |
| meilisearch | **73** | C | DRX003, DRX004, DRX027 |
| minio | **72** | C | DRX002, DRX003, DRX004, DRX006 |
| nextjs | **72** | C | DRX004, DRX006, DRX011, DRX013, DRX015, DRX016 |
| gitea | **70** | C | DRX003, DRX004, DRX006, DRX011, DRX016 |
| syncthing | **64** | D | DRX002, DRX003, DRX005 |
| grafana | **63** | D | DRX002, DRX003, DRX004, DRX015, DRX016 |
| oauth2-proxy | **61** | D | DRX002, DRX003, DRX004 |
| qdrant | **54** | F | DRX002, DRX004, DRX016, DRX027 |
| rclone | **53** | F | DRX002, DRX003, DRX004, DRX005, DRX006, DRX016 |
| keycloak | **47** | F | DRX002, DRX004, DRX005, DRX008, DRX016 |

## Pre-release rule fixes validated here

- DRX022 / DRX002 / DRX014 false positives cleared on Gitea / Argo CD
- DRX003 now requires `USER` in the **final** stage only
- DRX004 skips scratch/distroless finals

## How to re-run

```bash
for d in examples/realworld/*/; do
  printf "%-14s " "$(basename "$d")"
  uv run dockrx analyze "$d" --score-only || true
done
```

`analyze` exits non-zero when a project trips `fail-on-severity` (default `HIGH`), so the
`|| true` keeps the loop going.
