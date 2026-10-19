"""Setup wizard (CAI-DAT.bat) against a real PostgreSQL. Needs BULKEX_TEST_PG like test_runner_pg."""
import json

import pytest

from bulkex import setup as S
from test_runner_pg import PG, pg  # noqa: F401  (pg is the database fixture)

pytestmark = pytest.mark.skipif(not PG, reason="set BULKEX_TEST_PG to run the PostgreSQL tests")


def write_conn(d, pg):
    d.mkdir(parents=True, exist_ok=True)
    (d / "connection.yaml").write_text(f"host: {pg['host']}\nport: {pg.get('port', 5432)}\nuser: {pg['user']}\npassword: ''\n", encoding="utf-8")


def no_prompt(*a, **k):
    raise AssertionError("setup asked for a password although a saved one works")


def test_saved_password_with_bom_is_used_without_asking(pg, tmp_path):
    cfgdir = tmp_path / "config"
    write_conn(cfgdir, pg)
    (cfgdir / ".password").write_bytes(b"\xef\xbb\xbf" + pg["_password"].encode() + b"\r\n")
    cfg = S.setup_connection(cfgdir, input_func=no_prompt, getpass_func=no_prompt, pgpass_path=tmp_path / "none")
    assert cfg["_password"] == pg["_password"]


def test_password_from_pgpass_file(pg, tmp_path):
    cfgdir = tmp_path / "config"
    write_conn(cfgdir, pg)
    pgpass = tmp_path / "pgpass.conf"
    pgpass.write_text(f"localhost:5432:*:{pg['user']}:{pg['_password']}\n", encoding="utf-8")
    S.setup_connection(cfgdir, input_func=no_prompt, getpass_func=no_prompt, pgpass_path=pgpass)
    assert (cfgdir / ".password").read_text(encoding="utf-8").strip() == pg["_password"]


def test_wrong_saved_password_asks_once_then_saves(pg, tmp_path):
    cfgdir = tmp_path / "config"
    write_conn(cfgdir, pg)
    (cfgdir / ".password").write_text("old-wrong-password\n", encoding="utf-8")
    answers = iter(["still-wrong", pg["_password"]])
    S.setup_connection(cfgdir, input_func=no_prompt, getpass_func=lambda *_: next(answers), pgpass_path=tmp_path / "none")
    assert (cfgdir / ".password").read_text(encoding="utf-8").strip() == pg["_password"]
    assert "password: ''" in (cfgdir / "connection.yaml").read_text(encoding="utf-8")  # never written in clear there


def test_full_setup_into_a_test_folder(pg, tmp_path):
    cfgdir = tmp_path / "config"
    write_conn(cfgdir, pg)
    (cfgdir / ".password").write_text(pg["_password"], encoding="utf-8")
    calls = []
    rc = S.main(input_func=lambda *_: "1", getpass_func=no_prompt, config_dir=cfgdir, app_dir=S.APP_DIR,
                root_dir=tmp_path, roots=[], downloads=tmp_path / "Downloads", run=lambda *a, **k: calls.append(a))
    ws = tmp_path / "Downloads" / "SQL-BulkEx"
    assert rc == 0
    assert (ws / "BulkEx.html").exists() and (ws / "input").is_dir() and (ws / "output").is_dir()
    cat = (ws / "_system" / "catalog.js").read_text(encoding="utf-8")
    assert '"2025-01"' in cat and "bx_test_main" not in cat
    assert "SQL-BulkEx" in (cfgdir / "bulkex.yaml").read_text(encoding="utf-8")
    assert json.loads((cfgdir / "values.json").read_text(encoding="utf-8"))["export"]


def test_old_v6_jobs_are_removed_and_new_job_points_at_v7(tmp_path):
    calls = []

    class R:
        returncode = 0
        stdout = stderr = ""

    def run(cmd, **k):
        calls.append(cmd)
        return R()
    assert S.install_task(tmp_path, run, windows=True)
    flat = [" ".join(map(str, c)) for c in calls]
    assert any("/delete /tn SQL BulkEx Runner" in c for c in flat)
    create = next(c for c in flat if "/create" in c)
    assert "/sc minute /mo 2" in create and str(tmp_path / "app" / "bulkex") in create and create.endswith("once /f")
