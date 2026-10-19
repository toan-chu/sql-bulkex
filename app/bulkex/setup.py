"""Setup wizard behind CAI-DAT.bat. Safe to run again at any time.

1. Connect to PostgreSQL - reuses a saved password; asks (hidden) only when none works.
2. Find the Export / Import tables in every database.
3. Pick the shared folder (OneDrive, or any folder for testing) and put BulkEx.html, input/, output/ there.
4. Fill the page's field list and suggestion lists.
5. Register the background job in Windows Task Scheduler (every 2 minutes).
"""
from __future__ import annotations

import getpass
import os
import shutil
import subprocess
import sys
from pathlib import Path

import psycopg2
import yaml

from .onedrive import keep_on_device
from .catalog import load_defs, scan_values
from .config import APP_DIR, CONFIG_DIR, ROOT_DIR, Settings, connect, load_yaml
from .runner import Runner, setup_logging
from .scan import scan

TASK_NAME = "BulkEx Runner"
OLD_TASKS = ("SQL BulkEx Runner", "SQL BulkEx Cleanup")
FOLDER_NAME = "SQL-BulkEx"


def say(msg=""):
    print(msg, flush=True)


def ask(prompt, default=None, input_func=input):
    hint = f" [{default}]" if default not in (None, "") else ""
    raw = input_func(f"{prompt}{hint}: ").strip().strip('"')
    return raw or (default if default is not None else "")


# ---------------------------------------------------------------- 1. database password
def pgpass_passwords(user, path=None):
    """Passwords for `user` in PostgreSQL's own password file (pgAdmin / psql may have saved one)."""
    if path is None:
        base = os.environ.get("APPDATA")
        path = Path(base) / "postgresql" / "pgpass.conf" if base else Path.home() / ".pgpass"
    path = Path(path)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.strip().split(":")
        if len(parts) >= 5 and not line.startswith("#") and parts[3] in (user, "*"):
            out.append(":".join(parts[4:]))
    return out


def saved_passwords(cfg, config_dir: Path, pgpass_path=None):
    """Every password already stored somewhere on this machine, best guess first, no duplicates."""
    found = []
    pw_file = config_dir / ".password"
    if pw_file.exists():
        lines = pw_file.read_text(encoding="utf-8-sig").splitlines()
        if lines:
            found.append(lines[0].strip())
    found.append(str(cfg.get("password") or "").strip())
    found.append(os.environ.get("PGPASSWORD", ""))
    found += pgpass_passwords(cfg.get("user", "postgres"), pgpass_path)
    return [p for i, p in enumerate(found) if p and p not in found[:i]]


def try_connect(cfg, password):
    test = dict(cfg, _password=password)
    try:
        connect(test, cfg.get("maintenance_db") or "postgres").close()
        return True, ""
    except psycopg2.OperationalError as e:
        return False, str(e).strip().splitlines()[0] if str(e).strip() else "connection failed"


def setup_connection(config_dir: Path, input_func=input, getpass_func=getpass.getpass, pgpass_path=None):
    say("\n[1/5] Kết nối PostgreSQL")
    cfg = {"host": "localhost", "port": 5432, "user": "postgres", "maintenance_db": "postgres"}
    cfg.update({k: v for k, v in load_yaml(config_dir / "connection.yaml").items() if v not in (None, "")})
    for pw in saved_passwords(cfg, config_dir, pgpass_path):
        ok, _ = try_connect(cfg, pw)
        if ok:
            say(f"   OK  Đăng nhập {cfg['user']}@{cfg['host']}:{cfg['port']} bằng mật khẩu đã lưu - không cần nhập.")
            return save_connection(config_dir, cfg, pw)
    for attempt in range(3):
        pw = getpass_func(f"   Nhập mật khẩu PostgreSQL của user '{cfg['user']}' (gõ không hiện chữ, xong bấm Enter): ")
        ok, err = try_connect(cfg, pw)
        if ok:
            say("   OK  Đăng nhập được, đã lưu mật khẩu cho lần sau.")
            return save_connection(config_dir, cfg, pw)
        if "password authentication failed" in err:
            say("   Sai mật khẩu, thử lại.")
            continue
        say(f"   Không kết nối được: {err}")
        say("   Thường là PostgreSQL chưa chạy, hoặc khác máy / cổng / user.")
        cfg["host"] = ask("   Máy chủ (host)", cfg["host"], input_func)
        cfg["port"] = int(ask("   Cổng (port)", cfg["port"], input_func))
        cfg["user"] = ask("   User", cfg["user"], input_func)
    raise SystemExit("   Dừng: chưa đăng nhập được PostgreSQL. Kiểm tra lại rồi nháy đúp CAI-DAT.bat lần nữa.")


