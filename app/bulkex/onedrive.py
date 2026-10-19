"""OneDrive "online-only" files on the database computer.

A file synced by OneDrive can sit on disk as a cloud placeholder. When Windows does not let a background
program download it, reading it fails with "[Errno 22] Invalid argument". The fix is to mark the shared
folder "Always keep on this device" (attribute +P), which is what `keep_on_device` does.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

# FILE_ATTRIBUTE_OFFLINE | FILE_ATTRIBUTE_RECALL_ON_OPEN | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
ONLINE_ONLY = 0x1000 | 0x40000 | 0x400000


def online_only(path: Path) -> bool:
    try:
        return bool(getattr(os.stat(path), "st_file_attributes", 0) & ONLINE_ONLY)
    except OSError:
        return False


def keep_on_device(folder: Path, run=subprocess.run, windows=None) -> bool:
    """Mark a folder and everything in it "Always keep on this device". Harmless outside OneDrive."""
    if not (os.name == "nt" if windows is None else windows):
        return False
    folder = Path(folder)
    ok = True
    for args in (["attrib", "+P", "-U", str(folder)], ["attrib", "+P", "-U", str(folder / "*"), "/S", "/D"]):
        try:
            r = run(args, capture_output=True, text=True, timeout=120)
            ok = ok and r.returncode == 0
        except (OSError, subprocess.SubprocessError):
            ok = False
    return ok
