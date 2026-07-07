# SQL BulkEx — Hướng dẫn sử dụng (v5, column-based)

Export dữ liệu PostgreSQL không cần viết SQL. 2 lối vào:

- **`portal.py`** — menu tương tác terminal, dành cho admin DB.
- **`runner.py`** — chạy nền, quét folder OneDrive/Google Drive để nhận Excel request từ sales/MKT.

Tool chỉ đọc/ghi folder local. Không mở port DB, không gọi cloud API, không lưu password trong repo.

---

## 1. Cài đặt (làm 1 lần trên máy giữ DB)

**Yêu cầu:** Python 3.9+, PostgreSQL local truy cập được.

```powershell
git clone <repo-url> sql-bulkex
cd sql-bulkex
python -m pip install -r requirements.txt
```

**Cấu hình kết nối** — sửa `connection.yaml`:

```yaml
host: localhost
port: 5432
user: postgres
password: ""
maintenance_db: postgres
```

**Password thật** — tạo file `.password` cạnh `portal.py`, 1 dòng duy nhất:

```powershell
Set-Content .password "mat_khau_postgres"
```

File `.password` đã có sẵn trong `.gitignore`.

---

## 2. Setup column.yaml (bước quan trọng nhất, làm 1 lần)

Mở `column.yaml` — điền phần `datasets` với thông tin DB của anh:

```yaml
datasets:
  export:
    database: vn_export
    schema: vietnam_export
    tables: "x_y{year}_{month}"     # placeholder {year} {month}
    columns: []                      # tự động điền ở bước sau
  import:
    database: vn_import
    schema: vietnam_import
    tables: "i_y{year}_{month}"
    columns: []

operator_defaults: {}
```

**Quét cột thật từ DB:**

```powershell
python runner.py --scan-columns
```

Runner connect vào DB, tìm 1 bảng mẫu gần nhất (vd `x_y2026_06`), đọc `information_schema.columns`, ghi lại danh sách cột thật vào `column.yaml`.

Output ví dụ:

```
[SCAN] dataset=export sample_table=vietnam_export.x_y2026_06 → 32 columns
[SCAN] dataset=import sample_table=vietnam_import.i_y2026_06 → 44 columns
```

**Tinh chỉnh `operator_defaults`** (khuyên):

Thêm vào `column.yaml` để sales không cần chọn toán tử cho các cột phổ biến:

```yaml
operator_defaults:
  ma_nguoi_xuat_khau: prefix       # MST — cover cả 10 và 13 số
  ma_nguoi_nhap_khau: prefix
  ma_so_hang_hoa: prefix           # HS code — user thường tra theo nhóm
  mo_ta_hang_hoa: contains
  ten_nguoi_xuat_khau: contains
  ten_nguoi_nhap_khau: contains
  ten_nguoi_uy_thac_nhap_khau: contains
  ten_phuong_tien_van_chuyen: contains
```

Sales điền giá trị cột `ma_so_hang_hoa` = `8436` mà quên chọn Toán tử → runner tự áp `prefix` → SQL `LIKE '8436%'`.

**Khi nào chạy lại `--scan-columns`:**
- DB thêm/xoá cột
- Đổi tên bảng/schema
- Chạy lại là idempotent — `operator_defaults` được giữ nguyên.

---

## 3. Tạo Excel template và gửi cho sales

```powershell
python runner.py --make-template
```

Sinh `request_template.xlsx` với 4 sheet:

- **Request** — 7 ô header (Người yêu cầu, Bảng, Năm, Tháng, Tách file theo, Xác nhận lớn, Ghi chú)
- **Cột Export** — 32 dòng pre-populated tên cột Export + [Toán tử | Giá trị | Lấy về?]
- **Cột Import** — 44 dòng pre-populated cột Import + [Toán tử | Giá trị | Lấy về?]
- **Tham chiếu** — bảng giải thích 5 toán tử + cách điền Tháng

**Quan trọng:** repo là source of truth. File `request_template.xlsx` trong repo chỉ dùng để **copy sang OneDrive cho sales**, không sync trực tiếp.

```
sql-bulkex/request_template.xlsx  (repo, máy admin)
        ↓ [copy sang]
OneDrive/SQL_Requests/inbox/request_template.xlsx
        ↑ sales tại xa: copy → điền → save tên mới → thả cùng folder
```

