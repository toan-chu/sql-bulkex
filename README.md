# SQL BulkEx

SQL BulkEx helps non-technical requestors export PostgreSQL data without writing SQL. It has two entry points:

- `portal.py`: interactive terminal portal for the database owner/admin.
- `runner.py`: headless request watcher for a shared local sync folder such as OneDrive or Google Drive Desktop.

The tool reads and writes local folders only. It does not open a database port, call a cloud API, or store credentials in the repo.

## Quick Start

1. Clone the repo and install dependencies:

```powershell
python -m pip install -r requirements.txt
```

2. Edit `connection.yaml` on the machine that can access PostgreSQL. Keep `password: ""` for public git.

3. Create `.password` next to `portal.py` and put the PostgreSQL password on the first line:

```powershell
Set-Content .password "your_postgres_password"
```

4. Edit `templates.yaml`. Each repeated request type should become one template. The request form's `Cột cần lấy` field is only for one-off column overrides.

5. Edit `settings.yaml` so `input_dir` points to the shared request folder and `output_dir` points to the shared result folder.

6. Generate the blank request form:

```powershell
python runner.py --make-template
```

Send `request_template.xlsx` to the team. They fill one request per file and drop it into `input_dir`.

7. Register the scheduled runner using Task Scheduler.

## Chạy Nền Bằng Task Scheduler

Use `pythonw.exe` so no console window appears. Adjust paths before running:

```powershell
schtasks /create /tn "SQL BulkEx Runner" /sc minute /mo 2 /tr "\"C:\Path\To\pythonw.exe\" \"C:\Path\To\sql-bulkex\runner.py\" --once" /f
```

Bạn cũng có thể tạo trigger "At log on" trong Task Scheduler và đặt repeat every 2 minutes.

## Chạy Lại Request Cũ

1. Open the shared `processed/` folder.
2. Copy an old completed request file back to the request folder.
3. Edit values such as month, filters, or note, then save it as a new `.xlsx`.

File request cũ đã điền chính là job có thể tái sử dụng. Server không giữ state riêng cho requestor.

## Request Quá Lớn Thì Làm Gì

If a request is moved to `error/` with a message saying the query is too large:

1. Prefer narrowing filters or splitting the request.
2. If the size is expected and below the hard cap, fill `Xác nhận dữ liệu lớn` with `YES` and submit again.
3. If it is above the hard cap, the runner will reject it even with `YES`; split or filter the request.

Kết quả vượt giới hạn số dòng của Excel sẽ tự chuyển sang CSV và có file ghi chú đi kèm.

## Security

- Keep `connection.yaml` committed with `password: ""`; put the real password in local `.password`.
- `.password` is ignored by git and must never be committed.
- `jobs.yaml` is local state and is ignored by git.
- Do not place this repo itself inside the shared cloud-sync folder.
- Share access to exported data by controlling access to the sync folder.

## Portal Saved Jobs

Admins can save an interactive portal state after choosing `export` or `queue`. Saved jobs go to local `jobs.yaml` and are independent from requestor Excel files:

```powershell
python portal.py --list-jobs
python portal.py --job job_name
```

`--job` reads `job_export_format` from `connection.yaml` and defaults to `xlsx`.

## English Quick Start

1. Install dependencies: `python -m pip install -r requirements.txt`.
2. Fill local PostgreSQL host/user settings in `connection.yaml`, keeping `password: ""`.
3. Create `.password` with the database password on the first line.
4. Define request types in `templates.yaml`.
5. Point `input_dir` and `output_dir` in `settings.yaml` to shared sync folders.
6. Run `python runner.py --make-template`, share `request_template.xlsx`, and schedule `pythonw.exe runner.py --once` every 2 minutes.
