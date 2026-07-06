import portal


def sample_state():
    return {
        "db": "vn/import",
        "schema": "public",
        "tables": ["x_y2025_01"],
        "cols": ["mst", "hs"],
        "filters": [("mst", "prefix", "010")],
        "split": None,
        "split_len": None,
        "sort": ("mst", "ASC"),
        "merged": False,
        "cur": object(),
    }


def test_serializable_job_state_excludes_runtime_and_sql():
    state = portal.serializable_job_state(sample_state())

    assert "cur" not in state
    assert "query" not in state
    assert state == {
        "db": "vn/import",
        "schema": "public",
        "tables": ["x_y2025_01"],
        "cols": ["mst", "hs"],
        "filters": [("mst", "prefix", "010")],
        "split": None,
        "split_len": None,
        "sort": ("mst", "ASC"),
        "merged": False,
    }


def test_save_and_load_job_yaml(tmp_path):
    jobs_path = tmp_path / "jobs.yaml"
    state = portal.serializable_job_state(sample_state())

    portal.save_job("daily-mst", state, path=jobs_path)

    loaded = portal.load_saved_jobs(path=jobs_path)
    assert loaded["daily-mst"]["db"] == "vn/import"
    assert loaded["daily-mst"]["filters"] == [["mst", "prefix", "010"]]


def test_list_jobs_does_not_read_connection_config(monkeypatch, tmp_path, capsys):
    jobs_path = tmp_path / "jobs.yaml"
    portal.save_job("daily-mst", portal.serializable_job_state(sample_state()), path=jobs_path)
    monkeypatch.setattr(portal, "JOBS_FILE", str(jobs_path))

    def fail_load_config():
        raise AssertionError("list jobs should not read connection.yaml")

    monkeypatch.setattr(portal, "load_config", fail_load_config)

    assert portal.main(["--list-jobs"]) == 0

    out = capsys.readouterr().out
    assert "daily-mst" in out
    assert "vn/import.public" in out


def test_run_saved_job_uses_saved_state_without_menu(monkeypatch, tmp_path):
    jobs_path = tmp_path / "jobs.yaml"
    portal.save_job("daily-mst", portal.serializable_job_state(sample_state()), path=jobs_path)
    monkeypatch.setattr(portal, "JOBS_FILE", str(jobs_path))

    class FakeCursor:
        def close(self):
            pass

    class FakeConn:
        closed = False

        def cursor(self):
            return FakeCursor()

        def rollback(self):
            pass

        def close(self):
            pass

    captured = {}

    monkeypatch.setattr(portal, "load_config", lambda: {"password": "secret", "job_export_format": "csv"})
    monkeypatch.setattr(portal, "get_conn", lambda conns, cfg, dbname: FakeConn())
    monkeypatch.setattr(portal, "missing_tables", lambda cur, schema, tables: [])
    monkeypatch.setattr(
        portal,
        "make_jobs",
        lambda st, cur: captured.setdefault("state", st)
        and [("out", st["db"], "SQL_OBJECT", ["010%"])],
    )

    def fake_run_export(conns, cfg, jobs, fmt=None):
        captured["jobs"] = jobs
        captured["fmt"] = fmt
        return True

    monkeypatch.setattr(portal, "run_export", fake_run_export)

    assert portal.main(["--job", "daily-mst"]) == 0
    assert captured["state"]["db"] == "vn/import"
    assert captured["state"]["cur"].__class__.__name__ == "FakeCursor"
    assert captured["jobs"] == [("out", "vn/import", "SQL_OBJECT", ["010%"])]
    assert captured["fmt"] == "csv"


def run_review_path(monkeypatch, actions):
    class FakeConnection:
        def rollback(self):
            pass

    class FakeCursor:
        connection = FakeConnection()

        def close(self):
            pass

    class FakeConn:
        closed = False

        def cursor(self):
            return FakeCursor()

    sel_values = iter([portal.SKIP, portal.SKIP, *actions])
    saved = []

    monkeypatch.setattr(portal, "pick_database", lambda cfg, conns: "db")
    monkeypatch.setattr(portal, "get_conn", lambda conns, cfg, dbname: FakeConn())
    monkeypatch.setattr(portal, "pick_schema", lambda cur: "public")
    monkeypatch.setattr(portal, "pick_tables", lambda cur, schema: ["table1"])
    monkeypatch.setattr(portal, "pick_columns", lambda cur, schema, tables: ["mst"])
    monkeypatch.setattr(portal, "build_filters", lambda cur, schema, tables, cols: [])
    monkeypatch.setattr(portal, "make_jobs", lambda st, cur: [("out", "db", "SQL", [])])
    monkeypatch.setattr(portal, "count_rows", lambda cur, query, params: 1)
    monkeypatch.setattr(portal, "show_preview", lambda cur, query, params: None)
    monkeypatch.setattr(portal, "sel", lambda message, choices: next(sel_values))
    monkeypatch.setattr(portal, "prompt_save_job", lambda st: saved.append(st.copy()))

    result = portal.build_job({}, {}, queued=0)

    return result, saved


def test_build_job_saves_only_after_export_or_queue(monkeypatch):
    result, saved = run_review_path(monkeypatch, ["export"])

    assert result[0] == "export"
    assert len(saved) == 1


def test_build_job_does_not_save_before_preview_or_drop(monkeypatch):
    result, saved = run_review_path(monkeypatch, ["prev", "drop"])

    assert result == ("drop", [])
    assert saved == []
