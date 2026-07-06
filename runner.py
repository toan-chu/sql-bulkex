#!/usr/bin/env python3
"""Headless SQL BulkEx request runner."""

import argparse
import csv
import datetime as dt
import os
import shutil
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

import psycopg2
from psycopg2 import sql
import yaml
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.datavalidation import DataValidation

import portal


BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "settings.yaml"
TEMPLATES_FILE = BASE_DIR / "templates.yaml"
REQUEST_TEMPLATE_FILE = BASE_DIR / "request_template.xlsx"
LOG_DIR = BASE_DIR / "log"
TMP_DIR = LOG_DIR / "tmp"
RUNNER_LOG_FILE = LOG_DIR / "runner.log"
XLSX_ROW_LIMIT = 1_000_000

REQUEST_LABELS = [
    "Người yêu cầu",
    "Loại request",
    "Năm",
    "Tháng",
    "Giá trị 1",
    "Giá trị 2",
    "Giá trị 3",
    "Cột cần lấy",
    "Tách file theo",
    "Xác nhận dữ liệu lớn",
    "Ghi chú / tên request",
]

KEY_BY_LABEL = {
    "Người yêu cầu": "user",
    "Loại request": "request_type",
    "Năm": "year",
    "Tháng": "month",
    "Giá trị 1": "value_1",
    "Giá trị 2": "value_2",
    "Giá trị 3": "value_3",
    "Cột cần lấy": "columns",
    "Tách file theo": "split",
    "Xác nhận dữ liệu lớn": "large_confirm",
    "Ghi chú / tên request": "request_name",
}

DEFAULT_SETTINGS = {
    "input_dir": str(BASE_DIR / "requests"),
    "output_dir": str(BASE_DIR / "exports"),
    "poll_seconds": 120,
    "filename_pattern": "{ts}_{user}_{request}",
    "max_rows_auto": 300000,
    "max_rows_hard": 3000000,
}


class RequestError(Exception):
    """A user-fixable request file problem."""


class RunnerConfigError(Exception):
    """A runner startup config problem."""


def configure_stdio():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def log_event(message):
    LOG_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(RUNNER_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {message}\n")


def load_yaml_file(path, default):
    path = Path(path)
    if not path.exists():
        return dict(default)
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if isinstance(default, dict):
        merged = dict(default)
        merged.update(data)
        return merged
    return data


def load_settings(path=SETTINGS_FILE):
    return load_yaml_file(path, DEFAULT_SETTINGS)


def load_templates(path=TEMPLATES_FILE):
    data = load_yaml_file(path, {})
    return data.get("templates", {}) if isinstance(data, dict) else {}


def validate_templates(templates):
    warnings = []
    required = {"label", "type", "database", "schema", "tables", "columns", "filters"}
    for name, template in templates.items():
        missing = sorted(required - set(template or {}))
        if missing:
            warnings.append(f"Template {name} thiếu trường: {', '.join(missing)}")
        if template.get("type", "select") not in TYPE_BUILDERS:
            warnings.append(f"Template {name} có type chưa hỗ trợ: {template.get('type')}")
    return warnings


def load_connection_config():
    cfg = portal.load_config()
    password = portal.config_or_file_password(cfg)
    if not password:
        raise RunnerConfigError(
            "Runner cần password trong connection.yaml hoặc file .password. "
            "Tạo file .password cạnh runner.py vì runner chạy headless/pythonw không thể hỏi getpass."
        )
    cfg["_password"] = password
    return cfg


def cell_text(value):
    if value is None:
        return ""
    return str(value).strip()


def parse_request_xlsx(path):
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb.active
        values = {}
        for row in ws.iter_rows(min_row=1, max_col=2, values_only=True):
            label = cell_text(row[0])
            if not label:
                continue
            key = KEY_BY_LABEL.get(label)
            if key:
                values[key] = cell_text(row[1])
        return values
    finally:
        wb.close()


def find_template(request_type, templates):
    wanted = cell_text(request_type)
    if not wanted:
        raise RequestError("Thiếu Loại request.")
    if wanted in templates:
        return wanted, templates[wanted]
    for name, template in templates.items():
        if cell_text(template.get("label")) == wanted:
            return name, template
    valid = ", ".join(sorted(templates)) or "(chưa có template)"
    raise RequestError(f"Template không tồn tại: {wanted}. Template hợp lệ: {valid}")


def parse_months(raw):
    text = cell_text(raw).lower()
    if text == "all":
        return [f"{i:02d}" for i in range(1, 13)]
    if not text:
        raise RequestError("Thiếu Tháng.")
    months = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = [p.strip() for p in part.split("-", 1)]
            if not start.isdigit() or not end.isdigit():
                raise RequestError(f"Tháng không hợp lệ: {part}")
            a, b = int(start), int(end)
            if a > b:
                raise RequestError(f"Khoảng tháng không hợp lệ: {part}")
            months.extend(range(a, b + 1))
        else:
            if not part.isdigit():
                raise RequestError(f"Tháng không hợp lệ: {part}")
            months.append(int(part))
    if not months:
        raise RequestError("Thiếu Tháng.")
    bad = [m for m in months if m < 1 or m > 12]
    if bad:
        raise RequestError(f"Tháng ngoài khoảng 1-12: {bad[0]}")
    return [f"{m:02d}" for m in months]


def table_exists(cur, schema, table):
    cur.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_name = %s
        LIMIT 1
        """,
        (schema, table),
    )
    return cur.fetchone() is not None


def glob_tables(cur, schema, pattern):
    like = pattern.replace("*", "%")
    cur.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_name LIKE %s
        ORDER BY table_name
        """,
        (schema, like),
    )
    return [r[0] for r in cur.fetchall()]


