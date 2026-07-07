# SQL BulkEx v5 — Spec (Column-Based Filter Model)

**Status:** Draft for Codex build
**Author:** Ryan + Cowork (Claude)
**Date:** 2026-07-07
**Supersedes:** v4 template model (`templates.yaml` + TYPE_BUILDERS)

---

## 0. TL;DR

Bỏ hoàn toàn khái niệm "template". Excel request mirror portal terminal: cùng danh sách cột thật quét từ DB, cùng 5 toán tử, cùng logic filter. Sales chọn cột (đã pre-populated) + toán tử + giá trị + lấy về. Runner không cần biết business template, chỉ resolve column-op-value từ Excel.

**Thay đổi kiến trúc:**
- **Bỏ:** `templates.yaml`, `TYPE_BUILDERS` trong `runner.py`, request_template.xlsx v4 (11 ô cố định)
- **Thêm:** `column.yaml` (auto-generated qua `--scan-columns`), CLI `--scan-columns`, request_template.xlsx v5 (4 sheet)
- **Đổi:** `--make-template` regen từ `column.yaml`, runner parse Sheet `Cột Export`/`Cột Import`

**Quantify diff:**
- Runner logic: `-200` dòng (bỏ TYPE_BUILDERS + template resolve), `+150` dòng (scan-columns + parse-sheet-columns). Net: `-50`.
- File config user maintain: từ `2` (`templates.yaml` + `settings.yaml`) → `2` (`column.yaml` + `settings.yaml`), nhưng `column.yaml` auto-gen thay vì hand-write.
- Combo query hỗ trợ: từ vài chục template hardcode → mọi combo `Cn × Op × Val` (lý thuyết `2860+` export, `4004+` import).

---

## 1. Scope

**In scope:**
- CLI `python runner.py --scan-columns` — quét DB, sinh `column.yaml`
- CLI `python runner.py --make-template` — regen `request_template.xlsx` từ `column.yaml`
- Excel template v5 với 4 sheet + styling
- Runner logic mới: parse Sheet Cột Export/Import, apply operator_defaults, validate cột × bảng
- Multi-year expand cho ô `Năm` (`2025` / `2025,2026` / `2025-2026`)
- Error handling: file lỗi rename in-place với prefix `[LOI]_`, companion `.txt` mô tả lỗi
- **Cleanup file cũ v4:** xoá `templates.yaml`, `TYPE_BUILDERS`, hàm `find_template` trong runner.py, request_template.xlsx v4 cũ. Repo phải sạch, không giữ dead code.

**Out of scope (giữ nguyên v4):**
- `portal.py` — không thay đổi (không dùng column.yaml, không đọc Excel request)
- `connection.yaml` + `.password` — giữ nguyên
- Saved jobs (`jobs.yaml`, `--job`, `--list-jobs`) — giữ nguyên
- Output pipeline (xlsx/csv/split-file, ngưỡng max_rows) — giữ nguyên
- Task Scheduler setup — giữ nguyên

**Non-goals:**
- Không hỗ trợ join cross-dataset (Export ⋈ Import)
- Không hỗ trợ OR giữa filters (chỉ AND)
- Không hỗ trợ subquery / aggregate

---

## 2. `column.yaml` — Structure

**Location:** repo root, cạnh `connection.yaml`.
**Git:** commit trên git với `datasets: {}` và `operator_defaults: {}` rỗng (skeleton). Nội dung thật auto-gen per-machine.
**Gitignore:** không gitignore (schema DB không sensitive như password).

**Schema đầy đủ:**

