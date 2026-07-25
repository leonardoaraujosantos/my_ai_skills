#!/usr/bin/env python3
"""
MCP Client - A comprehensive tool for testing, exploring, and managing MCP servers.

Supports stdio, SSE, and Streamable HTTP transports.
Manages authentication tokens per server.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

TOKEN_FILE = Path.home() / ".claude" / "skills" / "mcp-client" / "tokens.json"
SERVERS_FILE = Path.home() / ".claude" / "skills" / "mcp-client" / "servers.json"


def out(msg: str = ""):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


# ─── Token Management ────────────────────────────────────────────────────────

def load_tokens() -> dict:
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text())
    return {}

def save_tokens(tokens: dict):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2))

def set_token(server_name: str, token: str, token_type: str = "bearer"):
    tokens = load_tokens()
    tokens[server_name] = {"token": token, "type": token_type}
    save_tokens(tokens)
    out(f"Token saved for '{server_name}' (type: {token_type})")

def get_token(server_name: str) -> Optional[dict]:
    return load_tokens().get(server_name)

def list_tokens():
    tokens = load_tokens()
    if not tokens:
        out("No tokens stored.")
        return
    out(f"{'Server':<30} {'Type':<15} {'Token (preview)':<30}")
    out("-" * 75)
    for name, info in tokens.items():
        t = info["token"]
        preview = t[:8] + "..." + t[-4:] if len(t) > 16 else "****"
        out(f"{name:<30} {info['type']:<15} {preview:<30}")

def delete_token(server_name: str):
    tokens = load_tokens()
    if server_name in tokens:
        del tokens[server_name]
        save_tokens(tokens)
        out(f"Token deleted for '{server_name}'")
    else:
        out(f"No token found for '{server_name}'")


# ─── Server Registry ─────────────────────────────────────────────────────────

def load_servers() -> dict:
    if SERVERS_FILE.exists():
        return json.loads(SERVERS_FILE.read_text())
    return {}

def save_servers(servers: dict):
    SERVERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SERVERS_FILE.write_text(json.dumps(servers, indent=2))

def register_server(name: str, transport: str, **kwargs):
    servers = load_servers()
    servers[name] = {"transport": transport, **kwargs}
    save_servers(servers)
    out(f"Server '{name}' registered (transport: {transport})")

def list_servers():
    servers = load_servers()
    if not servers:
        out("No servers registered.")
        return
    out(f"{'Name':<25} {'Transport':<15} {'Target':<50}")
    out("-" * 90)
    for name, info in servers.items():
        t = info["transport"]
        if t == "stdio":
            target = f"{info.get('command', '')} {' '.join(info.get('args', []))}"
        else:
            target = info.get("url", "N/A")
        out(f"{name:<25} {t:<15} {target:<50}")

def delete_server(name: str):
    servers = load_servers()
    if name in servers:
        del servers[name]
        save_servers(servers)
        out(f"Server '{name}' removed")
    else:
        out(f"Server '{name}' not found")


# ─── Connection ───────────────────────────────────────────────────────────────

def _get_headers(server_name: Optional[str] = None) -> dict:
    headers = {}
    if server_name:
        token_info = get_token(server_name)
        if token_info:
            if token_info["type"] == "bearer":
                headers["Authorization"] = f"Bearer {token_info['token']}"
            elif token_info["type"] == "api-key":
                headers["X-API-Key"] = token_info["token"]
            elif token_info["type"] == "custom":
                headers["Authorization"] = token_info["token"]
    return headers


@asynccontextmanager
async def connect_server(transport: str, server_name: Optional[str] = None, **kwargs):
    headers = _get_headers(server_name)

    if transport == "stdio":
        cmd = kwargs.get("command", "")
        cmd_args = kwargs.get("args", [])
        env = kwargs.get("env")
        params = StdioServerParameters(command=cmd, args=cmd_args, env=env)
        async with stdio_client(params) as (rs, ws):
            async with ClientSession(rs, ws) as session:
                await session.initialize()
                yield session

    elif transport == "sse":
        url = kwargs.get("url", "")
        async with sse_client(url, headers=headers) as (rs, ws):
            async with ClientSession(rs, ws) as session:
                await session.initialize()
                yield session

    elif transport in ("http", "streamable-http"):
        url = kwargs.get("url", "")
        async with streamablehttp_client(url, headers=headers) as (rs, ws, _):
            async with ClientSession(rs, ws) as session:
                await session.initialize()
                yield session
    else:
        raise ValueError(f"Unknown transport: {transport}")


def resolve_conn(args) -> tuple[str, dict, Optional[str]]:
    if args.server:
        servers = load_servers()
        if args.server not in servers:
            out(f"Error: Server '{args.server}' not registered.")
            sys.exit(1)
        info = servers[args.server]
        transport = info["transport"]
        params = {k: v for k, v in info.items() if k != "transport"}
        return transport, params, args.server

    transport = args.transport
    if not transport:
        out("Error: --transport or --server is required")
        sys.exit(1)

    params = {}
    if transport == "stdio":
        if not args.cmd:
            out("Error: --cmd required for stdio transport")
            sys.exit(1)
        params["command"] = args.cmd
        params["args"] = args.cmd_args or []
    else:
        if not args.url:
            out("Error: --url required for SSE/HTTP transport")
            sys.exit(1)
        params["url"] = args.url

    return transport, params, args.server


# ─── Commands ─────────────────────────────────────────────────────────────────

async def cmd_explore(args):
    transport, params, sname = resolve_conn(args)
    out(f"Connecting via {transport}...")
    start = time.time()

    async with connect_server(transport, sname, **params) as session:
        out(f"Connected in {time.time() - start:.2f}s\n")

        if hasattr(session, 'server_info') and session.server_info:
            si = session.server_info
            out(f"Server: {getattr(si, 'name', 'N/A')} v{getattr(si, 'version', 'N/A')}\n")

        out("=" * 60)
        out("TOOLS")
        out("=" * 60)
        try:
            r = await session.list_tools()
            tools = r.tools if hasattr(r, 'tools') else []
            if tools:
                for t in tools:
                    out(f"\n  {t.name}")
                    if t.description:
                        out(f"    Description: {t.description}")
                    if t.inputSchema:
                        props = t.inputSchema.get("properties", {})
                        req = t.inputSchema.get("required", [])
                        if props:
                            out("    Parameters:")
                            for pn, pi in props.items():
                                r_mark = " (required)" if pn in req else ""
                                out(f"      - {pn}: {pi.get('type', 'any')}{r_mark} {pi.get('description', '')}")
            else:
                out("  (none)")
        except Exception as e:
            out(f"  Error: {e}")

        out(f"\n{'=' * 60}")
        out("RESOURCES")
        out("=" * 60)
        try:
            r = await session.list_resources()
            resources = r.resources if hasattr(r, 'resources') else []
            if resources:
                for res in resources:
                    out(f"\n  {res.uri}")
                    if hasattr(res, 'name') and res.name:
                        out(f"    Name: {res.name}")
                    if hasattr(res, 'description') and res.description:
                        out(f"    Description: {res.description}")
            else:
                out("  (none)")
        except Exception as e:
            out(f"  Error: {e}")

        out(f"\n{'=' * 60}")
        out("RESOURCE TEMPLATES")
        out("=" * 60)
        try:
            r = await session.list_resource_templates()
            templates = r.resource_templates if hasattr(r, 'resource_templates') else []
            if templates:
                for t in templates:
                    out(f"\n  {t.uriTemplate}")
                    if hasattr(t, 'name') and t.name:
                        out(f"    Name: {t.name}")
                    if hasattr(t, 'description') and t.description:
                        out(f"    Description: {t.description}")
            else:
                out("  (none)")
        except Exception as e:
            out(f"  Error: {e}")

        out(f"\n{'=' * 60}")
        out("PROMPTS")
        out("=" * 60)
        try:
            r = await session.list_prompts()
            prompts = r.prompts if hasattr(r, 'prompts') else []
            if prompts:
                for p in prompts:
                    out(f"\n  {p.name}")
                    if p.description:
                        out(f"    Description: {p.description}")
            else:
                out("  (none)")
        except Exception as e:
            out(f"  Error: {e}")

        out(f"\n{'=' * 60}")
        out(f"Done. Total: {time.time() - start:.2f}s")


async def cmd_list_tools(args):
    transport, params, sname = resolve_conn(args)
    async with connect_server(transport, sname, **params) as session:
        r = await session.list_tools()
        tools = r.tools if hasattr(r, 'tools') else []
        if args.json_output:
            data = [{"name": t.name, "description": t.description, "schema": t.inputSchema} for t in tools]
            out(json.dumps(data, indent=2))
        else:
            for t in tools:
                out(f"  {t.name}: {t.description or '(no description)'}")


def _parse_tool_args(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        result = {}
        for pair in raw.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                if v.lower() in ("true", "false"):
                    v = v.lower() == "true"
                else:
                    try:
                        v = int(v)
                    except ValueError:
                        try:
                            v = float(v)
                        except ValueError:
                            pass
                result[k.strip()] = v
        return result


async def cmd_call_tool(args):
    transport, params, sname = resolve_conn(args)
    tool_args = _parse_tool_args(args.tool_args)

    async with connect_server(transport, sname, **params) as session:
        out(f"Calling: {args.tool_name}")
        out(f"Args: {json.dumps(tool_args, indent=2)}")
        out("-" * 40)

        start = time.time()
        result = await session.call_tool(args.tool_name, tool_args)
        elapsed = time.time() - start

        if hasattr(result, 'content'):
            for item in result.content:
                if hasattr(item, 'text'):
                    if args.json_output:
                        try:
                            out(json.dumps(json.loads(item.text), indent=2))
                        except json.JSONDecodeError:
                            out(item.text)
                    else:
                        out(item.text)
                elif hasattr(item, 'data'):
                    out(f"[Binary: {len(item.data)} bytes]")

        if hasattr(result, 'isError') and result.isError:
            out("[ERROR] Tool returned an error")
        out(f"\nTime: {elapsed:.3f}s")


async def cmd_read_resource(args):
    transport, params, sname = resolve_conn(args)
    async with connect_server(transport, sname, **params) as session:
        out(f"Reading: {args.uri}")
        out("-" * 40)
        result = await session.read_resource(args.uri)
        if hasattr(result, 'contents'):
            for item in result.contents:
                if hasattr(item, 'text'):
                    out(item.text)
                elif hasattr(item, 'blob'):
                    out(f"[Binary: {len(item.blob)} bytes]")


async def cmd_get_prompt(args):
    transport, params, sname = resolve_conn(args)
    prompt_args = _parse_tool_args(args.prompt_args)

    async with connect_server(transport, sname, **params) as session:
        out(f"Prompt: {args.prompt_name}")
        out("-" * 40)
        result = await session.get_prompt(args.prompt_name, prompt_args)
        if hasattr(result, 'messages'):
            for msg in result.messages:
                out(f"\n[{getattr(msg, 'role', '?')}]")
                if hasattr(msg, 'content'):
                    c = msg.content
                    if isinstance(c, str):
                        out(c)
                    elif hasattr(c, 'text'):
                        out(c.text)


async def cmd_health(args):
    transport, params, sname = resolve_conn(args)
    out(f"Health check ({transport})...")
    start = time.time()
    try:
        async with connect_server(transport, sname, **params) as session:
            ct = time.time() - start

            t0 = time.time()
            tr = await session.list_tools()
            tt = time.time() - t0
            tools = tr.tools if hasattr(tr, 'tools') else []

            t0 = time.time()
            rr = await session.list_resources()
            rt = time.time() - t0
            resources = rr.resources if hasattr(rr, 'resources') else []

            total = time.time() - start
            status = {
                "status": "healthy",
                "connect_ms": round(ct * 1000),
                "tools": len(tools),
                "tools_ms": round(tt * 1000),
                "resources": len(resources),
                "resources_ms": round(rt * 1000),
                "total_ms": round(total * 1000),
            }
            if hasattr(session, 'server_info') and session.server_info:
                status["server"] = getattr(session.server_info, 'name', None)
                status["version"] = getattr(session.server_info, 'version', None)

            if args.json_output:
                out(json.dumps(status, indent=2))
            else:
                out(f"  Status: HEALTHY")
                if status.get("server"):
                    out(f"  Server: {status['server']} v{status.get('version', '?')}")
                out(f"  Connect: {status['connect_ms']}ms")
                out(f"  Tools: {status['tools']} ({status['tools_ms']}ms)")
                out(f"  Resources: {status['resources']} ({status['resources_ms']}ms)")
                out(f"  Total: {status['total_ms']}ms")
    except Exception as e:
        elapsed = time.time() - start
        if args.json_output:
            out(json.dumps({"status": "unhealthy", "error": str(e), "elapsed_ms": round(elapsed * 1000)}, indent=2))
        else:
            out(f"  Status: UNHEALTHY")
            out(f"  Error: {e}")
            out(f"  Elapsed: {round(elapsed * 1000)}ms")
        sys.exit(1)


async def cmd_benchmark(args):
    transport, params, sname = resolve_conn(args)
    n = args.iterations or 5
    tool_args = _parse_tool_args(args.tool_args)

    async with connect_server(transport, sname, **params) as session:
        out(f"Benchmarking '{args.tool_name}' x{n}...")
        out("-" * 40)

        times, errors = [], 0
        for i in range(n):
            t0 = time.time()
            try:
                result = await session.call_tool(args.tool_name, tool_args)
                elapsed = time.time() - t0
                if hasattr(result, 'isError') and result.isError:
                    errors += 1
                    out(f"  [{i+1}] {elapsed*1000:.1f}ms (error)")
                else:
                    times.append(elapsed)
                    out(f"  [{i+1}] {elapsed*1000:.1f}ms")
            except Exception as e:
                errors += 1
                out(f"  [{i+1}] {(time.time()-t0)*1000:.1f}ms (exception: {e})")

        if times:
            avg = sum(times) / len(times)
            s = sorted(times)
            out(f"\nResults ({len(times)} ok, {errors} errors):")
            out(f"  Avg: {avg*1000:.1f}ms  Min: {s[0]*1000:.1f}ms  Max: {s[-1]*1000:.1f}ms  P50: {s[len(s)//2]*1000:.1f}ms")
        else:
            out("\nAll iterations failed.")


async def cmd_schema(args):
    transport, params, sname = resolve_conn(args)
    async with connect_server(transport, sname, **params) as session:
        r = await session.list_tools()
        for t in (r.tools if hasattr(r, 'tools') else []):
            if t.name == args.tool_name:
                out(json.dumps(t.inputSchema, indent=2))
                return
        out(f"Tool '{args.tool_name}' not found")
        sys.exit(1)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def add_conn_args(parser):
    g = parser.add_argument_group("connection")
    g.add_argument("-s", "--server", help="Registered server name")
    g.add_argument("-t", "--transport", choices=["stdio", "sse", "http", "streamable-http"])
    g.add_argument("-u", "--url", help="Server URL (SSE/HTTP)")
    g.add_argument("--cmd", help="Server command (stdio)")
    g.add_argument("--args", dest="cmd_args", nargs="*", help="Command args (stdio)")
    g.add_argument("--json", dest="json_output", action="store_true", help="JSON output")


CMD_MAP = {
    "explore": cmd_explore,
    "tools": cmd_list_tools,
    "call": cmd_call_tool,
    "resource": cmd_read_resource,
    "prompt": cmd_get_prompt,
    "health": cmd_health,
    "benchmark": cmd_benchmark,
    "schema": cmd_schema,
}


def main():
    parser = argparse.ArgumentParser(prog="mcp-client", description="MCP Client")
    sub = parser.add_subparsers(dest="subcmd", required=True)

    p = sub.add_parser("explore", help="Full server exploration")
    add_conn_args(p)

    p = sub.add_parser("tools", help="List tools")
    add_conn_args(p)

    p = sub.add_parser("call", help="Call a tool")
    p.add_argument("tool_name")
    p.add_argument("tool_args", nargs="?", help='JSON or key=val,key=val')
    add_conn_args(p)

    p = sub.add_parser("resource", help="Read a resource")
    p.add_argument("uri")
    add_conn_args(p)

    p = sub.add_parser("prompt", help="Get a prompt")
    p.add_argument("prompt_name")
    p.add_argument("prompt_args", nargs="?", help='JSON or key=val,key=val')
    add_conn_args(p)

    p = sub.add_parser("health", help="Health check")
    add_conn_args(p)

    p = sub.add_parser("benchmark", help="Benchmark a tool")
    p.add_argument("tool_name")
    p.add_argument("tool_args", nargs="?", help='JSON or key=val,key=val')
    p.add_argument("-n", "--iterations", type=int, default=5)
    add_conn_args(p)

    p = sub.add_parser("schema", help="Get tool schema")
    p.add_argument("tool_name")
    add_conn_args(p)

    p = sub.add_parser("token-set", help="Save a token")
    p.add_argument("server_name")
    p.add_argument("token")
    p.add_argument("--type", default="bearer", choices=["bearer", "api-key", "custom"])

    p = sub.add_parser("token-list", help="List tokens")

    p = sub.add_parser("token-delete", help="Delete a token")
    p.add_argument("server_name")

    p = sub.add_parser("register", help="Register a server")
    p.add_argument("name")
    p.add_argument("-t", "--transport", required=True, choices=["stdio", "sse", "http", "streamable-http"])
    p.add_argument("-u", "--url")
    p.add_argument("--cmd", dest="reg_cmd")
    p.add_argument("--args", dest="reg_args", nargs="*")

    p = sub.add_parser("servers", help="List servers")

    p = sub.add_parser("unregister", help="Remove a server")
    p.add_argument("name")

    args = parser.parse_args()

    if args.subcmd == "token-set":
        set_token(args.server_name, args.token, args.type)
    elif args.subcmd == "token-list":
        list_tokens()
    elif args.subcmd == "token-delete":
        delete_token(args.server_name)
    elif args.subcmd == "register":
        kw = {"transport": args.transport}
        if args.url:
            kw["url"] = args.url
        if args.reg_cmd:
            kw["command"] = args.reg_cmd
        if args.reg_args:
            kw["args"] = args.reg_args
        register_server(args.name, **kw)
    elif args.subcmd == "servers":
        list_servers()
    elif args.subcmd == "unregister":
        delete_server(args.name)
    else:
        func = CMD_MAP.get(args.subcmd)
        if func:
            try:
                asyncio.run(func(args))
            except KeyboardInterrupt:
                out("Interrupted.")
                sys.exit(130)
            except SystemExit as e:
                sys.exit(e.code)
            except BaseException as e:
                out(f"Error ({type(e).__name__}): {e}")
                import traceback
                traceback.print_exc(file=sys.stderr)
                sys.exit(1)


if __name__ == "__main__":
    main()