def expand_tables(cur, schema, pattern, request):
    pattern = cell_text(pattern)
    if "{year}" in pattern and not cell_text(request.get("year")):
        raise RequestError("Template cần Năm nhưng request chưa điền.")
    years = [cell_text(request.get("year"))] if "{year}" in pattern else [""]
    if "{month}" in pattern:
        months = parse_months(request.get("month"))
    else:
        months = [""]

    wanted = []
    if "{year}" in pattern or "{month}" in pattern:
        for year in years:
            for month in months:
                wanted.append(pattern.format(year=year, month=month))
    elif "*" in pattern:
        wanted = glob_tables(cur, schema, pattern)
        if not wanted:
            return [], [pattern]
    else:
        wanted = [pattern]

    existing, missing = [], []
    for table in wanted:
        if table_exists(cur, schema, table):
            existing.append(table)
        else:
            missing.append(table)
    return existing, missing


def column_names(cur, schema, table):
    return [name for name, _dtype in portal.get_columns(cur, schema, table)]


def common_columns(cur, schema, tables):
    per_table = [column_names(cur, schema, table) for table in tables]
    if not per_table:
        return []
    common = set(per_table[0])
    for cols in per_table[1:]:
        common &= set(cols)
    return [col for col in per_table[0] if col in common]


def split_values(raw):
    return [part.strip() for part in cell_text(raw).split(",") if part.strip()]


def resolve_columns(request, template, valid_columns):
    override = split_values(request.get("columns"))
    if override:
        chosen = override
    else:
        configured = template.get("columns", "ALL")
        chosen = list(valid_columns) if configured == "ALL" else list(configured or [])
    bad = [col for col in chosen if col not in valid_columns]
    if bad:
        valid = ", ".join(valid_columns)
        raise RequestError(f"Cột không hợp lệ: {', '.join(bad)}. Cột hợp lệ: {valid}")
    if not chosen:
        raise RequestError("Không có cột nào để export.")
    return chosen


def parse_filter_value(filter_def, raw_value):
    op = filter_def.get("type")
    raw = cell_text(raw_value)
    if not raw:
        if filter_def.get("required"):
            raise RequestError(f"Thiếu giá trị bắt buộc: {filter_def.get('label') or filter_def.get('column')}")
        return None
    if op in ("prefix", "in"):
        values = split_values(raw)
        if not values:
            return None
        return values
    if op == "between":
        parts = split_values(raw)
        if len(parts) != 2:
            raise RequestError(f"Giá trị between cần đúng 2 mốc: {filter_def.get('column')}")
        return tuple(parts)
    return raw


def build_filters_from_request(request, template):
    filters = []
    for index, filter_def in enumerate(template.get("filters") or [], 1):
        value = parse_filter_value(filter_def, request.get(f"value_{index}"))
        if value is None:
            continue
        filters.append((filter_def["column"], filter_def["type"], value))
    return filters


