#!/usr/bin/env python3
"""
PostgreSQL Client — query, inspect, mutate, and graph-query PostgreSQL databases.

Supports local, remote, and Supabase connections.
Includes Apache AGE graph query support.
Connection profiles are saved for reuse.
"""

import argparse
import json
import os
import sys
import csv as csv_mod
import time
import io
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

import psycopg2
import psycopg2.extras

PROFILES_FILE = Path.home() / ".claude" / "skills" / "pg-client" / "profiles.json"

# ─── Profile Management ──────────────────────────────────────────────────────

def load_profiles() -> dict:
    if PROFILES_FILE.exists():
        return json.loads(PROFILES_FILE.read_text())
    return {}

def save_profiles(profiles: dict):
    PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILES_FILE.write_text(json.dumps(profiles, indent=2))

def cmd_profile_add(args):
    profiles = load_profiles()
    p = {"dsn": args.dsn}
    if args.supabase:
        p["supabase"] = True
    profiles[args.name] = p
    save_profiles(profiles)
    print(f"Profile '{args.name}' saved.")

def cmd_profile_list(args):
    profiles = load_profiles()
    if not profiles:
        print("No profiles saved.")
        return
    print(f"{'Name':<20} {'DSN (preview)':<60} {'Type':<10}")
    print("-" * 90)
    for name, info in profiles.items():
        dsn = info["dsn"]
        # Mask password in display
        preview = _mask_dsn(dsn)
        ptype = "supabase" if info.get("supabase") else "postgres"
        print(f"{name:<20} {preview:<60} {ptype:<10}")

def cmd_profile_delete(args):
    profiles = load_profiles()
    if args.name in profiles:
        del profiles[args.name]
        save_profiles(profiles)
        print(f"Profile '{args.name}' deleted.")
    else:
        print(f"Profile '{args.name}' not found.")

def _mask_dsn(dsn: str) -> str:
    """Mask password in DSN for display."""
    if "@" in dsn and ":" in dsn:
        try:
            pre_at = dsn.split("@")[0]
            post_at = dsn.split("@", 1)[1]
            if ":" in pre_at:
                parts = pre_at.rsplit(":", 1)
                return f"{parts[0]}:****@{post_at}"
        except Exception:
            pass
    return dsn[:40] + "..." if len(dsn) > 40 else dsn


# ─── Connection ───────────────────────────────────────────────────────────────

def _resolve_dsn(args) -> str:
    """Get DSN from --profile or --dsn."""
    if hasattr(args, 'profile') and args.profile:
        profiles = load_profiles()
        if args.profile not in profiles:
            print(f"Error: Profile '{args.profile}' not found.")
            sys.exit(1)
        return profiles[args.profile]["dsn"]
    if hasattr(args, 'dsn') and args.dsn:
        return args.dsn
    # Check env
    env_dsn = os.environ.get("DATABASE_URL") or os.environ.get("PG_DSN")
    if env_dsn:
        return env_dsn
    print("Error: No connection. Use --profile, --dsn, or set DATABASE_URL env var.")
    sys.exit(1)

@contextmanager
def get_conn(args):
    """Get a psycopg2 connection from args."""
    dsn = _resolve_dsn(args)
    conn = psycopg2.connect(dsn)
    try:
        yield conn
    finally:
        conn.close()


# ─── Output Formatting ───────────────────────────────────────────────────────

def format_rows(columns, rows, fmt="table"):
    """Format query results."""
    if fmt == "json":
        data = [dict(zip(columns, row)) for row in rows]
        return json.dumps(data, indent=2, default=str)
    elif fmt == "csv":
        buf = io.StringIO()
        writer = csv_mod.writer(buf)
        writer.writerow(columns)
        writer.writerows(rows)
        return buf.getvalue()
    elif fmt == "vertical":
        lines = []
        for i, row in enumerate(rows):
            lines.append(f"*** Row {i+1} ***")
            for col, val in zip(columns, row):
                lines.append(f"  {col}: {val}")
        return "\n".join(lines)
    else:  # table
        if not rows:
            return "(0 rows)"
        col_widths = [len(str(c)) for c in columns]
        for row in rows:
            for i, val in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(val) if val is not None else "NULL"))
        # Cap width
        col_widths = [min(w, 60) for w in col_widths]

        header = " | ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(columns))
        sep = "-+-".join("-" * w for w in col_widths)
        lines = [header, sep]
        for row in rows:
            line = " | ".join(
                str(val if val is not None else "NULL")[:60].ljust(col_widths[i])
                for i, val in enumerate(row)
            )
            lines.append(line)
        lines.append(f"({len(rows)} rows)")
        return "\n".join(lines)


