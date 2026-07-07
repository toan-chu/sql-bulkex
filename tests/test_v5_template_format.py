from openpyxl import load_workbook
import yaml

import runner


def build_template(tmp_path):
    cfg = {
        "datasets": {
            "export": {
                "database": "vn_export",
                "schema": "vietnam_export",
                "tables": "x_y{year}_{month}",
                "columns": ["export_col"],
            },
            "import": {
                "database": "vn_import",
                "schema": "vietnam_import",
                "tables": "i_y{year}_{month}",
                "columns": ["import_col"],
            },
        },
        "operator_defaults": {},
    }
    output = tmp_path / "request_template.xlsx"
    runner.make_request_template_v5(cfg, output)
    return load_workbook(output)


def test_value_cells_are_text_formatted(tmp_path):
    wb = build_template(tmp_path)

    assert wb["Request"]["B3"].number_format == "@"
    assert wb["Cột Export"]["C2"].number_format == "@"
    assert wb["Cột Import"]["C2"].number_format == "@"


def test_make_template_cli_does_not_fallback_to_v4_for_empty_column_yaml(monkeypatch, tmp_path):
    column_path = tmp_path / "column.yaml"
    output_path = tmp_path / "request_template.xlsx"
    column_path.write_text(yaml.safe_dump({"datasets": {}, "operator_defaults": {}}), encoding="utf-8")
    monkeypatch.setattr(runner, "COLUMN_FILE", column_path)
    monkeypatch.setattr(runner, "REQUEST_TEMPLATE_FILE", output_path)
    monkeypatch.setattr(runner, "LOG_DIR", tmp_path)
    monkeypatch.setattr(runner, "RUNNER_LOG_FILE", tmp_path / "runner.log")

    assert runner.main(["--make-template"]) == 1
    assert not output_path.exists()