def parse_split_config(raw, template_split):
    text = cell_text(raw)
    if not text and template_split:
        return template_split.get("column"), template_split.get("chars")
    if not text:
        return None, None
    if ":" in text:
        col, chars = [p.strip() for p in text.split(":", 1)]
        if not chars.isdigit() or int(chars) < 1:
            raise RequestError("Tách file theo dạng <cột>:<N>, N phải là số dương.")
        return col, int(chars)
    return text, None


def note_rows(request, template_name, template, missing_tables, extra=None):
    rows = [
        ("Template", template_name),
        ("Loại request", template.get("label", template_name)),
        ("Người yêu cầu", request.get("user", "")),
        ("Ghi chú / tên request", request.get("request_name", "")),
        ("Năm", request.get("year", "")),
        ("Tháng", request.get("month", "")),
        ("Giá trị 1", request.get("value_1", "")),
        ("Giá trị 2", request.get("value_2", "")),
        ("Giá trị 3", request.get("value_3", "")),
    ]
    if missing_tables:
        rows.append(("Bảng thiếu", ", ".join(missing_tables)))
    for item in extra or []:
        rows.append(item)
    return rows


def build_select_jobs(request, template_name, template, cur):
    schema = template["schema"]
    tables, missing = expand_tables(cur, schema, template["tables"], request)
    if not tables:
        raise RequestError(f"Không có bảng nào tồn tại cho pattern: {template['tables']}")
    valid_columns = common_columns(cur, schema, tables)
    columns = resolve_columns(request, template, valid_columns)
    filters = build_filters_from_request(request, template)
    split_col, split_len = parse_split_config(request.get("split"), template.get("split"))
    if split_col and split_col not in valid_columns:
        valid = ", ".join(valid_columns)
        raise RequestError(f"Cột tách file không hợp lệ: {split_col}. Cột hợp lệ: {valid}")
    merge = template.get("merge", "union")
    state = {
        "db": template["database"],
        "schema": schema,
        "tables": tables,
        "cols": columns,
        "filters": filters,
        "split": split_col,
        "split_len": split_len,
        "sort": template.get("sort"),
        "merged": merge == "union",
    }
    jobs = portal.make_jobs(state, cur)
    notes = note_rows(request, template_name, template, missing)
    return jobs, notes, columns


TYPE_BUILDERS = {"select": build_select_jobs}


def build_jobs_from_request(request, templates, cur):
    template_name, template = find_template(request.get("request_type"), templates)
    request_type = template.get("type", "select")
    builder = TYPE_BUILDERS.get(request_type)
    if builder is None:
        raise RequestError(f"Loại template chưa hỗ trợ: {request_type}")
    if not cell_text(request.get("user")):
        raise RequestError("Thiếu Người yêu cầu.")
    if not cell_text(request.get("request_name")):
        raise RequestError("Thiếu Ghi chú / tên request.")
    return template["database"], builder(request, template_name, template, cur)


def estimate_mb(rows, columns):
    return rows * max(len(columns), 1) * 15 / (1024 * 1024)


def output_dir(settings):
    path = Path(settings.get("output_dir") or DEFAULT_SETTINGS["output_dir"])
    path.mkdir(parents=True, exist_ok=True)
    return path


def input_dir(settings):
    path = Path(settings.get("input_dir") or DEFAULT_SETTINGS["input_dir"])
    path.mkdir(parents=True, exist_ok=True)
    return path


def unique_path(path):
    path = Path(path)
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for i in range(2, 10000):
        candidate = path.with_name(f"{stem}_{i}{suffix}")
        if not candidate.exists():
            return candidate
    raise RequestError(f"Không tìm được tên file trống cho: {path.name}")


def output_path_for_job(settings, request, suffix, ext):
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M")
    pattern = settings.get("filename_pattern") or DEFAULT_SETTINGS["filename_pattern"]
    base = pattern.format(
        ts=ts,
        user=portal.safe_name(request.get("user", "")),
        request=portal.safe_name(request.get("request_name", "")),
    )
    if suffix:
        base = f"{base}_{portal.safe_name(suffix)}"
    return unique_path(output_dir(settings) / f"{base}{ext}")