# ─── SQL Commands ─────────────────────────────────────────────────────────────

def cmd_query(args):
    """Execute a SQL query and display results."""
    sql = args.sql
    if sql == "-":
        sql = sys.stdin.read()
    elif sql.endswith(".sql") and Path(sql).exists():
        sql = Path(sql).read_text()

    with get_conn(args) as conn:
        conn.autocommit = True
        start = time.time()
        with conn.cursor() as cur:
            cur.execute(sql)
            elapsed = time.time() - start

            if cur.description:
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()

                if args.limit and len(rows) > args.limit:
                    rows = rows[:args.limit]
                    print(f"(showing first {args.limit} of more rows)")

                print(format_rows(columns, rows, args.format))
                print(f"\nTime: {elapsed:.3f}s")
            else:
                print(f"OK ({cur.rowcount} rows affected, {elapsed:.3f}s)")


def cmd_exec(args):
    """Execute a SQL statement (INSERT/UPDATE/DELETE) with transaction."""
    sql = args.sql
    if sql == "-":
        sql = sys.stdin.read()
    elif sql.endswith(".sql") and Path(sql).exists():
        sql = Path(sql).read_text()

    with get_conn(args) as conn:
        start = time.time()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                elapsed = time.time() - start
                rowcount = cur.rowcount

                if args.returning and cur.description:
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    conn.commit()
                    print(format_rows(columns, rows, args.format))
                else:
                    conn.commit()
                    print(f"OK ({rowcount} rows affected, {elapsed:.3f}s)")
        except Exception as e:
            conn.rollback()
            print(f"Error (rolled back): {e}")
            sys.exit(1)


def cmd_explain(args):
    """Run EXPLAIN ANALYZE on a query."""
    sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT {'JSON' if args.format == 'json' else 'TEXT'}) {args.sql}"

    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            if args.format == "json":
                print(json.dumps(rows[0][0], indent=2))
            else:
                for row in rows:
                    print(row[0])


# ─── Schema Inspection ───────────────────────────────────────────────────────

def cmd_tables(args):
    """List tables in the database."""
    schema = args.schema or "public"
    sql = """
        SELECT table_name, table_type,
               pg_size_pretty(pg_total_relation_size(quote_ident(table_schema) || '.' || quote_ident(table_name))) as size
        FROM information_schema.tables
        WHERE table_schema = %s
        ORDER BY table_name
    """
    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql, (schema,))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            print(format_rows(columns, rows, args.format))


def cmd_describe(args):
    """Describe a table's columns, types, constraints."""
    table = args.table
    schema = args.schema or "public"

    sql_columns = """
        SELECT c.column_name, c.data_type, c.is_nullable, c.column_default,
               c.character_maximum_length,
               CASE WHEN tc.constraint_type = 'PRIMARY KEY' THEN 'PK'
                    WHEN tc.constraint_type = 'FOREIGN KEY' THEN 'FK'
                    WHEN tc.constraint_type = 'UNIQUE' THEN 'UQ'
                    ELSE '' END as constraint
        FROM information_schema.columns c
        LEFT JOIN information_schema.key_column_usage kcu
            ON c.table_schema = kcu.table_schema
            AND c.table_name = kcu.table_name
            AND c.column_name = kcu.column_name
        LEFT JOIN information_schema.table_constraints tc
            ON kcu.constraint_name = tc.constraint_name
            AND kcu.table_schema = tc.table_schema
        WHERE c.table_schema = %s AND c.table_name = %s
        ORDER BY c.ordinal_position
    """

    sql_indexes = """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = %s AND tablename = %s
    """

    sql_fks = """
        SELECT
            tc.constraint_name,
            kcu.column_name,
            ccu.table_name AS foreign_table,
            ccu.column_name AS foreign_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
            ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_schema = %s AND tc.table_name = %s
            AND tc.constraint_type = 'FOREIGN KEY'
    """

    sql_row_count = f"SELECT count(*) FROM {schema}.{table}"

    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            # Table info
            print(f"Table: {schema}.{table}")

            # Row count
            try:
                cur.execute(sql_row_count)
                count = cur.fetchone()[0]
                print(f"Rows: {count:,}")
            except Exception:
                pass

            # Columns
            print(f"\nColumns:")
            cur.execute(sql_columns, (schema, table))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            print(format_rows(columns, rows, args.format))

            # Indexes
            print(f"\nIndexes:")
            cur.execute(sql_indexes, (schema, table))
            idx_rows = cur.fetchall()
            if idx_rows:
                for row in idx_rows:
                    print(f"  {row[0]}: {row[1]}")
            else:
                print("  (none)")

            # Foreign keys
            print(f"\nForeign Keys:")
            cur.execute(sql_fks, (schema, table))
            fk_rows = cur.fetchall()
            if fk_rows:
                for row in fk_rows:
                    print(f"  {row[0]}: {row[1]} -> {row[2]}({row[3]})")
            else:
                print("  (none)")