```yaml
datasets:
  export:
    database: vn_export
    schema: vietnam_export
    tables: "x_y{year}_{month}"      # placeholder {year} {month} hoặc *
    columns:                          # auto-populated bởi --scan-columns
      - so_to_khai
      - ma_chi_cuc_hai_quan_tao_moi
      - phuong_thuc_van_chuyen
      # ... đủ 32 cột Export
  import:
    database: vn_import
    schema: vietnam_import
    tables: "i_y{year}_{month}"
    columns:
      - so_to_khai
      # ... đủ 44 cột Import

operator_defaults:                    # optional, admin tinh chỉnh sau scan
  ma_nguoi_xuat_khau: prefix
  ma_nguoi_nhap_khau: prefix
  ma_so_hang_hoa: prefix
  mo_ta_hang_hoa: contains
  ten_nguoi_xuat_khau: contains
  ten_nguoi_nhap_khau: contains
  ten_nguoi_uy_thac_nhap_khau: contains
  ten_phuong_tien_van_chuyen: contains
# Cột không listed → không có default; user không set toán tử → warning + bỏ qua giá trị
```

**Validation khi load:**
- `datasets` phải có ≥1 key
- Mỗi dataset phải có `database`, `schema`, `tables`, `columns` (không rỗng)
- `operator_defaults` optional, giá trị ∈ `{eq, in, prefix, contains, between}`

---

## 3. CLI: `--scan-columns`

**Cú pháp:**

```powershell
python runner.py --scan-columns
python runner.py --scan-columns --dataset export      # chỉ scan 1 dataset
```

**Precondition:**
- `connection.yaml` + `.password` OK (connect được DB)
- `column.yaml` tồn tại với ít nhất phần `datasets` được điền (database, schema, tables pattern). Nếu file chưa có → tạo skeleton, print hướng dẫn:

```yaml
# column.yaml skeleton
datasets:
  export:
    database: ""      # điền tên database
    schema: ""        # điền schema
    tables: ""        # điền pattern, vd "x_y{year}_{month}"
    columns: []
operator_defaults: {}
```

Sau đó exit với message: `"Chưa điền datasets trong column.yaml. Vui lòng điền database/schema/tables rồi chạy lại."`

**Behavior:**

Cho mỗi dataset:
1. Connect vào `database` (dùng `_password` từ `connection.yaml`/`.password`)
2. Tìm 1 bảng mẫu:
   - Nếu `tables` chứa `{year}` `{month}`: build list các bảng có thể (từ năm hiện tại lùi 5 năm × 12 tháng), query `information_schema.tables` check tồn tại, pick bảng gần nhất
   - Nếu `tables` chứa `*`: `LIKE` query, pick bảng đầu tiên (order by table_name DESC)
   - Nếu `tables` là tên bảng cụ thể: query trực tiếp
3. Nếu không tìm được bảng mẫu → warning + skip dataset
4. Query cột từ bảng mẫu:
   ```sql
   SELECT column_name
   FROM information_schema.columns
   WHERE table_schema = %s AND table_name = %s
   ORDER BY ordinal_position
   ```
5. Ghi `columns:` list vào `column.yaml` cho dataset đó

**Idempotent + confirmation:**
- `operator_defaults` không bị overwrite (giữ nguyên nếu đã có)
- `datasets.<name>.database/schema/tables` không bị overwrite (chỉ update `columns`)
- Chạy lại → so sánh danh sách cột mới vs cũ, in ra diff (added/removed), hỏi confirmation `[Y/n]` trước khi ghi đè
- Flag `--yes` để bỏ qua confirmation (dùng trong CI/script)

**Assumption "schema đồng nhất cross-year":** confirmed từ user (2024-2026 giống nhau). Scan 1 bảng đủ, không union.

**Output:**
```
[SCAN] dataset=export sample_table=vietnam_export.x_y2026_06 → 32 columns
[SCAN] dataset=import sample_table=vietnam_import.i_y2026_06 → 44 columns
[SCAN] operator_defaults giữ nguyên (8 entries)
[SCAN] column.yaml đã cập nhật.
```

---

## 4. Excel Template v5 — `request_template.xlsx`

**Sinh bởi:** `python runner.py --make-template` (đọc `column.yaml` mới nhất).

### 4.1. Sheet 1: `Request`

7 ô, mỗi ô 1 row với label ở cột A, value điền cột B.

