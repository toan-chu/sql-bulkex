# SQL BulkEx v6 — Spec (Operator Registry + Approval Workflow + OneDrive Free-Up)

> SPEC v6 canonical. v5 archived tại `docs/SPEC_v5_archived.md`.

**Status:** Canonical v6 implementation spec
**Author:** Ryan + Cowork (Claude)
**Date:** 2026-07-08
**Supersedes:** v5 hardcoded operator, `inbox/processed/` flow
**Target machine:** Máy admin **Hà Nội** (Windows 10/11, Python 3.11+, PostgreSQL client psycopg2). Không phải máy Ryan.

---

## 0. TL;DR

v6 mở rộng v5 theo 3 trục:

1. **Operator registry** — tách 5 op (eq/in/prefix/contains/between) khỏi hardcode, đưa vào `operators.yaml` với template SQL. Thêm 1 op mới `suffix` (yêu cầu manager). Excel hiển thị 6 ô toán tử tiếng Việt riêng trên mỗi dòng thay vì dropdown code cũ. Thêm operator tương lai = 1 dòng YAML, zero code change.
2. **Approval workflow không cần Power Automate** — 3 folder OneDrive `01_Pending / 02_Approved / 03_Output`. Requester upload → nhắn Zalo admin → admin drag-drop trên OneDrive mobile → runner poll `02_Approved/`. Rename `[DONE] ` sau khi chạy thay cho move `processed/`. Free up space qua OneDrive Files On-Demand để máy admin không bloat.
3. **UX cải thiện** — cột `Digits` cho prefix/suffix dùng để validate độ dài giá trị nhập (không thêm `LENGTH()` vào SQL), value dropdown khi cardinality thấp (auto-scan DB), cho phép 1 request bao cả Export + Import (output 2 sheet), track requester từ metadata + log CSV.

**Quantify diff v5 → v6:**

| Trục | v5 | v6 | Diff |
|---|---|---|---|
| Operator count | 5 hardcoded | 6 registry (5 + suffix) | +1 op, +1 file YAML, -~40 dòng hardcode |
| Excel operator UX | code text `eq/in/prefix/contains/between` | 6 ô toán tử VN riêng: Bằng / Trong danh sách / … | +readability, combine op cùng cột |
| Filter columns trong Cột Export | 3 (Toán tử, Giá trị, Lấy về?) | 8 input cột: 6 op cells + Digits + Lấy về? | +multi-op UX |
| Value input | free text | dropdown khi cardinality ≤ threshold (config) | +1 CLI `--scan-values`, +sheet `Values` |
| Dataset per request | 1 (export HOẶC import) | 1 hoặc 2 (both → 2 sheet output) | +option "both" |
| Folder flow | `inbox/` + `processed/` | `01_Pending/` + `02_Approved/` + `03_Output/` | +1 folder (approval), file rename `[DONE] ` thay move |
| Requester tracking | cell "Người yêu cầu" text tự do | + metadata `lastModifiedBy` + log CSV | +log/requests.csv structured |
| Disk cleanup | none (`processed/` giữ mãi) | Files On-Demand free up sau N giờ/ngày | +CLI `--cleanup`, +Task Scheduler job phụ |

**Ước lượng code diff (Codex thô):** runner.py +400/-200 dòng, thêm 1 file `operators.yaml`, thêm 1 module `operators.py` (registry loader + SQL builder), Excel template regen +200 dòng styling, test cases +30 cases.

**KHÔNG đổi:** portal.py, connection.yaml, .password, jobs.yaml, DB engine (PostgreSQL), core query engine.

---

## 1. Scope

**In scope:**

1. `operators.yaml` — registry 6 operator với template SQL, flag `supports_digits`, `multi_value`, `arity`
2. `operators.py` — module load registry + build WHERE clause từ template (không hardcode 5 op)
3. Excel template v6 — 6 ô toán tử VN riêng, cột `Digits`, conditional visibility Digits, dropdown value từ sheet `Values`
4. CLI mới `python runner.py --scan-values` — quét DB, sinh sheet `Values` trong template với distinct list cho cột cardinality thấp
5. Config `column.yaml` thêm 3 field: `cardinality_threshold`, `sample_size`, `skip_text_length`
6. Sheet Request thêm option `Bảng` = `both` (export + import)
7. Output 2 sheet khi Bảng = `both` (sheet `Export` + `Import` trong 1 file .xlsx)
8. 3 folder OneDrive workflow: `01_Pending / 02_Approved / 03_Output` (thay `inbox/` + `processed/`)
9. Rename `[DONE] ` prefix sau khi chạy (thay move sang `processed/`)
10. CLI mới `python runner.py --cleanup` — Files On-Demand free up space cho `[DONE] ` cũ + output cũ
11. Log CSV `log/requests.csv` — structured tracking requester, dataset, row_count, duration, status
12. Track requester qua `wb.properties.lastModifiedBy` (fallback về cell "Người yêu cầu" nếu metadata rỗng)

**Out of scope (giữ nguyên v5):**

- `portal.py` — không đổi
- `connection.yaml` + `.password` — không đổi
- Saved jobs (`jobs.yaml`, `--job`, `--list-jobs`) — không đổi
- Core query engine + expand tables + multi-year — không đổi
- Reject flow `[LOI]_` + companion `.txt` — không đổi (chỉ đổi folder)

**Non-goals:**

- Không hỗ trợ join Export ⋈ Import (both = 2 query độc lập, 2 sheet riêng)
- Không hỗ trợ OR giữa cột khác nhau (chỉ AND cross-column, đã có OR trong cùng cột qua multi-value comma)
- Không integrate Power Automate / Teams — cố tình tránh dependency M365 để repo share cho MNC

---

## 2. `operators.yaml` — Structure

