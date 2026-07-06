import importlib

import portal


def test_import_portal_does_not_run_main(monkeypatch):
    called = False

    def fake_main():
        nonlocal called
        called = True

    monkeypatch.setattr(portal, "main", fake_main)
    importlib.reload(portal)

    assert called is False
    assert portal.sys.dont_write_bytecode is True


def test_ensure_password_reads_connection_yaml_password(monkeypatch):
    def fail_getpass(prompt):
        raise AssertionError("getpass should not be called when password is configured")

    monkeypatch.setattr(portal.getpass, "getpass", fail_getpass)

    cfg = portal.ensure_password({"user": "postgres", "password": "secret"})

    assert cfg["_password"] == "secret"


def test_ensure_password_reads_password_file(monkeypatch, tmp_path):
    password_file = tmp_path / ".password"
    password_file.write_text("file-secret\n", encoding="utf-8")

    def fail_getpass(prompt):
        raise AssertionError("getpass should not be called when .password exists")

    monkeypatch.setattr(portal, "PASSWORD_FILE", str(password_file))
    monkeypatch.setattr(portal.getpass, "getpass", fail_getpass)

    cfg = portal.ensure_password({"user": "postgres", "password": ""})

    assert cfg["_password"] == "file-secret"


def test_ensure_password_falls_back_to_getpass(monkeypatch):
    prompts = []

    def fake_getpass(prompt):
        prompts.append(prompt)
        return "typed-secret"

    monkeypatch.setattr(portal.getpass, "getpass", fake_getpass)
    monkeypatch.setattr(portal, "PASSWORD_FILE", "missing-test-password-file")

    cfg = portal.ensure_password({"user": "alice"})

    assert cfg["_password"] == "typed-secret"
    assert prompts == ["Password PostgreSQL (user: alice): "]
