"""Command line for the BulkEx runner.

  python app/bulkex once     one pass: rescan tables, run new requests (what Task Scheduler calls)
  python app/bulkex scan     show which tables were found as Export / Import, and why others were skipped
  python app/bulkex values   refresh the suggestion lists (country codes, units...) shown in the page
  python app/bulkex setup    the setup wizard (what CAI-DAT.bat runs)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `import bulkex` work when run as a folder

from bulkex.catalog import load_defs, scan_values  # noqa: E402
from bulkex.config import CONFIG_DIR, ConfigError, load_connection, load_settings  # noqa: E402
from bulkex.runner import Runner, log, run_with_lock, setup_logging  # noqa: E402
from bulkex.scan import scan  # noqa: E402


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):  # Vietnamese text in a Windows console
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    cmd = (argv or sys.argv[1:] or ["once"])[0]
    if cmd == "setup":
        from bulkex.setup import main as setup_main
        return setup_main()
    try:
        settings = load_settings()
        cfg = load_connection()
    except ConfigError as e:
        print(e)
        return 2
    setup_logging(settings.log_dir)
    if cmd == "once":
        n = run_with_lock(Runner(settings, cfg, CONFIG_DIR))
        print("Skipped: another pass is running." if n is None else f"Processed {n} request(s).")
        return 0
    labels, defs = load_defs(settings.app_dir)
    found, warnings = scan(cfg, defs.get("datasets") or {}, settings.databases or None)
    if cmd == "scan":
        for ds, tables in found.items():
            months = [t["period"] for t in tables]
            print(f"{ds}: {len(tables)} tables" + (f", {months[0]} .. {months[-1]}" if months else ""))
            for t in tables:
                print(f"   {t['period']}  {t['db']}.{t['schema']}.{t['table']}  ({len(t['columns'])} columns)")
        for w in warnings:
            print("NOTE:", w)
        return 0
    if cmd == "values":
        values = scan_values(cfg, found, defs)
        (CONFIG_DIR / "values.json").write_text(json.dumps(values, ensure_ascii=False, indent=1), encoding="utf-8")
        print({ds: len(v) for ds, v in values.items()}, "columns with suggestions saved to config/values.json")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - leave a trace when run hidden by Task Scheduler
        log.exception("Runner crashed")
        raise
