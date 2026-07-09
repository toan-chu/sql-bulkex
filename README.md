# 📊 SQL BulkEx

> **Export PostgreSQL data through Excel — no SQL required.**
> Xuất dữ liệu PostgreSQL qua Excel — không cần viết SQL.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)](https://www.python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-supported-336791.svg)](https://www.postgresql.org)

---

## 🎯 Vấn đề giải quyết

Doanh nghiệp có 1 người biết SQL (thường là data analyst / IT). Cả team sales/marketing/vận hành cần data lẻ tẻ mỗi ngày → nghẽn 1 người, chờ đợi, mệt cả 2 phía.

**SQL BulkEx tách nút thắt đó:**

- 👤 **Sales/MKT** điền request qua Excel (chọn cột, điền giá trị, thả vào OneDrive)
- 🖥️ **Máy giữ DB** tự đọc request, query, xuất Excel/CSV về OneDrive
- 📁 **Không server, không mở port, không API cloud** — chỉ dùng folder sync sẵn có

---

## ✨ Điểm chính

| Tính năng | Mô tả |
|---|---|
| 🎯 **Column-based filter** | Chọn cột từ danh sách thật quét từ DB, không hardcode template |
| 📋 **5 toán tử** | `eq` / `in` / `prefix` / `contains` / `between` |
| 🔮 **Auto-default operator** | HS code auto `prefix`, MST auto `prefix` (10 và 13 số), mô tả auto `contains` |
| 📅 **Multi-year** | `2025,2026` hoặc `2025-2026` — cross-product với tháng |
| 🗂️ **Excel 4 sheet** | Request → Cột Export → Cột Import → Tham chiếu |
| 🚫 **Reject in-place** | File lỗi rename `[LOI]_*.xlsx` + `.txt` giải thích, ngay tại folder user thả |
| 🔒 **Password local-only** | `.password` gitignored, không đụng cloud |
| ⚙️ **Task Scheduler** | Chạy nền `pythonw.exe`, không hiện console |

---

## 🏗️ Kiến trúc

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
│  Sales / MKT    │       │   OneDrive /     │       │  Máy giữ DB     │
│                 │       │   Google Drive   │       │  (Admin)        │
│  📄 Excel       │       │                  │       │                 │
│  request        │──────►│  📁 inbox/       │──────►│  🐍 runner.py   │
│                 │       │                  │       │                 │
└─────────────────┘       │  📁 results/     │◄──────│  🗄️ PostgreSQL  │
                          │                  │       │                 │
                          └──────────────────┘       └─────────────────┘
```

**Không tunnel, không API, không port.** Nút chai là folder sync — sales bỏ Excel, admin's runner đọc, xuất kết quả về folder cùng sync.

---

## 🚀 Cài đặt cho Admin

**Yêu cầu:** Python 3.9+, PostgreSQL local truy cập được.

### 1. Clone và cài dependency

```powershell
git clone https://github.com/YOUR_USERNAME/sql-bulkex.git
cd sql-bulkex
python -m pip install -r requirements.txt
```

### 2. Cấu hình kết nối

Sửa `connection.yaml` (giữ password rỗng để commit an toàn):

```yaml
host: localhost
port: 5432
user: postgres
password: ""
maintenance_db: postgres
```

Tạo `.password` cạnh `runner.py` (đã có trong `.gitignore`):

```powershell
Set-Content .password "mat_khau_postgres"
```

### 3. Điền `column.yaml` với thông tin DB

```yaml
datasets:
  export:
    database: vn_export
    schema: vietnam_export
    tables: "x_y{year}_{month}"     # placeholder {year} {month}
    columns: []                       # để trống, sẽ auto-fill ở bước sau
  import:
    database: vn_import
    schema: vietnam_import
    tables: "i_y{year}_{month}"
    columns: []
```

### 4. Quét cột thật từ DB

```powershell
python runner.py --scan-columns --yes
```

Runner tìm bảng mẫu gần nhất, đọc `information_schema.columns`, ghi vào `column.yaml`.

### 5. (Tuỳ chọn) Thêm operator defaults

Sales sẽ ít phải chọn toán tử hơn nếu admin set default sẵn:

```yaml
operator_defaults:
  ma_nguoi_xuat_khau: prefix       # MST — cover cả 10 và 13 số
  ma_nguoi_nhap_khau: prefix
  ma_so_hang_hoa: prefix           # HS code — user hay tra theo nhóm
  mo_ta_hang_hoa: contains
  ten_nguoi_xuat_khau: contains
  ten_nguoi_nhap_khau: contains
```

### 6. Trỏ folder OneDrive/GDrive trong `settings.yaml`

```yaml
folders:
  pending: "C:/Users/xxx/OneDrive/SQL-BulkEx-Workspace/01_Pending"
  approved: "C:/Users/xxx/OneDrive/SQL-BulkEx-Workspace/02_Approved"
  output: "C:/Users/xxx/OneDrive/SQL-BulkEx-Workspace/03_Output"
poll_seconds: 120
max_rows_auto: 300000
max_rows_hard: 3000000
onedrive_freeup:
  enabled: true
  approved_delay_hours: 2
  output_delay_days: 7
log:
  requests_csv: "log/requests.csv"
  runner_log: "log/runner.log"
  portal_log: "log/portal.log"
```

Workflow:
- Sales copy file request vào `01_Pending`.
- Admin review rồi kéo file sang `02_Approved`.
- Runner chỉ quét `02_Approved`; file ở `01_Pending` không bị xử lý.
- Kết quả xuất ra `03_Output`.

### 7. Sinh Excel template cho sales

```powershell
python runner.py --make-template
```

Copy file `request_template.xlsx` sang folder OneDrive `01_Pending/` cho sales.

### 8. Bật runner nền qua Task Scheduler

Runner cần chạy tự động mỗi 2 phút. Windows có sẵn Task Scheduler làm việc này — không cần cài gì thêm.

#### 8.1. Tìm 2 path cần thay vào lệnh

Mở **PowerShell** (Start → gõ "PowerShell" → Enter), chạy 2 lệnh:

```powershell
# Path pythonw.exe (Python chạy không hiện console)
Get-Command pythonw | Select-Object Source

# Path repo sql-bulkex
cd "C:\Users\<TÊN_USER>\Downloads\GIT\sql-bulkex"
$PWD.Path
```

Ghi lại 2 kết quả in ra. Ví dụ:
- pythonw: `C:\Users\RYAN TOAN\AppData\Local\Programs\Python\Python313\pythonw.exe`
- repo: `C:\Users\RYAN TOAN\Downloads\GIT\sql-bulkex`

> **Nếu `Get-Command pythonw` báo lỗi** — chưa cài Python hoặc chưa add vào PATH. Cài lại Python từ [python.org](https://www.python.org/downloads/), tick **"Add Python to PATH"** trong installer.

#### 8.2. Tạo task runner chạy mỗi 2 phút

Dán lệnh sau vào PowerShell, thay 2 path bằng path anh vừa lấy:

```powershell
schtasks /create /tn "SQL BulkEx Runner" /sc minute /mo 2 /tr "\"<PATH_PYTHONW>\" \"<PATH_REPO>\runner.py\" --once" /f
```

Ví dụ với path thật:

```powershell
schtasks /create /tn "SQL BulkEx Runner" /sc minute /mo 2 /tr "\"C:\Users\RYAN TOAN\AppData\Local\Programs\Python\Python313\pythonw.exe\" \"C:\Users\RYAN TOAN\Downloads\GIT\sql-bulkex\runner.py\" --once" /f
```

Ý nghĩa flag:

| Flag | Ý nghĩa |
|---|---|
| `/tn` | Tên task (viết trong ngoặc kép nếu có dấu cách) |
| `/sc minute /mo 2` | Chạy mỗi 2 phút |
| `/tr` | Command chạy (pythonw + script + arg `--once`) |
| `/f` | Force overwrite nếu task cùng tên đã tồn tại |

Sau khi chạy, PowerShell in ra: `SUCCESS: The scheduled task "SQL BulkEx Runner" has successfully been created.`

#### 8.3. Tạo task cleanup chạy mỗi 1 giờ

Task cleanup chuyển file `[DONE]` cũ và output cũ sang trạng thái cloud-only của OneDrive Files On-Demand, giúp máy admin không phình dung lượng.

```powershell
schtasks /create /tn "SQL-BulkEx-Cleanup" /sc hourly /mo 1 /tr "\"<PATH_PYTHONW>\" \"<PATH_REPO>\runner.py\" --cleanup" /st 00:30 /f
```

Ví dụ với path thật:

```powershell
schtasks /create /tn "SQL-BulkEx-Cleanup" /sc hourly /mo 1 /tr "\"C:\Users\RYAN TOAN\AppData\Local\Programs\Python\Python313\pythonw.exe\" \"C:\Users\RYAN TOAN\Downloads\GIT\sql-bulkex\runner.py\" --cleanup" /st 00:30 /f
```

Cleanup đọc `settings.yaml -> onedrive_freeup`. Nếu `enabled: false`, lệnh thoát thành công và không đụng file nào.

#### 8.4. Kiểm tra runner đang chạy

```powershell
# Xem task tồn tại
schtasks /query /tn "SQL BulkEx Runner"
schtasks /query /tn "SQL-BulkEx-Cleanup"

# Runner chỉ poll folder settings.yaml -> folders.approved
# File ở 01_Pending phải chờ admin kéo sang 02_Approved.

# Xem log runner realtime (mỗi 2 phút phải có dòng mới nếu có request)
Get-Content "<PATH_REPO>\log\runner.log" -Tail 20 -Wait
# Ctrl+C để thoát
```

#### 8.5. Bật / Tắt / Xoá task

```powershell
# Chạy NGAY 1 lần (không chờ 2 phút)
schtasks /run /tn "SQL BulkEx Runner"
schtasks /run /tn "SQL-BulkEx-Cleanup"

# TẠM DỪNG (giữ task, không chạy nữa)
schtasks /change /tn "SQL BulkEx Runner" /disable
schtasks /change /tn "SQL-BulkEx-Cleanup" /disable

# BẬT LẠI
schtasks /change /tn "SQL BulkEx Runner" /enable
schtasks /change /tn "SQL-BulkEx-Cleanup" /enable

# XOÁ HẲN
schtasks /delete /tn "SQL BulkEx Runner" /f
schtasks /delete /tn "SQL-BulkEx-Cleanup" /f
```

#### 8.6. Dùng GUI thay CLI (dễ nhìn hơn)

Nếu không quen PowerShell, dùng Task Scheduler GUI:

1. Nhấn **`Win + R`** → gõ `taskschd.msc` → Enter
2. Panel trái: click **Task Scheduler Library**
3. Panel giữa: tìm dòng `SQL BulkEx Runner` hoặc `SQL-BulkEx-Cleanup`
4. Right-click → chọn: **Run** (chạy ngay) / **Disable** (tạm tắt) / **Enable** (bật lại) / **Delete** (xoá)
5. Double-click task để xem chi tiết: tab **Triggers** (lịch chạy), **Actions** (lệnh chạy), **History** (lịch sử chạy)

#### 8.7. Lưu ý thực chiến

- 🖥️ **Task chỉ chạy khi user đăng nhập.** Nếu máy đăng xuất → runner dừng. Muốn chạy ngay cả khi logout → cần setup "Run whether user is logged on or not" trong GUI (yêu cầu nhập password Windows, không khuyến nghị).
- 💤 **Máy sleep = task không chạy.** Vào **Settings → Power & sleep → Sleep = Never** cho máy giữ DB.
- 🐛 **Debug lần đầu:** tạm thay `pythonw.exe` (silent) bằng `python.exe` (có console) trong lệnh tạo → thấy log ngay để test. Xong đổi lại `pythonw.exe` để chạy nền.
- 📁 **Path có dấu space** như `C:\Users\RYAN TOAN\...` — schtasks parse quoted path OK, nếu lỗi thì thử copy repo sang path không có space (vd `C:\sql-bulkex\`).

---

## 📝 Hướng dẫn cho Sales / Requestor

**Chỉ 3 bước:**

1. **Copy** `request_template.xlsx` trong folder OneDrive `inbox/`, đổi tên (vd `hoa_20260707_HS8436.xlsx`)
2. **Điền** 2 sheet:
   - Sheet `Request`: 7 ô (Người yêu cầu, Bảng, Năm, Tháng, Tách file, Xác nhận lớn, Ghi chú)
   - Sheet `Cột Export` / `Cột Import`: mỗi cột 1 dòng đã có sẵn — chỉ điền 3 cột phải: Toán tử, Giá trị, Lấy về
3. **Thả** file vào `inbox/` (OneDrive tự sync)

Sau tối đa 2 phút:
- ✅ **Thành công** → kết quả xuất hiện ở `results/`
- ❌ **Lỗi** → file bị rename `[LOI]_*.xlsx` + kèm `.txt` giải thích. Sửa xong đổi tên bỏ prefix hoặc save mới, thả lại.

**Ví dụ điền:**

Muốn tra: tờ khai xuất khẩu HS `8436*` sang Trung Quốc, lấy 3 cột.

Sheet `Request`:
```
Người yêu cầu:  Hoa
Bảng:           export
Năm:            2026
Tháng:          03
Ghi chú:        HS8436_CN_thang3
```

Sheet `Cột Export` (chỉ điền các dòng cần):
| Cột | Toán tử | Giá trị | Lấy về? |
|---|---|---|---|
| ma_so_hang_hoa | *(để trống, auto prefix)* | 8436 | *(auto YES)* |
| ma_nuoc | eq | CN | *(auto YES)* |
| so_to_khai | | | YES |
| tri_gia_usd | | | YES |
| ngay_dang_ky | | | YES |

→ SQL: `WHERE ma_so_hang_hoa LIKE '8436%' AND ma_nuoc = 'CN'` với 5 cột trong output.

**5 toán tử:**

| Toán tử | Cách nhập Giá trị | Ví dụ |
|---|---|---|
| `eq` | 1 giá trị | `CN` |
| `in` | Nhiều giá trị, cách phẩy | `CN,KR,JP` |
| `prefix` | 1 hoặc nhiều prefix cách phẩy | `84,85` hoặc `0301234` |
| `contains` | 1 chuỗi | `laptop` |
| `between` | Đúng 2 giá trị cách phẩy | `1000,5000` |

**Quy tắc:**
- Có Toán tử + Giá trị = **filter WHERE + tự động có trong output**
- Trống Toán tử + Có Giá trị + cột có default = auto áp default (xem sheet NOTE trong file kết quả)
- Trống Toán tử + Có Giá trị + không có default = warning, giá trị bỏ qua
- Trống Toán tử + Trống Giá trị + Lấy về = YES → chỉ output
- Trống hết = skip cột này

---

## 🔧 Portal terminal (dành cho admin query trực tiếp)

Admin có thể query trực tiếp qua menu tương tác (không cần Excel):

```powershell
python portal.py
```

Flow menu: database → schema → bảng → tick cột → thêm bộ lọc → tách file (tuỳ chọn) → sắp xếp → review → export.

**Saved jobs:**

```powershell
python portal.py                  # menu tương tác, save job trong đó
python portal.py --list-jobs      # xem job đã lưu
python portal.py --job ten_job    # chạy lại
```

`jobs.yaml` là local state, đã gitignored.

---

## 🚨 Xử lý sự cố

| Triệu chứng | Cách sửa |
|---|---|
| `column.yaml chưa có datasets` | Điền datasets rồi chạy `--scan-columns` |
| `--scan-columns` không tìm được bảng | Kiểm tra pattern `tables` khớp tên bảng thật trong DB |
| File bị `[LOI]_` | Đọc `.txt` cùng thư mục, sửa Excel, đổi tên bỏ prefix, thả lại |
| Giá trị filter không có tác dụng | Quên set Toán tử + cột không có default → điền Toán tử vào dropdown |
| MST 13 số bị mất số 0 đầu | Cột `Giá trị` đã format Text — nếu vẫn lỗi, chèn `'` trước giá trị |
| Kết quả ra CSV thay xlsx | Vượt 1M dòng Excel limit, bình thường |
| Chọn Bảng = Export nhưng điền sheet Cột Import | Runner reject với message rõ |

Logs: `log/runner.log` (runner), `log/portal.log` (portal).

---

## 🔒 Bảo mật

- `connection.yaml` commit git với `password: ""`. Password thật ở `.password` (gitignored).
- `column.yaml` có thể commit (không chứa secret, chỉ tên bảng/cột).
- **Không đặt repo bên trong folder cloud-sync** — dễ leak file `.password` lên cloud.
- Share dữ liệu = share quyền truy cập folder `folders.output`.
- Máy giữ DB phải luôn bật khi giờ hành chính (single point of failure — chuyển từ 1 người biết SQL sang 1 máy).

---

## 📚 Tài liệu chi tiết

- **[docs/HUONG_DAN_SU_DUNG.md](docs/HUONG_DAN_SU_DUNG.md)** — Hướng dẫn đầy đủ tiếng Việt, có ví dụ điền cụ thể
- **[docs/SPEC.md](docs/SPEC.md)** — Spec kỹ thuật (cho ai muốn hiểu sâu / contribute)
- **[docs/SPEC_v5.md](docs/SPEC_v5.md)** — Spec architecture v5 (column-based model)

---

## 🧪 Development

```powershell
# Chạy toàn bộ test
python -m pytest

# Test theo group
python -m pytest tests/test_v5_scan.py -v
python -m pytest tests/test_v5_parse.py -v
python -m pytest tests/test_v5_e2e.py -v

# Không sinh __pycache__ và .pytest_cache
# (đã config trong conftest.py + pytest.ini)
```

---

## 📄 License

[MIT](LICENSE) © 2026 Vstream

---

## 💡 Đóng góp

Issues và PR welcome. Đọc `docs/SPEC.md` để hiểu kiến trúc trước khi contribute.
