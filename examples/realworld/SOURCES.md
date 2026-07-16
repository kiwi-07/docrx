# Real-world Dockerfile samples

Dockerfiles copied from popular open-source projects to validate DockRx
against production-style builds. Each subdirectory contains a snapshot of
the project's Dockerfile at the time of download.

| Project | Language / stack | Source |
|---------|------------------|--------|
| `argocd` | Go + Node multi-stage | [argoproj/argo-cd](https://github.com/argoproj/argo-cd) |
| `filebrowser` | Go multi-stage | [filebrowser/filebrowser](https://github.com/filebrowser/filebrowser) |
| `gitea` | Go multi-stage | [go-gitea/gitea](https://github.com/go-gitea/gitea) |
| `grafana` | Go + Node multi-stage | [grafana/grafana](https://github.com/grafana/grafana) |
| `homeassistant` | Python | [home-assistant/core](https://github.com/home-assistant/core) |
| `keycloak` | Java (UBI) | [keycloak/keycloak](https://github.com/keycloak/keycloak) |
| `meilisearch` | Rust multi-stage | [meilisearch/meilisearch](https://github.com/meilisearch/meilisearch) |
| `minio` | Distroless-style | [minio/minio](https://github.com/minio/minio) |
| `netdata` | C multi-stage | [netdata/netdata](https://github.com/netdata/netdata) |
| `nextjs` | Node multi-stage | [vercel/next.js `examples/with-docker`](https://github.com/vercel/next.js/tree/canary/examples/with-docker) |
| `oauth2-proxy` | Go multi-stage | [oauth2-proxy/oauth2-proxy](https://github.com/oauth2-proxy/oauth2-proxy) |
| `outline` | Node | [outline/outline](https://github.com/outline/outline) |
| `prometheus` | BusyBox runtime | [prometheus/prometheus](https://github.com/prometheus/prometheus) |
| `qdrant` | Rust + GPU stages | [qdrant/qdrant](https://github.com/qdrant/qdrant) |
| `rclone` | Go multi-stage | [rclone/rclone](https://github.com/rclone/rclone) |
| `syncthing` | Go multi-stage | [syncthing/syncthing](https://github.com/syncthing/syncthing) |
| `traefik` | Alpine binary drop | [traefik/traefik](https://github.com/traefik/traefik) |
| `watchtower` | Alpine + scratch | [containrrr/watchtower](https://github.com/containrrr/watchtower) |

These files are owned by their respective projects under their own licenses.
They are included here only for analysis testing of DockRx.

For a smaller clone, you may omit this directory; it is not required to run
DockRx or its unit tests.
