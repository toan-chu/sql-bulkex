"""SQL BulkEx - Setup wizard cho admin (chay 1 lan sau khi clone repo).

Tu dong:
1. Detect vi tri repo (khong can sua path).
2. Detect moi folder OneDrive / SharePoint da sync tren may (doc registry).
3. Tao 3 folder workspace (01_Pending / 02_Approved / 03_Output).
4. Ghi settings.yaml voi path tuyet doi cua may nay.
5. Scan database + schema PostgreSQL tren may -> ghi column.yaml.
6. Cai 2 Task Scheduler (runner --once moi 2 phut, --cleanup moi gio).

Chay: double-click setup.bat  (hoac: python setup.py)
"""

import os
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Thieu thu vien. Chay truoc:  pip install -r requirements.txt")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "settings.yaml"
WORKSPACE_NAME = "SQL-BulkEx-Workspace"
SUBFOLDERS = {"pending": "01_Pending", "approved": "02_Approved", "output": "03_Output"}


def detect_sync_roots():
    """Doc registry -> list (ten hien thi, local path) cua moi thu vien OneDrive/SharePoint da sync."""
    roots = []
    seen = set()
    try:
        import winreg
    except ImportError:
        return roots

    # SharePoint / OneDrive sync engines
    try:
        base = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\SyncEngines\Providers\OneDrive")
        i = 0
        while True:
            try:
                sub_name = winreg.EnumKey(base, i)
            except OSError:
                break
            i += 1
            try:
                sub = winreg.OpenKey(base, sub_name)
                mount, _ = winreg.QueryValueEx(sub, "MountPoint")
                try:
                    url, _ = winreg.QueryValueEx(sub, "UrlNamespace")
                except OSError:
                    url = ""
                if mount and mount not in seen and Path(mount).exists():
                    seen.add(mount)
                    roots.append((url or mount, mount))
            except OSError:
                continue
    except OSError:
        pass

    # Fallback: bien moi truong OneDrive ca nhan / cong ty
    for env in ("OneDriveCommercial", "OneDrive"):
        p = os.environ.get(env)
        if p and p not in seen and Path(p).exists():
            seen.add(p)
            roots.append((f"%{env}%", p))
    return roots


def pick_root(roots):
    print("\n=== Folder OneDrive / SharePoint tim thay tren may ===")
    for idx, (label, path) in enumerate(roots, 1):
        print(f"  [{idx}] {path}")
        if label != path:
            print(f"      ({label})")
    print(f"  [0] Nhap path thu cong")
    while True:
        raw = input(f"Chon noi dat workspace [1-{len(roots)} hoac 0]: ").strip()
        if raw == "0":
            manual = input("Dan path folder OneDrive/SharePoint: ").strip().strip('"')
            if Path(manual).exists():
                return manual
            print("Path khong ton tai, thu lai.")
        elif raw.isdigit() and 1 <= int(raw) <= len(roots):
            return roots[int(raw) - 1][1]
        else:
            print("Nhap so trong danh sach.")


