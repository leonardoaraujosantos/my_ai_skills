---
name: api-client
description: HTTP client with saved request collections and named environments - a CLI Postman. Send requests with headers, query params, JSON/form bodies, and auth; save requests with {{var}} placeholders and replay them per environment; inspect request history. Use when the user says "test this API/endpoint", "call this REST API", "save this request", "API collection", or "hit the endpoint with auth".
argument-hint: <command> [url|request-name] [options]
---

# API Client

A CLI Postman: ad-hoc HTTP requests, saved request collections, and named environments. Python 3 stdlib only. Complements `pg-client` (databases) and `mcp-client` (MCP servers).

## Script Location

```bash
API="$HOME/.claude/skills/api-client/scripts/api_client.py"
```

## Commands

| Command | Description |
|---------|-------------|
| `request <url>` (alias `r`) | Send an HTTP request |
| `save <name> <url> [flags]` | Save a request template (`{{var}}` placeholders allowed; group with `--collection`) |
| `run <name> [-e env] [--var k=v]` | Run a saved request with variable substitution |
| `list` | List saved requests grouped by collection |
| `delete <name>` | Delete a saved request |
| `env-set <env> key=value ...` | Set variables in a named environment |
| `env-list [env]` | List environments (secret-looking values masked) |
| `env-delete <env> [key]` | Delete an environment or one variable |
| `history [-n 10]` | Recent requests: method, url, status, ms |

## Request Options

| Option | Description |
|--------|-------------|
| `-X, --method <M>` | HTTP method (default GET; auto-POST when a body is given) |
| `-H "K: V"` | Header (repeatable) |
| `-q key=value` | Query param (repeatable) |
| `-d, --data <json\|@file>` | JSON body: inline string or `@file.json` |
| `--form key=value` | Urlencoded form field (repeatable) |
| `--auth <spec>` | `bearer:<token>` \| `basic:<user:pass>` \| `env:<VAR>` (bearer from env var) |
| `--timeout <sec>` | Timeout in seconds (default 30) |
| `-e, --env <name>` | Apply a named environment for `{{var}}` substitution |
| `-o <file>` | Save response body to a file |
| `--json` | Print only the pretty JSON body |
| `--no-verify` | Skip TLS verification (prints a warning) |

Output: status line + timing + response headers + pretty-printed JSON body (raw text fallback, truncated past 200 lines). Exit code is non-zero on network errors, timeouts, and HTTP >= 400.

## Named Requests + Environments

Like `mcp-client` registrations: save once with placeholders, run by name per environment.

```bash
# One-time setup
python3 "$API" env-set dev base_url=http://localhost:3000 token=dev-secret
python3 "$API" env-set prod base_url=https://api.example.com token=sk-live-abc

python3 "$API" save get-user '{{base_url}}/users/{{id}}' --auth 'bearer:{{token}}' --collection users

# Run against any environment
python3 "$API" run get-user -e dev --var id=42
python3 "$API" run get-user -e prod --var id=42 --json
```

Unresolved `{{var}}` placeholders fail with a list of the missing variables.

## Examples

```bash
# Quick GET with query params
python3 "$API" r https://api.example.com/search -q q=widgets -q limit=5

# POST JSON (method auto-switches to POST)
python3 "$API" r https://api.example.com/items -d '{"name": "widget", "qty": 3}'
python3 "$API" r https://api.example.com/items -d @payload.json -H "X-Request-Id: abc"

# Form post, bearer token from an env var (preferred for secrets)
python3 "$API" r https://api.example.com/login --form user=leo --form pass=hunter2
python3 "$API" r https://api.example.com/me --auth env:API_TOKEN
```

### Typical API debugging session

```bash
python3 "$API" r https://api.example.com/health --json          # is it up?
python3 "$API" r https://api.example.com/orders --auth env:API_TOKEN -q status=failed
python3 "$API" save failed-orders '{{base_url}}/orders' --auth 'bearer:{{token}}' -q status=failed
python3 "$API" env-set staging base_url=https://staging.example.com token=st-123
python3 "$API" run failed-orders -e staging                     # reproduce on staging
python3 "$API" history -n 5                                     # compare status/latency
```

## Storage & Security

Files live in `~/.claude/skills/api-client/`: `collections.json`, `environments.json` (chmod 600), `history.jsonl` (Authorization header values redacted).

Environment variables may hold tokens and are stored **plaintext** (chmod 600). Prefer `--auth env:VAR` so tokens stay in your shell environment and never touch disk.