| Cell A | Cell B (nhập) | Validation |
|---|---|---|
| Người yêu cầu | text | required |
| Bảng | dropdown: `export` / `import` | required |
| Năm | text (`2026`, `2025,2026`, `2025-2026`) | required |
| Tháng | text (`03`, `01,03,05`, `01-06`, `all`) | required |
| Tách file theo | dropdown union cột Export ∪ Import, hoặc trống | optional |
| Xác nhận lớn | dropdown `YES` / trống | optional |
| Ghi chú / tên request | text | required |

**Multi-year parsing (`parse_years()`, tương tự `parse_months()` sẵn có):**
- `2026` → `[2026]`
- `2025,2026` → `[2025, 2026]`
- `2025-2026` → `[2025, 2026]`
- Không hỗ trợ `all` (tránh scan toàn bộ DB) — user phải liệt kê rõ
- Runner expand tables: cross-product Năm × Tháng. Ví dụ Năm=`2025,2026` × Tháng=`01-03` → 6 bảng (`x_y2025_01, x_y2025_02, x_y2025_03, x_y2026_01, x_y2026_02, x_y2026_03`), UNION ALL với cột `bang_nguon` đánh dấu bảng gốc.

**Styling:**
- Header cells A1-A7: bg `#1F3864`, text trắng, bold, align right
- Value cells B1-B7: bg trắng, border, format Text (chặn Excel convert số MST 13 số)
- Freeze row 1, column A
- Column A width: 30
- Column B width: 40

### 4.2. Sheet 2: `Cột Export`

**Header row (row 1):** `Cột` | `Toán tử` | `Giá trị` | `Lấy về?`

**Data rows (row 2 → 2+N):** N = số cột trong `datasets.export.columns` (32 với DB anh)

Mỗi row: cell A = tên cột đã pre-populated (locked), cell B/C/D user điền.

| Cột (locked) | Toán tử | Giá trị | Lấy về? |
|---|---|---|---|
| so_to_khai | dropdown | text | dropdown |
| ma_chi_cuc_hai_quan_tao_moi | dropdown | text | dropdown |
| ... | ... | ... | ... |

**Data validation:**
- Cột `Toán tử` (B2:B33): dropdown 6 lựa chọn — `eq`, `in`, `prefix`, `contains`, `between`, và trống
- Cột `Lấy về?` (D2:D33): dropdown 3 lựa chọn — `YES`, `NO`, trống

**Cell format:**
- Cột A (Cột): bg `#F2F2F2` (xám nhạt), font italic — **không lock** (chỉ visual, sales muốn xem chi tiết cột thoải mái)
- Cột C (Giá trị): format Text
- Cột D (Lấy về?): center align

**Conditional formatting:**
- Nếu `B2` (Toán tử) không rỗng → highlight cả row `A2:D2` với bg `#FFF2CC` (vàng nhạt) — visual hint "đây là anchor filter"

**Zebra striping:** row chẵn bg `#FAFAFA` (nếu không bị conditional format override)

**Freeze pane:** row 1

**Column widths:**
- A: 35 (tên cột dài)
- B: 18
- C: 30
- D: 12

### 4.3. Sheet 3: `Cột Import`

Giống Sheet 2 nhưng data rows lấy từ `datasets.import.columns` (44 rows với DB anh).

### 4.4. Sheet 4: `Tham chiếu`

Readonly reference cho sales. Không data validation, không formula. Chỉ text + border.

**Section 1: 5 toán tử**

| Toán tử | Ý nghĩa | Cách nhập Giá trị | Ví dụ |
|---|---|---|---|
| `eq` | Bằng đúng | 1 giá trị | `CN` |
| `in` | Trong danh sách | Nhiều, cách phẩy | `CN,KR,JP` |
| `prefix` | Bắt đầu bằng | 1 hoặc nhiều prefix, cách phẩy | `84,85` hoặc `0301234` |
| `contains` | Chứa chuỗi | 1 chuỗi | `laptop` |
| `between` | Trong khoảng | Đúng 2 giá trị, cách phẩy | `1000,5000` |

**Section 2: 4 cột trong Sheet Cột Export/Import**

