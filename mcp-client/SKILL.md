---
name: mcp-client
description: Test, explore, and manage MCP servers. Verify connectivity, list tools/resources/prompts, execute tools, benchmark performance, manage auth tokens, and register servers. Use when the user wants to test, debug, or interact with MCP servers.
argument-hint: <command> [server-name or connection flags] [args]
---

# MCP Client

A comprehensive MCP client for testing, exploring, and managing MCP servers.

## Script Location

```
MCP_CLIENT="$HOME/.claude/skills/mcp-client/scripts/mcp_client.py"
```

## Dependencies

Requires `mcp` Python package (pip install mcp). Uses `mcp.client` SDK for stdio, SSE, and Streamable HTTP transports.

## Commands

| Command | Description |
|---------|-------------|
| `explore` | Full exploration: lists tools, resources, resource templates, and prompts |
| `tools` | List available tools (supports `--json`) |
| `call <tool> [args]` | Execute a tool with arguments (JSON or `key=val,key=val`) |
| `resource <uri>` | Read a resource by URI |
| `prompt <name> [args]` | Get a prompt with optional arguments |
| `health` | Health check with latency metrics (supports `--json`) |
| `benchmark <tool> [args] -n N` | Benchmark tool response time (default 5 iterations) |
| `schema <tool>` | Get the full JSON schema for a tool |
| `token-set <server> <token> [--type bearer\|api-key\|custom]` | Save auth token |
| `token-list` | List all saved tokens |
| `token-delete <server>` | Delete a saved token |
| `register <name> -t <transport> [-u url] [--cmd command] [--args arg1 arg2...]` | Register a server |
| `servers` | List registered servers |
| `unregister <name>` | Remove a registered server |

## Connection Options

Every server command accepts either:

**Named server** (registered):
```bash
python3 "$MCP_CLIENT" explore -s my-server
```

**Inline connection**:
```bash
# stdio
python3 "$MCP_CLIENT" explore -t stdio --cmd mcp --args run server.py

# SSE
python3 "$MCP_CLIENT" explore -t sse -u http://localhost:8000/sse

# Streamable HTTP
python3 "$MCP_CLIENT" explore -t http -u http://localhost:8000/mcp
```

## Auth Tokens

Tokens stored at `~/.claude/skills/mcp-client/tokens.json`. Auto-included when server name matches:
- `bearer` → `Authorization: Bearer <token>`
- `api-key` → `X-API-Key: <token>`
- `custom` → `Authorization: <token>`

## Examples

```bash
# Register a server
python3 "$MCP_CLIENT" register my-kg -t http -u http://localhost:8000/mcp

# Save token
python3 "$MCP_CLIENT" token-set my-kg "sk-abc123" --type bearer

# Full exploration
python3 "$MCP_CLIENT" explore -s my-kg

# Call a tool (JSON args)
python3 "$MCP_CLIENT" call query '{"query": "test"}' -s my-kg

# Call a tool (key=value args)
python3 "$MCP_CLIENT" call add 'a=2,b=3' -t stdio --cmd python3 --args server.py

# Health check (JSON output)
python3 "$MCP_CLIENT" health -s my-kg --json

# Benchmark 10 iterations
python3 "$MCP_CLIENT" benchmark query '{"q": "test"}' -s my-kg -n 10

# Schema for a tool
python3 "$MCP_CLIENT" schema query -s my-kg
```

## Workflow

When the user says `/mcp-client`, parse `$ARGUMENTS`:

1. If contains a command (`explore`, `call`, `health`, etc.) — run it via bash.
2. If vague ("test my server at localhost:8000") — run `health` first, then `explore` if healthy.
3. If mentions "register"/"save" — use `register` + optionally `token-set`.
4. Always show the full output to the user.
5. For `benchmark` results, briefly analyze latency distribution.

**Note:** All output goes to stderr to avoid conflicts with stdio MCP transport. Use `2>&1` to capture output when running from shell.
