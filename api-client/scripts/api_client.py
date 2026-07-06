#!/usr/bin/env python3
"""api-client: a CLI Postman -- HTTP client with saved request collections and environments.

Stdlib only. Storage lives in the skill directory (parent of scripts/):
  collections.json   saved request templates ({{var}} placeholders allowed)
  environments.json  named environments with variables (chmod 600, may hold tokens)
  history.jsonl      request history (Authorization header values redacted)
"""

import argparse
import base64
import json
import os
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
COLLECTIONS_FILE = BASE_DIR / "collections.json"
ENVIRONMENTS_FILE = BASE_DIR / "environments.json"
HISTORY_FILE = BASE_DIR / "history.jsonl"

VAR_RE = re.compile(r"\{\{(\w+)\}\}")
SECRET_KEY_RE = re.compile(r"(token|secret|passw|api[_-]?key|auth|bearer|credential)", re.I)
SECRET_VALUE_RE = re.compile(r"^(sk-|ghp_|gho_|xox[a-z]?-|eyJ|Bearer\s)")
REDACT_HEADERS = {"authorization", "proxy-authorization", "x-api-key"}
MAX_BODY_LINES = 200


def die(msg, code=1):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------- storage

def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        die(f"cannot read {path.name}: {exc}")


def save_json(path, data, secure=False):
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    if secure:
        os.chmod(path, 0o600)


# ---------------------------------------------------------------- parsing helpers

def parse_kv(pairs, what):
    out = {}
    for item in pairs or []:
        if "=" not in item:
            die(f"invalid {what} '{item}', expected key=value")
        key, value = item.split("=", 1)
        out[key.strip()] = value
    return out


def parse_headers(items):
    out = {}
    for item in items or []:
        if ":" not in item:
            die(f"invalid header '{item}', expected 'Key: Value'")
        key, value = item.split(":", 1)
        out[key.strip()] = value.strip()
    return out


# ---------------------------------------------------------------- variables

def substitute_spec(spec, variables):
    """Replace {{var}} placeholders in every string of the spec."""
    missing = set()

    def repl(match):
        name = match.group(1)
        if name in variables:
            return str(variables[name])
        missing.add(name)
        return match.group(0)

    def walk(value):
        if isinstance(value, str):
            return VAR_RE.sub(repl, value)
        if isinstance(value, dict):
            return {key: walk(val) for key, val in value.items()}
        if isinstance(value, list):
            return [walk(item) for item in value]
        return value

    return walk(spec), sorted(missing)


def env_vars(name):
    if not name:
        return {}
    envs = load_json(ENVIRONMENTS_FILE, {})
    if name not in envs:
        available = ", ".join(sorted(envs)) or "(none)"
        die(f"environment '{name}' not found. Available: {available}")
    return envs[name]


# ---------------------------------------------------------------- request building

def auth_header(auth):
    if auth.startswith("bearer:"):
        return "Bearer " + auth[len("bearer:"):]
    if auth.startswith("basic:"):
        creds = auth[len("basic:"):]
        if ":" not in creds:
            die("--auth basic requires basic:<user:pass>")
        return "Basic " + base64.b64encode(creds.encode()).decode()
    if auth.startswith("env:"):
        var = auth[len("env:"):]
        token = os.environ.get(var)
        if not token:
            die(f"environment variable '{var}' is not set")
        return "Bearer " + token
    die("--auth must be bearer:<token>, basic:<user:pass>, or env:<VAR>")


def read_data(data):
    if data.startswith("@"):
        path = Path(data[1:]).expanduser()
        if not path.is_file():
            die(f"data file not found: {path}")
        text = path.read_text()
    else:
        text = data
    try:
        json.loads(text)
    except json.JSONDecodeError:
        print("Warning: --data is not valid JSON; sending as-is", file=sys.stderr)
    return text


def resolve_body(spec, headers):
    """Return the request body bytes, setting Content-Type if needed."""
    data, form = spec.get("data"), spec.get("form")
    if data and form:
        die("--data and --form are mutually exclusive")
    lower = {key.lower() for key in headers}
    if form:
        if "content-type" not in lower:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        return urllib.parse.urlencode(parse_kv(form, "form field")).encode()
    if data:
        text = read_data(data)
        if "content-type" not in lower:
            headers["Content-Type"] = "application/json"
        return text.encode()
    return None


def build_url(url, query_pairs):
    params = parse_kv(query_pairs, "query param")
    if not params:
        return url
    sep = "&" if "?" in url else "?"
    return url + sep + urllib.parse.urlencode(params)


def spec_from_args(args):
    return {
        "url": args.url,
        "method": args.method,
        "headers": args.header or [],
        "query": args.query or [],
        "data": args.data,
        "form": args.form or [],
        "auth": args.auth,
        "timeout": args.timeout,
    }


# ---------------------------------------------------------------- execution