**Location:** repo root, cạnh `column.yaml`.
**Git:** commit trên git (schema public, không sensitive).

**Schema đầy đủ:**

```yaml
# operators.yaml — Registry định nghĩa toán tử.
# Thêm operator mới: thêm 1 entry, restart runner. Không đụng code.
# SQL template dùng psycopg2 sql.SQL / sql.Identifier / sql.Literal composable.

operators:
  eq:
    display: "Bằng"
    hint: "1 giá trị"
    example: "CN"
    sql_single: "{col} = {val}"
    sql_multi: "{col} = ANY({vals})"       # tự chuyển sang IN khi multi-value
    multi_value: true                       # cho phép comma-separated
    arity: null                             # null = không giới hạn, số = cố định
    supports_digits: false

  in:
    display: "Trong danh sách"
    hint: "Nhiều giá trị, cách phẩy"
    example: "CN, KR, JP"
    sql_multi: "{col} = ANY({vals})"
    multi_value: true
    arity: null
    supports_digits: false

  between:
    display: "Trong khoảng"
    hint: "Đúng 2 giá trị, cách phẩy"
    example: "1000, 5000"
    sql_multi: "{col} BETWEEN {v1} AND {v2}"
    multi_value: true
    arity: 2
    supports_digits: false

  prefix:
    display: "Bắt đầu bằng"
    hint: "1 hoặc nhiều prefix, cách phẩy"
    example: "84, 85"
    sql_single: "{col} LIKE {val_prefix}"          # val_prefix = 'X%'
    sql_multi: "({col} LIKE ANY({vals_prefix}))"    # vals_prefix = ['X%','Y%']
    multi_value: true
    arity: null
    supports_digits: true                           # validate len(value) only, no SQL LENGTH

  contains:
    display: "Chứa"
    hint: "1 hoặc nhiều chuỗi, cách phẩy"
    example: "laptop, gaming"
    sql_single: "{col} LIKE {val_contains}"        # val_contains = '%X%'
    sql_multi: "({col} LIKE ANY({vals_contains}))"
    multi_value: true
    arity: null
    supports_digits: false

  suffix:
    display: "Kết thúc bằng"
    hint: "1 hoặc nhiều suffix, cách phẩy"
    example: "AA, BB"
    sql_single: "{col} LIKE {val_suffix}"          # val_suffix = '%X'
    sql_multi: "({col} LIKE ANY({vals_suffix}))"
    multi_value: true
    arity: null
    supports_digits: true                           # validate len(value) only, no SQL LENGTH

# Thứ tự 6 ô toán tử trong Excel (đảo được — display order tách khỏi định nghĩa)
display_order:
  - eq
  - in
  - between
  - prefix
  - contains
  - suffix
```

**Validation khi load `operators.yaml`:**

- Mỗi entry phải có: `display`, ít nhất 1 trong (`sql_single` / `sql_multi`), `multi_value`, `arity`, `supports_digits`
- `display_order` chứa mọi key trong `operators` (không thiếu, không thừa)
- Nếu `supports_digits: true` → parser validate mọi value part có đúng số ký tự `Digits`; SQL template vẫn dùng `sql_single/sql_multi`, không thêm `LENGTH()`
- Nếu `arity: N` → nếu multi_value=True và len(parts) != N → error

**Builder pattern (`operators.py`):**

```python
class OperatorBuilder:
    """Build WHERE clause fragment từ registry template."""

    def __init__(self, registry_path="operators.yaml"):
        self.registry = load_yaml_file(registry_path, {})
        self._validate()

    def build_where(self, col: str, op: str, val: str, digits: int | None = None):
        """
        Trả về (sql.Composable, params_dict) cho psycopg2.
        col: tên cột (safe, đã validate)
        op: key operator (eq/in/prefix/…)
        val: giá trị raw từ Excel (có thể có comma)
        digits: số nguyên hoặc None
        """
        spec = self.registry["operators"][op]
        parts = self._split(val)

        # Digits đã được validate trước đó, không đổi SQL shape.
        multi = len(parts) > 1 or spec.get("arity") not in (None, 1)
        key = "sql_multi" if multi else "sql_single"
        template_str = spec[key]

        # Compose SQL bằng psycopg2 sql.SQL + Identifier + Literal
        return self._compose(template_str, col, parts, digits)

    def display_labels(self) -> list[tuple[str, str]]:
        """Trả list (key, display) theo display_order — dùng cho 6 ô toán tử trong Excel."""
        order = self.registry["display_order"]
        return [(k, self.registry["operators"][k]["display"]) for k in order]
```

**Không hardcode:** parser trong `runner.py` gọi `builder.build_where()`, không có `if op == "eq"`. Thêm op mới = thêm entry YAML.

---

## 3. `column.yaml` — mở rộng

**Thêm 3 field:**

```yaml
datasets:
  export:
    database: vn_import/export
    schema: vietnam_export
    tables: "x_y{year}_{month}"
    columns: [...]
    # MỚI v6:
    cardinality_cache:                   # cache kết quả --scan-values
      ma_nuoc: 195                        # có 195 distinct → skip dropdown
      phuong_thuc_van_chuyen: 4           # có 4 distinct → dropdown
      ma_loai_hinh: 12                    # dropdown
      # ...
  import:
    # tương tự

operator_defaults:                       # giữ nguyên v5
  ma_nguoi_xuat_khau: prefix
  # ...

# MỚI v6 — config cardinality scan
cardinality:
  threshold: 30                          # ≤30 distinct → dropdown, >30 → free text
  sample_size: 1000                      # sample TOP N để đếm distinct nhanh
  skip_text_length: 100                  # cột text dài > N chars → skip dropdown (VD address)
  skip_columns:                          # cột explicit skip (VD ID số, quá nhiều distinct)
    - so_to_khai
    - so_van_don
```

