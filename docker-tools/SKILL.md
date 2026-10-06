---
name: docker-tools
description: Opinionated Docker and Docker Compose debugging and maintenance recipes - container status, unhealthy/restarting container diagnosis, logs, exec/copy, disk cleanup, compose lifecycle, networking, and images. Use when the user asks "why is my container unhealthy/restarting", wants docker logs or disk usage, says "clean up docker", "debug this container", or "compose up/down".
argument-hint: [container|compose-service] [action]
---

# Docker Tools Skill

Recipes for local/host-level Docker and Compose debugging and maintenance.
Verified against Docker 28.x / Compose v2 (`docker compose`, not `docker-compose`).

> For Coolify-deployed apps, the **coolify** skill handles remote deployment concerns
> (deploys, env vars, app logs via the Coolify API). Use docker-tools for local or
> host-level container debugging.

---

## Status Overview

| Task | Command |
|------|---------|
| All containers, status + health + ports | `docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'` |
| Only running | `docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'` |
| Live resource snapshot (CPU/mem) | `docker stats --no-stream` |
| One container's full state | `docker inspect <c> --format '{{json .State}}' \| jq` |
| Compose project status | `docker compose ps` |

`Status` includes health (`Up 2 hours (healthy)`, `(unhealthy)`, `Restarting (1) 5 seconds ago`) — start here.

---

## Debug an Unhealthy / Restarting Container

Run these in order; stop when you find the cause.

1. **Health-check history** — what the probe actually returned:
   ```bash
   docker inspect <c> --format '{{json .State.Health}}' | jq
   ```
   Look at `.Log[].ExitCode` and `.Log[].Output` for the failing probe output.

2. **Last logs** (crash reason is usually in the final lines):
   ```bash
   docker logs --tail 100 --timestamps <c>
   ```

3. **Exit code and OOM kill**:
   ```bash
   docker inspect <c> --format '{{.State.ExitCode}} {{.State.OOMKilled}}'
   ```
   - `137 true` → OOM-killed: raise memory limit or fix the leak
   - `137 false` → SIGKILL from outside (e.g. `docker stop` timeout)
   - `1`/`2` → app error, see step 2
   - `126`/`127` → bad entrypoint/command (not executable / not found)

4. **Restart count and policy** (crash-looping?):
   ```bash
   docker inspect <c> --format 'restarts={{.RestartCount}} policy={{.HostConfig.RestartPolicy.Name}}'
   ```

5. **Resource limits** vs actual usage:
   ```bash
   docker inspect <c> --format 'mem={{.HostConfig.Memory}} cpus={{.HostConfig.NanoCpus}}'
   docker stats --no-stream <c>
   ```
   `mem=0` means unlimited. If usage sits at the limit, that's your answer.

6. **Get inside** and run the healthcheck by hand:
   ```bash
   docker exec -it <c> sh          # or bash
   # then run the exact healthcheck command:
   docker inspect <c> --format '{{json .Config.Healthcheck.Test}}'
   ```
   If the container won't stay up long enough to exec, override the entrypoint:
   ```bash
   docker run -it --rm --entrypoint sh <image>
   ```

---

## Logs

| Task | Command |
|------|---------|
| Last N lines with timestamps | `docker logs --tail 100 --timestamps <c>` |
| Follow live | `docker logs -f --tail 50 <c>` |
| Since a time window | `docker logs --since 15m <c>` / `--since 2026-07-06T10:00:00` |
| Compose, one service | `docker compose logs -f --tail 100 <svc>` |
| Compose, all services | `docker compose logs -f` |
| Grep for errors | `docker logs --tail 500 <c> 2>&1 \| grep -iE 'error\|fatal\|panic'` |

Note: `docker logs` writes app stderr to stderr — add `2>&1` before piping.

---

## Exec & Copy

| Task | Command |
|------|---------|
| Interactive shell | `docker exec -it <c> sh` (try `bash` first on Debian-based images) |
| One-off command | `docker exec <c> env` / `docker exec <c> cat /etc/hosts` |
| As root | `docker exec -it -u root <c> sh` |
| Copy container → host | `docker cp <c>:/path/in/container ./local-dir/` |
| Copy host → container | `docker cp ./local-file <c>:/path/in/container/` |

---