def ssl_context(no_verify):
    ctx = ssl.create_default_context()
    if no_verify:
        print("Warning: TLS certificate verification disabled (--no-verify)", file=sys.stderr)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def execute(spec, no_verify=False):
    headers = parse_headers(spec.get("headers"))
    body = resolve_body(spec, headers)
    method = (spec.get("method") or ("POST" if body is not None else "GET")).upper()
    url = build_url(spec["url"], spec.get("query"))
    if not url.startswith(("http://", "https://")):
        die(f"invalid URL (must start with http:// or https://): {url}")
    if spec.get("auth"):
        headers["Authorization"] = auth_header(spec["auth"])
    request = urllib.request.Request(url, data=body, method=method)
    for key, value in headers.items():
        request.add_header(key, value)
    timeout = float(spec.get("timeout") or 30)
    start = time.monotonic()
    try:
        response = urllib.request.urlopen(request, timeout=timeout, context=ssl_context(no_verify))
    except urllib.error.HTTPError as exc:
        response = exc  # 4xx/5xx still carry a full response
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            die(f"request timed out after {timeout:g}s: {method} {url}")
        die(f"request failed: {exc.reason} ({method} {url})")
    except (TimeoutError, socket.timeout):
        die(f"request timed out after {timeout:g}s: {method} {url}")
    elapsed_ms = int((time.monotonic() - start) * 1000)
    return {
        "status": getattr(response, "status", None) or response.code,
        "reason": response.reason,
        "headers": dict(response.headers.items()),
        "body": response.read(),
        "ms": elapsed_ms,
        "method": method,
        "url": url,
        "request_headers": headers,
    }


# ---------------------------------------------------------------- output

def decode_body(raw, headers):
    match = re.search(r"charset=([\w-]+)", headers.get("Content-Type", ""))
    encoding = match.group(1) if match else "utf-8"
    try:
        return raw.decode(encoding, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def pretty_body(text):
    stripped = text.strip()
    if stripped.startswith(("{", "[")):
        try:
            return json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
    return text


def truncate(text):
    lines = text.splitlines()
    if len(lines) <= MAX_BODY_LINES:
        return text
    extra = len(lines) - MAX_BODY_LINES
    head = "\n".join(lines[:MAX_BODY_LINES])
    return f"{head}\n... [truncated {extra} more lines; use -o <file> to save the full body]"


def print_response(result, args):
    if args.output:
        Path(args.output).write_bytes(result["body"])
    body_text = pretty_body(decode_body(result["body"], result["headers"]))
    if args.json:
        print(body_text)
        return
    print(f"{result['status']} {result['reason']}  {result['ms']} ms  {result['method']} {result['url']}")
    for key, value in result["headers"].items():
        print(f"{key}: {value}")
    print()
    if args.output:
        print(f"[body saved to {args.output}, {len(result['body'])} bytes]")
    else:
        print(truncate(body_text))


def record_history(result):
    redacted = {
        key: ("<redacted>" if key.lower() in REDACT_HEADERS else value)
        for key, value in result["request_headers"].items()
    }
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "method": result["method"],
        "url": result["url"],
        "status": result["status"],
        "ms": result["ms"],
        "request_headers": redacted,
    }
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "a") as handle:
        handle.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------- commands

def run_spec(spec, variables, args):
    resolved, missing = substitute_spec(spec, variables)
    if missing:
        names = ", ".join("{{%s}}" % name for name in missing)
        die(f"unresolved variables: {names} (set with -e <env> or --var key=value)", 2)
    result = execute(resolved, no_verify=args.no_verify)
    record_history(result)
    print_response(result, args)
    return 0 if result["status"] < 400 else 1


def cmd_request(args):
    return run_spec(spec_from_args(args), env_vars(args.env), args)


def cmd_save(args):
    spec = spec_from_args(args)
    spec["collection"] = args.collection or "default"
    collections = load_json(COLLECTIONS_FILE, {})
    action = "Updated" if args.name in collections else "Saved"
    collections[args.name] = spec
    save_json(COLLECTIONS_FILE, collections)
    print(f"{action} request '{args.name}' in collection '{spec['collection']}'")
    return 0


def cmd_run(args):
    collections = load_json(COLLECTIONS_FILE, {})
    if args.name not in collections:
        die(f"no saved request '{args.name}'. Run `list` to see saved requests.")
    spec = dict(collections[args.name])
    spec.pop("collection", None)
    variables = {**env_vars(args.env), **parse_kv(args.var, "--var")}
    return run_spec(spec, variables, args)


def display_method(spec):
    return (spec.get("method") or ("POST" if spec.get("data") or spec.get("form") else "GET")).upper()


def cmd_list(_args):
    collections = load_json(COLLECTIONS_FILE, {})
    if not collections:
        print("No saved requests.")
        return 0
    groups = {}
    for name, spec in sorted(collections.items()):
        groups.setdefault(spec.get("collection", "default"), []).append((name, spec))
    for group, items in sorted(groups.items()):
        print(f"[{group}]")
        for name, spec in items:
            print(f"  {name:24} {display_method(spec):7} {spec['url']}")
    return 0


def cmd_delete(args):
    collections = load_json(COLLECTIONS_FILE, {})
    if args.name not in collections:
        die(f"no saved request '{args.name}'")
    del collections[args.name]
    save_json(COLLECTIONS_FILE, collections)
    print(f"Deleted request '{args.name}'")
    return 0


