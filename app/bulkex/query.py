"""Turn one part of a BulkEx request into safe PostgreSQL.

Safety rules (handoff/RULES.md):
- field names must exist in the scanned tables, operators must be known -> otherwise the request is refused;
- table and column names go in with sql.Identifier, every user value goes in as a query parameter;
- type names used in casts come from a fixed list, never from the request.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from psycopg2 import sql

TEXT_OPS = {"is_any_of", "is_none_of", "starts_with", "not_starts_with", "contains", "not_contains",
            "ends_with", "length_is", "is_empty", "is_not_empty"}
NUM_OPS = {"is_any_of", "between", "gt", "gte", "lt", "lte", "is_empty", "is_not_empty"}
NO_VALUE = {"is_empty", "is_not_empty"}
TEXT_TYPES = {"text", "character varying", "character"}
CASTABLE = {"text", "character varying", "character", "smallint", "integer", "bigint", "numeric", "real",
            "double precision", "date", "timestamp without time zone", "timestamp with time zone", "boolean"}
MONTH_RE = re.compile(r"^20\d{2}-(0[1-9]|1[0-2])$")
MAX_VALUES = 5000
MAX_DEPTH = 3


class RequestError(Exception):
    """Something the requester can fix; the message is shown on the page."""


# ---------------------------------------------------------------- validation
def _num(v, where):
    try:
        d = Decimal(str(v).strip().replace(",", ""))
    except (InvalidOperation, ValueError):
        raise RequestError(f"{where}: '{v}' is not a number.") from None
    if not d.is_finite():
        raise RequestError(f"{where}: '{v}' is not a number.")
    return d


def validate_filter(node, types, labels, depth=1):
    if not isinstance(node, dict) or node.get("match") not in ("all", "any") or not isinstance(node.get("items"), list):
        raise RequestError("The filter in this request is damaged. Send it again from the page.")
    if depth > MAX_DEPTH:
        raise RequestError("Groups are nested too deep.")
    if len(node["items"]) > 200:
        raise RequestError("Too many conditions (more than 200).")
    for it in node["items"]:
        if "items" in it:
            validate_filter(it, types, labels, depth + 1)
            continue
        field, op, values = it.get("field"), it.get("op"), it.get("values") or []
        if field not in types:
            raise RequestError(f"Field '{field}' does not exist in this data set.")
        name = labels.get(field, field)
        kind = "number" if types[field] != "text" else "text"
        allowed = NUM_OPS if kind == "number" else TEXT_OPS
        if op not in allowed:
            raise RequestError(f"{name}: '{op}' can't be used on this field.")
        if not isinstance(values, list) or len(values) > MAX_VALUES:
            raise RequestError(f"{name}: too many values (the limit is {MAX_VALUES}).")
        values = [str(v).strip() for v in values if str(v).strip() != ""]
        if any(len(v) > 300 for v in values):
            raise RequestError(f"{name}: one of the values is longer than 300 characters.")
        if op in NO_VALUE:
            values = []
        elif not values:
            raise RequestError(f"{name}: add at least one value.")
        if op == "between" and len(values) != 2:
            raise RequestError(f"{name}: 'between' needs two numbers.")
        if op in ("gt", "gte", "lt", "lte") and len(values) != 1:
            raise RequestError(f"{name}: needs exactly one number.")
        if op == "length_is":
            if len(values) != 1 or not values[0].isdigit() or not 0 < int(values[0]) <= 200:
                raise RequestError(f"{name}: the number of characters must be a whole number from 1 to 200.")
        if kind == "number" and op not in NO_VALUE:
            values = [_num(v, name) for v in values]
        it["values"] = values


def validate_part(part, catalog_ds, labels):
    """Check one part against the scanned catalog; returns the cleaned part."""
    types = catalog_ds["types"]
    months = (part.get("period") or {}).get("months") or []
    if not isinstance(months, list) or not months:
        raise RequestError("Pick at least one month.")
    bad = [m for m in months if not isinstance(m, str) or not MONTH_RE.match(m)]
    if bad:
        raise RequestError(f"Month '{bad[0]}' is not valid.")
    validate_filter(part.get("filter") or {"match": "all", "items": []}, types, labels)
    out = part.get("output") or {}
    rows, summary = out.get("rows"), out.get("summary")
    if not rows and not summary:
        raise RequestError("Tick Detail rows, Summary, or both.")
    if rows:
        cols = rows.get("columns") or []
        unknown = [c for c in cols if c not in types]
        if unknown:
            raise RequestError(f"Column '{unknown[0]}' does not exist in this data set.")
        if not cols:
            raise RequestError("Choose at least one column for the Detail sheet.")
        for s in rows.get("sort") or []:
            if s.get("field") not in types or s.get("dir") not in ("asc", "desc"):
                raise RequestError("The sort setting is not valid.")
    if summary:
        gb = summary.get("group_by") or []
        if not gb or any(g not in types for g in gb):
            raise RequestError("Pick what each Summary row stands for.")
        for m in summary.get("measures") or []:
            if m.get("fn") == "sum" and types.get(m.get("field")) not in ("number", "number_text"):
                raise RequestError(f"'{labels.get(m.get('field'), m.get('field'))}' can't be added up.")
            if m.get("fn") not in ("count", "sum"):
                raise RequestError("The summary setting is not valid.")
        top = summary.get("top")
        if top is not None and (not isinstance(top, int) or not 0 < top <= 1_000_000):
            raise RequestError("'Keep only the top' must be a whole number.")
    return part


# ---------------------------------------------------------------- expressions
def _dtype(table, col):
    return table["columns"].get(col)


def text_expr(table, col):
    dt = _dtype(table, col)
    if dt is None:
        return sql.SQL("NULL::text")
    ident = sql.Identifier(col)
    return ident if dt in TEXT_TYPES else sql.SQL("CAST({} AS text)").format(ident)


def num_expr(table, col):
    dt = _dtype(table, col)
    if dt is None:
        return sql.SQL("NULL::numeric")
    ident = sql.Identifier(col)
    if dt in TEXT_TYPES:  # numbers stored as text: keep digits, dot and minus; '' -> NULL
        return sql.SQL("NULLIF(regexp_replace(CAST({} AS text), '[^0-9.\\-]', '', 'g'), '')::numeric").format(ident)
    return sql.SQL("CAST({} AS numeric)").format(ident)


def out_type(tables, col):
    """One SQL type for a column across months, so UNION ALL never fails on mismatched types."""
    seen = {t["columns"][col] for t in tables if col in t["columns"]}
    if len(seen) == 1:
        only = next(iter(seen))
        return only if only in CASTABLE else "text"
    return "text"


def out_expr(table, col, common):
    dt = _dtype(table, col)
    if dt is None:
        return sql.SQL("NULL::" + common)  # common comes from CASTABLE or is "text"
    ident = sql.Identifier(col)
    return ident if dt == common else sql.SQL("CAST({} AS " + common + ")").format(ident)


def _like(v, pre, post):
    v = v.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return pre + v + post


def compile_cond(c, table, types):
    field, op, vals = c["field"], c["op"], c.get("values") or []
    if types[field] != "text":
        e = num_expr(table, field)
        if op == "is_any_of":
            return sql.SQL("{} = ANY(%s::numeric[])").format(e), [list(vals)]
        if op == "between":
            lo, hi = sorted(vals)
            return sql.SQL("{} BETWEEN %s AND %s").format(e), [lo, hi]
        sym = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}.get(op)
        if sym:
            return sql.SQL("{} " + sym + " %s").format(e), [vals[0]]
        if op == "is_empty":
            return sql.SQL("{} IS NULL").format(e), []
        if op == "is_not_empty":
            return sql.SQL("{} IS NOT NULL").format(e), []
        raise RequestError(f"'{op}' can't be used on a number field.")
    e = text_expr(table, field)
    if op == "is_any_of":
        return sql.SQL("lower({}) = ANY(%s)").format(e), [[v.lower() for v in vals]]
    if op == "is_none_of":
        return sql.SQL("({0} IS NULL OR NOT lower({0}) = ANY(%s))").format(e), [[v.lower() for v in vals]]
    patterns = {"starts_with": ("", "%"), "not_starts_with": ("", "%"), "contains": ("%", "%"),
                "not_contains": ("%", "%"), "ends_with": ("%", "")}
    if op in patterns:
        pre, post = patterns[op]
        pats = [_like(v, pre, post) for v in vals]
        if op.startswith("not_"):
            return sql.SQL("({0} IS NULL OR NOT {0} ILIKE ANY(%s))").format(e), [pats]
        return sql.SQL("{} ILIKE ANY(%s)").format(e), [pats]
    if op == "length_is":
        return sql.SQL("char_length({}) = %s").format(e), [int(vals[0])]
    if op == "is_empty":
        return sql.SQL("({0} IS NULL OR btrim({0}) = '')").format(e), []
    if op == "is_not_empty":
        return sql.SQL("({0} IS NOT NULL AND btrim({0}) <> '')").format(e), []
    raise RequestError(f"Unknown condition '{op}'.")


def compile_filter(node, table, types):
    parts, params = [], []
    for it in node.get("items") or []:
        frag, p = compile_filter(it, table, types) if "items" in it else compile_cond(it, table, types)
        parts.append(frag)
        params.extend(p)
    if not parts:
        return sql.SQL("TRUE"), []
    joiner = sql.SQL(" AND " if node.get("match") == "all" else " OR ")
    return sql.SQL("(") + joiner.join(parts) + sql.SQL(")"), params


# ---------------------------------------------------------------- queries
def tables_for(part, tables):
    """Tables for the requested months, grouped by database; plus the months that have no table."""
    want = set(part["period"]["months"])
    chosen = [t for t in tables if t["period"] in want]
    missing = sorted(want - {t["period"] for t in chosen})
    by_db = {}
    for t in sorted(chosen, key=lambda t: t["period"]):
        by_db.setdefault(t["db"], []).append(t)
    return by_db, missing


def _from(t):
    return sql.SQL("{}.{}").format(sql.Identifier(t["schema"]), sql.Identifier(t["table"]))


def _union(tables, select_for, flt, types):
    blocks, params = [], []
    for t in tables:
        where, p = compile_filter(flt, t, types)
        blocks.append(sql.SQL("SELECT {} FROM {} WHERE {}").format(select_for(t), _from(t), where))
        params.extend(p)
    return sql.SQL(" UNION ALL ").join(blocks), params


def count_query(part, tables, types):
    union, params = _union(tables, lambda t: sql.SQL("1"), part["filter"], types)
    return sql.SQL("SELECT COUNT(*) FROM (") + union + sql.SQL(") u"), params


def filter_fields(node):
    out = []
    for it in node.get("items") or []:
        for k in (filter_fields(it) if "items" in it else [it.get("field")]):
            if k and k not in out:
                out.append(k)
    return out


def rows_query(part, tables, types, all_tables=None, with_sort_key=False):
    rows = part["output"]["rows"]
    cols = list(rows["columns"])
    sort = (rows.get("sort") or [None])[0]
    common = {c: out_type(all_tables or tables, c) for c in cols}

    def select_for(t):
        items = [sql.SQL("{} AS {}").format(out_expr(t, c, common[c]), sql.Identifier(c)) for c in cols]
        if sort:
            key = num_expr(t, sort["field"]) if types[sort["field"]] != "text" else text_expr(t, sort["field"])
            items.append(sql.SQL("{} AS __sort").format(key))
        return sql.SQL(", ").join(items)

    union, params = _union(tables, select_for, part["filter"], types)
    outcols = sql.SQL(", ").join(sql.Identifier(c) for c in cols)
    if rows.get("distinct"):
        extra = sql.SQL(", __sort") if sort else sql.SQL("")
        inner = sql.SQL("SELECT DISTINCT {}{} FROM (").format(outcols, extra) + union + sql.SQL(") u")
    else:
        inner = union
    shown = outcols + (sql.SQL(", __sort") if sort and with_sort_key else sql.SQL(""))
    q = sql.SQL("SELECT {} FROM (").format(shown) + inner + sql.SQL(") d")
    if sort:
        q += sql.SQL(" ORDER BY __sort " + ("DESC" if sort["dir"] == "desc" else "ASC") + " NULLS LAST")
    return q, params


def summary_query(part, tables, types, with_limit=True, all_tables=None):
    s = part["output"]["summary"]
    gb = list(s["group_by"])
    sums = [m["field"] for m in s.get("measures") or [] if m.get("fn") == "sum"]
    common = {c: out_type(all_tables or tables, c) for c in gb}

    def select_for(t):
        items = [sql.SQL("{} AS {}").format(out_expr(t, c, common[c]), sql.Identifier("g" + str(i))) for i, c in enumerate(gb)]
        items += [sql.SQL("{} AS {}").format(num_expr(t, c), sql.Identifier("s" + str(i))) for i, c in enumerate(sums)]
        return sql.SQL(", ").join(items)

    union, params = _union(tables, select_for, part["filter"], types)
    gcols = [sql.Identifier("g" + str(i)) for i in range(len(gb))]
    scols = [sql.SQL("SUM({})").format(sql.Identifier("s" + str(i))) for i in range(len(sums))]
    q = (sql.SQL("SELECT ") + sql.SQL(", ").join(gcols + [sql.SQL("COUNT(*)")] + scols)
         + sql.SQL(" FROM (") + union + sql.SQL(") u GROUP BY ") + sql.SQL(", ").join(gcols)
         + sql.SQL(" ORDER BY COUNT(*) DESC"))
    top = s.get("top")
    if with_limit and top:
        q += sql.SQL(" LIMIT %s")
        params = params + [int(top)]
    return q, params, gb, sums