def public_job_suffix(job_name, dbname, schema):
    prefix = portal.safe_name(f"{dbname}_{schema}_")
    public = job_name[len(prefix):] if job_name.startswith(prefix) else job_name
    if public.startswith("gop") and "bang_" in public:
        public = public.rsplit("_", 1)[-1]
    return public


def fetch_headers(conn, query, params):
    with conn.cursor() as cur:
        cur.execute(sql.SQL("SELECT * FROM (") + query + sql.SQL(") _h LIMIT 0"), params or None)
        return [d[0] for d in cur.description]


def export_xlsx_with_note(conn, query, params, headers, filepath, notes):
    wb = Workbook(write_only=True)
    ws = wb.create_sheet("data")
    ws.append(headers)
    count = 0
    with conn.cursor(name="bulkex_runner_stream") as cur:
        cur.itersize = 5000
        cur.execute(query, params or None)
        for row in cur:
            ws.append(list(row))
            count += 1
    note_ws = wb.create_sheet("NOTE")
    for row in notes:
        note_ws.append(list(row))
    wb.save(filepath)
    return count


def export_csv_with_note(conn, query, params, headers, filepath, notes):
    count = 0
    with conn.cursor(name="bulkex_runner_stream") as cur:
        cur.itersize = 5000
        cur.execute(query, params or None)
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in cur:
                writer.writerow(row)
                count += 1
    write_note_txt(Path(filepath).with_suffix(".txt"), notes)
    return count


def write_note_txt(path, notes):
    with open(path, "w", encoding="utf-8") as f:
        for key, value in notes:
            f.write(f"{key}: {value}\n")


def move_finished_file(src, dst):
    dst = unique_path(dst)
    shutil.move(str(src), str(dst))
    return dst


def move_request(path, folder_name):
    path = Path(path)
    target_dir = path.parent / folder_name
    target_dir.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return move_finished_file(path, target_dir / f"{stamp}_{path.name}")


def move_to_error(path, message):
    moved = move_request(path, "error")
    txt = moved.with_suffix(".txt")
    with open(txt, "w", encoding="utf-8") as f:
        f.write(message.strip() + "\n")
    return moved


def process_request_file(path, cfg, conns, settings, templates):
    request = parse_request_xlsx(path)
    template_name, template = find_template(request.get("request_type"), templates)
    conn = portal.get_conn(conns, cfg, template["database"])
    cur = conn.cursor()
    try:
        _dbname, (jobs, base_notes, columns) = build_jobs_from_request(request, templates, cur)
        rows_by_job = []
        for job in jobs:
            rows = portal.count_rows(cur, job[2], job[3])
            rows_by_job.append(rows)
        conn.rollback()
    finally:
        cur.close()

    max_auto = int(settings.get("max_rows_auto", DEFAULT_SETTINGS["max_rows_auto"]))
    max_hard = int(settings.get("max_rows_hard", DEFAULT_SETTINGS["max_rows_hard"]))
    confirmed = cell_text(request.get("large_confirm")).upper() == "YES"
    for rows in rows_by_job:
        mb = estimate_mb(rows, columns)
        if rows > max_hard:
            raise RequestError(
                f"Query ra {rows:,} dòng (ước ~{mb:.1f} MB), vượt ngưỡng cứng. "
                "Vui lòng lọc hẹp hơn hoặc tách request."
            )
        if rows > max_auto and not confirmed:
            raise RequestError(
                f"Query ra {rows:,} dòng (ước ~{mb:.1f} MB). Nếu chắc chắn, "
                "điền ô 'Xác nhận dữ liệu lớn' = YES rồi gửi lại."
            )

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    for index, job in enumerate(jobs):
        name, _dbname, query, params = job
        rows = rows_by_job[index]
        force_csv = rows > XLSX_ROW_LIMIT
        ext = ".csv" if force_csv else ".xlsx"
        suffix = public_job_suffix(name, template["database"], template["schema"]) if len(jobs) > 1 else ""
        final_path = output_path_for_job(settings, request, suffix, ext)
        tmp_path = unique_path(TMP_DIR / final_path.name)
        notes = list(base_notes)
        notes.append(("Số dòng", rows))
        if rows == 0:
            notes.append(("Gợi ý", "0 dòng: kiểm tra giá trị lọc, đặc biệt MST 10/13 số hoặc dùng bắt đầu bằng."))
        if force_csv:
            notes.append(("Định dạng", "Tự chuyển CSV vì kết quả vượt giới hạn 1,000,000 dòng của Excel."))
        headers = fetch_headers(conn, query, params)
        if force_csv:
            exported = export_csv_with_note(conn, query, params, headers, tmp_path, notes)
            txt_src = tmp_path.with_suffix(".txt")
        else:
            exported = export_xlsx_with_note(conn, query, params, headers, tmp_path, notes)
            txt_src = None
        conn.rollback()
        final = move_finished_file(tmp_path, final_path)
        if txt_src and txt_src.exists():
            move_finished_file(txt_src, final.with_suffix(".txt"))
        log_event(f"Exported {final.name}: {exported} rows")

    moved = move_request(path, "processed")
    log_event(f"Processed request {path.name} -> {moved}")
    return moved