**Validation:** `cardinality.threshold` ∈ [1, 500]. `sample_size` ∈ [100, 10000].

---

## 4. `settings.yaml` — folder + freeup config

**Schema mới:**

```yaml
# Folder workflow — 3 folder OneDrive
folders:
  pending: "C:\\Users\\admin\\OneDrive\\SQL-BulkEx-Workspace\\01_Pending"
  approved: "C:\\Users\\admin\\OneDrive\\SQL-BulkEx-Workspace\\02_Approved"
  output: "C:\\Users\\admin\\OneDrive\\SQL-BulkEx-Workspace\\03_Output"

# Runner polling
poll_seconds: 120                        # Task Scheduler chạy --once mỗi 120s
stable_wait_seconds: 5                    # đợi file ổn định trước khi đọc

# Output
filename_pattern: "{ts}_{user}_{request}"
max_rows_auto: 300000
max_rows_hard: 3000000

# OneDrive Files On-Demand free up (Windows attrib +U -P)
onedrive_freeup:
  enabled: true
  approved_delay_hours: 2                # file [DONE] > 2h → cloud-only
  output_delay_days: 7                   # output > 7 ngày → cloud-only

# Log
log:
  requests_csv: "log/requests.csv"
  runner_log: "log/runner.log"
  portal_log: "log/portal.log"
```

**Backward compat:** nếu `folders` không có, fall back về `input_dir`/`output_dir` cũ (v5) và **cảnh báo runner cần migrate**. Không tự động migrate — an toàn hơn.

---

## 5. Excel Template v6 — Changes

### 5.1. Sheet 1: `Request`

Thêm 1 row so với v5 (từ 7 → 8 rows).

| Cell A | Cell B | Validation |
|---|---|---|
| Người yêu cầu | text | required, tự động validate cross-check với `wb.properties.lastModifiedBy` |
| Bảng | dropdown: `export` / `import` / **`both`** | required |
| Năm | text (`2026`, `2025,2026`, `2025-2026`) | required |
| Tháng | text (`03`, `01,03,05`, `01-06`, `all`) | required |
| Tách file theo | dropdown union cột, hoặc trống | optional |
| Xác nhận lớn | dropdown `YES` / trống | optional |
| Ghi chú / tên request | text | required |
| **Người duyệt (Admin điền sau approve)** | text | optional — visual only, không ảnh hưởng runner |

**Behavior với `Bảng = both`:**

- Runner parse cả sheet `Cột Export` và `Cột Import`
- Chạy 2 query độc lập, output 2 sheet (`Export` + `Import`) trong 1 file .xlsx
- Filter/select rỗng ở 1 dataset → sheet đó trống (không error)
- Sheet `NOTE` gộp cả 2 dataset warnings

### 5.2. Sheet 2 + 3: `Cột Export` / `Cột Import`

**Header row (row 1):** `Cột` | `Bằng` | `Trong danh sách` | `Trong khoảng` | `Bắt đầu bằng` | `Chứa` | `Kết thúc bằng` | `Digits` | `Lấy về?`

**Data rows:** N = số cột trong `datasets.<name>.columns`.

| Cột | Bằng | Trong danh sách | Trong khoảng | Bắt đầu bằng | Chứa | Kết thúc bằng | Digits | Lấy về? |
|---|---|---|---|---|---|---|---|---|
| so_to_khai | text/dropdown | text/dropdown | text | text | text | text | conditional | dropdown |
| ma_so_hang_hoa | | | | 8471 | | | 4 | YES |

**Operator cells (B:G):**

- Không còn dropdown `Toán tử` riêng. Mỗi toán tử là 1 ô nhập giá trị riêng theo `display_order` từ `operators.yaml`.
- Có thể điền nhiều ô op cùng một dòng để tạo nhiều điều kiện AND trên cùng cột.
- Ví dụ `ma_so_hang_hoa`: `Bắt đầu bằng=84` và `Kết thúc bằng=10` → `ma_so_hang_hoa LIKE '84%' AND ma_so_hang_hoa LIKE '%10'`.
- Ô `Bằng` và `Trong danh sách` có value dropdown từ sheet `Values` nếu cột có cardinality thấp.

**Value dropdown trong các operator cells:**

- Nếu cột có entry trong `datasets.<name>.cardinality_cache` và giá trị ≤ threshold → ô `Bằng` và `Trong danh sách` có dropdown list từ sheet `Values` (named range `{col}_values`)
- Nếu > threshold hoặc cột trong `skip_columns` → free text, format Text
- Sales vẫn có thể gõ multi-value comma trong cell dropdown (Excel cho phép override)

**Data validation cột `Digits` (H2:H<N+1>):**

- Dropdown gợi ý: `2, 4, 6, 8, 10, 13`
- Parser chỉ dùng Digits với ô `Bắt đầu bằng` hoặc `Kết thúc bằng`.
- Digits validate độ dài từng giá trị nhập. Ví dụ `Bắt đầu bằng=8471`, `Digits=4` pass; `Bắt đầu bằng=84`, `Digits=4` fail.
- Digits không thêm `LENGTH(column)` vào SQL. SQL vẫn chỉ là `LIKE`.
- Allow blank

**Conditional formatting cột `Digits`:**

- Rule: nếu ô `Bắt đầu bằng` (E) và `Kết thúc bằng` (G) đều trống → background xám `#E7E6E6`, font xám nhạt `#A6A6A6`
- Visual "cell này không active"

**Conditional formatting row anchor (giữ v5):**

- Nếu bất kỳ ô toán tử nào trong `B2:G2` không rỗng → highlight row `A2:I2` bg `#FFF2CC`

**Column widths:**

- A: 35, B:G: 14, H: 10, I: 12

