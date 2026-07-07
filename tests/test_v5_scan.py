import datetime as dt

import yaml

import runner


class ScanCursor:
    def __init__(self, tables, columns_by_table):
        self.tables = set(tables)
        self.columns_by_table = columns_by_table
        self.rows = []
        self.closed = False

    def execute(self, query, params=None):
        query_text = str(query)
        if "information_schema.columns" in query_text:
            table = params[1]
            self.rows = [(column,) for column in self.columns_by_table.get(table, [])]
            return
        if "LIKE" in query_text:
            pattern = params[1].replace("%", "")
            matches = sorted([table for table in self.tables if table.startswith(pattern)], reverse=True)
            self.rows = [(matches[0],)] if "LIMIT 1" in query_text and matches else [(table,) for table in matches]
            return
        table = params[1]
        self.rows = [(1,)] if table in self.tables else []

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


class ScanConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False

    def set_client_encoding(self, encoding):
        self.encoding = encoding

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


def write_column_yaml(path, data):
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def read_column_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_scan_columns_updates_export_columns_in_order(monkeypatch, tmp_path):
    path = tmp_path / "column.yaml"
    columns = [f"col_{i:02d}" for i in range(1, 33)]
    write_column_yaml(
        path,
        {
            "datasets": {
                "export": {
                    "database": "vn_export",
                    "schema": "vietnam_export",
                    "tables": "x_y{year}_{month}",
                    "columns": [],
                }
            },
            "operator_defaults": {},
        },
    )
    cursor = ScanCursor({"x_y2025_06"}, {"x_y2025_06": columns})
    monkeypatch.setattr(runner.portal, "connect", lambda cfg, dbname: ScanConn(cursor))

    runner.scan_columns(
        column_path=path,
        cfg={"_password": "secret"},
        today=dt.date(2026, 7, 7),
        yes=True,
    )

    data = read_column_yaml(path)
    assert data["datasets"]["export"]["columns"] == columns


def test_scan_columns_is_idempotent_and_preserves_operator_defaults(monkeypatch, tmp_path):
    path = tmp_path / "column.yaml"
    write_column_yaml(
        path,
        {
            "datasets": {
                "export": {
                    "database": "vn_export",
                    "schema": "vietnam_export",
                    "tables": "x_y2025_06",
                    "columns": ["old_col"],
                }
            },
            "operator_defaults": {"ma_so_hang_hoa": "prefix"},
        },
    )
    cursor = ScanCursor({"x_y2025_06"}, {"x_y2025_06": ["ma_so_hang_hoa", "mo_ta_hang_hoa"]})
    monkeypatch.setattr(runner.portal, "connect", lambda cfg, dbname: ScanConn(cursor))

    for _ in range(2):
        runner.scan_columns(column_path=path, cfg={"_password": "secret"}, yes=True)

    data = read_column_yaml(path)
    assert data["datasets"]["export"]["columns"] == ["ma_so_hang_hoa", "mo_ta_hang_hoa"]
    assert data["operator_defaults"] == {"ma_so_hang_hoa": "prefix"}


def test_scan_columns_creates_skeleton_when_column_yaml_missing(monkeypatch, tmp_path, capsys):
    path = tmp_path / "column.yaml"
    monkeypatch.setattr(runner, "COLUMN_FILE", path)

    assert runner.main(["--scan-columns"]) == 1

    output = capsys.readouterr().out
    assert "Chưa điền datasets" in output
    data = read_column_yaml(path)
    assert data == runner.COLUMN_SCAN_SKELETON


def test_scan_column_candidates_cover_current_year_and_previous_four_years():
    candidates = runner.candidate_tables_from_pattern(
        "x_y{year}_{month}",
        today=dt.date(2026, 7, 7),
    )

    assert len(candidates) == 60
    assert candidates[0] == "x_y2026_12"
    assert candidates[-1] == "x_y2022_01"