| Cột | Mục đích |
|---|---|
| Cột | Tên cột DB (đã điền sẵn, không sửa được) |
| Toán tử | Cách so sánh. Để trống nếu chỉ muốn xuất cột này, không filter |
| Giá trị | Giá trị cần tìm. Bắt buộc nếu có Toán tử |
| Lấy về? | `YES` = cột này có trong file kết quả. `NO`/trống = không. Cột đã có Toán tử tự động YES. |

**Section 3: Cách điền ô `Tháng`**

| Cú pháp | Ý nghĩa |
|---|---|
| `03` | Tháng 3 |
| `01,03,05` | Tháng 1, 3, 5 (rời rạc) |
| `01-06` | Tháng 1 đến 6 (khoảng) |
| `all` | Cả 12 tháng |

**Section 4: Logic quyết định**

```
Có Toán tử + Có Giá trị       → Filter WHERE, auto SELECT
Có Toán tử + Trống Giá trị    → LỖI: thiếu giá trị
Trống Toán tử + Có Giá trị   → Nếu cột có default trong column.yaml → auto áp default
                                Nếu không → WARNING, giá trị bỏ qua
Trống Toán tử + Trống Giá trị → Xem "Lấy về?": YES = chỉ SELECT, NO/trống = skip
```

### 4.5. Styling tổng

- Header màu chủ đạo `#1F3864` (navy) + text trắng + bold
- Border: thin `#BFBFBF` toàn bộ bảng data
- Font: Calibri 11
- Print area: sheet Request + Cột Export/Import in vừa A4

**Implementation gợi ý (openpyxl):**
- `PatternFill(start_color="1F3864", end_color="1F3864", fill_type="solid")`
- `Font(color="FFFFFF", bold=True)`
- `Alignment(horizontal="center", vertical="center", wrap_text=True)`
- `DataValidation(type="list", formula1='"eq,in,prefix,contains,between"', allow_blank=True)` cho Toán tử
- `DataValidation(type="list", formula1='"YES,NO"', allow_blank=True)` cho Lấy về
- `ConditionalFormatting` với `FormulaRule(formula=['NOT(ISBLANK($B2))'], stopIfTrue=False, fill=yellow_fill)` cho highlight anchor
- Không dùng sheet protection (đã bỏ lock cell theo quyết định)

---

## 5. Runner Logic — Parse Request

### 5.1. Load config (thay đổi)

```python
def load_column_config(path=COLUMN_YAML):
    """Load column.yaml, validate datasets + columns."""
    cfg = load_yaml_file(path, {})
    datasets = cfg.get("datasets") or {}
    if not datasets:
        raise RunnerConfigError("column.yaml chưa có datasets. Chạy: python runner.py --scan-columns")
    for name, ds in datasets.items():
        for k in ("database", "schema", "tables", "columns"):
            if not ds.get(k):
                raise RunnerConfigError(f"Dataset {name} thiếu field: {k}")
    return cfg
```

### 5.2. Parse request

```python
def parse_request_v5(path, column_cfg):
    wb = load_workbook(path, data_only=True)
    
    # Sheet Request → 7 fields
    req = parse_sheet_request(wb["Request"])
    dataset_name = req["bang"].lower()  # 'export' | 'import'
    if dataset_name not in column_cfg["datasets"]:
        raise RequestError(f"Bảng không hợp lệ: {req['bang']}")
    
    dataset = column_cfg["datasets"][dataset_name]
    valid_cols = set(dataset["columns"])
    op_defaults = column_cfg.get("operator_defaults") or {}
    
    # Sheet Cột Export/Import → filter + select rules
    col_sheet_name = "Cột Export" if dataset_name == "export" else "Cột Import"
    filters, select_cols, warnings = parse_column_sheet(
        wb[col_sheet_name], valid_cols, op_defaults
    )
    
    if not filters and not select_cols:
        raise RequestError("Chưa chọn cột filter cũng chưa chọn cột lấy về.")
    
    return {
        "request": req,
        "dataset": dataset,
        "dataset_name": dataset_name,
        "filters": filters,
        "select_cols": select_cols,
        "warnings": warnings,
    }
```