def cmd_schemas(args):
    """List database schemas."""
    sql = """
        SELECT schema_name,
               (SELECT count(*) FROM information_schema.tables t
                WHERE t.table_schema = s.schema_name) as table_count
        FROM information_schema.schemata s
        WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        ORDER BY schema_name
    """
    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            print(format_rows(columns, rows, args.format))


def cmd_extensions(args):
    """List installed extensions."""
    sql = "SELECT extname, extversion, extrelocatable FROM pg_extension ORDER BY extname"
    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            print(format_rows(columns, rows, args.format))


def cmd_size(args):
    """Show database and table sizes."""
    sql_db = "SELECT pg_size_pretty(pg_database_size(current_database())) as db_size, current_database() as db_name"

    sql_tables = """
        SELECT schemaname || '.' || relname as table,
               pg_size_pretty(pg_total_relation_size(relid)) as total_size,
               pg_size_pretty(pg_relation_size(relid)) as data_size,
               pg_size_pretty(pg_indexes_size(relid)) as index_size,
               n_live_tup as est_rows
        FROM pg_stat_user_tables
        ORDER BY pg_total_relation_size(relid) DESC
        LIMIT %s
    """

    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql_db)
            row = cur.fetchone()
            print(f"Database: {row[1]} ({row[0]})\n")

            limit = args.limit or 20
            cur.execute(sql_tables, (limit,))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            print(format_rows(columns, rows, args.format))


def cmd_activity(args):
    """Show active connections and queries."""
    sql = """
        SELECT pid, usename, client_addr, state,
               now() - query_start as duration,
               left(query, 100) as query
        FROM pg_stat_activity
        WHERE state IS NOT NULL
            AND pid != pg_backend_pid()
        ORDER BY query_start DESC NULLS LAST
        LIMIT %s
    """
    limit = args.limit or 20
    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            print(format_rows(columns, rows, args.format))


def cmd_locks(args):
    """Show current locks."""
    sql = """
        SELECT l.pid, l.locktype, l.mode, l.granted,
               a.usename, a.state,
               left(a.query, 80) as query
        FROM pg_locks l
        JOIN pg_stat_activity a ON l.pid = a.pid
        WHERE a.pid != pg_backend_pid()
        ORDER BY l.granted, a.query_start
        LIMIT 30
    """
    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            print(format_rows(columns, rows, args.format))


def cmd_vacuum(args):
    """Show vacuum stats for tables."""
    sql = """
        SELECT schemaname || '.' || relname as table,
               last_vacuum, last_autovacuum,
               last_analyze, last_autoanalyze,
               n_dead_tup as dead_tuples,
               n_live_tup as live_tuples,
               CASE WHEN n_live_tup > 0
                    THEN round(100.0 * n_dead_tup / n_live_tup, 1)
                    ELSE 0 END as dead_pct
        FROM pg_stat_user_tables
        ORDER BY n_dead_tup DESC
        LIMIT %s
    """
    limit = args.limit or 20
    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            print(format_rows(columns, rows, args.format))


def cmd_slow_queries(args):
    """Show slow queries from pg_stat_statements (if available)."""
    sql = """
        SELECT left(query, 120) as query,
               calls,
               round(total_exec_time::numeric, 2) as total_ms,
               round(mean_exec_time::numeric, 2) as avg_ms,
               round(max_exec_time::numeric, 2) as max_ms,
               rows
        FROM pg_stat_statements
        ORDER BY mean_exec_time DESC
        LIMIT %s
    """
    limit = args.limit or 20
    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            try:
                cur.execute(sql, (limit,))
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                print(format_rows(columns, rows, args.format))
            except psycopg2.errors.UndefinedTable:
                print("pg_stat_statements extension not enabled.")
                print("Enable with: CREATE EXTENSION pg_stat_statements;")


