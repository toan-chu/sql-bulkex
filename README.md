# SQL BulkEx v6

Bulk export tool for PostgreSQL customs datasets. Sales creates an Excel request, admin approves by moving the file between OneDrive folders, and the runner exports data without opening a UI.

Cong cu xuat du lieu hang loat tu PostgreSQL. Sales dien file Excel request, admin phe duyet bang cach keo file trong OneDrive, runner tu dong xuat file ket qua.

---

## 1. Quick Start / Bat Dau Nhanh

```powershell
cd C:\path\to\sql-bulkex
python runner.py --scan-columns --yes
python runner.py --scan-values --yes
python runner.py --make-template
python runner.py --once
```

Main files:

| File | Purpose |
|---|---|
| `connection.yaml` | PostgreSQL connection config, no password committed |
| `.password` | Local ignored DB password |
| `column.yaml` | Dataset schemas, scanned columns, cardinality/value cache |
| `operators.yaml` | 6 registry operators, no operator hardcode |
| `settings.yaml` | Folder paths, thresholds, cleanup/log paths |
| `request_template.xlsx` | Excel template for users |
| `log/requests.csv` | Structured request history |

---

## 2. Three-Folder OneDrive Approval / Quy Trinh 3 Folder

v6 does not use `inbox/processed`. Approval is visual and simple:

```text
SQL-BulkEx-Workspace/
  01_Pending/    Sales uploads request here
  02_Approved/   Admin moves approved files here
  03_Output/     Runner writes result files here
```

VN flow:

1. Sales dien `request_template.xlsx`.
2. Sales upload file vao `01_Pending/`.
3. Sales nhan Zalo/admin: "Em da gui request, nho anh/chị approve".
4. Admin review nhanh va keo file sang `02_Approved/`.
5. Runner chi scan `02_Approved/`, khong scan `01_Pending/`.
6. Thanh cong: file request duoc rename thanh `[DONE] original.xlsx` cung folder.
7. Loi request: file duoc rename `[LOI]_original.xlsx` va co file `.txt` giai thich.
8. Ket qua nam trong `03_Output/`.

EN flow:

1. Requester fills `request_template.xlsx`.
2. Requester uploads to `01_Pending/`.
3. Admin approves by moving the file to `02_Approved/`.
4. Runner processes approved files only.
5. Done files are renamed in place with `[DONE] `.
6. Rejected files are renamed in place with `[LOI]_` plus a companion `.txt`.
7. Output files appear in `03_Output/`.

Example `settings.yaml`:

```yaml
folders:
  pending: "C:/Users/admin/OneDrive/SQL-BulkEx-Workspace/01_Pending"
  approved: "C:/Users/admin/OneDrive/SQL-BulkEx-Workspace/02_Approved"
  output: "C:/Users/admin/OneDrive/SQL-BulkEx-Workspace/03_Output"

onedrive_freeup:
  enabled: true
  approved_delay_hours: 2
  output_delay_days: 7

log:
  requests_csv: "log/requests.csv"
  runner_log: "log/runner.log"
  portal_log: "log/portal.log"
```

Backward compatibility: old `input_dir` / `output_dir` settings still run with a deprecation warning.

---

## 3. Excel Request Template / Mau Excel

`python runner.py --make-template` creates a v6 workbook with 5 sheets:

| Sheet | Purpose |
|---|---|
| `Request` | requester, dataset, year/month, both/export/import, request name |
| `Cột Export` | export filters and output columns |
| `Cột Import` | import filters and output columns |
| `Values` | hidden low-cardinality dropdown values |
| `Tham chiếu` | operator and usage reference |

`Request` supports:

| Field | Example |
|---|---|
| Người yêu cầu | Hoa |
| Bảng | `export`, `import`, or `both` |
| Năm | `2026`, `2025,2026`, `2025-2026` |
| Tháng | `06`, `01-03`, `01,03,12` |
| Tách file theo | optional |
| Xác nhận lớn | `YES` for large exports |
| Ghi chú / tên request | short output name |
| Người duyệt | optional admin note |

---

## 4. Six Operators / 6 Toan Tu

v6 uses one input cell per operator. There is no old single `Toán tử` dropdown column.

| VN label | Code | Example | SQL meaning |
|---|---|---|---|
| Bằng | `eq` | `CN` | equals |
| Trong danh sách | `in` | `CN, KR, JP` | any of list |
| Trong khoảng | `between` | `1000, 5000` | inclusive range |
| Bắt đầu bằng | `prefix` | `8471` | `LIKE '8471%'` |
| Chứa | `contains` | `laptop, gaming` | contains any text |
| Kết thúc bằng | `suffix` | `0010` | `LIKE '%0010'` |

All operator SQL is built by `operators.yaml` + `operators.py`. Adding a future operator should be a registry change, not a runner rewrite.

---

## 5. Combine Operators On One Column / Gop Nhieu Dieu Kien Cung Cot

Because each operator is a separate cell, one row can hold multiple conditions on the same column. They combine with `AND`.

Example:

| Cột | Bắt đầu bằng | Kết thúc bằng | Digits |
|---|---:|---:|---:|
| `ma_so_hang_hoa` | `84` | `10` | |

Meaning:

```sql
ma_so_hang_hoa LIKE '84%' AND ma_so_hang_hoa LIKE '%10'
```

Use this for HS code patterns, suffix matching, or narrowing a text-like code without writing SQL.

