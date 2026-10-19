"""Find the export/import tables on this machine, whatever they are called.

A table belongs to a data set when it has all the data set's signature columns (app/datasets.yaml).
Its month comes from its name: the first "20YY" followed by a month number.
"""
from __future__ import annotations

import re

from .config import connect

PERIOD_RE = re.compile(r"(?<!\d)(20\d{2})[^0-9a-z]{0,2}(?:m)?(0[1-9]|1[0-2]|[1-9])(?!\d)", re.IGNORECASE)
NUMERIC_TYPES = {"smallint", "integer", "bigint", "numeric", "real", "double precision", "decimal", "money"}
SKIP_SCHEMAS = ("pg_catalog", "information_schema", "pg_toast")


def table_period(name: str):
    """'x_y2026_06' -> '2026-06'; 'i_2025_7' -> '2025-07'; no year+month -> None."""
    m = PERIOD_RE.search(name)
    if not m:
        return None
    return f"{m.group(1)}-{int(m.group(2)):02d}"


def list_databases(cfg) -> list:
    conn = connect(cfg, cfg.get("maintenance_db") or "postgres")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT datname FROM pg_database WHERE NOT datistemplate AND datallowconn ORDER BY datname")
            return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def tables_in_database(cfg, dbname) -> dict:
    """{(schema, table): {column: data_type}} for every user table/view in one database."""
    conn = connect(cfg, dbname)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT c.table_schema, c.table_name, c.column_name, c.data_type
                   FROM information_schema.columns c
                   JOIN information_schema.tables t ON t.table_schema = c.table_schema AND t.table_name = c.table_name
                   WHERE c.table_schema NOT IN %s AND c.table_schema NOT LIKE 'pg_temp%%'
                   ORDER BY c.table_schema, c.table_name, c.ordinal_position""",
                (SKIP_SCHEMAS,),
            )
            out = {}
            for schema, table, column, dtype in cur.fetchall():
                out.setdefault((schema, table), {})[column] = dtype
            return out
    finally:
        conn.close()


def scan(cfg, datasets_def: dict, only_databases=None):
    """Return ({dataset: [table info sorted by period]}, [warnings])."""
    warnings = []
    found = {ds: [] for ds in datasets_def}
    try:
        databases = only_databases or list_databases(cfg)
    except Exception as e:  # noqa: BLE001 - reported to the admin, not raised
        return found, [f"Cannot list databases: {e}"]
    for db in databases:
        try:
            tables = tables_in_database(cfg, db)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"Skipped database {db}: {str(e).strip().splitlines()[0]}")
            continue
        for (schema, table), columns in tables.items():
            cols = set(columns)
            matches = [ds for ds, d in datasets_def.items() if set(d.get("signature") or []) <= cols]
            if not matches:
                continue
            if len(matches) > 1:
                warnings.append(f"{db}.{schema}.{table} fits {', '.join(matches)}; used as {matches[0]}")
            period = table_period(table)
            if not period:
                warnings.append(f"{db}.{schema}.{table} looks like {matches[0]} data but its name has no year and month; skipped")
                continue
            found[matches[0]].append({"db": db, "schema": schema, "table": table, "period": period, "columns": columns})
    for ds, items in found.items():
        by_period = {}
        for t in items:
            by_period.setdefault(t["period"], []).append(t)
        kept = []
        for period, group in sorted(by_period.items()):
            if len(group) > 1:
                group.sort(key=lambda t: (len(t["table"]), t["db"], t["schema"], t["table"]))
                names = ", ".join(f"{t['db']}.{t['schema']}.{t['table']}" for t in group)
                warnings.append(f"{ds} {period}: several tables ({names}); using {group[0]['table']}")
            kept.append(group[0])
        found[ds] = kept
    return found, warnings


def field_types(tables: list, numbers_as_text) -> dict:
    """{column: 'number' | 'text' | 'number_text'} across all tables of one data set."""
    out = {}
    numbers_as_text = set(numbers_as_text or [])
    for t in tables:
        for col, dtype in t["columns"].items():
            if dtype in NUMERIC_TYPES:
                out[col] = "number"
            elif col not in out:
                out[col] = "number_text" if col in numbers_as_text else "text"
    return out
