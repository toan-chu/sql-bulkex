import os
import subprocess
import time
from pathlib import Path

import runner


def cleanup_settings(tmp_path, enabled=True, approved_delay_hours=2, output_delay_days=7):
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
        "onedrive_freeup": {
            "enabled": enabled,
            "approved_delay_hours": approved_delay_hours,
            "output_delay_days": output_delay_days,
        },
    }


def write_file(path):
    path = Path(path)
    path.write_text("xlsx placeholder", encoding="utf-8")
    return path


def set_mtime_hours_ago(path, hours):
    stamp = time.time() - hours * 3600
    os.utime(path, (stamp, stamp))


def test_t59_old_done_file_calls_attrib(monkeypatch, tmp_path):
    settings = cleanup_settings(tmp_path, approved_delay_hours=2)
    approved = Path(settings["folders"]["approved"])
    path = write_file(approved / "[DONE] test.xlsx")
    set_mtime_hours_ago(path, 3)
    calls = []

    def fake_run(cmd, check, capture_output, timeout):
        calls.append((cmd, check, capture_output, timeout))

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.setattr(runner, "log_event", lambda message: None)

    result = runner.cleanup_onedrive(settings)

    assert result == {"freed": 1, "skipped": 0, "failed": 0}
    assert calls == [(["attrib", "+U", "-P", str(path)], True, True, 10)]


def test_t60_old_output_file_calls_attrib(monkeypatch, tmp_path):
    settings = cleanup_settings(tmp_path, output_delay_days=7)
    output = Path(settings["folders"]["output"])
    path = write_file(output / "output_test.xlsx")
    set_mtime_hours_ago(path, 8 * 24)
    calls = []

    def fake_run(cmd, check, capture_output, timeout):
        calls.append(cmd)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.setattr(runner, "log_event", lambda message: None)

    result = runner.cleanup_onedrive(settings)

    assert result == {"freed": 1, "skipped": 0, "failed": 0}
    assert calls == [["attrib", "+U", "-P", str(path)]]


def test_t61_attrib_fail_logs_and_does_not_raise(monkeypatch, tmp_path):
    settings = cleanup_settings(tmp_path, approved_delay_hours=2)
    approved = Path(settings["folders"]["approved"])
    path = write_file(approved / "[DONE] test.xlsx")
    set_mtime_hours_ago(path, 3)
    logs = []

    def fake_run(cmd, check, capture_output, timeout):
        raise subprocess.CalledProcessError(1, cmd, stderr=b"not OneDrive")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.setattr(runner, "log_event", logs.append)

    result = runner.cleanup_onedrive(settings)

    assert result == {"freed": 0, "skipped": 0, "failed": 1}
    assert any("[FREEUP] FAIL [DONE] test.xlsx: exit 1 - not OneDrive" in item for item in logs)


def test_t61b_fresh_done_file_is_skipped(monkeypatch, tmp_path):
    settings = cleanup_settings(tmp_path, approved_delay_hours=2)
    approved = Path(settings["folders"]["approved"])
    path = write_file(approved / "[DONE] fresh.xlsx")
    set_mtime_hours_ago(path, 1)
    calls = []

    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(runner, "log_event", lambda message: None)

    result = runner.cleanup_onedrive(settings)

    assert result == {"freed": 0, "skipped": 1, "failed": 0}
    assert calls == []


def test_t61c_disabled_config_skips_all(monkeypatch, tmp_path):
    settings = cleanup_settings(tmp_path, enabled=False)
    approved = Path(settings["folders"]["approved"])
    path = write_file(approved / "[DONE] old.xlsx")
    set_mtime_hours_ago(path, 100)
    calls = []

    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(runner, "log_event", lambda message: None)

    result = runner.cleanup_onedrive(settings)

    assert result == {"freed": 0, "skipped": 0, "failed": 0}
    assert calls == []
