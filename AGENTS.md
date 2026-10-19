# SQL BulkEx agent router

SQL BulkEx lets non-SQL staff pull customs export/import data from a PostgreSQL
database that lives on one Windows machine in Hà Nội. Requests and results travel
through a shared OneDrive folder; a headless runner on the Hà Nội machine builds
safe parameterized SQL and writes the result files.

Before doing any work:

1. Read `handoff/RULES.md` and `handoff/STATE.md`.
2. Open exactly one ticket assigned to your identity in `handoff/`.
3. Read `handoff/MAP.md` only when the work touches architecture.
4. Follow `Nối tiếp` to at most one prior ticket when `Kế thừa` is insufficient.

Do not recreate `handoff/todo.md`, `handoff/audit.md`, `handoff/handoff.md`,
`log/history.md`, `log/failure.md`, or `log/sessions/`.
Do not read `handoff/archive/` unless the Chairman names a file in it.
Runtime evidence on Windows belongs to the executor with pasted commands; static review belongs to Claude.
Do not change product behavior without a ticket containing a Chairman-written acceptance scenario.
Verification command: `python -m pytest -q` (run on a copy - see RULES.md).
