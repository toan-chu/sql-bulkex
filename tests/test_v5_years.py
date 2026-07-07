import pytest

import runner


def test_t19b_parse_years_accepts_comma_list():
    assert runner.parse_years("2025,2026") == [2025, 2026]


def test_t19c_parse_years_accepts_range():
    assert runner.parse_years("2025-2026") == [2025, 2026]


def test_t19d_expand_tables_uses_year_month_cross_product():
    class Cursor:
        def __init__(self):
            self.rows = []

        def execute(self, query, params=None):
            self.rows = [(1,)]

        def fetchone(self):
            return self.rows[0] if self.rows else None

    existing, missing = runner.expand_tables(
        Cursor(),
        "public",
        "x_y{year}_{month}",
        {"year": "2025,2026", "month": "01-03"},
    )

    assert existing == [
        "x_y2025_01",
        "x_y2025_02",
        "x_y2025_03",
        "x_y2026_01",
        "x_y2026_02",
        "x_y2026_03",
    ]
    assert missing == []


def test_t19e_parse_years_rejects_all():
    with pytest.raises(runner.RequestError, match="Không hỗ trợ all"):
        runner.parse_years("all")
