#!/usr/bin/env python3
"""Coolify CLI helper — thin wrapper around Coolify API v1.

Usage:
    python3 coolify_cli.py <command> [args...]

Environment:
    COOLIFY_URL   — Coolify instance URL (e.g. https://coolify.example.com)
    COOLIFY_TOKEN — API bearer token

Commands:
    apps                          List all applications
    app <uuid>                    Show application details
    app-envs <uuid>               List environment variables
    app-env-set <uuid> <key> <value> [--literal] [--build] [--runtime]
                                  Create or update an env var
    app-env-delete <uuid> <env_uuid>
                                  Delete an env var
    deploy <uuid> [--force]       Trigger deployment
    deployments <uuid> [--limit N]
                                  List recent deployments
    logs <uuid> [--lines N]       Show application logs
    services                      List all services
    service <uuid>                Show service details
    resources                     List all resources (apps + services + DBs)
    servers                       List all servers
    server <uuid>                 Show server details
    teams                         List all teams
"""

import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def get_config():
    url = os.environ.get("COOLIFY_URL", "").rstrip("/")
    token = os.environ.get("COOLIFY_TOKEN", "")
    if not url or not token:
        print("Error: COOLIFY_URL and COOLIFY_TOKEN must be set", file=sys.stderr)
        sys.exit(1)
    return url, token


def api(method, path, data=None):
    url, token = get_config()
    full_url = f"{url}/api/v1{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = Request(full_url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
        except Exception:
            err = body
        print(f"HTTP {e.code}: {json.dumps(err, indent=2)}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def pp(obj):
    print(json.dumps(obj, indent=2, default=str))


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_apps():
    apps = api("GET", "/applications")
    rows = []
    for a in apps:
        rows.append({
            "uuid": a.get("uuid"),
            "name": a.get("name"),
            "status": a.get("status"),
            "fqdn": a.get("fqdn"),
            "git": a.get("git_repository"),
            "branch": a.get("git_branch"),
        })
    pp(rows)


def cmd_app(uuid):
    pp(api("GET", f"/applications/{uuid}"))


def cmd_app_envs(uuid):
    envs = api("GET", f"/applications/{uuid}/envs")
    rows = []
    for e in envs:
        rows.append({
            "uuid": e.get("uuid"),
            "key": e.get("key"),
            "value": e.get("value", "")[:80] + ("..." if len(e.get("value", "")) > 80 else ""),
            "is_literal": e.get("is_literal"),
            "is_build": e.get("is_buildtime"),
            "is_runtime": e.get("is_runtime"),
        })
    pp(rows)


def cmd_app_env_set(uuid, key, value, literal=False, build=True, runtime=True):
    data = {
        "key": key,
        "value": value,
        "is_literal": literal,
    }
    result = api("PATCH", f"/applications/{uuid}/envs", data)
    pp(result)


def cmd_app_env_delete(uuid, env_uuid):
    result = api("DELETE", f"/applications/{uuid}/envs/{env_uuid}")
    pp(result)


def cmd_deploy(uuid, force=False):
    params = "?force=true" if force else ""
    result = api("POST", f"/applications/{uuid}/deploy{params}")
    pp(result)


def cmd_deployments(uuid, limit=5):
    result = api("GET", f"/applications/{uuid}/deployments")
    items = result.get("data", result) if isinstance(result, dict) else result
    if isinstance(items, list):
        items = items[:limit]
    rows = []
    for d in items:
        if isinstance(d, dict):
            rows.append({
                "status": d.get("status"),
                "commit": str(d.get("commit", ""))[:8],
                "message": str(d.get("commit_message", ""))[:60],
                "created": d.get("created_at"),
                "finished": d.get("finished_at"),
            })
    pp(rows)


def cmd_logs(uuid, lines=50):
    result = api("GET", f"/applications/{uuid}/logs?limit={lines}")
    if isinstance(result, list):
        for line in result:
            if isinstance(line, dict):
                print(f"{line.get('timestamp','')} {line.get('output','')}")
            else:
                print(line)
    else:
        pp(result)


def cmd_services():
    services = api("GET", "/services")
    rows = []
    for s in services:
        rows.append({
            "uuid": s.get("uuid"),
            "name": s.get("name"),
            "status": s.get("status"),
            "type": s.get("type"),
        })
    pp(rows)


def cmd_service(uuid):
    pp(api("GET", f"/services/{uuid}"))


def cmd_resources():
    pp(api("GET", "/resources"))


def cmd_servers():
    servers = api("GET", "/servers")
    rows = []
    for s in servers:
        rows.append({
            "uuid": s.get("uuid"),
            "name": s.get("name"),
            "ip": s.get("ip"),
            "status": s.get("settings", {}).get("is_reachable"),
        })
    pp(rows)


def cmd_server(uuid):
    pp(api("GET", f"/servers/{uuid}"))


def cmd_teams():
    pp(api("GET", "/teams"))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    if cmd == "apps":
        cmd_apps()
    elif cmd == "app" and len(args) >= 2:
        cmd_app(args[1])
    elif cmd == "app-envs" and len(args) >= 2:
        cmd_app_envs(args[1])
    elif cmd == "app-env-set" and len(args) >= 4:
        literal = "--literal" in args
        build = "--build" in args or "--literal" not in args
        runtime = "--runtime" in args or "--literal" not in args
        cmd_app_env_set(args[1], args[2], args[3], literal=literal, build=build, runtime=runtime)
    elif cmd == "app-env-delete" and len(args) >= 3:
        cmd_app_env_delete(args[1], args[2])
    elif cmd == "deploy" and len(args) >= 2:
        force = "--force" in args
        cmd_deploy(args[1], force=force)
    elif cmd == "deployments" and len(args) >= 2:
        limit = 5
        if "--limit" in args:
            idx = args.index("--limit")
            if idx + 1 < len(args):
                limit = int(args[idx + 1])
        cmd_deployments(args[1], limit=limit)
    elif cmd == "logs" and len(args) >= 2:
        lines = 50
        if "--lines" in args:
            idx = args.index("--lines")
            if idx + 1 < len(args):
                lines = int(args[idx + 1])
        cmd_logs(args[1], lines=lines)
    elif cmd == "services":
        cmd_services()
    elif cmd == "service" and len(args) >= 2:
        cmd_service(args[1])
    elif cmd == "resources":
        cmd_resources()
    elif cmd == "servers":
        cmd_servers()
    elif cmd == "server" and len(args) >= 2:
        cmd_server(args[1])
    elif cmd == "teams":
        cmd_teams()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
