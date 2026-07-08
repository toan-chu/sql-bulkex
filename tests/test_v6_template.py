from openpyxl import load_workbook

import runner


EXPORT_COLUMNS = ["ma_nuoc", "ma_so_hang_hoa", "mo_ta_hang_hoa"]
IMPORT_COLUMNS = ["ma_nuoc", "ma_nguoi_nhap_khau"]
VN_OPERATOR_LABELS = ["Bằng", "Trong danh sách", "Trong khoảng", "Bắt đầu bằng", "Chứa", "Kết thúc bằng"]


def column_cfg():
    return {
        "datasets": {
            "export": {
                "database": "vn_export",
                "schema": "vietnam_export",
                "tables": "x_y{year}_{month}",
                "columns": EXPORT_COLUMNS,
                "cardinality_cache": {"ma_nuoc": 4},
                "value_cache": {"ma_nuoc": ["CN", "VN", "KR", "JP"]},
            },
            "import": {
                "database": "vn_import",
                "schema": "vietnam_import",
                "tables": "i_y{year}_{month}",
                "columns": IMPORT_COLUMNS,
                "cardinality_cache": {},
                "value_cache": {},
            },
        },
        "operator_defaults": {},
        "cardinality": {
            "threshold": 30,
            "sample_size": 1000,
            "skip_text_length": 100,
            "skip_columns": [],
        },
    }


def build_template(tmp_path):
    output = tmp_path / "request_template.xlsx"
    runner.make_request_template_v5(column_cfg(), output)
    return load_workbook(output)


def validation_for_cell(ws, cell_ref, validation_type=None):
    for dv in ws.data_validations.dataValidation:
        if cell_ref in dv.cells and (validation_type is None or dv.type == validation_type):
            return dv
    return None


def defined_name_text(wb, name):
    defined = wb.defined_names.get(name)
    if isinstance(defined, list):
        defined = defined[0]
    return defined.attr_text if defined is not None else None


def conditional_rules(ws, cell_range):
    for item in ws.conditional_formatting:
        if cell_range in str(item):
            return ws.conditional_formatting[item]
    return []


def test_t42_make_template_has_five_v6_sheets_with_hidden_values(tmp_path):
    wb = build_template(tmp_path)

    assert wb.sheetnames == ["Request", "Cột Export", "Cột Import", "Values", "Tham chiếu"]
    assert wb["Values"].sheet_state == "hidden"
    assert wb["Request"]["A8"].value == "Người duyệt (Admin điền sau approve)"


def test_t43_column_export_has_digits_header(tmp_path):
    wb = build_template(tmp_path)
    ws = wb["Cột Export"]

    assert [ws.cell(row=1, column=col).value for col in range(1, 6)] == [
        "Cột",
        "Toán tử",
        "Giá trị",
        "Digits",
        "Lấy về?",
    ]
    assert ws.column_dimensions["B"].width == 22
    assert ws.column_dimensions["D"].width == 10


def test_t44_operator_dropdown_uses_vn_registry_labels(tmp_path):
    wb = build_template(tmp_path)
    ws = wb["Cột Export"]
    dv = validation_for_cell(ws, "B2", "list")

    assert dv is not None
    assert dv.allow_blank
    assert all(label in dv.formula1 for label in VN_OPERATOR_LABELS)
    assert "eq" not in dv.formula1


def test_t45_digits_column_has_gray_out_conditional_formatting(tmp_path):
    wb = build_template(tmp_path)
    ws = wb["Cột Export"]
    rules = conditional_rules(ws, "D2:D4")

    assert any(
        rule.type == "expression"
        and 'Bắt đầu bằng' in "".join(rule.formula)
        and 'Kết thúc bằng' in "".join(rule.formula)
        and 'Chứa' not in "".join(rule.formula)
        and rule.dxf.fill.fgColor.rgb == "00E7E6E6"
        and rule.dxf.font.color.rgb == "00A6A6A6"
        for rule in rules
    )


def test_t46_values_sheet_hidden_and_named_range_for_low_cardinality_column(tmp_path):
    wb = build_template(tmp_path)
    ws = wb["Values"]

    assert ws.sheet_state == "hidden"
    assert ws["A1"].value == "ma_nuoc"
    assert [ws.cell(row=row, column=1).value for row in range(2, 6)] == ["CN", "VN", "KR", "JP"]
    assert defined_name_text(wb, "ma_nuoc_values") == "Values!$A$2:$A$5"


def test_t47_value_cell_for_cached_column_references_named_range(tmp_path):
    wb = build_template(tmp_path)
    ws = wb["Cột Export"]
    dv = validation_for_cell(ws, "C2", "list")

    assert dv is not None
    assert dv.formula1 == "=ma_nuoc_values"