Khi DB đổi schema → admin chạy lại `--scan-columns` + `--make-template` → copy đè file mới sang OneDrive.

---

## 4. Setup folder chia sẻ

**`settings.yaml`:**

```yaml
input_dir: "C:/Users/xxx/OneDrive/SQL_Requests/inbox"
output_dir: "C:/Users/xxx/OneDrive/SQL_Requests/results"
poll_seconds: 120
filename_pattern: "{ts}_{user}_{request}"
max_rows_auto: 300000
max_rows_hard: 3000000
```

Cả 2 folder nằm trong OneDrive/Google Drive Desktop đã sync. **Repo KHÔNG nằm trong folder sync.**

Runner tự tạo:
- `input_dir/processed/` — request đã xong
- File lỗi được rename in-place với prefix `[LOI]_` + companion `.txt` mô tả lỗi (không move đi đâu — sales thấy lỗi ngay tại folder họ vừa thả file)

---

## 5. Bật runner nền qua Task Scheduler

```powershell
schtasks /create /tn "SQL BulkEx Runner" /sc minute /mo 2 /tr "\"C:\Path\To\pythonw.exe\" \"C:\Path\To\sql-bulkex\runner.py\" --once" /f
```

Dùng `pythonw.exe` để không hiện cửa sổ console. Trigger 2 phút/lần.

---

## 6. Cách sales dùng (chỉ 3 bước)

### Bước 1 — Copy template

Sales mở folder OneDrive `SQL_Requests/inbox/` → copy `request_template.xlsx` → đổi tên (vd `hoa_20260707_khachA.xlsx`).

### Bước 2 — Điền 2 sheet

**Sheet `Request`** — điền 7 ô:

| Ô | Ví dụ |
|---|---|
| Người yêu cầu | `Hoa` |
| Bảng | `export` (dropdown) |
| Năm | `2026` hoặc `2025,2026` hoặc `2025-2026` |
| Tháng | `03` hoặc `01,03,05` hoặc `01-06` hoặc `all` |
| Tách file theo | (trống = 1 file) hoặc chọn cột (vd `ma_nuoc` để mỗi nước 1 file) |
| Xác nhận lớn | `YES` nếu biết trước data lớn |
| Ghi chú / tên request | `khachA_HS8436_thang3` |

**Sheet `Cột Export`** (hoặc `Cột Import` tuỳ Bảng đã chọn) — điền 3 cột phải với các dòng cần:

| Cột (đã điền sẵn) | Toán tử | Giá trị | Lấy về? |
|---|---|---|---|
| so_to_khai | | | YES |
| ma_nguoi_xuat_khau | prefix | `0301234567` | (auto YES) |
| ma_so_hang_hoa | | `8436` | (auto YES nếu có default) |
| ma_nuoc | eq | `CN` | (auto YES) |
| ten_nguoi_xuat_khau | | | YES |
| tri_gia_hoa_don | | | YES |
| ... | | | |

**Quy tắc:**
- **Có Toán tử + Giá trị** = filter WHERE, tự động có trong file kết quả (không cần tick Lấy về)
- **Trống Toán tử + có Giá trị** + cột có `operator_defaults` = auto áp default (vd HS code auto prefix)
- **Trống Toán tử + có Giá trị** + cột không có default = giá trị bị bỏ qua, xem sheet NOTE của file kết quả
- **Trống Toán tử + trống Giá trị + Lấy về = YES** = chỉ xuất cột này, không filter
- **Trống hết** = skip cột này

**5 toán tử:**

| Toán tử | Cách nhập | Ví dụ |
|---|---|---|
| `eq` | 1 giá trị | `CN` |
| `in` | nhiều, cách phẩy | `CN,KR,JP` |
| `prefix` | 1 hoặc nhiều prefix cách phẩy | `84,85` |
| `contains` | 1 chuỗi | `laptop` |
| `between` | đúng 2 giá trị cách phẩy | `1000,5000` |

### Bước 3 — Thả file vào inbox

Save file → OneDrive tự sync. Sau tối đa 2 phút:
- **Thành công** → file kết quả xuất hiện ở `SQL_Requests/results/`. File request gốc chuyển sang `inbox/processed/`.
- **Lỗi** → file gốc bị rename thành `[LOI]_hoa_20260707_khachA.xlsx` (vẫn ở `inbox/`) + có file `[LOI]_hoa_20260707_khachA.txt` cạnh bên chứa nội dung lỗi. Sales sửa xong đổi tên bỏ prefix `[LOI]_` (hoặc save tên mới) rồi thả lại.