def cmd_env_set(args):
    envs = load_json(ENVIRONMENTS_FILE, {})
    env = envs.setdefault(args.env, {})
    env.update(parse_kv(args.pairs, "variable"))
    save_json(ENVIRONMENTS_FILE, envs, secure=True)
    print(f"Environment '{args.env}' updated ({len(env)} variables)")
    return 0


def mask_value(key, value):
    if SECRET_KEY_RE.search(key) or SECRET_VALUE_RE.match(value):
        return "****" if len(value) <= 8 else value[:4] + "****"
    return value


def cmd_env_list(args):
    envs = load_json(ENVIRONMENTS_FILE, {})
    if not envs:
        print("No environments.")
        return 0
    if args.env and args.env not in envs:
        die(f"environment '{args.env}' not found. Available: {', '.join(sorted(envs))}")
    for name in sorted(envs):
        if args.env and name != args.env:
            continue
        print(f"{name}:")
        for key, value in sorted(envs[name].items()):
            print(f"  {key} = {mask_value(key, value)}")
    return 0


def cmd_env_delete(args):
    envs = load_json(ENVIRONMENTS_FILE, {})
    if args.env not in envs:
        die(f"environment '{args.env}' not found")
    if args.key:
        if args.key not in envs[args.env]:
            die(f"variable '{args.key}' not found in environment '{args.env}'")
        del envs[args.env][args.key]
        print(f"Deleted '{args.key}' from environment '{args.env}'")
    else:
        del envs[args.env]
        print(f"Deleted environment '{args.env}'")
    save_json(ENVIRONMENTS_FILE, envs, secure=True)
    return 0


def cmd_history(args):
    if not HISTORY_FILE.exists():
        print("No history.")
        return 0
    for line in HISTORY_FILE.read_text().splitlines()[-args.number:]:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        print(f"{entry.get('ts', '?')}  {entry.get('method', ''):7} {entry.get('status', '?')}  "
              f"{entry.get('ms', '?'):>6} ms  {entry.get('url', '')}")
    return 0


# ---------------------------------------------------------------- CLI

def add_request_flags(parser):
    parser.add_argument("-X", "--method", help="HTTP method (default GET; auto-POST when a body is given)")
    parser.add_argument("-H", "--header", action="append", metavar='"K: V"', help="request header (repeatable)")
    parser.add_argument("-q", "--query", action="append", metavar="key=value", help="query param (repeatable)")
    parser.add_argument("-d", "--data", metavar="JSON|@file", help="JSON body: inline string or @file.json")
    parser.add_argument("--form", action="append", metavar="key=value", help="urlencoded form field (repeatable)")
    parser.add_argument("--auth", metavar="SPEC", help="bearer:<token> | basic:<user:pass> | env:<VAR>")
    parser.add_argument("--timeout", type=float, default=30, metavar="SEC", help="timeout in seconds (default 30)")


def add_output_flags(parser):
    parser.add_argument("-e", "--env", help="apply a named environment for {{var}} substitution")
    parser.add_argument("-o", "--output", metavar="FILE", help="save response body to a file")
    parser.add_argument("--json", action="store_true", help="print only the pretty JSON body")
    parser.add_argument("--no-verify", action="store_true", dest="no_verify", help="skip TLS certificate verification")


def build_parser():
    parser = argparse.ArgumentParser(prog="api_client.py", description="CLI Postman: HTTP client with saved request collections and environments")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("request", aliases=["r"], help="send an HTTP request")
    p.add_argument("url")
    add_request_flags(p)
    add_output_flags(p)
    p.set_defaults(func=cmd_request)

    p = sub.add_parser("save", help="save a request template ({{var}} placeholders allowed)")
    p.add_argument("name")
    p.add_argument("url")
    add_request_flags(p)
    p.add_argument("--collection", metavar="GROUP", help="collection group (default 'default')")
    p.set_defaults(func=cmd_save)

    p = sub.add_parser("run", help="run a saved request")
    p.add_argument("name")
    p.add_argument("--var", action="append", metavar="key=value", help="variable override (repeatable)")
    add_output_flags(p)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("list", help="list saved requests grouped by collection")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("delete", help="delete a saved request")
    p.add_argument("name")
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("env-set", help="set variables in a named environment")
    p.add_argument("env")
    p.add_argument("pairs", nargs="+", metavar="key=value")
    p.set_defaults(func=cmd_env_set)

    p = sub.add_parser("env-list", help="list environments (secret-looking values masked)")
    p.add_argument("env", nargs="?")
    p.set_defaults(func=cmd_env_list)

    p = sub.add_parser("env-delete", help="delete an environment or one of its variables")
    p.add_argument("env")
    p.add_argument("key", nargs="?")
    p.set_defaults(func=cmd_env_delete)

    p = sub.add_parser("history", help="show recent requests")
    p.add_argument("-n", "--number", type=int, default=10, help="entries to show (default 10)")
    p.set_defaults(func=cmd_history)

    return parser


def main():
    args = build_parser().parse_args()
    sys.exit(args.func(args) or 0)


if __name__ == "__main__":
    main()
