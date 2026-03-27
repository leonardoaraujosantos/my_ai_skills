---
name: pg-client
description: Investigate and interact with PostgreSQL databases — run queries, inspect schema, insert/update/delete data, explore graph data (Apache AGE), check RLS policies, monitor performance. Supports local, remote, and Supabase connections with saved profiles. Use when the user wants to query, explore, or manage PostgreSQL databases.
argument-hint: <command> [args] [-p profile | --dsn connection_string]
---

# PostgreSQL Client

Full-featured PostgreSQL client for querying, inspecting, mutating, and graph-querying databases.

## Script Location

```
PG_CLIENT="$HOME/.claude/skills/pg-client/scripts/pg_client.py"
```

## Dependencies

Requires `psycopg2` (already installed). For graph queries, the database needs Apache AGE extension.

## Commands

### Queries & Mutations
| Command | Description |
|---------|-------------|
| `query <sql>` / `q` | Execute SQL and display results |
| `exec <sql>` / `e` | Execute mutating SQL (INSERT/UPDATE/DELETE) with transaction |
| `explain <sql>` | EXPLAIN ANALYZE a query |

### Schema Inspection
| Command | Description |
|---------|-------------|
| `tables` | List all tables with sizes |
| `describe <table>` / `desc` | Columns, types, constraints, indexes, FKs, row count |
| `schemas` | List database schemas |
| `extensions` | List installed extensions |
| `functions` | List user-defined functions |
| `triggers [--table t]` | List triggers |

### Data Exploration
| Command | Description |
|---------|-------------|
| `search <table> <pattern>` | Full-text search across all text columns |
| `sample <table>` | Random sample rows |
| `dump <table>` | Dump as INSERT statements, CSV, or JSON |

### Database Health & Stats
| Command | Description |
|---------|-------------|
| `size` | Database and table sizes |
| `activity` | Active connections and running queries |
| `locks` | Current lock status |
| `vacuum` | Vacuum statistics and dead tuple counts |
| `slow` | Slow queries (requires pg_stat_statements) |

### Supabase / RLS
| Command | Description |
|---------|-------------|
| `rls [--table t]` | Show Row Level Security policies |

### Apache AGE Graph Queries
| Command | Description |
|---------|-------------|
| `graph <name> <cypher>` | Execute Cypher query on a graph |
| `graphs` | List available graphs |
| `graph-schema <name>` | Show graph node labels, edge types, samples |
| `graph-create <name>` | Create a new graph |
| `graph-drop <name> [--cascade]` | Drop a graph |

### Connection Profiles
| Command | Description |
|---------|-------------|
| `profile-add <name> <dsn> [--supabase]` | Save a connection |
| `profiles` | List saved profiles |
| `profile-delete <name>` | Remove a profile |

## Connection Options

Every command accepts:
- `-p <profile>` — use a saved profile
- `--dsn <connection_string>` — direct DSN
- Or set `DATABASE_URL` / `PG_DSN` environment variable

## Output Formats

`-f table` (default), `-f json`, `-f csv`, `-f vertical`

## Examples

```bash
# Save connection profiles
python3 "$PG_CLIENT" profile-add local "postgresql://user:pass@localhost:5432/mydb"
python3 "$PG_CLIENT" profile-add supabase "postgresql://postgres.xxxx:pass@aws-0-us-east-1.pooler.supabase.com:6543/postgres" --supabase
python3 "$PG_CLIENT" profile-add rag "postgresql://bridge:secret@localhost:5432/bridge"

# List tables
python3 "$PG_CLIENT" tables -p local

# Describe a table
python3 "$PG_CLIENT" describe users -p supabase

# Run a query
python3 "$PG_CLIENT" query "SELECT * FROM users LIMIT 10" -p local
python3 "$PG_CLIENT" q "SELECT count(*) FROM orders" -p local -f json

# Run from a .sql file
python3 "$PG_CLIENT" query report.sql -p local

# Insert/Update with transaction safety
python3 "$PG_CLIENT" exec "INSERT INTO users (name, email) VALUES ('Leo', 'leo@example.com')" -p local
python3 "$PG_CLIENT" exec "UPDATE users SET active=true WHERE id=1 RETURNING *" -p local --returning

# Explain a query
python3 "$PG_CLIENT" explain "SELECT * FROM orders WHERE total > 100" -p local

# Search across text columns
python3 "$PG_CLIENT" search users "john" -p local

# Random sample
python3 "$PG_CLIENT" sample orders -p local -n 5

# Dump table
python3 "$PG_CLIENT" dump users -p local -f csv
python3 "$PG_CLIENT" dump users -p local -f json -n 100

# Database health
python3 "$PG_CLIENT" size -p local
python3 "$PG_CLIENT" activity -p supabase
python3 "$PG_CLIENT" vacuum -p local
python3 "$PG_CLIENT" slow -p local

# RLS policies (Supabase)
python3 "$PG_CLIENT" rls -p supabase
python3 "$PG_CLIENT" rls --table profiles -p supabase

# Apache AGE graph queries
python3 "$PG_CLIENT" graphs -p rag
python3 "$PG_CLIENT" graph-schema my_graph -p rag
python3 "$PG_CLIENT" graph my_graph "MATCH (n) RETURN n LIMIT 10" -p rag
python3 "$PG_CLIENT" graph my_graph "MATCH (a)-[r]->(b) RETURN a.name, type(r), b.name LIMIT 20" -p rag
python3 "$PG_CLIENT" graph my_graph "CREATE (n:Person {name: 'Leo', role: 'dev'}) RETURN n" -p rag
```

## Workflow

When the user says `/pg-client`, parse `$ARGUMENTS`:

1. If contains a known command — run it directly.
2. If just a table name — run `describe` on it.
3. If a question about the DB — translate to SQL and run `query`.
4. If mentions "graph" — use the graph commands.
5. If mentions "supabase" — check for RLS too.
6. Always show output and execution time.
7. For mutations, confirm the SQL before executing.

## Security Notes

- Profiles with passwords are stored at `~/.claude/skills/pg-client/profiles.json`
- Passwords are masked in `profiles` output
- `exec` command uses transactions — rolls back on error
- Never run DROP/TRUNCATE without user confirmation