### 5.3. Sheet 4: `Values` (MỚI)

Sinh bởi `--scan-values`. Chứa distinct list cho các cột cardinality thấp.

**Format:** mỗi cột 1 column, header = tên cột, data từ row 2 xuống.

| ma_nuoc | phuong_thuc_van_chuyen | ma_loai_hinh | … |
|---|---|---|---|
| AF | Air | A11 | |
| AL | Ocean | A12 | |
| … | Rail | … | |

**Named range:** với mỗi cột, tạo named range `{col}_values` reference `Values!$X$2:$X$<lastrow>`. Data Validation trong Cột Export/Import reference named range đó.

**Hidden:** sheet ẩn (`sheet_state = 'hidden'`) để sales không thấy noise. Admin unhide qua Excel nếu muốn edit.

### 5.4. Sheet 5: `Tham chiếu`

**Section 1: 6 toán tử (thay 5)**

| Toán tử | Ý nghĩa | Cách nhập Giá trị | Ví dụ | Có Digits? |
|---|---|---|---|---|
| Bằng | Trùng đúng 1 giá trị | 1 giá trị | `CN` | Không |
| Trong danh sách | Thuộc 1 trong nhiều giá trị | Nhiều, cách phẩy | `CN, KR, JP` | Không |
| Trong khoảng | Nằm giữa 2 mốc (bao gồm) | Đúng 2 giá trị, cách phẩy | `1000, 5000` | Không |
| Bắt đầu bằng | Khớp phần đầu chuỗi | 1 hoặc nhiều, cách phẩy | `84, 85` | Có |
| Chứa | Xuất hiện chuỗi con | 1 chuỗi | `laptop` | Không |
| Kết thúc bằng | Khớp phần cuối chuỗi | 1 hoặc nhiều, cách phẩy | `AA, BB` | Có |

**Section 2: Digits** — MỚI

> Chỉ dùng với ô `Bắt đầu bằng` / `Kết thúc bằng`. Điền số nguyên = độ dài giá trị nhập kỳ vọng.
> Ví dụ HS Code `Bắt đầu bằng 8471` + `Digits 4` → pass và SQL là `LIKE '8471%'`.
> Ví dụ `Bắt đầu bằng 84` + `Digits 4` → reject vì value có 2 ký tự, không phải 4.
> Digits là validation input để tránh nhập sai MST/HS length; không thêm điều kiện `LENGTH(column)` vào SQL.

**Section 3: Bảng = both** — MỚI

> Nếu chọn Bảng = `both`, sales điền CẢ sheet `Cột Export` VÀ sheet `Cột Import`. Runner chạy 2 query, output 2 sheet.
> Chỉ điền 1 sheet, sheet kia trống → sheet trống ở output (không lỗi).

**Section 4, 5, 6:** giữ nguyên v5 về Tháng và logic filter/select, nhưng phần "4 cột" được thay bằng 9 cột operator-cell layout.

### 5.5. Migration display value

Runner phải parse được cả workbook v6 9 cột và workbook v5 legacy:

- v6: header `Cột` + 6 ô toán tử theo display labels trong `OperatorBuilder.display_order`.
- v5: header cũ `Cột | Toán tử | Giá trị | Lấy về?` hoặc có thêm `Digits`; parser fallback qua `OperatorBuilder.normalize_operator()` để nhận code `eq/in/prefix/...`.
- File v5 vẫn parse được, chỉ warning "template v5, khuyến khích download template v6".

---

## 6. CLI mới

### 6.1. `python runner.py --scan-values`

**Cú pháp:**

```powershell
python runner.py --scan-values
python runner.py --scan-values --dataset export
python runner.py --scan-values --dataset export --column ma_nuoc
```

**Behavior:**

Với mỗi cột trong `datasets.<name>.columns` (bỏ cột trong `skip_columns` và cột text dài):

1. Query `pg_stats` trước (nếu có ANALYZE):

    ```sql
    SELECT n_distinct FROM pg_stats
    WHERE schemaname = %s AND tablename = %s AND attname = %s
    ```

    - `n_distinct > 0` → estimated distinct count
    - `n_distinct < 0` → fraction (× row_count)
    - Không có row → fall back sample

2. Nếu `pg_stats` không có hoặc `n_distinct > threshold`:

    ```sql
    SELECT COUNT(DISTINCT {col}) FROM (
        SELECT {col} FROM {schema}.{table} LIMIT {sample_size}
    ) t
    ```

3. Nếu `distinct_count ≤ threshold`:
    - Query `SELECT DISTINCT {col} FROM {schema}.{table} ORDER BY 1 LIMIT {threshold + 5}`
    - Ghi vào `cardinality_cache[col] = distinct_count`
    - Lưu list values riêng vào `column.yaml.datasets.<name>.value_cache[col] = [...]`

4. Nếu `> threshold`:
    - Chỉ ghi `cardinality_cache[col] = <count>` để đánh dấu "skip dropdown"
    - Không lưu values

**Output:**

```
[SCAN-VALUES] dataset=export skip_columns=2 text_long=1 scanned=29
[SCAN-VALUES] dropdown_candidates=8 free_text=21
[SCAN-VALUES]   ma_nuoc: 195 distinct → free text
[SCAN-VALUES]   phuong_thuc_van_chuyen: 4 distinct → dropdown
[SCAN-VALUES]   ma_loai_hinh: 12 distinct → dropdown
[SCAN-VALUES] column.yaml đã cập nhật cardinality_cache + value_cache.
```

**Idempotent:** flag `--yes` skip confirmation. Chạy lại → refresh values.

**Cost bảo vệ:** cột không trong `columns` (drift) → skip. Query có `LIMIT sample_size` → không quét full table.

### 6.2. `python runner.py --cleanup`

