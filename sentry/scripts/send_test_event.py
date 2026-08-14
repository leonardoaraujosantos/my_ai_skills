#!/usr/bin/env python3
"""Send a test event to Sentry using only the Python standard library.

Proves a DSN is valid and the ingest endpoint is reachable without installing an SDK
or touching the project under test. Posts a single event envelope to
``<scheme>://<host>/api/<project_id>/envelope/``.

Usage:
    python3 send_test_event.py                       # DSN from $SENTRY_DSN
    python3 send_test_event.py --dsn "https://k@o1.ingest.de.sentry.io/2"
    python3 send_test_event.py --message "hi" --environment staging --level warning
    python3 send_test_event.py --dry-run             # print the payload, send nothing
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

CLIENT = "sentry-skill-test-sender/1.0"
LEVELS = ("debug", "info", "warning", "error", "fatal")


class DsnError(ValueError):
    """Raised when a DSN cannot be parsed."""


def parse_dsn(dsn: str) -> dict[str, str]:
    """Split a Sentry DSN into the parts needed to build an envelope request."""
    parsed = urlparse(dsn.strip())
    if parsed.scheme not in ("http", "https"):
        raise DsnError(f"DSN scheme must be http or https, got {parsed.scheme!r}")
    if not parsed.username:
        raise DsnError("DSN has no public key (expected https://<key>@<host>/<project_id>)")
    if not parsed.hostname:
        raise DsnError("DSN has no host")

    # Self-hosted installs may live under a path prefix: https://key@host/prefix/<id>
    segments = [part for part in parsed.path.split("/") if part]
    project_id = segments[-1] if segments else ""
    if not project_id.isdigit():
        raise DsnError(f"DSN path must end in a numeric project id, got {parsed.path!r}")

    netloc = parsed.hostname
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    path_prefix = "/".join(segments[:-1])
    base = f"{parsed.scheme}://{netloc}" + (f"/{path_prefix}" if path_prefix else "")

    return {
        "scheme": parsed.scheme,
        "host": netloc,
        "public_key": parsed.username,
        "project_id": project_id,
        "envelope_url": f"{base}/api/{project_id}/envelope/",
    }


def build_event(args: argparse.Namespace, event_id: str, timestamp: str) -> dict:
    event: dict = {
        "event_id": event_id,
        "timestamp": timestamp,
        "platform": "other",
        "level": args.level,
        "logger": "sentry-skill",
        "logentry": {"formatted": args.message},
        "sdk": {"name": "sentry.skill.testsender", "version": "1.0"},
        "tags": {"test_event": "true"},
        "extra": {"sent_by": CLIENT, "host": platform.node()},
    }
    if args.environment:
        event["environment"] = args.environment
    if args.release:
        event["release"] = args.release
    for pair in args.tag or []:
        key, _, value = pair.partition("=")
        if not _:
            raise ValueError(f"--tag expects key=value, got {pair!r}")
        event["tags"][key] = value
    return event


def build_envelope(event: dict, event_id: str, timestamp: str) -> bytes:
    # No "dsn" key in the header — the X-Sentry-Auth header already carries the key.
    header = {"event_id": event_id, "sent_at": timestamp}
    body = json.dumps(event, separators=(",", ":"))
    item_header = {
        "type": "event",
        "content_type": "application/json",
        "length": len(body.encode("utf-8")),
    }
    lines = [
        json.dumps(header, separators=(",", ":")),
        json.dumps(item_header, separators=(",", ":")),
        body,
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def send(dsn: dict, envelope: bytes, timeout: float) -> tuple[int, str]:
    auth = (
        "Sentry sentry_version=7, "
        f"sentry_client={CLIENT}, "
        f"sentry_key={dsn['public_key']}"
    )
    request = urllib.request.Request(
        dsn["envelope_url"],
        data=envelope,
        method="POST",
        headers={
            "Content-Type": "application/x-sentry-envelope",
            "X-Sentry-Auth": auth,
            "User-Agent": CLIENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send a test event to Sentry (stdlib only).")
    parser.add_argument("--dsn", default=os.environ.get("SENTRY_DSN"),
                        help="Sentry DSN (defaults to $SENTRY_DSN)")
    parser.add_argument("--message", default="Sentry skill test event",
                        help="Message body of the event")
    parser.add_argument("--level", default="error", choices=LEVELS)
    parser.add_argument("--environment", default=os.environ.get("SENTRY_ENVIRONMENT"))
    parser.add_argument("--release", default=os.environ.get("SENTRY_RELEASE"))
    parser.add_argument("--tag", action="append", metavar="KEY=VALUE",
                        help="Extra tag; repeatable")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the envelope and exit without sending")
    args = parser.parse_args(argv)

    if not args.dsn:
        parser.error("no DSN: pass --dsn or set SENTRY_DSN")

    try:
        dsn = parse_dsn(args.dsn)
    except DsnError as exc:
        print(f"invalid DSN: {exc}", file=sys.stderr)
        return 2

    event_id = uuid.uuid4().hex
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    try:
        event = build_event(args, event_id, timestamp)
    except ValueError as exc:
        parser.error(str(exc))

    envelope = build_envelope(event, event_id, timestamp)

    print(f"host       : {dsn['host']}")
    print(f"project id : {dsn['project_id']}")
    print(f"public key : {dsn['public_key'][:6]}… ({len(dsn['public_key'])} chars)")
    print(f"endpoint   : {dsn['envelope_url']}")
    print(f"event id   : {event_id}")

    if args.dry_run:
        print("\n--- envelope ---")
        print(envelope.decode("utf-8"))
        return 0

    try:
        status, body = send(dsn, envelope, args.timeout)
    except urllib.error.URLError as exc:
        print(f"\nnetwork error: {exc.reason}", file=sys.stderr)
        return 1

    print(f"http status: {status}")
    if body.strip():
        print(f"response   : {body.strip()[:400]}")

    if status == 200:
        print(f"\nSent. Search Sentry for id:{event_id} (allow a minute for indexing).")
        print("If it never appears, the project is filtering or rate-limiting it —")
        print("check Settings -> Inbound Filters and Stats -> Usage.")
        return 0
    if status == 400:
        print("\n400: Sentry rejected the envelope — usually a wrong public key "
              "('invalid project key') or a malformed payload.", file=sys.stderr)
    elif status == 401:
        print("\n401: the public key in the DSN is wrong or has been revoked.", file=sys.stderr)
    elif status == 403:
        print("\n403: key disabled, or the project no longer exists.", file=sys.stderr)
    elif status == 429:
        print("\n429: rate limited or quota exhausted for this project.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
