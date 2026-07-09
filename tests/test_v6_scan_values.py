import yaml

import runner


def write_column_yaml(path, cfg):
    path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")


def read_column_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def column_cfg(columns, threshold=30, skip_columns=None):
    return {
        "datasets": {
            "export": {
                "database": "vn_export",
                "schema": "vietnam_export",
                "tables": "x_y2025_06",
                "columns": columns,
            }
        },
        "operator_defaults": {},
        "cardinality": {
            "threshold": threshold,
            "sample_size": 1000,
            "skip_text_length": 100,
            "skip_columns": skip_columns or [],
        },
    }


class ValueScanCursor:
    def __init__(self, *, tables, pg_stats=None, counts=None, values=None, avg_lengths=None):
        self.tables = set(tables)
        self.pg_stats = pg_stats or {}
        self.counts = counts or {}
        self.values = values or {}
        self.avg_lengths = avg_lengths or {}
        self.rows = []
        self.executed = []
        self.closed = False

    def _column_from_query(self, query_text):
        candidates = set(self.pg_stats) | set(self.counts) | set(self.values) | set(self.avg_lengths)
        for column in candidates:
            if column in query_text:
                return column
        return None

    def execute(self, query, params=None):
        query_text = str(query)
        self.executed.append((query_text, params))
        if "information_schema.tables" in query_text:
            table = params[1]
            self.rows = [(1,)] if table in self.tables else []
            return
        if "pg_stats" in query_text:
            column = params[2]
            value = self.pg_stats.get(column)
            self.rows = [(value,)] if value is not None else []
            return
        if "reltuples" in query_text:
            self.rows = [(1000,)]
            return
        if "AVG(char_length" in query_text:
            column = self._column_from_query(query_text)
            self.rows = [(self.avg_lengths.get(column, 10),)]
            return
        if "COUNT(DISTINCT" in query_text:
            column = self._column_from_query(query_text)
            self.rows = [(self.counts.get(column, 0),)]
            return
        if "SELECT DISTINCT" in query_text:
            column = self._column_from_query(query_text)
            self.rows = [(value,) for value in self.values.get(column, [])]
            return
        self.rows = []

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


class ValueScanConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False

    def set_client_encoding(self, encoding):
        self.encoding = encoding

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


def test_t38_pg_stats_low_cardinality_updates_count_and_values(monkeypatch, tmp_path):
    path = tmp_path / "column.yaml"
    write_column_yaml(path, column_cfg(["phuong_thuc_van_chuyen"]))
    cursor = ValueScanCursor(
        tables={"x_y2025_06"},
        pg_stats={"phuong_thuc_van_chuyen": 4},
        values={"phuong_thuc_van_chuyen": ["Air", "Ocean", "Rail", "Road"]},
    )
    monkeypatch.setattr(runner.portal, "connect", lambda cfg, dbname: ValueScanConn(cursor))

    runner.scan_values(column_path=path, cfg={"_password": "secret"}, yes=True)

    data = read_column_yaml(path)
    dataset = data["datasets"]["export"]
    assert dataset["cardinality_cache"]["phuong_thuc_van_chuyen"] == 4
    assert dataset["value_cache"]["phuong_thuc_van_chuyen"] == ["Air", "Ocean", "Rail", "Road"]
    assert any("pg_stats" in query for query, _params in cursor.executed)


def test_t39_skip_columns_are_not_scanned(monkeypatch, tmp_path):
    path = tmp_path / "column.yaml"
    write_column_yaml(path, column_cfg(["so_to_khai", "ma_loai_hinh"], skip_columns=["so_to_khai"]))
    cursor = ValueScanCursor(
        tables={"x_y2025_06"},
        pg_stats={"ma_loai_hinh": 2},
        values={"ma_loai_hinh": ["A11", "A12"]},
    )
    monkeypatch.setattr(runner.portal, "connect", lambda cfg, dbname: ValueScanConn(cursor))

    runner.scan_values(column_path=path, cfg={"_password": "secret"}, yes=True)

    data = read_column_yaml(path)
    dataset = data["datasets"]["export"]
    assert "so_to_khai" not in dataset["cardinality_cache"]
    assert "so_to_khai" not in dataset["value_cache"]
    assert all("so_to_khai" not in query for query, _params in cursor.executed)


def test_t40_long_text_column_skips_dropdown(monkeypatch, tmp_path):
    path = tmp_path / "column.yaml"
    write_column_yaml(path, column_cfg(["mo_ta_hang_hoa"]))
    cursor = ValueScanCursor(
        tables={"x_y2025_06"},
        pg_stats={"mo_ta_hang_hoa": 3},
        values={"mo_ta_hang_hoa": ["very long"]},
        avg_lengths={"mo_ta_hang_hoa": 150},
    )
    monkeypatch.setattr(runner.portal, "connect", lambda cfg, dbname: ValueScanConn(cursor))

    messages = runner.scan_values(column_path=path, cfg={"_password": "secret"}, yes=True)

    data = read_column_yaml(path)
    dataset = data["datasets"]["export"]
    assert dataset["cardinality_cache"] == {}
    assert dataset["value_cache"] == {}
    assert any("skip text long" in message for message in messages)


def test_t41_scan_values_refreshes_cache_idempotently(monkeypatch, tmp_path):
    path = tmp_path / "column.yaml"
    write_column_yaml(path, column_cfg(["ma_loai_hinh"], threshold=3))
    cursor = ValueScanCursor(
        tables={"x_y2025_06"},
        counts={"ma_loai_hinh": 2},
        values={"ma_loai_hinh": ["A11", "A12"]},
    )
    monkeypatch.setattr(runner.portal, "connect", lambda cfg, dbname: ValueScanConn(cursor))

    runner.scan_values(column_path=path, cfg={"_password": "secret"}, yes=True)
    cursor.counts["ma_loai_hinh"] = 4
    cursor.values["ma_loai_hinh"] = ["A11", "A12", "A21", "A31"]
    runner.scan_values(column_path=path, cfg={"_password": "secret"}, yes=True)

    data = read_column_yaml(path)
    dataset = data["datasets"]["export"]
    assert dataset["cardinality_cache"]["ma_loai_hinh"] == 4
    assert "ma_loai_hinh" not in dataset["value_cache"]
    assert any("COUNT(DISTINCT" in query for query, _params in cursor.executed)