## Disk Usage & Safe Cleanup

Always measure first:

```bash
docker system df        # summary: images, containers, volumes, build cache
docker system df -v     # per-item breakdown (find the big offenders)
```

**Safe prune order** — each step is reversible-ish (rebuildable/re-pullable); confirm with the user before each:

```bash
docker image prune            # 1. dangling images only (untagged layers)
docker container prune        # 2. stopped containers
docker builder prune          # 3. build cache (often the biggest win)
docker network prune          # 4. unused networks
```

**Volumes LAST and only with explicit user confirmation** — volume data (databases!) is gone forever:

```bash
docker volume ls                              # show what exists first
docker volume prune                           # DESTRUCTIVE: removes unused volumes
docker volume rm <specific-volume>            # prefer targeted removal
```

Never run `docker system prune -a --volumes` blindly — it deletes ALL unused images (not just dangling) and ALL unused volumes in one shot.

---

## Compose Lifecycle

Run from the directory with `compose.yaml`/`docker-compose.yml`, or use `-f <file>`.

| Task | Command |
|------|---------|
| Start (detached) | `docker compose up -d` |
| Stop and remove containers/networks | `docker compose down` |
| Rebuild + restart one service | `docker compose up -d --build <svc>` |
| Validate/render final config | `docker compose config` |
| Restart (same container, no config reload) | `docker compose restart <svc>` |
| Recreate (picks up compose/env changes) | `docker compose up -d --force-recreate <svc>` |
| Pull newer images then apply | `docker compose pull && docker compose up -d` |
| Tail one service | `docker compose logs -f --tail 100 <svc>` |

**Restart vs recreate:** `restart` only bounces the process — it does NOT apply changes to `compose.yaml`, env files, or images. After editing config, use `up -d` (recreates only changed services).

`docker compose down -v` also deletes the project's named volumes — DESTRUCTIVE, treat like volume prune (list volumes and confirm first).

---

## Networking

| Task | Command |
|------|---------|
| List networks | `docker network ls` |
| Which networks a container is on | `docker inspect <c> --format '{{range $k, $_ := .NetworkSettings.Networks}}{{$k}} {{end}}'` |
| Who is on a network | `docker network inspect <net> --format '{{range .Containers}}{{.Name}} {{end}}'` |
| Port mappings for a container | `docker port <c>` |
| Container-to-container DNS test | `docker exec <c1> ping -c 2 <c2>` or `docker exec <c1> curl -sf http://<c2>:<port>/health` |
| Connect container to a network | `docker network connect <net> <c>` |

Containers resolve each other by **container name (or compose service name)** only when on the same user-defined network — the default `bridge` network has no DNS.

**"port is already allocated"** — find the holder, then stop it or change the host port:

```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}' | grep <port>
lsof -iTCP:<port> -sTCP:LISTEN     # if it's not a container, it's a host process
```

---

## Images

| Task | Command |
|------|---------|
| List with sizes | `docker images --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}'` |
| Sort biggest first | `docker images --format '{{.Size}}\t{{.Repository}}:{{.Tag}}' \| sort -rh \| head` |
| Dangling images | `docker images -f dangling=true` |
| Remove dangling | `docker image prune` |
| Remove one image | `docker rmi <image>:<tag>` |
| Pull | `docker pull <image>:<tag>` |
| Retag (e.g. for a registry push) | `docker tag <image>:<tag> <registry>/<image>:<tag>` |
| Image layer history | `docker history <image>` |

---

## Safety Rules

- **Show before destroy.** Before any `rm`, `prune`, or `down -v`, run the matching list command (`docker ps -a`, `docker volume ls`, `docker system df -v`, `docker images -f dangling=true`) so the user sees exactly what will be affected, then get confirmation.
- **Volumes require explicit approval.** Never `docker volume prune`, `docker volume rm`, or `docker compose down -v` without the user explicitly approving volume deletion — volumes hold databases and irreplaceable state.
- **Never run `docker system prune -a --volumes` blindly.** Prefer the staged prune order in the cleanup section.
- **Prefer targeted over bulk.** `docker rm <c>` / `docker rmi <img>` / `docker volume rm <v>` on named items beats a broad prune.
- **Don't `docker kill` when `docker stop` will do** — give the app its shutdown grace period first.
