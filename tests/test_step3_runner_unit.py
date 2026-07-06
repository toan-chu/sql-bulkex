from pathlib import Path

import psycopg2
import pytest
from openpyxl import Workbook, load_workbook

import runner


def write_request(path, **values):
    wb = Workbook()
    ws = wb.active
    defaults = {
        "Người yêu cầu": "Ana",
        "Loại request": "MST",
        "Năm": "2025",
        "Tháng": "1",
        "Giá trị 1": "010",
        "Giá trị 2": "",
        "Giá trị 3": "",
        "Cột cần lấy": "",
        "Tách file theo": "",
        "Xác nhận dữ liệu lớn": "",
        "Ghi chú / tên request": "daily",
    }
    defaults.update(values)
    for row, label in enumerate(runner.REQUEST_LABELS, 1):
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=defaults.get(label, ""))
    wb.save(path)
    return path


def template():
    return {
        "label": "MST",
        "type": "select",
        "database": "db/name",
        "schema": "public",
        "tables": "x_y{year}_{month}",
        "columns": "ALL",
        "merge": "union",
        "filters": [
            {"column": "mst", "type": "prefix", "label": "MST", "required": True},
        ],
        "split": None,
    }


def test_parse_months_all_list_and_range():
    assert runner.parse_months("all") == [f"{i:02d}" for i in range(1, 13)]
    assert runner.parse_months("1,3,5") == ["01", "03", "05"]
    assert runner.parse_months("2-4") == ["02", "03", "04"]


def test_parse_request_xlsx_key_value_layout(tmp_path):
    path = write_request(tmp_path / "request.xlsx", **{"Tháng": "1,3"})

    request = runner.parse_request_xlsx(path)

    assert request["user"] == "Ana"
    assert request["request_type"] == "MST"
    assert request["month"] == "1,3"


def test_template_missing_and_required_value_errors():
    with pytest.raises(runner.RequestError, match="Template không tồn tại"):
        runner.find_template("unknown", {"mst": template()})

    missing = template()
    with pytest.raises(runner.RequestError, match="Thiếu giá trị bắt buộc"):
        runner.build_filters_from_request({"value_1": ""}, missing)


def test_bad_column_and_split_override_errors_include_valid_columns():
    request = {"columns": "missing_col", "split": ""}

    with pytest.raises(runner.RequestError, match="Cột hợp lệ: mst, hs"):
        runner.resolve_columns(request, template(), ["mst", "hs"])

    assert runner.parse_split_config("mst:2", None) == ("mst", 2)
    with pytest.raises(runner.RequestError, match="N phải là số dương"):
        runner.parse_split_config("mst:x", None)


class TableCursor:
    def __init__(self, existing):
        self.existing = set(existing)
        self.rows = []

    def execute(self, query, params=None):
        if "LIKE" in query:
            pattern = params[1].replace("%", "")
            self.rows = [(t,) for t in sorted(self.existing) if t.startswith(pattern)]
        else:
            table = params[1]
            self.rows = [(1,)] if table in self.existing else []

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


def test_expand_tables_records_missing_tables():
    cur = TableCursor({"x_y2025_01", "x_y2025_03"})

    existing, missing = runner.expand_tables(
        cur,
        "public",
        "x_y{year}_{month}",
        {"year": "2025", "month": "1,3,5"},
    )

    assert existing == ["x_y2025_01", "x_y2025_03"]
    assert missing == ["x_y2025_05"]


def test_make_request_template_has_template_dropdown(tmp_path):
    output = runner.make_request_template({"mst": template()}, tmp_path / "request_template.xlsx")

    wb = load_workbook(output)
    ws = wb["Request"]

    assert ws["A1"].value == "Người yêu cầu"
    assert ws["A2"].value == "Loại request"
    assert list(ws.data_validations.dataValidation)


class FakeConn:
    closed = False

    def __init__(self):
        self.closed_count = 0

    def cursor(self):
        class Cur:
            def close(self):
                pass

        return Cur()

    def rollback(self):
        pass

    def close(self):
        self.closed_count += 1


def patch_process_boundaries(monkeypatch, rows, export_kind="xlsx"):
    captured = {"notes": []}

    monkeypatch.setattr(runner.portal, "get_conn", lambda conns, cfg, dbname: FakeConn())
    monkeypatch.setattr(
        runner,
        "build_jobs_from_request",
        lambda request, templates, cur: (
            "db/name",
            ([("job_suffix", "db/name", "SQL", [])], [("Template", "mst")], ["mst", "hs"]),
        ),
    )
    monkeypatch.setattr(runner.portal, "count_rows", lambda cur, query, params: rows)
    monkeypatch.setattr(runner, "fetch_headers", lambda conn, query, params: ["mst", "hs"])

    def fake_xlsx(conn, query, params, headers, filepath, notes):
        captured["notes"].append(notes)
        Path(filepath).write_text("xlsx", encoding="utf-8")
        return rows

    def fake_csv(conn, query, params, headers, filepath, notes):
        captured["notes"].append(notes)
        Path(filepath).write_text("csv", encoding="utf-8")
        runner.write_note_txt(Path(filepath).with_suffix(".txt"), notes)
        return rows

    monkeypatch.setattr(runner, "export_xlsx_with_note", fake_xlsx)
    monkeypatch.setattr(runner, "export_csv_with_note", fake_csv)
    return captured