def save_connection(config_dir: Path, cfg, password):
    config_dir.mkdir(parents=True, exist_ok=True)
    keep = {k: cfg[k] for k in ("host", "port", "user", "maintenance_db")}
    keep["password"] = ""
    (config_dir / "connection.yaml").write_text(
        "# Written by BulkEx setup. The password is kept in config/.password.\n" + yaml.safe_dump(keep, sort_keys=False),
        encoding="utf-8")
    (config_dir / ".password").write_text(password + "\n", encoding="utf-8")
    return dict(keep, _password=password)


# ---------------------------------------------------------------- 2. tables
def show_scan(cfg, app_dir: Path):
    say("\n[2/5] Tìm bảng Export / Import trong mọi database")
    _, defs = load_defs(app_dir)
    found, warnings = scan(cfg, defs.get("datasets") or {})
    total = 0
    for ds, tables in found.items():
        total += len(tables)
        if tables:
            dbs = sorted({t["db"] for t in tables})
            say(f"   {ds}: {len(tables)} bảng, {tables[0]['period']} → {tables[-1]['period']}  (database: {', '.join(dbs)})")
        else:
            say(f"   {ds}: không thấy bảng nào")
    for w in warnings[:15]:
        say(f"   ghi chú: {w}")
    if not total:
        raise SystemExit("   Dừng: không thấy bảng dữ liệu nào. Nếu tên cột khác, sửa 'signature' trong app/datasets.yaml rồi chạy lại.")
    return found, defs


# ---------------------------------------------------------------- 3. shared folder
def sync_roots():
    """OneDrive / SharePoint folders synced on this computer (Windows registry + environment)."""
    roots, seen = [], set()
    try:
        import winreg
        base = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\SyncEngines\Providers\OneDrive")
        i = 0
        while True:
            try:
                sub = winreg.OpenKey(base, winreg.EnumKey(base, i))
            except OSError:
                break
            i += 1
            try:
                mount, _ = winreg.QueryValueEx(sub, "MountPoint")
                if mount and mount not in seen and Path(mount).exists():
                    seen.add(mount)
                    roots.append(Path(mount))
            except OSError:
                continue
    except (ImportError, OSError):
        pass
    for env in ("OneDriveCommercial", "OneDrive"):
        p = os.environ.get(env)
        if p and p not in seen and Path(p).exists():
            seen.add(p)
            roots.append(Path(p))
    return roots


def pick_workspace(current, input_func=input, roots=None, downloads=None):
    say("\n[3/5] Chọn thư mục chung (nơi người dùng mở BulkEx.html và nhận file kết quả)")
    roots = sync_roots() if roots is None else roots
    downloads = Path(downloads or Path.home() / "Downloads")
    options = []
    if current:
        options.append((Path(current), "đang dùng"))
    for r in roots:
        options.append((r / FOLDER_NAME, "OneDrive / SharePoint - dùng thật"))
    options.append((downloads / FOLDER_NAME, "Downloads - để thử trên máy này"))
    seen, uniq = set(), []
    for p, why in options:
        if str(p) not in seen:
            seen.add(str(p))
            uniq.append((p, why))
    for i, (p, why) in enumerate(uniq, 1):
        say(f"   [{i}] {p}   ({why})")
    say("   [0] Tự gõ đường dẫn khác")
    while True:
        raw = ask("   Chọn số", "1", input_func)
        if raw == "0":
            p = Path(ask("   Dán đường dẫn thư mục", "", input_func))
            if str(p) and (p.exists() or p.parent.exists()):
                return p
            say("   Thư mục không có, thử lại.")
        elif raw.isdigit() and 1 <= int(raw) <= len(uniq):
            return uniq[int(raw) - 1][0]
        else:
            say("   Gõ một số trong danh sách.")