def is_file_stable(path, wait_seconds=5):
    first = Path(path).stat().st_size
    if wait_seconds:
        time.sleep(wait_seconds)
    second = Path(path).stat().st_size
    return first == second


def request_files(settings, stable_wait=5):
    root = input_dir(settings)
    for path in sorted(root.glob("*.xlsx")):
        if path.name.startswith("~$"):
            continue
        if not is_file_stable(path, stable_wait):
            log_event(f"Skip unstable file: {path.name}")
            continue
        yield path


def run_once(settings=None, templates=None, cfg=None, stable_wait=5):
    settings = load_settings() if settings is None else settings
    templates = load_templates() if templates is None else templates
    for warning in validate_templates(templates):
        log_event(f"WARNING: {warning}")
    cfg = load_connection_config() if cfg is None else cfg
    conns = {}
    processed = 0
    try:
        for path in request_files(settings, stable_wait=stable_wait):
            try:
                process_request_file(path, cfg, conns, settings, templates)
                processed += 1
            except psycopg2.OperationalError as e:
                log_event(f"DB down, giữ request {path.name}: {e}")
            except RequestError as e:
                moved = move_to_error(path, str(e))
                log_event(f"Request lỗi {path.name} -> {moved}: {e}")
            except Exception as e:
                moved = move_to_error(path, f"Lỗi xử lý request: {e}")
                log_event(f"Unexpected error {path.name} -> {moved}: {e}")
    finally:
        for conn in conns.values():
            try:
                conn.close()
            except Exception:
                pass
    return processed


def make_request_template(templates, output_path=REQUEST_TEMPLATE_FILE):
    wb = Workbook()
    ws = wb.active
    ws.title = "Request"
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 48
    for row, label in enumerate(REQUEST_LABELS, 1):
        ws.cell(row=row, column=1, value=label)
    list_ws = wb.create_sheet("templates")
    labels = []
    for name, template in sorted(templates.items()):
        labels.append(template.get("label") or name)
    if not labels:
        labels = ["(chưa có template)"]
    for row, label in enumerate(labels, 1):
        list_ws.cell(row=row, column=1, value=label)
    list_ws.sheet_state = "hidden"
    dv = DataValidation(type="list", formula1=f"=templates!$A$1:$A${len(labels)}", allow_blank=False)
    ws.add_data_validation(dv)
    dv.add(ws["B2"])
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return Path(output_path)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="SQL BulkEx request runner")
    parser.add_argument("--once", action="store_true", help="Chạy một vòng quét request rồi thoát")
    parser.add_argument("--make-template", action="store_true", help="Sinh request_template.xlsx từ templates.yaml")
    return parser.parse_args(argv)


def main(argv=None):
    configure_stdio()
    args = parse_args(argv)
    settings = load_settings()
    templates = load_templates()
    for warning in validate_templates(templates):
        log_event(f"WARNING: {warning}")

    if args.make_template:
        path = make_request_template(templates)
        print(f"Đã sinh file mẫu: {path}")
        return 0

    try:
        cfg = load_connection_config()
    except RunnerConfigError as e:
        log_event(str(e))
        print(str(e))
        return 1
    if args.once:
        return 0 if run_once(settings=settings, templates=templates, cfg=cfg) >= 0 else 1

    while True:
        run_once(settings=settings, templates=templates, cfg=cfg)
        time.sleep(int(settings.get("poll_seconds", DEFAULT_SETTINGS["poll_seconds"])))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nĐã thoát.")
        sys.exit(0)