def cmd_search(args):
    """Search for a string across all text columns in a table."""
    table = args.table
    pattern = args.pattern
    schema = args.schema or "public"

    # Get text columns
    sql_cols = """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
            AND data_type IN ('text', 'character varying', 'character', 'name', 'json', 'jsonb')
    """
    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql_cols, (schema, table))
            text_cols = [r[0] for r in cur.fetchall()]
            if not text_cols:
                print(f"No text columns found in {schema}.{table}")
                return

            conditions = " OR ".join(f'"{col}"::text ILIKE %s' for col in text_cols)
            sql = f"SELECT * FROM {schema}.{table} WHERE {conditions} LIMIT %s"
            params = [f"%{pattern}%"] * len(text_cols) + [args.limit or 50]

            cur.execute(sql, params)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            print(format_rows(columns, rows, args.format))


def cmd_sample(args):
    """Get random sample rows from a table."""
    table = args.table
    schema = args.schema or "public"
    n = args.limit or 10
    sql = f"SELECT * FROM {schema}.{table} TABLESAMPLE BERNOULLI(10) LIMIT %s"
    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            try:
                cur.execute(sql, (n,))
            except Exception:
                # Fallback for views or tables that don't support TABLESAMPLE
                cur.execute(f"SELECT * FROM {schema}.{table} ORDER BY random() LIMIT %s", (n,))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            print(format_rows(columns, rows, args.format))


def cmd_dump_table(args):
    """Dump table data as INSERT statements or CSV."""
    table = args.table
    schema = args.schema or "public"

    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            limit_clause = f"LIMIT {args.limit}" if args.limit else ""
            cur.execute(f"SELECT * FROM {schema}.{table} {limit_clause}")
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

            if args.format == "csv":
                print(format_rows(columns, rows, "csv"))
            elif args.format == "json":
                print(format_rows(columns, rows, "json"))
            else:
                # INSERT statements
                for row in rows:
                    vals = []
                    for v in row:
                        if v is None:
                            vals.append("NULL")
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        elif isinstance(v, bool):
                            vals.append("TRUE" if v else "FALSE")
                        else:
                            escaped = str(v).replace("'", "''")
                            vals.append(f"'{escaped}'")
                    cols_str = ", ".join(f'"{c}"' for c in columns)
                    vals_str = ", ".join(vals)
                    print(f"INSERT INTO {schema}.{table} ({cols_str}) VALUES ({vals_str});")
                print(f"\n-- {len(rows)} rows")


# ─── Apache AGE Graph Queries ────────────────────────────────────────────────

def cmd_graph(args):
    """Execute an Apache AGE graph query (Cypher)."""
    graph_name = args.graph
    cypher = args.cypher

    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            # Load AGE extension
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, '$user', public;")

            # Wrap in age_cypher function
            sql = f"SELECT * FROM cypher('{graph_name}', $$ {cypher} $$) as (result agtype);"

            start = time.time()
            cur.execute(sql)
            elapsed = time.time() - start

            if cur.description:
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                # Parse agtype results
                parsed_rows = []
                for row in rows:
                    parsed = []
                    for val in row:
                        if isinstance(val, str):
                            try:
                                parsed.append(json.loads(val))
                            except (json.JSONDecodeError, TypeError):
                                parsed.append(val)
                        else:
                            parsed.append(val)
                    parsed_rows.append(parsed)

                if args.format == "json":
                    data = [dict(zip(columns, r)) for r in parsed_rows]
                    print(json.dumps(data, indent=2, default=str))
                else:
                    for i, row in enumerate(parsed_rows):
                        print(f"[{i+1}] {row[0] if len(row) == 1 else row}")
                print(f"\n({len(rows)} results, {elapsed:.3f}s)")
            else:
                print(f"OK ({elapsed:.3f}s)")


def cmd_graph_list(args):
    """List available graphs (Apache AGE)."""
    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            try:
                cur.execute("LOAD 'age';")
                cur.execute("SET search_path = ag_catalog, '$user', public;")
                cur.execute("SELECT name, namespace FROM ag_graph ORDER BY name;")
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                if rows:
                    print(format_rows(columns, rows, args.format))
                else:
                    print("No graphs found.")
            except Exception as e:
                print(f"Apache AGE not available: {e}")