def test_process_request_rejects_auto_threshold_without_yes(monkeypatch, tmp_path):
    request_path = write_request(tmp_path / "request.xlsx")
    captured = patch_process_boundaries(monkeypatch, rows=301)

    settings = {
        "output_dir": str(tmp_path / "out"),
        "max_rows_auto": 300,
        "max_rows_hard": 1000,
        "filename_pattern": "{ts}_{user}_{request}",
    }

    with pytest.raises(runner.RequestError, match="Xác nhận dữ liệu lớn"):
        runner.process_request_file(request_path, {}, {}, settings, {"mst": template()})

    assert captured["notes"] == []


def test_process_request_yes_runs_and_moves_processed(monkeypatch, tmp_path):
    request_path = write_request(tmp_path / "request.xlsx", **{"Xác nhận dữ liệu lớn": "YES"})
    patch_process_boundaries(monkeypatch, rows=301)
    settings = {
        "output_dir": str(tmp_path / "out"),
        "max_rows_auto": 300,
        "max_rows_hard": 1000,
        "filename_pattern": "{ts}_{user}_{request}",
    }

    moved = runner.process_request_file(request_path, {}, {}, settings, {"mst": template()})

    assert moved.parent.name == "processed"
    assert list((tmp_path / "out").glob("*.xlsx"))


def test_process_request_rejects_hard_cap(monkeypatch, tmp_path):
    request_path = write_request(tmp_path / "request.xlsx", **{"Xác nhận dữ liệu lớn": "YES"})
    patch_process_boundaries(monkeypatch, rows=1001)
    settings = {
        "output_dir": str(tmp_path / "out"),
        "max_rows_auto": 300,
        "max_rows_hard": 1000,
        "filename_pattern": "{ts}_{user}_{request}",
    }

    with pytest.raises(runner.RequestError, match="vượt ngưỡng cứng"):
        runner.process_request_file(request_path, {}, {}, settings, {"mst": template()})


def test_process_request_zero_rows_adds_note_hint(monkeypatch, tmp_path):
    request_path = write_request(tmp_path / "request.xlsx")
    captured = patch_process_boundaries(monkeypatch, rows=0)
    settings = {
        "output_dir": str(tmp_path / "out"),
        "max_rows_auto": 300,
        "max_rows_hard": 1000,
        "filename_pattern": "{ts}_{user}_{request}",
    }

    runner.process_request_file(request_path, {}, {}, settings, {"mst": template()})

    flattened = [item for notes in captured["notes"] for item in notes]
    assert ("Gợi ý", "0 dòng: kiểm tra giá trị lọc, đặc biệt MST 10/13 số hoặc dùng bắt đầu bằng.") in flattened


def test_process_request_over_excel_limit_switches_to_csv(monkeypatch, tmp_path):
    request_path = write_request(tmp_path / "request.xlsx", **{"Xác nhận dữ liệu lớn": "YES"})
    patch_process_boundaries(monkeypatch, rows=runner.XLSX_ROW_LIMIT + 1)
    settings = {
        "output_dir": str(tmp_path / "out"),
        "max_rows_auto": 300,
        "max_rows_hard": runner.XLSX_ROW_LIMIT + 10,
        "filename_pattern": "{ts}_{user}_{request}",
    }

    runner.process_request_file(request_path, {}, {}, settings, {"mst": template()})

    assert list((tmp_path / "out").glob("*.csv"))
    assert list((tmp_path / "out").glob("*.txt"))


def test_public_job_suffix_does_not_expose_db_schema():
    assert runner.public_job_suffix("db_name_public_gop2bang_KG", "db/name", "public") == "KG"
    assert runner.public_job_suffix("db_name_public_x_y2025_01", "db/name", "public") == "x_y2025_01"


def test_split_output_filename_uses_public_suffix(monkeypatch, tmp_path):
    request_path = write_request(tmp_path / "request.xlsx", **{"Xác nhận dữ liệu lớn": "YES"})
    captured = {"paths": []}

    monkeypatch.setattr(runner.portal, "get_conn", lambda conns, cfg, dbname: FakeConn())
    monkeypatch.setattr(
        runner,
        "build_jobs_from_request",
        lambda request, templates, cur: (
            "db/name",
            (
                [
                    ("db_name_public_gop2bang_KG", "db/name", "SQL1", []),
                    ("db_name_public_gop2bang_VN", "db/name", "SQL2", []),
                ],
                [("Template", "mst")],
                ["mst"],
            ),
        ),
    )
    monkeypatch.setattr(runner.portal, "count_rows", lambda cur, query, params: 1)
    monkeypatch.setattr(runner, "fetch_headers", lambda conn, query, params: ["mst"])

    def fake_xlsx(conn, query, params, headers, filepath, notes):
        captured["paths"].append(Path(filepath).name)
        Path(filepath).write_text("xlsx", encoding="utf-8")
        return 1

    monkeypatch.setattr(runner, "export_xlsx_with_note", fake_xlsx)
    settings = {
        "output_dir": str(tmp_path / "out"),
        "max_rows_auto": 300,
        "max_rows_hard": 1000,
        "filename_pattern": "{ts}_{user}_{request}",
    }

    runner.process_request_file(request_path, {}, {}, settings, {"mst": template()})

    output_names = sorted(p.name for p in (tmp_path / "out").glob("*.xlsx"))
    assert all("db_name" not in name and "public" not in name and "gop2bang" not in name for name in output_names)
    assert any(name.endswith("_KG.xlsx") for name in output_names)
    assert any(name.endswith("_VN.xlsx") for name in output_names)