**Cú pháp:** không tham số (đọc từ `settings.yaml`).

**Behavior:**

1. `folders.approved/[DONE]*.xlsx` với `mtime > approved_delay_hours` → `attrib +U -P` (cloud-only)
2. `folders.output/*.xlsx` với `mtime > output_delay_days * 24h` → `attrib +U -P`
3. Ghi log số file đã free-up
4. Nếu Windows attrib fail (OneDrive không có Files On-Demand active) → log warning, không raise error

```python
def free_up_space(path: Path) -> bool:
    """Set file to cloud-only. Return True if success."""
    try:
        result = subprocess.run(
            ["attrib", "+U", "-P", str(path)],
            check=True, capture_output=True, timeout=10
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        log_event(f"[FREEUP] Fail {path.name}: {e}")
        return False
```

**Task Scheduler task riêng:** `python runner.py --cleanup` chạy mỗi 1 giờ (config user setup).

### 6.3. `python runner.py --make-template` (mở rộng)

Regen `request_template.xlsx` v6:

- Đọc `column.yaml` (columns + cardinality_cache + value_cache)
- Đọc `operators.yaml` (display order + labels VN)
- Sinh 5 sheet: `Request`, `Cột Export`, `Cột Import`, `Values` (hidden), `Tham chiếu`
- Nếu `--scan-values` chưa chạy → `Values` sheet trống, tất cả Giá trị là free text (không dropdown)

---

## 7. Runner Logic v6

### 7.1. Load config

```python
def load_runtime():
    settings = load_settings()                          # settings.yaml
    column_cfg = load_column_config()                   # column.yaml
    op_builder = OperatorBuilder("operators.yaml")      # operators.yaml
    conn_cfg = load_connection_config()
    return settings, column_cfg, op_builder, conn_cfg
```

### 7.2. Poll folder — đổi từ `input_dir` sang `folders.approved`

```python
def request_files_v6(settings, stable_wait=5) -> list[Path]:
    approved = Path(settings["folders"]["approved"])
    files = []
    for path in sorted(approved.glob("*.xlsx")):
        # Bỏ qua file đã xử lý và file lỗi
        if path.name.startswith("[DONE] ") or path.name.startswith("[LOI]_"):
            continue
        # Bỏ qua file đang được sync bởi OneDrive
        if not is_file_stable(path, wait_seconds=stable_wait):
            continue
        files.append(path)
    return files
```

**Files trong `01_Pending/`:** runner **KHÔNG** poll. Admin phải move sang `02_Approved/` trước.

### 7.3. Process request

```python
def process_request_file_v6(path, settings, column_cfg, op_builder, conns):
    """Full flow cho 1 file request v6."""
    ts_start = time.time()

    # 1. Parse metadata + cell "Người yêu cầu"
    wb = load_workbook(path, data_only=True)
    requester_meta = wb.properties.lastModifiedBy or ""
    requester_cell = cell_text(wb["Request"]["B1"].value)
    requester = requester_cell or requester_meta or "unknown"

    # 2. Parse request
    parsed = parse_request_v6(path, column_cfg, op_builder)

    # 3. Build + execute
    if parsed["bang"] == "both":
        result_export = run_dataset("export", parsed, column_cfg, op_builder, conns)
        result_import = run_dataset("import", parsed, column_cfg, op_builder, conns)
        output_path = write_output_2sheets(settings, requester, parsed, result_export, result_import)
    else:
        result = run_dataset(parsed["bang"], parsed, column_cfg, op_builder, conns)
        output_path = write_output_1sheet(settings, requester, parsed, result)

    # 4. Rename [DONE] thay vì move sang processed/
    done_path = path.parent / f"[DONE] {path.name}"
    path.rename(done_path)

    # 5. Log CSV
    duration = time.time() - ts_start
    log_request_csv(
        settings, ts_start, requester_cell, requester_meta,
        path.name, parsed["bang"],
        row_count=sum(r["row_count"] for r in [result_export, result_import] if r) if parsed["bang"] == "both" else result["row_count"],
        duration=duration, status="success",
        output=output_path.name
    )
```

### 7.4. Log CSV `log/requests.csv`

**Header (row 1):**

```csv
timestamp,requester_cell,requester_meta,file_name,dataset,row_count,duration_sec,status,output_file,error
```

**Ví dụ:**

```csv
2026-07-08T14:30:15,Hoa,VSTREAM\\hoa.nguyen,request_hoa_20260708.xlsx,export,45230,12.3,success,20260708_hoa_HS8436.xlsx,
2026-07-08T14:45:02,,VSTREAM\\admin,request_test.xlsx,import,0,0.8,rejected,,Cột ma_nguoi_nhap_khau: giá trị thiếu
```

**Append-only.** Không rotate — user tự manage (Excel mở xem đủ trong ~1000-năm-request tại 100 req/ngày).

### 7.5. Parse 9-column operator cells + Digits

```python
def parse_column_sheet_v6_multi_op(sheet, valid_cols, op_defaults, op_builder):
    filters = []
    select_cols = []
    warnings = []
    op_keys = op_builder.display_order  # eq, in, between, prefix, contains, suffix

    for row in sheet.iter_rows(min_row=2, max_col=9, values_only=True):
        cells = [cell_text(c) for c in row]
        col = cells[0]
        op_values = {op_keys[i]: cells[i + 1] for i in range(6)}
        digits_raw = cells[7]
        out = cells[8].upper()

        if not col:
            continue
        if col not in valid_cols:
            warnings.append(f"Cột không hợp lệ trong sheet: {col}")
            continue

        digits_int = op_builder.normalize_digits(digits_raw) if digits_raw else None
        active_ops = {op: val for op, val in op_values.items() if val}

        if not active_ops:
            if out == "YES":
                select_cols.append(col)
            continue

        digits_used = False
        for op, val in active_ops.items():
            spec = op_builder.operators[op]
            digits_for_op = digits_int if spec["supports_digits"] else None
            op_builder.validate(col, op, val, digits_for_op)
            filters.append({"col": col, "op": op, "val": val, "digits": digits_for_op})
            select_cols.append(col)
            digits_used = digits_used or digits_for_op is not None

        if digits_int is not None and not digits_used:
            warnings.append(f"Cột {col}: Digits bị bỏ qua vì op active không hỗ trợ Digits")

    return filters, dedupe(select_cols), warnings
```