### 5.3. Parse column sheet — logic trung tâm

```python
VALID_OPS = {"eq", "in", "prefix", "contains", "between"}

def parse_column_sheet(sheet, valid_cols, op_defaults):
    filters = []
    select_cols = []
    warnings = []
    
    for row in sheet.iter_rows(min_row=2, max_col=4, values_only=True):
        col, op, val, out = [cell_text(c) for c in row]
        
        if not col:
            continue
        if col not in valid_cols:
            # không nên xảy ra vì sheet pre-populated, nhưng defensive
            warnings.append(f"Cột không hợp lệ trong sheet: {col}")
            continue
        
        op = op.lower() if op else ""
        out = out.upper() if out else ""
        
        has_op = op in VALID_OPS
        has_val = bool(val)
        
        if op and not has_op:
            raise RequestError(f"Cột {col}: toán tử không hợp lệ '{op}'. Chỉ chấp nhận: {', '.join(VALID_OPS)}")
        
        # 4 case
        if has_op and has_val:
            # Filter + auto SELECT
            validate_op_value(col, op, val)
            filters.append({"col": col, "op": op, "val": val})
            if col not in select_cols:
                select_cols.append(col)
        elif has_op and not has_val:
            raise RequestError(f"Cột {col}: có toán tử '{op}' nhưng thiếu Giá trị.")
        elif not has_op and has_val:
            default_op = op_defaults.get(col)
            if default_op and default_op in VALID_OPS:
                validate_op_value(col, default_op, val)
                filters.append({"col": col, "op": default_op, "val": val})
                if col not in select_cols:
                    select_cols.append(col)
                warnings.append(f"Cột {col}: auto {default_op} (user không chọn toán tử)")
            else:
                warnings.append(f"Cột {col}: có Giá trị nhưng thiếu Toán tử và không có default. Giá trị bỏ qua.")
        else:
            # Không op, không val → xem output
            if out == "YES" and col not in select_cols:
                select_cols.append(col)
            # NO / trống → skip
    
    return filters, select_cols, warnings
```

### 5.4. Validate operator value

```python
def validate_op_value(col, op, val):
    parts = [p.strip() for p in val.split(",") if p.strip()]
    if op == "eq":
        if len(parts) != 1:
            raise RequestError(f"Cột {col}: toán tử eq cần đúng 1 giá trị, có {len(parts)}.")
    elif op == "between":
        if len(parts) != 2:
            raise RequestError(f"Cột {col}: toán tử between cần đúng 2 giá trị cách dấu phẩy, có {len(parts)}.")
    elif op == "contains":
        if len(parts) != 1:
            raise RequestError(f"Cột {col}: toán tử contains cần 1 chuỗi, có {len(parts)}.")
    elif op in ("in", "prefix"):
        if len(parts) < 1:
            raise RequestError(f"Cột {col}: toán tử {op} cần ≥1 giá trị.")
```

### 5.5. Build SQL

Sử dụng logic hiện có trong `portal.py` (build WHERE clause với 5 toán tử qua psycopg2 `sql` composable). Không thay đổi.

- `eq` → `col = %s`
- `in` → `col = ANY(%s)`
- `prefix` → `(col LIKE %s OR col LIKE %s OR ...)` với `%s` = `'X%'`
- `contains` → `col LIKE %s` với `%s` = `'%X%'`
- `between` → `col BETWEEN %s AND %s`

Tables expand: dùng `expand_tables()` từ v4 (giữ nguyên).

### 5.6. Output

- File output: `{output_dir}/{ts}_{user}_{request_name}.xlsx` (hoặc .csv nếu > 1M dòng)
- Sheet `Data`: kết quả query
- Sheet `NOTE`: chứa metadata + `warnings[]` (auto default, giá trị bỏ qua...) + timestamp + query summary

---

## 6. Error Handling

### 6.1. File reject flow

**Trước v5:** file lỗi move sang `error/` subfolder.