def cmd_graph_schema(args):
    """Show graph schema — node labels and edge types."""
    graph_name = args.graph
    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, '$user', public;")

            # Node labels
            print("Node Labels:")
            try:
                cur.execute(f"""
                    SELECT name, kind
                    FROM ag_label
                    WHERE graph = (SELECT graphid FROM ag_graph WHERE name = '{graph_name}')
                    ORDER BY kind, name
                """)
                for row in cur.fetchall():
                    kind = "vertex" if row[1] == 'v' else "edge"
                    print(f"  {row[0]} ({kind})")
            except Exception as e:
                print(f"  Error: {e}")

            # Sample nodes per label
            print(f"\nSample data (first 3 per label):")
            try:
                cur.execute(f"""
                    SELECT name FROM ag_label
                    WHERE graph = (SELECT graphid FROM ag_graph WHERE name = '{graph_name}')
                        AND kind = 'v' AND name != '_ag_label_vertex'
                """)
                labels = [r[0] for r in cur.fetchall()]
                for label in labels[:10]:
                    print(f"\n  [{label}]:")
                    try:
                        cur.execute(f"SELECT * FROM cypher('{graph_name}', $$ MATCH (n:{label}) RETURN n LIMIT 3 $$) as (n agtype);")
                        for row in cur.fetchall():
                            print(f"    {row[0]}")
                    except Exception:
                        print(f"    (could not sample)")
            except Exception:
                pass


def cmd_graph_create(args):
    """Create a new graph."""
    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, '$user', public;")
            cur.execute(f"SELECT create_graph('{args.graph}');")
            print(f"Graph '{args.graph}' created.")


def cmd_graph_drop(args):
    """Drop a graph."""
    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, '$user', public;")
            cascade = "true" if args.cascade else "false"
            cur.execute(f"SELECT drop_graph('{args.graph}', {cascade});")
            print(f"Graph '{args.graph}' dropped.")


# ─── Supabase-Specific ───────────────────────────────────────────────────────

def cmd_rls(args):
    """Show Row Level Security policies for a table or all tables."""
    sql = """
        SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
        FROM pg_policies
        WHERE schemaname = %s
    """
    params = [args.schema or "public"]
    if args.table:
        sql += " AND tablename = %s"
        params.append(args.table)
    sql += " ORDER BY tablename, policyname"

    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            if rows:
                print(format_rows(columns, rows, args.format))
            else:
                print("No RLS policies found.")


def cmd_functions(args):
    """List user-defined functions."""
    schema = args.schema or "public"
    sql = """
        SELECT p.proname as name,
               pg_get_function_arguments(p.oid) as arguments,
               t.typname as return_type,
               CASE p.prokind WHEN 'f' THEN 'function' WHEN 'p' THEN 'procedure' WHEN 'a' THEN 'aggregate' END as kind
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        JOIN pg_type t ON p.prorettype = t.oid
        WHERE n.nspname = %s
        ORDER BY p.proname
    """
    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql, (schema,))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            print(format_rows(columns, rows, args.format))


def cmd_triggers(args):
    """List triggers for a table or all tables."""
    schema = args.schema or "public"
    sql = """
        SELECT trigger_name, event_manipulation, event_object_table,
               action_timing, action_statement
        FROM information_schema.triggers
        WHERE trigger_schema = %s
    """
    params = [schema]
    if args.table:
        sql += " AND event_object_table = %s"
        params.append(args.table)
    sql += " ORDER BY event_object_table, trigger_name"

    with get_conn(args) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            print(format_rows(columns, rows, args.format))


# ─── CLI ──────────────────────────────────────────────────────────────────────

def add_conn_args(parser):
    g = parser.add_argument_group("connection")
    g.add_argument("-p", "--profile", help="Use saved profile")
    g.add_argument("--dsn", help="PostgreSQL DSN (connection string)")
    g.add_argument("--format", "-f", choices=["table", "json", "csv", "vertical"], default="table")
    g.add_argument("--schema", default=None, help="Schema (default: public)")
    g.add_argument("--limit", "-n", type=int, default=None)


