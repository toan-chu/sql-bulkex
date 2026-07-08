"""Operator registry for SQL BulkEx runner filters."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from psycopg2 import sql


BASE_DIR = Path(__file__).resolve().parent
OPERATORS_FILE = BASE_DIR / "operators.yaml"
TOKEN_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class OperatorRegistryError(Exception):
    """Raised when operators.yaml is invalid."""


class OperatorValueError(Exception):
    """Raised when an operator value is invalid."""


def load_yaml_file(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class OperatorBuilder:
    """Load operator definitions and build WHERE fragments from registry templates."""

    def __init__(self, registry_path=None):
        self.registry_path = Path(registry_path) if registry_path is not None else OPERATORS_FILE
        self.registry = load_yaml_file(self.registry_path)
        self.operators = self.registry.get("operators") or {}
        self.display_order = self.registry.get("display_order") or []
        self._validate_registry()
        self.display_to_key = self._build_display_to_key()

    def _validate_registry(self):
        if not self.operators:
            raise OperatorRegistryError("operators.yaml thiếu operators.")
        if not self.display_order:
            raise OperatorRegistryError("operators.yaml thiếu display_order.")

        operator_keys = set(self.operators)
        order_keys = set(self.display_order)
        if operator_keys != order_keys:
            missing = sorted(operator_keys - order_keys)
            extra = sorted(order_keys - operator_keys)
            details = []
            if missing:
                details.append(f"thiếu trong display_order: {', '.join(missing)}")
            if extra:
                details.append(f"thừa trong display_order: {', '.join(extra)}")
            raise OperatorRegistryError("; ".join(details))

        required = {"display", "multi_value", "arity", "supports_digits"}
        for key, spec in self.operators.items():
            if not isinstance(spec, dict):
                raise OperatorRegistryError(f"Operator {key} phải là mapping.")
            missing = sorted(required - set(spec))
            if missing:
                raise OperatorRegistryError(f"Operator {key} thiếu field: {', '.join(missing)}")
            if not spec.get("sql_single") and not spec.get("sql_multi"):
                raise OperatorRegistryError(f"Operator {key} cần sql_single hoặc sql_multi.")
            if spec.get("supports_digits"):
                has_digits_template = any(
                    spec.get(name) for name in ("sql_single_with_digits", "sql_multi_with_digits")
                )
                if not has_digits_template:
                    raise OperatorRegistryError(f"Operator {key} supports_digits nhưng thiếu template digits.")

    def _build_display_to_key(self):
        result = {}
        for key, _display in self.display_labels():
            result[key.lower()] = key
            result[str(_display).strip().lower()] = key
        return result

    def display_labels(self):
        return [(key, self.operators[key]["display"]) for key in self.display_order]

    def valid_keys(self):
        return set(self.operators)

    def normalize_operator(self, raw):
        text = "" if raw is None else str(raw).strip()
        if not text:
            return ""
        return self.display_to_key.get(text.lower(), text.lower())

    def split_value(self, raw):
        return [part.strip() for part in str(raw).split(",") if part and part.strip()]

    def validate(self, col, op, val, digits=None):
        if op not in self.operators:
            raise OperatorValueError(f"Cột {col}: toán tử không hợp lệ '{op}'.")
        spec = self.operators[op]
        parts = self.split_value(val)
        if not parts:
            raise OperatorValueError(f"Cột {col}: toán tử {op} cần giá trị.")

        arity = spec.get("arity")
        if arity is not None and len(parts) != int(arity):
            raise OperatorValueError(f"Cột {col}: toán tử {op} cần đúng {arity} giá trị, có {len(parts)}.")
        if not spec.get("multi_value") and len(parts) != 1:
            raise OperatorValueError(f"Cột {col}: toán tử {op} cần 1 giá trị, có {len(parts)}.")

        digits_int = self.normalize_digits(digits)
        if digits_int is not None and spec.get("supports_digits"):
            longest = max(len(part) for part in parts)
            if digits_int < longest:
                raise OperatorValueError(f"Cột {col}: Digits ({digits_int}) < độ dài value ('{parts[0]}').")
        return True

    def normalize_digits(self, digits):
        if digits in (None, ""):
            return None
        if isinstance(digits, int):
            digits_int = digits
        else:
            text = str(digits).strip()
            if not text:
                return None
            if not text.isdigit():
                raise OperatorValueError(f"Digits phải là số nguyên dương: {digits}")
            digits_int = int(text)
        if digits_int < 1:
            raise OperatorValueError(f"Digits phải là số nguyên dương: {digits}")
        return digits_int

    def portal_value(self, op, val):
        parts = self.split_value(val)
        spec = self.operators[op]
        arity = spec.get("arity")
        if spec.get("multi_value") and (len(parts) > 1 or arity not in (None, 1)):
            return tuple(parts) if arity else parts
        return parts[0] if parts else ""

    def _template_key(self, spec, parts, digits):
        arity = spec.get("arity")
        multi = len(parts) > 1 or arity not in (None, 1)
        base = "sql_multi" if multi else "sql_single"
        if digits is not None and spec.get("supports_digits"):
            return f"{base}_with_digits" if spec.get(f"{base}_with_digits") else base
        return base

    def build_where(self, col, op, val, digits=None):
        self.validate(col, op, val, digits)
        spec = self.operators[op]
        parts = self.split_value(val)
        digits_int = self.normalize_digits(digits)
        if digits_int is not None and not spec.get("supports_digits"):
            digits_int = None
        template = spec.get(self._template_key(spec, parts, digits_int))
        if not template:
            raise OperatorRegistryError(f"Operator {op} thiếu SQL template phù hợp.")

        params = []
        fragment = self._compose_template(template, col, parts, digits_int, params)
        return fragment, params

    def debug_sql(self, col, op, val, digits=None):
        self.validate(col, op, val, digits)
        spec = self.operators[op]
        parts = self.split_value(val)
        digits_int = self.normalize_digits(digits)
        if digits_int is not None and not spec.get("supports_digits"):
            digits_int = None
        template = spec.get(self._template_key(spec, parts, digits_int))
        values = self._placeholder_values(parts, digits_int)
        text = template
        for name in sorted(set(TOKEN_RE.findall(template)), key=len, reverse=True):
            replacement = col if name == "col" else repr(values[name])
            text = text.replace("{" + name + "}", replacement)
        return text

    def _placeholder_values(self, parts, digits):
        first = parts[0] if parts else ""
        return {
            "val": first,
            "vals": list(parts),
            "v1": parts[0] if len(parts) > 0 else "",
            "v2": parts[1] if len(parts) > 1 else "",
            "val_prefix": f"{first}%",
            "vals_prefix": [f"{part}%" for part in parts],
            "val_contains": f"%{first}%",
            "vals_contains": [f"%{part}%" for part in parts],
            "val_suffix": f"%{first}",
            "vals_suffix": [f"%{part}" for part in parts],
            "digits": digits,
        }

    def _compose_template(self, template, col, parts, digits, params):
        values = self._placeholder_values(parts, digits)
        pieces = []
        pos = 0
        for match in TOKEN_RE.finditer(template):
            if match.start() > pos:
                pieces.append(sql.SQL(template[pos : match.start()]))
            token = match.group(1)
            if token == "col":
                pieces.append(sql.Identifier(col))
            elif token in values:
                pieces.append(sql.Placeholder())
                params.append(values[token])
            else:
                raise OperatorRegistryError(f"SQL template token không hỗ trợ: {token}")
            pos = match.end()
        if pos < len(template):
            pieces.append(sql.SQL(template[pos:]))
        if not pieces:
            return sql.SQL("")
        fragment = pieces[0]
        for piece in pieces[1:]:
            fragment += piece
        return fragment