### 7.6. Build WHERE — dùng OperatorBuilder

```python
def build_where_clause(filters, op_builder):
    fragments = []
    all_params = {}
    for i, f in enumerate(filters):
        frag, params = op_builder.build_where(f["col"], f["op"], f["val"], f["digits"])
        # rename params với suffix _i để tránh collision
        frag = frag.format(**{k: f"{k}_{i}" for k in params.keys()})
        fragments.append(frag)
        all_params.update({f"{k}_{i}": v for k, v in params.items()})
    return sql.SQL(" AND ").join(fragments), all_params
```

### 7.7. Output 2 sheet khi Bảng=both

```python
def write_output_2sheets(settings, requester, parsed, result_export, result_import):
    output_dir = Path(settings["folders"]["output"])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    request_name = parsed["ghi_chu"].replace(" ", "_")[:50]
    fname = f"{ts}_{requester}_{request_name}.xlsx"
    path = output_dir / fname

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    ws_ex = wb.create_sheet("Export")
    write_data_to_sheet(ws_ex, result_export)

    ws_im = wb.create_sheet("Import")
    write_data_to_sheet(ws_im, result_import)

    ws_note = wb.create_sheet("NOTE")
    write_notes(ws_note, parsed, result_export, result_import)

    wb.save(path)
    return path
```

### 7.8. Reject flow (giữ v5)

Đổi folder: rename `[LOI]_` in-place trong `folders.approved/` (không phải `input_dir/` cũ). Companion `.txt` cùng folder.

**Rule:** admin move file lỗi ngược về `01_Pending/` sau khi sửa để chạy lại. Hoặc xoá `[LOI]_` prefix ngay tại `02_Approved/` để runner retry.

---

## 8. Migration v5 → v6

### 8.1. Files phải đổi

**Thêm mới:**

- `operators.yaml` (repo root)
- `operators.py` (module registry)
- `docs/SPEC_v6.md` (spec này)

**Đổi:**

- `runner.py` — hầu hết logic parse + build WHERE + folder poll + rename [DONE] + log CSV
- `column.yaml` — thêm `cardinality`, `cardinality_cache`, `value_cache` per dataset
- `settings.yaml` — thay `input_dir/output_dir` bằng `folders.pending/approved/output`, thêm `onedrive_freeup`, thêm `log`
- `request_template.xlsx` — regen v6 với 5 sheet + 6 ô toán tử VN riêng + cột Digits

**Archive (đổi tên, không xoá):**

- `docs/SPEC.md` → `docs/SPEC_v5_archived.md`
- File request v5 (11 ô cố định — không còn hiện diện) — không cần archive
- Test v5 vẫn giữ (backward compat check) + thêm test v6

### 8.2. Migration steps (admin thao tác sau merge)

1. `git pull` (branch v6)
2. Tạo 3 folder OneDrive `01_Pending / 02_Approved / 03_Output` trong `SQL-BulkEx-Workspace`
3. Update `settings.yaml`: điền đường dẫn 3 folder
4. `python runner.py --scan-columns` (giữ nguyên v5)
5. `python runner.py --scan-values` (MỚI) — mất 1-2 phút cho ~76 cột
6. Tinh chỉnh `column.yaml.cardinality.skip_columns` nếu cần
7. `python runner.py --make-template` → regen request_template.xlsx v6
8. Copy `request_template.xlsx` sang `01_Pending/` để sales tham khảo
9. Setup Task Scheduler task mới: `python runner.py --cleanup` mỗi 1 giờ
10. Test end-to-end: upload file test → move sang Approved → verify output + log CSV
11. Sau 1-2 tuần chạy ổn → giữ `docs/SPEC_v5_archived.md` để reference; chỉ dọn folder runtime cũ nếu admin xác nhận không còn dùng

### 8.3. Backward compat

- File request v5 (không có cột Digits, dùng code text `eq/in/...`) — runner v6 vẫn parse được qua parser fallback, warning "template v5, download v6"
- Setting cũ (`input_dir`/`output_dir` thay `folders`) — fall back với deprecation warning

---

## 9. Test Cases mới (bắt buộc pass)

### 9.1. Operator registry (`tests/test_v6_operators.py`)

- **T30** — Load `operators.yaml` với 6 op đầy đủ → registry.operators có 6 keys, display_order có 6 entries.
- **T31** — Load registry thiếu `display_order` → raise error rõ ràng.
- **T32** — Load registry với op mới `neq` chỉ thêm YAML entry → builder tự nhận, không đụng code.
- **T33** — `builder.validate("ma_so", "prefix", "8485", digits=4)` pass; SQL prefix không chứa `LENGTH()`.
- **T34** — `builder.validate("ma_so", "suffix", "0010", digits=4)` pass; SQL suffix không chứa `LENGTH()`.
- **T35** — `builder.build_where("gia", "between", "1000,5000")` → SQL `gia BETWEEN 1000 AND 5000`. Digits ignored (không supports).
- **T36** — Validate: `between` với 3 giá trị → error.
- **T37** — Validate: `prefix` với digits < len(val) → error.

### 9.2. Cardinality scan (`tests/test_v6_scan_values.py`)