**v5:** rename in place trong `input_dir/`:
- File gốc: `request_hoa_20260707.xlsx` → **rename** thành `[LOI]_request_hoa_20260707.xlsx`
- Companion txt: `[LOI]_request_hoa_20260707.txt` — cùng thư mục, chứa nội dung lỗi:

```
File: request_hoa_20260707.xlsx
Timestamp: 2026-07-07 09:15:03
Người yêu cầu: Hoa
Bảng: export

LỖI:
- Cột ma_nguoi_nhap_khau không có trong bảng Export.
- Cột ma_so_hang_hoa: toán tử between cần 2 giá trị cách phẩy, có 1.

Cách xử lý:
- Mở file [LOI]_request_hoa_20260707.xlsx, sửa lại các cột lỗi.
- Đổi tên bỏ tiền tố [LOI]_ (hoặc save tên mới), thả lại vào folder.
```

**Runner scan:** bỏ qua file bắt đầu bằng `[LOI]_` khi tìm request để xử lý.

### 6.2. Success flow (giữ nguyên v4)

- File xlsx gốc → move sang `processed/`
- Kết quả → `output_dir/`

### 6.3. Warning flow

Warning không phải error — request vẫn chạy, chỉ ghi log:
- Vào file `log/runner.log` (như v4)
- Vào sheet `NOTE` của file kết quả (sales thấy ngay trong file output)

Ví dụ warning:
- `ma_so_hang_hoa: auto prefix (user không chọn toán tử)`
- `ten_phuong_tien_van_chuyen: có Giá trị nhưng không có default toán tử. Giá trị bỏ qua.`

---

## 7. Test Cases (bắt buộc pass)

### 7.1. Unit tests (`tests/test_v5_parse.py`)

1. **T1** — Scan columns: DB có 1 bảng x_y2025_06 với 32 cột → `column.yaml.datasets.export.columns` có đúng 32 cột đúng thứ tự.
2. **T2** — Scan idempotent: chạy `--scan-columns` 2 lần → `operator_defaults` giữ nguyên, `columns` refresh.
3. **T3** — Scan skeleton: `column.yaml` không tồn tại → tạo skeleton, exit với message hướng dẫn.
4. **T4** — Parse row `op=prefix, val=8436, out=trống` → filter `(ma_so_hang_hoa, prefix, 8436)` + auto SELECT `ma_so_hang_hoa`.
5. **T5** — Parse row `op=trống, val=8436, out=trống` + column.yaml có `ma_so_hang_hoa: prefix` → auto áp prefix + warning "auto prefix".
6. **T6** — Parse row `op=trống, val=8436, out=trống` + column.yaml không có default cho cột → warning "giá trị bỏ qua", KHÔNG filter.
7. **T7** — Parse row `op=eq, val=trống` → RequestError "thiếu giá trị".
8. **T8** — Parse row `op=between, val=1000` (1 phần) → RequestError "cần đúng 2 giá trị".
9. **T9** — Parse row `op=between, val=1000,5000` → filter OK.
10. **T10** — Parse row `op=between, val=1000,5000,9000` (3 phần) → RequestError.
11. **T11** — Parse row `op=trống, val=trống, out=YES` → chỉ SELECT, không filter.
12. **T12** — Parse row `op=eq, val=CN, out=NO` → override NO, cột vẫn có trong SELECT.
13. **T13** — Sheet Cột Export có 2 anchor + 3 output-only + 27 trống → filters=2, select_cols=5.
14. **T14** — Toàn sheet trống (0 filter, 0 YES) → RequestError "chưa chọn gì".
15. **T15** — Bảng = "export" → đọc sheet Cột Export, không đọc Cột Import.
16. **T16** — Cột trong sheet nhưng không có trong `datasets.export.columns` (DB drift) → warning "cột không hợp lệ".
17. **T17** — Toán tử không hợp lệ (vd `starts` thay `prefix`) → RequestError.

### 7.2. Reject flow tests (`tests/test_v5_reject.py`)

