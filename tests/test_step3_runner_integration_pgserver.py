from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

pgserver = pytest.importorskip("pgserver")
psycopg2 = pytest.importorskip("psycopg2")

import runner


def write_request(path):
    wb = Workbook()
    ws = wb.active
    values = {
        "Người yêu cầu": "Ana",
        "Loại request": "MST",
        "Năm": "2025",
        "Tháng": "1",
        "Giá trị 1": "010",
        "Ghi chú / tên request": "integration",
    }
    for row, label in enumerate(runner.REQUEST_LABELS, 1):
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=values.get(label, ""))
    wb.save(path)
    return path


@pytest.fixture
def pg_uri(tmp_path):
    if not hasattr(pgserver, "get_server"):
        pytest.skip("pgserver.get_server API is unavailable")
    pg = pgserver.get_server(str(tmp_path / "pgdata"), cleanup_mode="stop")
    try:
        yield pg.get_uri()
    finally:
        pg.cleanup()


def test_runner_valid_request_end_to_end_pgserver(monkeypatch, tmp_path, pg_uri):
    conn = psycopg2.connect(pg_uri)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE public.x_y2025_01 (
                mst text,
                hs text,
                ma_dia_diem_dich text
            )
            """
        )
        cur.execute(
            "INSERT INTO public.x_y2025_01 VALUES (%s, %s, %s), (%s, %s, %s)",
            ("0101234567", "0101", "VNSGN", "0209999999", "0202", "CNSHA"),
        )
    conn.close()

    requests = tmp_path / "requests"
    requests.mkdir()
    write_request(requests / "request.xlsx")

    templates = {
        "mst": {
            "label": "MST",
            "type": "select",
            "database": "ignored_db",
            "schema": "public",
            "tables": "x_y{year}_{month}",
            "columns": "ALL",
            "merge": "union",
            "filters": [
                {"column": "mst", "type": "prefix", "label": "MST", "required": True},
            ],
            "split": None,
        }
    }
    settings = {
        "input_dir": str(requests),
        "output_dir": str(tmp_path / "out"),
        "filename_pattern": "{ts}_{user}_{request}",
        "max_rows_auto": 300000,
        "max_rows_hard": 3000000,
    }
    monkeypatch.setattr(runner.portal, "connect", lambda cfg, dbname: psycopg2.connect(pg_uri))

    processed = runner.run_once(settings=settings, templates=templates, cfg={"_password": ""}, stable_wait=0)

    assert processed == 1
    outputs = list((tmp_path / "out").glob("*.xlsx"))
    assert len(outputs) == 1
    wb = load_workbook(outputs[0], read_only=True)
    assert "data" in wb.sheetnames
    assert "NOTE" in wb.sheetnames
    rows = list(wb["data"].iter_rows(values_only=True))
    # merge: union → lõi portal thêm cột bang_nguon (nguồn = tên bảng tháng) ở đầu
    assert rows[0] == ("bang_nguon", "mst", "hs", "ma_dia_diem_dich")
    assert rows[1][0] == "x_y2025_01"
    assert rows[1][1] == "0101234567"
    assert (requests / "processed").exists()
