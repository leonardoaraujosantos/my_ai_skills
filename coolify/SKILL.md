---
name: coolify
description: Manage Coolify deployments, applications, environment variables, and services via the Coolify API. Use when the user wants to deploy, check deployment status, manage env vars, view logs, or troubleshoot Coolify applications.
argument-hint: [command] [args...]
---

# Coolify Management Skill

Manage Coolify applications, deployments, environment variables, and services through the API.

## Setup

The skill supports multiple Coolify servers via environment variables:

| Server    | URL env var        | Token env var        |
|-----------|--------------------|----------------------|
| sandbox   | `COOLIFY_URL`      | `COOLIFY_TOKEN`      |
| prd       | `COOLIFY_PRD_URL`  | `COOLIFY_PRD_TOKEN`  |

Check if they're set:

```bash
echo "Sandbox URL: ${COOLIFY_URL:-NOT SET}"
echo "Sandbox Token: ${COOLIFY_TOKEN:+SET (hidden)}"
echo "Prd URL: ${COOLIFY_PRD_URL:-NOT SET}"
echo "Prd Token: ${COOLIFY_PRD_TOKEN:+SET (hidden)}"
```

## CLI Tool

All commands use the Python CLI helper at `~/.claude/skills/coolify/coolify_cli.py`.

**Base command (defaults to sandbox):**
```bash
python3 ~/.claude/skills/coolify/coolify_cli.py <command> [args...]
```

**Target a specific server with `--server`:**
```bash
python3 ~/.claude/skills/coolify/coolify_cli.py --server prd <command> [args...]
```

Available servers: `sandbox` (default), `prd`.

For brevity in this doc, we'll write `coolify_cli <command>` but always use the full path.

---

## Commands Reference

### List Applications
```bash
coolify_cli apps
```
Returns: uuid, name, status, fqdn, git repo, branch for each app.

### Show Application Details
```bash
coolify_cli app <app-uuid>
```

### List Environment Variables
```bash
coolify_cli app-envs <app-uuid>
```
Returns: uuid, key, value (truncated), is_literal, is_build, is_runtime.

### Set / Update Environment Variable
```bash
coolify_cli app-env-set <app-uuid> <KEY> <VALUE>
coolify_cli app-env-set <app-uuid> <KEY> <VALUE> --literal
```
Use `--literal` for values containing JSON, special characters, or `{}` braces.

**IMPORTANT:** For JSON env vars (like MCP configs), ALWAYS use `--literal` to prevent Coolify from interpreting braces as shell variables.

### Delete Environment Variable
```bash
coolify_cli app-env-delete <app-uuid> <env-uuid>
```

### Trigger Deployment
```bash
coolify_cli deploy <app-uuid>
coolify_cli deploy <app-uuid> --force
```
Use `--force` to rebuild without cache.

### List Recent Deployments
```bash
coolify_cli deployments <app-uuid>
coolify_cli deployments <app-uuid> --limit 10
```
Returns: status, commit, message, timestamps.

### View Application Logs
```bash
coolify_cli logs <app-uuid>
coolify_cli logs <app-uuid> --lines 100
```

### List Services
```bash
coolify_cli services
```

### Show Service Details
```bash
coolify_cli service <service-uuid>
```

### List All Resources
```bash
coolify_cli resources
```
Returns all resources: applications, services, databases.

### List Servers
```bash
coolify_cli servers
```

### Show Server Details
```bash
coolify_cli server <server-uuid>
```

### List Teams
```bash
coolify_cli teams
```

---

## Common Workflows

### Check deployment status after merge
```bash
coolify_cli deployments <app-uuid> --limit 3
```

### Debug a failed deployment
```bash
# Check recent deployments
coolify_cli deployments <app-uuid> --limit 5
# Check app logs
coolify_cli logs <app-uuid> --lines 100
```

### Set a JSON env var (e.g., MCP config)
```bash
coolify_cli app-env-set <app-uuid> DEEP_AGENT_MCP '{"name":"Deep Agent","endpoint_url":"https://..."}' --literal
```

### Force redeploy (no cache)
```bash
coolify_cli deploy <app-uuid> --force
```

### Find an app UUID
```bash
coolify_cli apps
# Look for the app name in the output
```

---

## Troubleshooting Tips

### "Invalid JSON" in logs for env vars with JSON values
The env var needs `is_literal: true` in Coolify. Use `--literal` flag:
```bash
coolify_cli app-env-set <uuid> MY_VAR '{"key":"value"}' --literal
```

### Deployment fails but app is healthy
Old deployment is still running. Check `coolify_cli deployments <uuid>` — if latest is failed but previous succeeded, the previous container is still serving.

### Build fails with npm/pip errors
Test the build locally first (see Coolify Tricks and Traps in Obsidian vault):
```bash
# Frontend
docker run --rm -v "$PWD/frontend/package.json:/app/package.json" \
  -v "$PWD/frontend/package-lock.json:/app/package-lock.json" \
  -v "$PWD/frontend/.npmrc:/app/.npmrc" \
  -w /app node:20-alpine sh -c "npm ci --legacy-peer-deps"

# Backend
docker run --rm -v "$PWD/backend/pyproject.toml:/app/pyproject.toml" \
  -v "$PWD/backend/uv.lock:/app/uv.lock" \
  -w /app python:3.12-slim sh -c "pip install uv && uv sync --frozen --no-dev --no-install-project"
```

---

## Notes

- The CLI uses only Python stdlib (no pip dependencies needed)
- All output is JSON for easy parsing
- The `app-envs` command truncates values at 80 chars for readability — use `app` for full details
- When setting env vars with `--literal`, Coolify wraps the value in quotes to prevent shell interpolation