---

## 6. Digits

Digits is a validation aid for `Bắt đầu bằng` and `Kết thúc bằng`.

Important: Digits validates the length of the value you type. It does not add `LENGTH(column)` to SQL.

Examples:

| Case | Result |
|---|---|
| `Bắt đầu bằng=8471`, `Digits=4` | accepted, SQL `LIKE '8471%'` |
| `Bắt đầu bằng=84`, `Digits=4` | rejected because `84` has 2 characters |
| `Kết thúc bằng=0010`, `Digits=4` | accepted, SQL `LIKE '%0010'` |
| `Bằng=CN`, `Digits=4` | Digits ignored with warning |

MST examples:

| MST need | How to enter |
|---|---|
| MST 10 digits prefix | `Bắt đầu bằng=0301234567`, `Digits=10` |
| MST 13 digits prefix | `Bắt đầu bằng=0301234567890`, `Digits=13` |

---

## 7. Cardinality Values / Dropdown Gia Tri

Run:

```powershell
python runner.py --scan-values --yes
```

The runner reads PostgreSQL stats first, then falls back to sampled distinct values. Low-cardinality columns are stored in `column.yaml`:

```yaml
cardinality_cache:
  ma_nuoc: 5
value_cache:
  ma_nuoc: [CN, JP, KR, US, VN]
```

When the template is regenerated, low-cardinality values go into hidden sheet `Values`, and operator cells such as `Bằng` / `Trong danh sách` get named-range dropdowns.

---

## 8. Task Scheduler: 2 Tasks

Use `pythonw.exe` for silent background runs.

Task 1: process approved requests every 2 minutes.

```powershell
schtasks /create /tn "SQL BulkEx Runner" /sc minute /mo 2 /tr "\"<PATH_PYTHONW>\" \"<PATH_REPO>\runner.py\" --once" /f
```

Task 2: free up OneDrive local disk space every hour.

```powershell
schtasks /create /tn "SQL-BulkEx-Cleanup" /sc hourly /mo 1 /tr "\"<PATH_PYTHONW>\" \"<PATH_REPO>\runner.py\" --cleanup" /st 00:30 /f
```

Useful commands:

```powershell
schtasks /query /tn "SQL BulkEx Runner"
schtasks /query /tn "SQL-BulkEx-Cleanup"
schtasks /run /tn "SQL BulkEx Runner"
schtasks /run /tn "SQL-BulkEx-Cleanup"
schtasks /change /tn "SQL BulkEx Runner" /disable
schtasks /change /tn "SQL-BulkEx-Cleanup" /disable
```

---

## 9. OneDrive Files On-Demand Cleanup

`python runner.py --cleanup` scans:

| Folder | Files | Delay |
|---|---|---|
| `folders.approved` | `[DONE] *.xlsx` and `[DONE *]*.xlsx` | `approved_delay_hours` |
| `folders.output` | `*.xlsx` | `output_delay_days` |

For each old file, it calls:

```powershell
attrib +U -P "<file>"
```

This asks OneDrive to keep the file in cloud-only state. If `attrib` fails or OneDrive is not active, the runner logs a warning and continues.

Disable cleanup:

```yaml
onedrive_freeup:
  enabled: false
```

---

## 10. Structured Log: `log/requests.csv`

Every processed request appends one row:

```csv
timestamp,requester_cell,requester_meta,file_name,dataset,row_count,duration_sec,status,output_file,error
```

Columns:

| Column | Meaning |
|---|---|
| `timestamp` | start time |
| `requester_cell` | `Request!B1` |
| `requester_meta` | Excel `lastModifiedBy` |
| `file_name` | original request file |
| `dataset` | `export`, `import`, or `both` |
| `row_count` | exported row count |
| `duration_sec` | processing time |
| `status` | `success`, `rejected`, `error` |
| `output_file` | result workbook/csv |
| `error` | rejection/error text |

The CSV is UTF-8-BOM so Excel opens Vietnamese text correctly. If Excel has the CSV locked, runner retries 3 times and logs a warning instead of crashing.

---

## 11. Common Commands

```powershell
# Scan columns from DB into column.yaml
python runner.py --scan-columns --yes

# Scan low-cardinality values into column.yaml
python runner.py --scan-values --yes

# Generate request_template.xlsx
python runner.py --make-template

# Process one polling round
python runner.py --once

# Free up old OneDrive files
python runner.py --cleanup

# Run tests
python -m pytest -q
```

---

## 12. Troubleshooting / Xu Ly Loi

| Symptom | Fix |
|---|---|
| File becomes `[LOI]_...xlsx` | Open the companion `.txt`, fix request, rename without `[LOI]_`, put back in `02_Approved/` |
| Pending file not processed | Expected. Admin must move it to `02_Approved/` |
| No dropdown values | Run `--scan-values --yes`, then `--make-template` |
| Digits rejected | Ensure the typed value length equals Digits |
| Cleanup does nothing | Check `onedrive_freeup.enabled` and OneDrive Files On-Demand |
| CSV log not updating | Close `log/requests.csv` in Excel, runner will retry next request |

---

## 13. Compatibility

- PostgreSQL only via `psycopg2`.
- v5 request workbooks still parse with a warning.
- Old `input_dir` / `output_dir` settings still work with a deprecation warning.
- `portal.py`, `.password`, `connection.yaml`, and `jobs.yaml` remain compatible.