def main():
    parser = argparse.ArgumentParser(prog="pg-client", description="PostgreSQL Client")
    sub = parser.add_subparsers(dest="subcmd", required=True)

    # Query
    p = sub.add_parser("query", aliases=["q"], help="Execute SQL query")
    p.add_argument("sql", help="SQL query, file.sql, or - for stdin")
    add_conn_args(p)

    # Exec (mutating)
    p = sub.add_parser("exec", aliases=["e"], help="Execute SQL (INSERT/UPDATE/DELETE)")
    p.add_argument("sql", help="SQL statement, file.sql, or - for stdin")
    p.add_argument("--returning", action="store_true", help="Expect RETURNING clause")
    add_conn_args(p)

    # Explain
    p = sub.add_parser("explain", help="EXPLAIN ANALYZE a query")
    p.add_argument("sql")
    add_conn_args(p)

    # Schema inspection
    p = sub.add_parser("tables", help="List tables")
    add_conn_args(p)

    p = sub.add_parser("describe", aliases=["desc"], help="Describe a table")
    p.add_argument("table")
    add_conn_args(p)

    p = sub.add_parser("schemas", help="List schemas")
    add_conn_args(p)

    p = sub.add_parser("extensions", help="List extensions")
    add_conn_args(p)

    p = sub.add_parser("functions", help="List functions")
    add_conn_args(p)

    p = sub.add_parser("triggers", help="List triggers")
    p.add_argument("--table", help="Filter by table")
    add_conn_args(p)

    # Data exploration
    p = sub.add_parser("search", help="Search text across table columns")
    p.add_argument("table")
    p.add_argument("pattern")
    add_conn_args(p)

    p = sub.add_parser("sample", help="Random sample rows")
    p.add_argument("table")
    add_conn_args(p)

    p = sub.add_parser("dump", help="Dump table as INSERT/CSV/JSON")
    p.add_argument("table")
    add_conn_args(p)

    # Database stats
    p = sub.add_parser("size", help="Database and table sizes")
    add_conn_args(p)

    p = sub.add_parser("activity", help="Active connections and queries")
    add_conn_args(p)

    p = sub.add_parser("locks", help="Current locks")
    add_conn_args(p)

    p = sub.add_parser("vacuum", help="Vacuum stats")
    add_conn_args(p)

    p = sub.add_parser("slow", help="Slow queries (pg_stat_statements)")
    add_conn_args(p)

    # RLS (Supabase)
    p = sub.add_parser("rls", help="Show RLS policies")
    p.add_argument("--table", help="Filter by table")
    add_conn_args(p)

    # Apache AGE graph
    p = sub.add_parser("graph", help="Execute Cypher graph query")
    p.add_argument("graph", help="Graph name")
    p.add_argument("cypher", help="Cypher query")
    add_conn_args(p)

    p = sub.add_parser("graphs", help="List graphs (Apache AGE)")
    add_conn_args(p)

    p = sub.add_parser("graph-schema", help="Show graph schema")
    p.add_argument("graph")
    add_conn_args(p)

    p = sub.add_parser("graph-create", help="Create a graph")
    p.add_argument("graph")
    add_conn_args(p)

    p = sub.add_parser("graph-drop", help="Drop a graph")
    p.add_argument("graph")
    p.add_argument("--cascade", action="store_true")
    add_conn_args(p)

    # Profile management
    p = sub.add_parser("profile-add", help="Save a connection profile")
    p.add_argument("name")
    p.add_argument("dsn", help="PostgreSQL DSN")
    p.add_argument("--supabase", action="store_true", help="Mark as Supabase connection")

    p = sub.add_parser("profiles", help="List profiles")

    p = sub.add_parser("profile-delete", help="Delete a profile")
    p.add_argument("name")

    args = parser.parse_args()

    CMD_MAP = {
        "query": cmd_query, "q": cmd_query,
        "exec": cmd_exec, "e": cmd_exec,
        "explain": cmd_explain,
        "tables": cmd_tables,
        "describe": cmd_describe, "desc": cmd_describe,
        "schemas": cmd_schemas,
        "extensions": cmd_extensions,
        "functions": cmd_functions,
        "triggers": cmd_triggers,
        "search": cmd_search,
        "sample": cmd_sample,
        "dump": cmd_dump_table,
        "size": cmd_size,
        "activity": cmd_activity,
        "locks": cmd_locks,
        "vacuum": cmd_vacuum,
        "slow": cmd_slow_queries,
        "rls": cmd_rls,
        "graph": cmd_graph,
        "graphs": cmd_graph_list,
        "graph-schema": cmd_graph_schema,
        "graph-create": cmd_graph_create,
        "graph-drop": cmd_graph_drop,
        "profile-add": cmd_profile_add,
        "profiles": cmd_profile_list,
        "profile-delete": cmd_profile_delete,
    }

    func = CMD_MAP.get(args.subcmd)
    if func:
        try:
            func(args)
        except psycopg2.OperationalError as e:
            print(f"Connection error: {e}")
            sys.exit(1)
        except psycopg2.Error as e:
            print(f"PostgreSQL error: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nInterrupted.")
            sys.exit(130)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