- **T38** — pg_stats có n_distinct=4 cho `phuong_thuc_van_chuyen` → cardinality_cache=4, value_cache có 4 values.
- **T39** — Cột trong `skip_columns` → không scan, không log.
- **T40** — Cột text dài (VD `mo_ta_hang_hoa` với sample > 100 chars) → skip dropdown, log "skip text long".
- **T41** — Chạy `--scan-values` 2 lần → value_cache refresh, cardinality_cache overwrite.

### 9.3. Excel template v6 (`tests/test_v6_template.py`)

- **T42** — Sinh template → có 5 sheet (Request, Cột Export, Cột Import, Values hidden, Tham chiếu).
- **T43** — Sheet Cột Export có 9 cột header: `Cột` + 6 op display cells + `Digits` + `Lấy về?`.
- **T44** — Value dropdown chỉ áp cho ô `Bằng`/`Trong danh sách` khi cột có `value_cache`.
- **T45** — Cột Digits conditional formatting: nếu ô `Bắt đầu bằng` và `Kết thúc bằng` đều trống → cell Digits xám.
- **T46** — Sheet Values hidden, có named range cho cột `ma_nuoc` reference `Values!$A$2:$A$5` (nếu có 4 distinct).
- **T47** — Data Validation cột Giá trị của `ma_nuoc` reference named range `ma_nuoc_values`.

### 9.4. Parse VN + Digits (`tests/test_v6_parse_vn.py`)

- **T48** — Parse row có ô `Bắt đầu bằng` + `Digits` → op=`prefix`, digits giữ lại.
- **T49** — Template v5 4/5-cột vẫn fallback parser cũ và warning "template v5, khuyến khích v6".
- **T50** — Row có `Digits` nhưng chỉ active ô `Bằng` → warning Digits bị bỏ qua.
- **T51** — Row `Bắt đầu bằng=84`, `Digits=4` → RequestError vì value length không khớp Digits.

### 9.5. Both dataset (`tests/test_v6_both.py`)

- **T52** — Bảng=`both` + fill cả Cột Export + Cột Import → output có sheet Export và Import, dữ liệu đúng cả 2.
- **T53** — Bảng=`both` + chỉ fill Cột Export → sheet Export có dữ liệu, sheet Import trống (không error).
- **T54** — Bảng=`both` + cả 2 sheet trống → RequestError.

### 9.6. Folder workflow (`tests/test_v6_folders.py`)

- **T55** — File ở `01_Pending/` → runner ignore, không process.
- **T56** — File ở `02_Approved/` → runner process → rename thành `[DONE] {name}`.
- **T57** — File `[DONE] xxx.xlsx` trong `02_Approved/` → runner skip khi poll.
- **T58** — File lỗi ở `02_Approved/` → rename `[LOI]_xxx.xlsx` + companion `.txt` cùng folder.

### 9.7. Cleanup + freeup (`tests/test_v6_cleanup.py`)

- **T59** — File `[DONE] xxx.xlsx` với mtime 3h trước, config delay 2h → gọi `attrib +U -P` (mock subprocess).
- **T60** — File output với mtime 8 ngày trước, config delay 7 ngày → freeup.
- **T61** — attrib fail (OneDrive không có Files On-Demand) → log warning, không raise.

### 9.8. Log CSV (`tests/test_v6_log.py`)

- **T62** — Chạy request success → append 1 row vào `log/requests.csv` với đủ 10 cột.
- **T63** — Chạy request reject → append 1 row với status=rejected, error message.
- **T64** — File CSV không tồn tại → tạo mới với header.

### 9.9. Integration end-to-end (`tests/test_v6_e2e.py`, pgserver)

- **T65** — Full flow: upload file vào `01_Pending/` → move sang `02_Approved/` → runner --once → output có mặt trong `03_Output/` → file gốc rename `[DONE] `. Log CSV có 1 entry success.
- **T66** — Bảng=both e2e → output 2 sheet đúng.
- **T67** — Cardinality scan → make-template → generated template có 6 ô toán tử VN riêng + dropdown value cho cột cardinality thấp.

**Total v6 tests:** 38 mới. Cộng dồn với v5: ~99 test cases.

---

## 10. Build Order gợi ý cho Codex

**Step 1 — Operator registry** (~3h)

- Sinh `operators.yaml` với 6 op
- Sinh `operators.py` với class `OperatorBuilder`
- Tests T30-T37
- Refactor `runner.py` để dùng builder thay vì `validate_op_value` hardcode

**Step 2 — Cardinality scan** (~2h)

- CLI `--scan-values` với pg_stats + fallback sample
- Update `column.yaml` schema
- Tests T38-T41

**Step 3 — Excel template v6** (~4h)

- Sheet Cột Export/Import chuyển sang 9 cột: `Cột` + 6 ô toán tử VN + `Digits` + `Lấy về?`
- Sheet Values (hidden) với named range
- Sheet Tham chiếu update section 6-op + Digits + both
- Conditional formatting Digits gray-out
- Tests T42-T47

**Step 4 — Parse v6** (~2h)

- `parse_column_sheet_v6_multi_op` với 9 cột, parse nhiều op cùng dòng, validate Digits
- Backward compat với v5 code text
- Tests T48-T54 (VN + both)

**Step 5 — Folder workflow + rename [DONE]** (~2h)

- Update `settings.yaml` schema
- `request_files_v6` poll `folders.approved/`
- Rename `[DONE] ` thay move `processed/`
- Reject flow `[LOI]_` trong `02_Approved/`
- Tests T55-T58

**Step 6 — Cleanup + freeup** (~1h)

- CLI `--cleanup` với `attrib +U -P`
- Tests T59-T61

**Step 7 — Log CSV + requester tracking** (~1h)