def test_runner_headless_missing_password_fails_fast_without_getpass(monkeypatch, tmp_path):
    log_path = tmp_path / "runner.log"
    monkeypatch.setattr(runner, "LOG_DIR", tmp_path)
    monkeypatch.setattr(runner, "RUNNER_LOG_FILE", log_path)
    monkeypatch.setattr(runner, "load_settings", lambda: {"input_dir": str(tmp_path / "requests")})
    monkeypatch.setattr(runner, "load_templates", lambda: {})
    monkeypatch.setattr(runner.portal, "load_config", lambda: {"user": "postgres"})
    monkeypatch.setattr(runner.portal, "PASSWORD_FILE", str(tmp_path / ".password"))

    def fail_getpass(prompt):
        raise AssertionError("runner must not call getpass in headless mode")

    monkeypatch.setattr(runner.portal.getpass, "getpass", fail_getpass)

    assert runner.main(["--once"]) == 1
    assert "connection.yaml hoặc file .password" in log_path.read_text(encoding="utf-8")


def test_runner_headless_reads_password_file(monkeypatch, tmp_path):
    password_file = tmp_path / ".password"
    password_file.write_text("file-secret\n", encoding="utf-8")

    monkeypatch.setattr(runner.portal, "load_config", lambda: {"user": "postgres", "password": ""})
    monkeypatch.setattr(runner.portal, "PASSWORD_FILE", str(password_file))

    cfg = runner.load_connection_config()

    assert cfg["_password"] == "file-secret"


def test_run_once_skips_temp_and_unstable_files(monkeypatch, tmp_path):
    requests = tmp_path / "requests"
    requests.mkdir()
    write_request(requests / "~$lock.xlsx")
    stable = write_request(requests / "stable.xlsx")
    unstable = write_request(requests / "unstable.xlsx")
    seen = []

    monkeypatch.setattr(runner, "is_file_stable", lambda path, stable_wait: Path(path) != unstable)
    monkeypatch.setattr(runner, "process_request_file", lambda path, cfg, conns, settings, templates: seen.append(Path(path).name))

    runner.run_once(
        settings={"input_dir": str(requests), "output_dir": str(tmp_path / "out")},
        templates={"mst": template()},
        cfg={},
        stable_wait=0,
    )

    assert seen == [stable.name]


def test_run_once_db_down_keeps_request_file(monkeypatch, tmp_path):
    requests = tmp_path / "requests"
    requests.mkdir()
    request = write_request(requests / "request.xlsx")

    def db_down(path, cfg, conns, settings, templates):
        raise psycopg2.OperationalError("db down")

    monkeypatch.setattr(runner, "process_request_file", db_down)

    runner.run_once(
        settings={"input_dir": str(requests), "output_dir": str(tmp_path / "out")},
        templates={"mst": template()},
        cfg={},
        stable_wait=0,
    )

    assert request.exists()
    assert not (requests / "error").exists()


def test_run_once_moves_validation_error_to_error_txt(monkeypatch, tmp_path):
    requests = tmp_path / "requests"
    requests.mkdir()
    request = write_request(requests / "request.xlsx")

    def invalid(path, cfg, conns, settings, templates):
        raise runner.RequestError("lỗi dễ hiểu")

    monkeypatch.setattr(runner, "process_request_file", invalid)

    runner.run_once(
        settings={"input_dir": str(requests), "output_dir": str(tmp_path / "out")},
        templates={"mst": template()},
        cfg={},
        stable_wait=0,
    )

    assert not request.exists()
    txt_files = list((requests / "error").glob("*.txt"))
    assert txt_files
    assert "lỗi dễ hiểu" in txt_files[0].read_text(encoding="utf-8")


def test_run_once_twice_does_not_process_processed_file(monkeypatch, tmp_path):
    requests = tmp_path / "requests"
    requests.mkdir()
    request = write_request(requests / "request.xlsx")
    seen = []

    def process(path, cfg, conns, settings, templates):
        seen.append(Path(path).name)
        return runner.move_request(path, "processed")

    monkeypatch.setattr(runner, "process_request_file", process)
    settings = {"input_dir": str(requests), "output_dir": str(tmp_path / "out")}

    runner.run_once(settings=settings, templates={"mst": template()}, cfg={}, stable_wait=0)
    runner.run_once(settings=settings, templates={"mst": template()}, cfg={}, stable_wait=0)

    assert seen == [request.name]