---

## 7. 3 ví dụ điền Excel

### Ví dụ 1: Tra MST người xuất khẩu, lấy 5 cột

Sales muốn: tất cả tờ khai xuất của công ty có MST `0301234567`, chỉ cần 5 cột.

Sheet Cột Export:
- `ma_nguoi_xuat_khau`: Toán tử `prefix`, Giá trị `0301234567`
- `so_to_khai`: Lấy về `YES`
- `ngay_dang_ky`: Lấy về `YES` *(nếu có trong bảng)*
- `ma_so_hang_hoa`: Lấy về `YES`
- `mo_ta_hang_hoa`: Lấy về `YES`
- `tri_gia_hoa_don`: Lấy về `YES`

Kết quả: 6 cột (5 output + 1 anchor tự động).

### Ví dụ 2: Tra HS 8436 xuất sang TQ, mỗi nước 1 file

Sheet Request:
- Bảng: `export`
- Năm: `2025-2026`, Tháng: `01-06`
- Tách file theo: `ma_nuoc`

*(Cross-product 2 năm × 6 tháng = 12 bảng UNION ALL với cột `bang_nguon` đánh dấu bảng gốc.)*

Sheet Cột Export:
- `ma_so_hang_hoa`: Toán tử trống, Giá trị `8436` *(auto prefix vì có default)*
- `ma_nuoc`: Toán tử `eq`, Giá trị `CN`
- Các cột khác: Lấy về `YES` tuỳ nhu cầu

### Ví dụ 3: 10 filter AND 10 cột output

Sales cần combo phức tạp: xuất từ VN sang TQ/KR/JP, HS bắt đầu 84 hoặc 85, giá 1000-5000 USD, PTVC = đường biển...

Sheet Cột Export điền 10 dòng có Toán tử + Giá trị (auto SELECT), thêm 10 dòng chỉ tick Lấy về = YES.

Runner sinh SQL `WHERE 10 điều kiện AND` với `SELECT 20 cột`.

---

## 8. Chạy lại request cũ

1. Mở `inbox/processed/`
2. Copy file cũ về `inbox/`
3. Sửa Năm/Tháng/filter → save tên mới → sync

Không cần server giữ state. File Excel request đã điền = job có thể tái sử dụng.

---

## 9. Xử lý sự cố

| Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|
| Runner báo `column.yaml chưa có datasets` | Chưa setup column.yaml | Điền datasets rồi chạy `--scan-columns` |
| `--scan-columns` không tìm được bảng | Pattern `tables` không match | Kiểm tra tên bảng thật trong DB, sửa pattern trong column.yaml |
| Request bị `[LOI]_` | Xem file `.txt` cùng thư mục | Đọc nội dung lỗi, sửa Excel, đổi tên bỏ prefix, thả lại |
| Filter có Giá trị nhưng không filter thật | Quên set Toán tử + cột không có default | Chọn Toán tử trong dropdown |
| MST 13 số bị Excel drop số 0 đầu | Cell format Number | Format Text (template đã set sẵn) |
| Kết quả CSV thay vì xlsx | Vượt 1M dòng Excel limit | Bình thường, đọc kèm sheet NOTE |
| Chọn Bảng=Export nhưng điền sheet Cột Import | Runner đọc sai sheet | Reject với message rõ; chọn đúng bảng |

Log: `log/runner.log` (runner), `log/portal.log` (portal).

---

## 10. Bảo mật

- `connection.yaml` commit git với `password: ""`. Password thật ở `.password` (gitignore).
- `column.yaml` commit git được (không chứa secret, chỉ có tên bảng/cột).
- Không đặt repo trong folder cloud-sync.
- Share dữ liệu = share quyền truy cập folder `output_dir`.
- Máy giữ DB phải luôn bật khi giờ hành chính.

---

## 11. Portal saved jobs (dành cho admin)

Vẫn giữ nguyên từ v4. Admin dùng portal terminal query xong có thể save job:

```powershell
python portal.py                  # menu tương tác, save job trong đó
python portal.py --list-jobs      # xem job đã lưu
python portal.py --job ten_job    # chạy lại
```

`jobs.yaml` gitignore, local state.