- Init CSV với header nếu chưa có
- Append per request
- Extract `wb.properties.lastModifiedBy`
- Tests T62-T64

**Step 8 — E2E integration** (~2h)

- pgserver setup mimic export + import
- Full flow test with folder move + attrib mock
- Tests T65-T67

**Step 9 — Docs + cleanup** (~1h)

- Update README song ngữ v6 (3 folder + operator VN + Digits + cleanup)
- Archive `docs/SPEC.md` → `docs/SPEC_v5_archived.md`
- Update `docs/HUONG_DAN_SU_DUNG.md` (Cowork sau)

**Total:** 18-20h thuần Codex + Cowork review từng step.

---

## 11. Design Decisions (đã chốt với Ryan)

- **Không dùng Power Automate** — repo share MNC, PA gây rào cản. Approval qua drag-drop OneDrive mobile.
- **3 folder** thay 2 (`inbox/processed`) — approval workflow tách bạch.
- **Rename `[DONE] `** thay move sang `processed/` — 1 folder ít hơn, visual clearer, cleanup dễ.
- **OneDrive Files On-Demand `attrib +U -P`** — máy admin không bloat, file vẫn trên SharePoint.
- **Operator registry YAML** — thêm op mới zero code change.
- **6 op** = 5 v5 + suffix (yêu cầu manager). Không thêm `neq/gt/lt/gte/lte/is_null/is_not_null` — nếu cần chỉ thêm YAML entry, không đụng code.
- **Dropdown VN** trong Excel, code (eq/in/…) chỉ tồn tại nội bộ.
- **Digits conditional** — Data Validation formula + Conditional Formatting gray-out + code safety net.
- **Cardinality dropdown** — pg_stats first, sample fallback. Threshold config.
- **Both dataset per request** — output 2 sheet trong 1 file .xlsx.
- **Track requester** — cell "Người yêu cầu" + wb.properties.lastModifiedBy → log CSV structured.
- **Không SMTP notify** — requester tự nhắn admin qua Zalo/Teams DM. Zero dependency mail server.
- **Task Scheduler mode** — `--once` mỗi 120s (giữ v5) + `--cleanup` mỗi 60 phút (mới).

---

## 12. Rủi ro và mitigation

| Rủi ro | Impact | Mitigation |
|---|---|---|
| OneDrive không active Files On-Demand → `attrib +U -P` không có tác dụng | Máy admin vẫn bloat theo thời gian | Log warning; user setup Windows Storage Sense làm fallback |
| Sales cài Excel cũ (2013-) không hỗ trợ Data Validation formula phức tạp | Digits conditional không work | Fall back: parser vẫn validate → cảnh báo user upgrade Excel 2016+ |
| Admin quên move file → file mãi ở `01_Pending/` | Request bị pending vô hạn | Cronjob phụ optional: cảnh báo Zalo nếu file Pending > 24h (out of scope v6, ghi note cho v7) |
| pg_stats chưa ANALYZE → n_distinct=null hoặc sai | Cardinality scan pick sai threshold | Fall back sample. Log rõ nguồn: pg_stats vs sample |
| File request v5 gửi sang runner v6 | Không parse được vì thiếu cột Digits | Backward compat: cột Digits absent → digits=None, chạy như v5. Warning trong NOTE sheet |
| OneDrive sync delay → file poll khi chưa sync xong → data không đầy đủ | Chạy trên file dở | `is_file_stable()` (v5) đã cover; giữ nguyên |
| Sales gõ multi-value comma trong dropdown cell (override list) | Data Validation warning cell | Cho phép (Excel default) + parser xử lý multi-value |
| Admin move file sai từ `02_Approved/` về `01_Pending/` giữa lúc runner đọc | Race condition | `is_file_stable` + try/except FileNotFoundError → skip |

---

## 13. Non-scope explicit (đừng làm nhầm)

- **KHÔNG** integrate M365 Graph API, Power Automate, Teams webhook
- **KHÔNG** thêm authentication/authorization layer (single-user admin machine)
- **KHÔNG** thêm operator ngoài 6 (registry để chừa chỗ, nhưng v6 ship với 6)
- **KHÔNG** đổi engine DB (giữ PostgreSQL, không port SQL Server)
- **KHÔNG** đổi portal.py (terminal tool giữ nguyên v5)
- **KHÔNG** hỗ trợ join Export ⋈ Import (both = 2 query độc lập)

---

## 14. Verification Checklist trước khi Codex tuyên bố xong

- [ ] `operators.yaml` load được, 6 op đầy đủ, `display_order` khớp
- [ ] `python runner.py --scan-values` chạy trên pgserver → cập nhật `column.yaml` đúng
- [ ] `python runner.py --make-template` sinh `request_template.xlsx` có 5 sheet
- [ ] Template dùng 6 ô toán tử VN riêng (`Bằng` ... `Kết thúc bằng`), không còn dropdown Toán tử cũ
- [ ] Cột Digits: ô `Bắt đầu bằng`/`Kết thúc bằng` có value → cell active; op khác/trống → cell xám
- [ ] Cột `ma_nuoc` có dropdown value (nếu cardinality ≤ threshold)
- [ ] Bảng=both → output 3 sheet đúng (`Export`, `Import`, `NOTE`)
- [ ] File ở `01_Pending/` không bị process
- [ ] File ở `02_Approved/` process xong → rename `[DONE] `
- [ ] `python runner.py --cleanup` → file `[DONE]` > delay → attrib +U -P (mock check)
- [ ] `log/requests.csv` có entry đúng cột
- [ ] All tests pass: 103 passed, 4 skipped trên Windows (pgserver E2E skip expected)
- [ ] README v6 update
- [ ] `docs/SPEC.md` canonical v6, `docs/SPEC_v5_archived.md` giữ v5

---

**End of SPEC.md**