18. **T18** — File bị reject → rename thành `[LOI]_{original}.xlsx` + tạo `[LOI]_{original}.txt` với nội dung lỗi.
19. **T19** — Runner scan → skip file có prefix `[LOI]_`.

### 7.2b. Multi-year tests

19b. **T19b** — `parse_years("2025,2026")` → `[2025, 2026]`.
19c. **T19c** — `parse_years("2025-2026")` → `[2025, 2026]`.
19d. **T19d** — Cross-product Năm × Tháng: `2025,2026` × `01-03` → 6 bảng expand.
19e. **T19e** — `parse_years("all")` → RequestError (không hỗ trợ).

### 7.3. Integration tests (`tests/test_v5_e2e.py`, pgserver)

20. **T20** — Case đơn giản: `--scan-columns` → `--make-template` → fill sheet Request + Cột Export (2 anchor + 20 output) → runner --once → output xlsx có đúng 20+2 cột, đúng số dòng match filter.
21. **T21** — Case complex: 10 anchor + 10 output riêng → SQL sinh ra 10 filter AND + 20 cột SELECT.
22. **T22** — Case auto default: điền chỉ Giá trị cột `ma_so_hang_hoa` = 8436, không set Toán tử → SQL LIKE '8436%'.

### 7.4. Excel template tests (`tests/test_v5_template.py`)

23. **T23** — `--make-template` → sinh xlsx có đủ 4 sheet với tên đúng.
24. **T24** — Sheet Cột Export có số dòng = số cột trong `datasets.export.columns` + 1 (header).
25. **T25** — Data validation Toán tử có đủ 5 options + allow_blank.
26. **T26** — Column A của Cột Export/Import locked (không cho edit).
27. **T27** — Conditional formatting: row có Toán tử được highlight.

---

## 8. Migration + Cleanup từ v4

**Cleanup checklist (Codex thực hiện, xoá triệt để, không giữ dead code):**

Files phải xoá:
- `templates.yaml` — thay hoàn toàn bằng `column.yaml`
- `request_template.xlsx` (v4, 5767 bytes hiện tại) — sẽ được regen bởi `--make-template` v5

Code phải xoá trong `runner.py`:
- Dict `TYPE_BUILDERS` (mapping template type → builder function)
- Function `find_template()` và các hàm phụ chỉ dùng cho template model
- Function `validate_templates()`
- Import/reference đến `TEMPLATES_FILE`
- CLI flag hoặc branch code chỉ chạy khi template model active

Files có thể review lại:
- `docs/SPEC.md` v4 (nếu có) — xoá hoặc rename thành `SPEC_v4_archived.md`
- `handoff/HANDOFF.md` — cập nhật nếu references template model

**Migration user flow (không phải Codex làm):**

- Saved jobs (`jobs.yaml`) từ v4: vẫn dùng được với `portal.py --job` (không đụng column-based flow, không thay đổi).
- Request Excel v4 (11 ô cố định): user gửi vào input_dir → runner v5 không nhận diện (thiếu sheet Cột Export/Import) → reject với message hướng dẫn download template mới.

**Admin thao tác sau khi Codex merge:**
1. `git pull` (branch v5)
2. Điền `datasets` trong `column.yaml` (skeleton có sẵn trong repo)
3. `python runner.py --scan-columns` (auto điền `columns`)
4. Tinh chỉnh `operator_defaults` trong `column.yaml` theo gợi ý section 2
5. `python runner.py --make-template` (regen `request_template.xlsx`)
6. Copy `request_template.xlsx` sang OneDrive, thông báo sales dùng file mới

---

## 9. File flow (không đổi so với v4)

```
sql-bulkex/ (repo, máy admin)
├─ request_template.xlsx  ← source of truth
│
[admin copy sang]
├─ OneDrive/SQL_Requests/inbox/
│    ├─ request_template.xlsx
│    ├─ [user drop] hoa_20260707_HS8436.xlsx  ← sales điền và thả vào
│    ├─ [LOI]_hoa_20260707_bad.xlsx           ← nếu lỗi
│    └─ [LOI]_hoa_20260707_bad.txt            ← log lỗi cạnh file
├─ OneDrive/SQL_Requests/inbox/processed/     ← file đã xong
└─ OneDrive/SQL_Requests/results/             ← kết quả sync về sales
```

