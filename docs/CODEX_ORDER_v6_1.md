# CODEX ORDER v6.1 — 4 fix nhỏ (free-up CSV, user dropdown, cột Hướng dẫn, ILIKE)

**Ngày:** 2026-07-14
**Scope:** runner.py, operators.yaml, .gitignore. KHÔNG đụng portal.py, setup.py, core query engine.
**Sau khi sửa xong:** chạy full pytest, regen template `python runner.py --make-template`, commit template mới.

---

## Fix 1 — Free up 03_Output phải bao gồm .csv

**Bug:** `output_cleanup_candidates()` (runner.py ~line 1681) glob `*.xlsx`, nhưng output > XLSX_ROW_LIMIT bị force sang `.csv` (line ~1593) → file nặng nhất không bao giờ được free up.

**Sửa:**
```python
def output_cleanup_candidates(settings, now=None):
    root = output_dir(settings)
    ...
    for path in sorted(p for p in root.iterdir() if p.is_file() and p.suffix.lower() in (".xlsx", ".csv")):
        yield path, path.stat().st_mtime <= cutoff
```

**Test:** thêm case vào test hiện có của cleanup — tạo 1 file `.csv` cũ trong output dir, assert nó nằm trong candidates. Giữ nguyên logic `done_cleanup_candidates` (02_Approved chỉ có .xlsx).

---

## Fix 2 — Dropdown "Người yêu cầu" từ bảng Tham chiếu

**Yêu cầu:** Admin gen template xong sẽ điền danh sách tên sales vào sheet `Tham chiếu`, cell B1 sheet `Request` dropdown từ danh sách đó. Template gửi đi là ready-to-use.

**Sửa:**

1. `setup_reference_sheet()` (runner.py ~line 2041): thêm section cuối sheet — header `"Danh sách người yêu cầu (Admin điền)"`, bên dưới chừa sẵn **30 dòng trống** (border + fill trắng để admin biết chỗ điền). Tạo named range `nguoi_yeu_cau_list` trỏ vào 30 dòng đó (dùng pattern named range sẵn có của value dropdowns).
2. `setup_request_sheet()` (runner.py ~line 1934): thêm data validation cho `B1` từ named range `nguoi_yeu_cau_list`, `allow_blank=True`, `errorStyle="information"` — KHÔNG hard-block, vì admin có thể chưa điền hoặc user gõ tay tên mới.
3. Parse phía runner không đổi — B1 vẫn đọc text như cũ.

**Test:** T-mới — gen template, assert workbook có defined name `nguoi_yeu_cau_list` và B1 có data validation trỏ named range đó.

---

## Fix 3 — Cột "Hướng dẫn" trong sheet Request

**Yêu cầu:** thêm cột C = hướng dẫn ngắn cho từng dòng, sales đọc nhanh không cần mở HUONG_DAN_SU_DUNG.md.

**Sửa `setup_request_sheet()`:**

1. Thêm dict hint theo đúng thứ tự `REQUEST_V6_LABELS_ORDER` (line ~65). Nội dung (khớp docs/HUONG_DAN_SU_DUNG.md, đối chiếu lại parse logic nếu nghi ngờ):

| Dòng | Hint cột C |
|---|---|
| Người yêu cầu | Chọn tên từ dropdown. Không có tên → gõ tay. |
| Bảng | export / import / both. both = kết quả 2 sheet. |
| Năm | VD: 2026 hoặc 2025,2026 hoặc 2025-2026 |
| Tháng | VD: 06 hoặc 01-03 hoặc 01,03,12 |
| Tách file theo | Để trống nếu không biết. |
| Xác nhận lớn | Chỉ điền YES khi admin yêu cầu. |
| Ghi chú / tên request | Tên ngắn không dấu, VD: hs8471_cn |
| Người duyệt (Admin điền sau approve) | Sales bỏ trống dòng này. |

2. Cột C: width 45, font italic, màu xám (`808080`), wrap_text, không border đậm — nhìn là biết chú thích, không phải ô nhập.
3. Update `print_area` = `A1:C8`, giữ freeze_panes.

**Test:** update test template hiện có — assert C1:C8 có text, C2 chứa "both".

---

## Fix 4 — LIKE → ILIKE (tìm không phân biệt hoa thường)

**Bug:** PostgreSQL `LIKE` phân biệt hoa thường → sales gõ `mAsAn` không match `MASAN`. 

**Sửa `operators.yaml`** (lines 34-55): đổi toàn bộ `LIKE` → `ILIKE` trong `sql_single`/`sql_multi` của 3 op `prefix`, `contains`, `suffix` (6 chỗ). Không đụng `eq`/`in`/`between`.

**Sửa `setup_reference_sheet()`:** cột "Ý nghĩa" của 3 op này thêm "(không phân biệt hoa thường)".

**Test:** unit test build WHERE clause cho contains → assert SQL chứa `ILIKE`. Nếu có integration test pgserver: insert `MASAN`, filter contains `masan`, assert 1 row.

---

## Fix 5 — .gitignore config theo máy (làm TRƯỚC khi push)

**Bug:** 3 file config theo từng máy đang bị git track → pull về máy admin sẽ đè config bên đó:
- `settings.yaml` — path OneDrive local
- `connection.yaml` — host/port/db (SQL 2 máy khác nhau)
- `column.yaml` — scan cache theo DB từng máy

**Sửa:**
```
# thêm vào .gitignore
settings.yaml
connection.yaml
column.yaml
```
```bash
git rm --cached settings.yaml connection.yaml column.yaml
```
Thêm `connection.example.yaml` (placeholder, không credentials). KHÔNG cần settings/column example — `setup.py` tự gen `settings.yaml` (hàm `write_settings`), `runner.py --scan-columns` tự gen `column.yaml`. Update README/HUONG_DAN: máy mới sau pull = chạy `setup.bat` + copy connection.example → connection.yaml + `--scan-columns`.

---

## Thứ tự thực hiện

1. Fix 5 (gitignore) → 2. Fix 1 → 3. Fix 4 → 4. Fix 2 → 5. Fix 3 → 6. Full pytest → 7. `--make-template` regen → 8. Append audit/history theo protocol cũ, stop for review.

**Quantify diff dự kiến:** runner.py ~+70/-5 dòng, operators.yaml 6 dòng sửa, .gitignore +1, +1 file settings.example.yaml, tests +4 case.