def pick_from_list(title, items):
    print(f"\n{title}:")
    for idx, item in enumerate(items, 1):
        print(f"  [{idx}] {item}")
    while True:
        raw = input(f"Chon [1-{len(items)}]: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(items):
            return items[int(raw) - 1]
        print("Nhap so trong danh sach.")


def pattern_to_regex(pattern):
    """'x_y{year}_{month}' -> regex '^x_y\\d{4}_\\d{2}$' de match ten bang that."""
    import re
    esc = re.escape(str(pattern))
    esc = esc.replace(re.escape("{year}"), r"\d{4}")
    esc = esc.replace(re.escape("{month}"), r"\d{2}")
    esc = esc.replace(re.escape("*"), ".*")
    return f"^{esc}$"


def infer_pattern(tables):
    """Tu ten bang that, suy ra pattern {year}/{month} pho bien nhat.

    Vd ['x_y2025_01', 'x_y2025_02', ...] -> ('x_y{year}_{month}', 24 bang khop).
    Tra ve (pattern, count) hoac (None, 0) neu khong bang nao co nam trong ten.
    """
    import re
    from collections import Counter
    pats = Counter()
    for t in tables:
        p = re.sub(r"(19|20)\d{2}", "{year}", t, count=1)
        if "{year}" not in p:
            continue
        p = re.sub(r"(\{year\}\D?)(\d{2})(?!\d)", r"\1{month}", p, count=1)
        pats[p] += 1
    if not pats:
        return None, 0
    pattern, count = pats.most_common(1)[0]
    return pattern, count


def detect_database():
    """Quet MOI database x MOI schema, tim noi co bang khop pattern -> tu ghi column.yaml."""
    try:
        import portal
    except ImportError as e:
        print(f"Bo qua buoc database (thieu thu vien: {e})")
        return

    try:
        cfg = portal.ensure_password(portal.load_config())
    except SystemExit:
        print("Bo qua buoc database: chua co connection.yaml (README Buoc 4).")
        return

    conn = None
    for maintenance_db in ("postgres", "template1"):
        try:
            conn = portal.connect(cfg, maintenance_db)
            break
        except Exception:
            continue
    if conn is None:
        print("LOI: khong ket noi duoc PostgreSQL.")
        print("     Kiem tra: service PostgreSQL da chay chua? connection.yaml dung host/port/user chua? .password dung chua?")
        print("     Sua xong chay lai setup.bat — cac buoc da xong se giu nguyen.")
        return

    with conn.cursor() as cur:
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false AND datname <> 'postgres' ORDER BY datname")
        dbs = [r[0] for r in cur.fetchall()]
    conn.close()
    if not dbs:
        print("LOI: PostgreSQL chua co database nao (chua restore data?). Bo qua buoc nay.")
        return

    col_file = BASE_DIR / "column.yaml"
    if not col_file.exists():
        print("Khong thay column.yaml — bo qua.")
        return
    with open(col_file, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    datasets = data.get("datasets") or {}
    if not datasets:
        print("column.yaml chua co dataset nao — bo qua.")
        return

    # Quet moi db x schema, dem so bang khop pattern cua tung dataset
    hits = {name: [] for name in datasets}          # dataset -> [(db, schema, so_bang)]
    all_tables = {}                                  # db -> [(schema, table)] de in khi khong khop
    for db in dbs:
        try:
            conn = portal.connect(cfg, db)
        except Exception:
            continue
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1, 2"
            )
            rows = cur.fetchall()
        conn.close()
        all_tables[db] = rows
        for name, ds in datasets.items():
            import re
            rx = re.compile(pattern_to_regex(ds.get("tables", "")))
            count = {}
            for schema, table in rows:
                if rx.match(table):
                    count[schema] = count.get(schema, 0) + 1
            for schema, n in count.items():
                hits[name].append((db, schema, n))

    updated = False
    for name, ds in datasets.items():
        found = sorted(hits[name], key=lambda x: -x[2])
        if len(found) == 1 or (found and found[0][2] > (found[1][2] if len(found) > 1 else 0)):
            db, schema, n = found[0]
            ds["database"], ds["schema"] = db, schema
            updated = True
            print(f"OK  dataset '{name}': {db} > {schema} ({n} bang khop pattern {ds['tables']})")
        elif found:
            choice = pick_from_list(
                f"Dataset '{name}' khop nhieu noi, chon 1",
                [f"{db} > {schema} ({n} bang)" for db, schema, n in found],
            )
            idx = [f"{db} > {schema} ({n} bang)" for db, schema, n in found].index(choice)
            ds["database"], ds["schema"] = found[idx][0], found[idx][1]
            updated = True
        else:
            # Pattern trong column.yaml khong khop -> tu suy pattern tu ten bang that
            print(f"\nDataset '{name}': pattern cu '{ds.get('tables')}' khong khop bang nao.")
            suggestions = []   # [(db, schema, pattern, count)]
            for db, rows in all_tables.items():
                by_schema = {}
                for schema, table in rows:
                    by_schema.setdefault(schema, []).append(table)
                for schema, tables in by_schema.items():
                    pattern, count = infer_pattern(tables)
                    if pattern and count >= 2:
                        suggestions.append((db, schema, pattern, count))
            if not suggestions:
                print("Khong suy duoc pattern (ten bang khong chua nam). Bang thuc te:")
                for db, rows in all_tables.items():
                    for schema, table in rows[:15]:
                        print(f"  {db} > {schema} > {table}")
                    if len(rows) > 15:
                        print(f"  ... ({len(rows) - 15} bang nua trong {db})")
                continue
            labels = [f"{db} > {schema} > {p} ({n} bang)" for db, schema, p, n in suggestions]
            if len(suggestions) == 1:
                db, schema, pattern, n = suggestions[0]
                print(f"Tim thay 1 ung vien: {labels[0]}")
                ans = input(f"Dung cho dataset '{name}'? [Y/n]: ").strip().lower()
                if ans not in ("", "y", "yes"):
                    continue
            else:
                choice = pick_from_list(f"Chon noi chua data cho dataset '{name}'", labels)
                db, schema, pattern, n = suggestions[labels.index(choice)]
            ds["database"], ds["schema"], ds["tables"] = db, schema, pattern
            updated = True
            print(f"OK  dataset '{name}': {db} > {schema}, tables = {pattern}")

    if updated:
        with open(col_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        print("OK  Da ghi column.yaml (database + schema cua may nay)")


def ensure_workspace(root):
    ws = Path(root) / WORKSPACE_NAME
    paths = {}
    for key, name in SUBFOLDERS.items():
        p = ws / name
        p.mkdir(parents=True, exist_ok=True)
        paths[key] = str(p).replace("\\", "/")
    print(f"\nOK  Workspace: {ws}")
    return paths


def write_settings(folders):
    data = {}
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    data["folders"] = folders
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    print(f"OK  Da ghi {SETTINGS_FILE.name}")


def find_pythonw():
    exe = Path(sys.executable)
    pw = exe.with_name("pythonw.exe")
    return str(pw if pw.exists() else exe)


def install_tasks():
    pythonw = find_pythonw()
    runner = str(BASE_DIR / "runner.py")
    tasks = [
        ("SQL BulkEx Runner", ["/sc", "minute", "/mo", "2"], "--once"),
        ("SQL BulkEx Cleanup", ["/sc", "hourly", "/mo", "1"], "--cleanup"),
    ]
    ok = True
    for name, schedule, flag in tasks:
        cmd = ["schtasks", "/create", "/tn", name, *schedule,
               "/tr", f'"{pythonw}" "{runner}" {flag}', "/f"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            print(f"OK  Task Scheduler: {name}")
            # Mac dinh schtasks chi chay khi cam sac -> tat dieu kien pin (laptop van chay)
            ps = (
                "$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries "
                "-DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew; "
                f"Set-ScheduledTask -TaskName '{name}' -Settings $s"
            )
            r2 = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                                capture_output=True, text=True)
            if r2.returncode != 0:
                print(f"    (canh bao: khong tat duoc dieu kien pin — "
                      f"neu laptop chay pin, mo Task Scheduler > {name} > Conditions "
                      f"> bo tick 'Start the task only if the computer is on AC power')")
        else:
            ok = False
            print(f"LOI Task '{name}': {(r.stderr or r.stdout).strip()}")
    return ok


def main():
    print("=== SQL BulkEx Setup ===")
    print(f"Repo: {BASE_DIR}")

    roots = detect_sync_roots()
    if roots:
        root = pick_root(roots)
    else:
        print("Khong tim thay OneDrive/SharePoint sync tren may.")
        root = input("Dan path folder OneDrive/SharePoint: ").strip().strip('"')
        if not Path(root).exists():
            print("Path khong ton tai. Thoat.")
            sys.exit(1)

    folders = ensure_workspace(root)
    write_settings(folders)

    print("\n=== Database PostgreSQL ===")
    detect_database()

    ans = input("\nCai Task Scheduler cho runner tu chay nen? [Y/n]: ").strip().lower()
    if ans in ("", "y", "yes"):
        install_tasks()
    else:
        print("Bo qua. Co the chay tay:  python runner.py --once")

    print("\n=== Xong. Buoc tiep theo (xem README Buoc 6-7) ===")
    print("  python runner.py --scan-columns --yes")
    print("  python runner.py --scan-values --yes")
    print("  python runner.py --make-template")


if __name__ == "__main__":
    main()
