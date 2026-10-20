"""Paths, settings and database connections for the BulkEx runner (v7).

Machine-specific files live in <repo>/config/ and are never committed:
  connection.yaml   host / port / user / maintenance_db (password may be left empty)
  .password         the database password, one line (read with utf-8-sig: PowerShell may add a BOM)
  bulkex.yaml       workspace folder + limits, written by setup
Logs go to <workspace>/_system/log (bulkex.log, requests.csv), so the repo never grows.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import psycopg2
import yaml

APP_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = APP_DIR.parent
CONFIG_DIR = ROOT_DIR / "config"


class ConfigError(Exception):
    """A setup problem the admin has to fix (missing file, wrong password...)."""


def load_yaml(path, default=None):
    path = Path(path)
    if not path.exists():
        return {} if default is None else default
    with open(path, encoding="utf-8-sig") as f:
        data = yaml.safe_load(f)
    return data if data is not None else ({} if default is None else default)


@dataclass
class Settings:
    workspace: Path
    max_rows: int = 3_000_000       # up to this many Detail rows the result is Excel (split over sheets); more -> CSV only
    csv_max_rows: int = 10_000_000  # hard ceiling: bigger requests are refused
    xlsx_max_rows: int = 1_000_000  # rows per Excel sheet; bigger Detail results continue on the next sheet
    query_timeout_minutes: int = 15
    min_free_gb: float = 5  # exports are refused when the disk has less free space than this
    databases: list = field(default_factory=list)  # empty = scan every database the user can open
    log_dir: Path | None = None  # default: <workspace>/_system/log - logs live in the shared folder, never in the repo
    app_dir: Path = APP_DIR

    def __post_init__(self):
        self.workspace = Path(self.workspace)
        self.log_dir = Path(self.log_dir) if self.log_dir else self.workspace / "_system" / "log"

    @property
    def input_dir(self):
        return self.workspace / "input"

    @property
    def output_dir(self):
        return self.workspace / "output"

    @property
    def system_dir(self):
        return self.workspace / "_system"

    def ensure_dirs(self):
        for d in (self.input_dir, self.output_dir, self.system_dir, self.system_dir / "done",
                  self.system_dir / "failed", self.system_dir / "tmp", self.log_dir):
            d.mkdir(parents=True, exist_ok=True)


def load_settings(config_dir=None) -> Settings:
    config_dir = Path(config_dir or CONFIG_DIR)
    data = load_yaml(config_dir / "bulkex.yaml")
    if not data.get("workspace"):
        raise ConfigError(f"{config_dir / 'bulkex.yaml'} has no workspace folder. Run setup first.")
    return Settings(
        workspace=Path(data["workspace"]),
        max_rows=int(data.get("max_rows", 3_000_000)),
        csv_max_rows=int(data.get("csv_max_rows", 10_000_000)),
        xlsx_max_rows=int(data.get("xlsx_max_rows", 1_000_000)),
        query_timeout_minutes=int(data.get("query_timeout_minutes", 15)),
        min_free_gb=float(data.get("min_free_gb", 5)),
        databases=list(data.get("databases") or []),
        log_dir=data.get("log_dir") or None,
    )


def read_password(config_dir=None):
    path = Path(config_dir or CONFIG_DIR) / ".password"
    if not path.exists():
        return None
    with open(path, encoding="utf-8-sig") as f:
        return f.readline().strip() or None


def load_connection(config_dir=None) -> dict:
    """Connection settings with the password resolved. Never asks on the keyboard (the runner has no window)."""
    config_dir = Path(config_dir or CONFIG_DIR)
    cfg = load_yaml(config_dir / "connection.yaml")
    if not cfg:
        raise ConfigError(f"{config_dir / 'connection.yaml'} is missing. Run setup first.")
    password = str(cfg.get("password") or "").strip() or read_password(config_dir)
    if not password:
        raise ConfigError("No database password: put it in config/.password (one line) or run setup again.")
    cfg["_password"] = password
    return cfg


def connect(cfg: dict, dbname: str, timeout_minutes: int | None = None):
    """Read-only connection. statement_timeout stops one heavy request from blocking every other request."""
    options = "-c default_transaction_read_only=on"
    if timeout_minutes:
        options += f" -c statement_timeout={int(timeout_minutes) * 60 * 1000}"
    conn = psycopg2.connect(
        host=cfg.get("host", "localhost"),
        port=cfg.get("port", 5432),
        user=cfg.get("user", "postgres"),
        password=cfg["_password"],
        dbname=dbname,
        connect_timeout=10,
        options=options,
        application_name="bulkex",
    )
    conn.set_client_encoding("UTF8")
    return conn
