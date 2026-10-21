"""Build the field list the page reads (_system/catalog.js) from the scanned tables + app/labels.yaml.

The catalog never contains database, schema or table names: the page asks in business terms
and each machine's runner translates to its own tables.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from .config import connect, load_yaml
from .scan import field_types

SMALL_WORDS = {"of", "and", "or", "the", "for", "to", "in"}


def display_name(en, acronyms=()):
    acronyms = {a.lower() for a in acronyms}
    out = []
    for i, w in enumerate(w for w in str(en).split("_") if w):
        if w.lower() in acronyms:
            out.append(w.upper())
        elif i and w.lower() in SMALL_WORDS:
            out.append(w.lower())
        else:
            out.append(w.capitalize())
    return " ".join(out)


def ordered_columns(tables: list) -> list:
    """Columns of the newest table first (its order), then any older-only columns."""
    out = []
    for t in sorted(tables, key=lambda t: t["period"], reverse=True):
        for col in t["columns"]:
            if col not in out:
                out.append(col)
    return out


def build_catalog(found: dict, labels: dict, datasets_def: dict, values: dict | None = None, sample=False) -> dict:
    lab = labels.get("fields") or {}
    acr = labels.get("acronyms") or []
    order = {g: i for i, g in enumerate(labels.get("group_order") or [])}
    numbers_as_text = datasets_def.get("numbers_stored_as_text") or []
    values = values or {}
    seen, unlabeled = set(), set()
    out = {"schema": "bulkex-catalog/1", "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
           "sample": sample, "group_order": labels.get("group_order") or [], "datasets": {}}
    for ds, meta in (datasets_def.get("datasets") or {}).items():
        tables = found.get(ds) or []
        if not tables:
            continue
        types = field_types(tables, numbers_as_text)
        fields = []
        for col in ordered_columns(tables):
            seen.add(col)
            info = lab.get(col)
            if info is None:  # never skip a column: show its raw name and tell the admin
                unlabeled.add(col)
                info = {}
            en = info.get("en")
            if isinstance(en, dict):  # same column, different meaning per data set: {export: ..., import: ...}
                en = en.get(ds) or next(iter(en.values()), None)
            f = {"key": col, "label": display_name(en, acr) if en else col,
                 "group": info.get("group", "Other"), "type": "number" if types.get(col, "text") != "text" else "text"}
            if info.get("vi"):
                f["vi"] = info["vi"]
            if info.get("essential"):
                f["essential"] = True
            if info.get("default_op"):
                f["default_op"] = info["default_op"]
            v = (values.get(ds) or {}).get(col)
            if v and f["type"] == "text":
                f["values"] = v
            fields.append(f)
        fields.sort(key=lambda f: order.get(f["group"], 99))  # stable: keeps column order inside a group
        out["datasets"][ds] = {"label": meta.get("label", ds.capitalize()),
                               "periods": sorted({t["period"] for t in tables}), "fields": fields}
    swaps = {}
    for col, info in lab.items():
        if isinstance(info, dict) and info.get("swap_with"):
            swaps[col], swaps[info["swap_with"]] = info["swap_with"], col
    for d in out["datasets"].values():
        for f in d["fields"]:
            if f["key"] in swaps:
                f["swap"] = swaps[f["key"]]
    out["label_report"] = {"unlabeled": sorted(unlabeled), "unused": sorted(set(lab) - seen)}
    return out


def write_js(path: Path, var: str, data: dict, comment: str):
    """Write `window.<var> = {...};` atomically. Skips the write when only the timestamp changed (less OneDrive churn)."""
    path = Path(path)
    body = json.dumps(data, ensure_ascii=False, indent=1)
    text = f"/* {comment} */\nwindow.{var} = {body};\n"
    if path.exists():
        old = path.read_text(encoding="utf-8")
        strip = lambda s: "\n".join(l for l in s.splitlines() if '"generated_at"' not in l and '"updated_at"' not in l)  # noqa: E731
        if strip(old) == strip(text):
            return False
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return True


def scan_values(cfg, found: dict, datasets_def: dict, sample_rows=200_000) -> dict:
    """Suggestion lists: for each text column of the newest table, its values when there are few of them."""
    limit = int(datasets_def.get("suggest_max_values") or 300)
    numbers_as_text = set(datasets_def.get("numbers_stored_as_text") or [])
    out = {}
    from psycopg2 import sql
    for ds, tables in found.items():
        if not tables:
            continue
        newest = max(tables, key=lambda t: t["period"])
        conn = connect(cfg, newest["db"], timeout_minutes=5)
        try:
            out[ds] = {}
            for col, dtype in newest["columns"].items():
                if col in numbers_as_text or dtype not in ("text", "character varying", "character"):
                    continue
                q = sql.SQL("SELECT DISTINCT v FROM (SELECT {c}::text AS v FROM {s}.{t} LIMIT %s) x "
                            "WHERE v IS NOT NULL AND v <> '' LIMIT %s").format(
                    c=sql.Identifier(col), s=sql.Identifier(newest["schema"]), t=sql.Identifier(newest["table"]))
                with conn.cursor() as cur:
                    cur.execute(q, (sample_rows, limit + 1))
                    vals = sorted(r[0] for r in cur.fetchall())
                conn.rollback()
                if 0 < len(vals) <= limit:
                    out[ds][col] = vals
        finally:
            conn.close()
    return out


def load_defs(app_dir: Path):
    return load_yaml(Path(app_dir) / "labels.yaml"), load_yaml(Path(app_dir) / "datasets.yaml")
