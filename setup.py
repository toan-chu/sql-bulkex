"""SQL BulkEx - Setup wizard cho admin (chay 1 lan sau khi clone repo).

Tu dong:
1. Detect vi tri repo (khong can sua path).
2. Detect moi folder OneDrive / SharePoint da sync tren may (doc registry).
3. Tao 3 folder workspace (01_Pending / 02_Approved / 03_Output).
4. Ghi settings.yaml voi path tuyet doi cua may nay.
5. Cai 2 Task Scheduler (runner --once moi 2 phut, --cleanup moi gio).

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
