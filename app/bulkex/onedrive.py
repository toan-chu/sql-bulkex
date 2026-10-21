"""OneDrive "online-only" files on the database computer.

A file synced by OneDrive can sit on disk as a cloud placeholder. When Windows does not let a background
program download it, reading it fails with "[Errno 22] Invalid argument". The fix is to mark the shared
requests "Always keep on this device" (attribute +P), which is what `keep_workspace` does.
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


def _attrib(args, run):
    try:
        return run(["attrib", *args], capture_output=True, text=True, timeout=120).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def keep_workspace(ws: Path, run=subprocess.run, windows=None) -> bool:
    """On the database computer: requests and the page's files always on disk, results only in the cloud.

    input/ and _system/ are pinned so the runner can always read them. output/ is set "online-only":
    OneDrive uploads each new result and then frees the space, so big CSV files don't fill the disk.
    The workspace folder itself is not pinned (a pinned folder would pin output/ again).
    """
    if not (os.name == "nt" if windows is None else windows):
        return False
    ws = Path(ws)
    ok = _attrib(["-P", str(ws)], run)
    for sub in ("input", "_system"):
        ok = _attrib(["+P", "-U", str(ws / sub)], run) and ok
        ok = _attrib(["+P", "-U", str(ws / sub / "*"), "/S", "/D"], run) and ok
    for page in ("BulkEx.html", "Help.html"):
        ok = _attrib(["+P", "-U", str(ws / page)], run) and ok
    ok = free_up(ws / "output", run, windows) and ok
    return ok


def free_up(path: Path, run=subprocess.run, windows=None) -> bool:
    """Keep only in the cloud (OneDrive 'Free up space'). For a folder, also everything already in it."""
    if not (os.name == "nt" if windows is None else windows):
        return False
    path = Path(path)
    ok = _attrib(["-P", "+U", str(path)], run)
    if path.is_dir():
        ok = _attrib(["-P", "+U", str(path / "*"), "/S", "/D"], run) and ok
    return ok