def make_workspace(ws: Path, app_dir: Path):
    for sub in ("input", "output", "_system"):
        (ws / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy2(app_dir / "web" / "BulkEx.html", ws / "BulkEx.html")  # always the newest page
    say(f"   OK  {ws}  (BulkEx.html, input, output, _system)")
    if keep_on_device(ws):  # the runner must be able to read every request: no cloud-only files on this computer
        say("   OK  OneDrive: thư mục được đặt 'Always keep on this device'")


def save_settings(config_dir: Path, ws: Path):
    path = config_dir / "bulkex.yaml"
    data = load_yaml(path)
    data["workspace"] = str(ws)
    data.setdefault("max_rows", 3_000_000)       # more Detail rows than this -> CSV files instead of Excel
    data.setdefault("csv_max_rows", 10_000_000)  # more than this -> refused
    data.setdefault("query_timeout_minutes", 15)
    path.write_text("# Written by BulkEx setup. Edit the limits if needed.\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                    encoding="utf-8")


# ---------------------------------------------------------------- 5. background job
def pythonw():
    exe = Path(sys.executable)
    w = exe.with_name("pythonw.exe")
    return w if w.exists() else exe


def install_task(root_dir: Path, run=subprocess.run, windows=None):
    say("\n[5/5] Cài lịch chạy nền (mỗi 2 phút)")
    if not (os.name == "nt" if windows is None else windows):
        say("   Bỏ qua: không phải Windows.")
        return False
    for old in OLD_TASKS:  # v6 jobs pointed at files that no longer exist
        r = run(["schtasks", "/delete", "/tn", old, "/f"], capture_output=True, text=True)
        if r.returncode == 0:
            say(f"   Đã gỡ lịch cũ: {old}")
    action = f'"{pythonw()}" "{root_dir / "app" / "bulkex"}" once'
    r = run(["schtasks", "/create", "/tn", TASK_NAME, "/sc", "minute", "/mo", "2", "/tr", action, "/f"],
            capture_output=True, text=True)
    if r.returncode != 0:
        say(f"   LỖI: {(r.stderr or r.stdout).strip()}")
        return False
    ps = ("$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
          "-MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 3); "
          f"Set-ScheduledTask -TaskName '{TASK_NAME}' -Settings $s | Out-Null")
    r2 = run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    say(f"   OK  Task Scheduler: {TASK_NAME}")
    if r2.returncode != 0:
        say("   (Chưa tắt được điều kiện 'chỉ chạy khi cắm sạc'. Nếu là laptop: Task Scheduler > "
            f"{TASK_NAME} > Conditions > bỏ tick 'Start the task only if the computer is on AC power'.)")
    return True


# ---------------------------------------------------------------- main
def main(input_func=input, getpass_func=getpass.getpass, config_dir=CONFIG_DIR, app_dir=APP_DIR, root_dir=ROOT_DIR,
         roots=None, downloads=None, run=subprocess.run):
    say("=== Cài đặt BulkEx ===")
    config_dir, app_dir = Path(config_dir), Path(app_dir)
    cfg = setup_connection(config_dir, input_func, getpass_func)
    found, defs = show_scan(cfg, app_dir)
    ws = pick_workspace(load_yaml(config_dir / "bulkex.yaml").get("workspace"), input_func, roots, downloads)
    make_workspace(ws, app_dir)
    save_settings(config_dir, ws)
    say("\n[4/5] Chuẩn bị danh sách trường và gợi ý cho trang (có thể mất 1-2 phút)")
    values = scan_values(cfg, found, defs)
    import json
    (config_dir / "values.json").write_text(json.dumps(values, ensure_ascii=False, indent=1), encoding="utf-8")
    settings = Settings(workspace=ws, app_dir=app_dir)
    setup_logging(settings.log_dir)
    Runner(settings, cfg, config_dir).run_once()
    say("   OK  Trang đã có danh sách trường và các tháng có dữ liệu.")
    install_task(Path(root_dir), run)
    say("\n=== Xong ===")
    say(f"Thư mục chung: {ws}")
    say("Người dùng mở BulkEx.html trong thư mục đó bằng Chrome hoặc Edge.")
    say("Nếu là thư mục OneDrive: chia sẻ (Share) thư mục SQL-BulkEx cho người cần dùng.")
    if os.name == "nt":
        try:
            os.startfile(str(ws))  # noqa: S606 - open the folder for the admin
        except OSError:
            pass
    return 0
