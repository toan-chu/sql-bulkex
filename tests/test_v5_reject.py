from pathlib import Path

from openpyxl import Workbook

import runner


def write_xlsx(path):
    wb = Workbook()
    wb.active["A1"] = "request"
    wb.save(path)
    return path


def test_t18_reject_renames_in_place_with_companion_txt(tmp_path):
    request = write_xlsx(tmp_path / "request_hoa_20260707.xlsx")

    moved = runner.move_to_error(request, "Cột ma_so_hang_hoa: toán tử between cần 2 giá trị.")

    assert moved == tmp_path / "[LOI]_request_hoa_20260707.xlsx"
    assert moved.exists()
    assert not request.exists()
    txt = tmp_path / "[LOI]_request_hoa_20260707.txt"
    content = txt.read_text(encoding="utf-8")
    assert "File: request_hoa_20260707.xlsx" in content
    assert "LỖI:" in content
    assert "toán tử between" in content
    assert "Đổi tên bỏ tiền tố [LOI]_" in content


def test_t19_request_scan_skips_rejected_files(monkeypatch, tmp_path):
    inbox = tmp_path / "requests"
    inbox.mkdir()
    write_xlsx(inbox / "[LOI]_bad.xlsx")
    good = write_xlsx(inbox / "good.xlsx")
    seen = []

    monkeypatch.setattr(runner, "is_file_stable", lambda path, stable_wait: seen.append(Path(path).name) or True)

    files = list(runner.request_files({"input_dir": str(inbox)}, stable_wait=0))

    assert files == [good]
    assert seen == ["good.xlsx"]