Runner Task Scheduler `python runner.py --once` mỗi 2 phút (không đổi).

---

## 10. Build order gợi ý cho Codex

**Step 1** — `column.yaml` + `--scan-columns`:
- Sinh skeleton nếu chưa có
- Query `information_schema.columns`
- Ghi lại yaml preserving `operator_defaults`
- Tests T1, T2, T3

**Step 2** — Parse column sheet + validate:
- `parse_column_sheet()` với 4-case logic
- `validate_op_value()` cho `between`
- Tests T4-T17

**Step 3** — Excel template regen:
- `--make-template` đọc `column.yaml`, sinh 4 sheet với styling
- Data validation + conditional formatting + cell lock
- Tests T23-T27

**Step 4** — Reject flow rename in-place:
- Đổi từ move sang error/ → rename `[LOI]_` prefix + companion txt
- Scan skip `[LOI]_`
- Tests T18, T19

**Step 5** — E2E integration:
- Setup pgserver với schema thực (export + import)
- Full flow --scan-columns → --make-template → fill → --once → verify output
- Tests T20-T22

**Step 6** — Cleanup:
- Xoá `templates.yaml` + `TYPE_BUILDERS` khỏi runner.py
- Update README.md song ngữ với column-based flow
- Update `docs/HUONG_DAN_SU_DUNG.md` (Cowork lo phần này)

---

## 11. Rủi ro và mitigation

| Rủi ro | Impact | Mitigation |
|---|---|---|
| Schema DB drift giữa các bảng cross-year | User chọn cột không có trong bảng năm cũ → SQL error | Runner check với `information_schema` khi expand tables, warning cột thiếu |
| Sales chọn Bảng=Export nhưng điền sheet Cột Import | Runner ignore sheet Import → filter/select rỗng → reject | Message rõ ràng: "Bạn chọn Bảng=Export nhưng chỉ điền sheet Cột Import." |
| Excel cell format số làm mất số MST đầu bằng 0 | MST `0301234567` bị Excel drop thành `301234567` | Format Text toàn bộ cột `Giá trị` (đã plan trong styling) |
| User sửa cell locked Cột A (bung protection) | Sai tên cột → không match DB | Runner validate cột vs `datasets.<name>.columns`, reject nếu mismatch |
| `--scan-columns` không tìm được bảng mẫu | column.yaml không update | Log rõ tên pattern search, gợi ý user check năm/tháng bảng hiện có |

---

## 12. Estimate build time

Codex effort (thô, không guarantee):
- Step 1 (scan-columns): ~1-2h
- Step 2 (parse logic): ~2-3h
- Step 3 (Excel template): ~3-4h (styling + validation phức tạp)
- Step 4 (reject flow): ~1h
- Step 5 (E2E): ~2h
- Step 6 (cleanup + docs): ~1h

**Total: 10-13h thuần Codex + Cowork review từng step.**

---

## 13. Design decisions (đã chốt)

- **Không lock cell Cột A** — chỉ format visual (bg xám + italic). Sales tự do click/copy.
- **Sheet `Tham chiếu` để cuối** — không ảnh hưởng UX, thứ tự sheet: `Request` → `Cột Export` → `Cột Import` → `Tham chiếu`.
- **`--scan-columns` có confirmation** — in diff cột mới vs cũ, hỏi `[Y/n]` trước khi overwrite. Flag `--yes` để skip cho automation.
- **Multi-year** — ô Năm chấp nhận `2026`, `2025,2026`, `2025-2026`. Không hỗ trợ `all` cho năm (bảo vệ khỏi accidental full-DB scan).

Nếu Codex gặp ambiguity mới trong quá trình build, dừng lại và ping Cowork/Ryan.

---

**End of SPEC_v5.md**
