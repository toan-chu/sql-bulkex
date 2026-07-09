from pathlib import Path

from openpyxl import Workbook

import runner


def write_xlsx(path):
    wb = Workbook()
    wb.active["A1"] = "request"
    wb.save(path)
    return path


def folder_settings(tmp_path):
    pending = tmp_path / "01_Pending"
    approved = tmp_path / "02_Approved"
    output = tmp_path / "03_Output"
    pending.mkdir()
    approved.mkdir()
    output.mkdir()
    return {
        "folders": {
            "pending": str(pending),
            "approved": str(approved),
            "output": str(output),
        },
        "filename_pattern": "{ts}_{user}_{request}",
        "max_rows_auto": 300000,
        "max_rows_hard": 3000000,
    }


def test_t55_pending_folder_is_ignored(monkeypatch, tmp_path):
    settings = folder_settings(tmp_path)
    pending_file = write_xlsx(Path(settings["folders"]["pending"]) / "request_x.xlsx")
    seen = []

    monkeypatch.setattr(runner, "process_request_file", lambda path, cfg, conns, settings: seen.append(path))

    processed = runner.run_once(settings=settings, cfg={}, stable_wait=0)

    assert processed == 0
    assert seen == []
    assert pending_file.exists()


def test_t56_approved_file_processes_to_output_and_done(monkeypatch, tmp_path):
    settings = folder_settings(tmp_path)
    approved = Path(settings["folders"]["approved"])
    output = Path(settings["folders"]["output"])
    request = write_xlsx(approved / "request_x.xlsx")

    def fake_process(path, cfg, conns, settings):
        (output / "result.xlsx").write_text("ok", encoding="utf-8")
        return runner.mark_done(path)

    monkeypatch.setattr(runner, "process_request_file", fake_process)

    processed = runner.run_once(settings=settings, cfg={}, stable_wait=0)

    assert processed == 1
    assert not request.exists()
    assert (approved / "[DONE] request_x.xlsx").exists()
    assert (output / "result.xlsx").exists()


def test_t57_done_files_are_skipped(monkeypatch, tmp_path):
    settings = folder_settings(tmp_path)
    approved = Path(settings["folders"]["approved"])
    done_file = write_xlsx(approved / "[DONE] old_request.xlsx")
    seen = []

    monkeypatch.setattr(runner, "process_request_file", lambda path, cfg, conns, settings: seen.append(path))

    processed = runner.run_once(settings=settings, cfg={}, stable_wait=0)

    assert processed == 0
    assert seen == []
    assert done_file.exists()


def test_t58_reject_stays_in_approved_with_companion_txt(monkeypatch, tmp_path):
    settings = folder_settings(tmp_path)
    approved = Path(settings["folders"]["approved"])
    request = write_xlsx(approved / "request_x.xlsx")

    def fake_process(path, cfg, conns, settings):
        raise runner.RequestError("Bảng không hợp lệ: bad")

    monkeypatch.setattr(runner, "process_request_file", fake_process)

    processed = runner.run_once(settings=settings, cfg={}, stable_wait=0)

    assert processed == 0
    assert not request.exists()
    rejected = approved / "[LOI]_request_x.xlsx"
    assert rejected.exists()
    txt = approved / "[LOI]_request_x.txt"
    assert txt.exists()
    assert "Bảng không hợp lệ" in txt.read_text(encoding="utf-8")
