# 📊 SQL BulkEx v6

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D6.svg?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Tests](https://img.shields.io/badge/tests-103%20passed-brightgreen.svg)](tests/)

> **Công cụ xuất dữ liệu hàng loạt từ PostgreSQL — không cần biết SQL.**
> Sales/MKT điền file Excel request → nhắn admin duyệt → runner tự chạy → file kết quả xuất hiện trong OneDrive.

---

## 🎯 Ai làm gì

| Vai trò | Việc | Cần biết code? |
|---|---|---|
| 👩‍💼 **Sales / MKT** (người xin dữ liệu) | Điền file Excel request, upload OneDrive, nhắn admin, chờ file kết quả | ❌ Không |
| 👨‍💻 **Admin Hà Nội** (người giữ máy) | Cài repo 1 lần, giữ máy bật khi làm việc, kéo file duyệt trên OneDrive | ❌ Không (sau khi cài xong) |
| 🖥️ **Runner** (script Python) | Tự động phát hiện file đã duyệt, chạy query, xuất kết quả | — |

---

## 🚀 Cài đặt lần đầu (chỉ admin, 1 lần)

### Bước 1 — Clone repo về máy Hà Nội

```powershell
cd C:\Users\admin\Downloads\GIT
git clone https://github.com/toan-chu/sql-bulkex.git
cd sql-bulkex
```

### Bước 2 — Cài Python + thư viện

```powershell
# Kiểm tra Python có chưa
python --version
# Nếu chưa có, tải từ python.org

# Cài dependencies
pip install -r requirements.txt
```

### Bước 3 — Điền password database

Tạo file `.password` cạnh `runner.py` (chỉ 1 dòng, không header):

```
mat_khau_db_cua_ban_o_day
```

⚠️ File này đã có trong `.gitignore` → không leak lên GitHub. Đừng commit password thật.

### Bước 4 — Chỉnh `connection.yaml`

Điền host, port, user, database name (giữ `password: ""` — runner sẽ đọc từ `.password`).

### Bước 5 — Tạo 3 folder trong OneDrive

Ví dụ trong OneDrive tạo folder `SQL-BulkEx-Workspace` với 3 subfolder:

```
📁 SQL-BulkEx-Workspace/
├── 📁 01_Pending    ← Sales upload file request vào đây
├── 📁 02_Approved   ← Admin kéo file sang đây = đã duyệt
└── 📁 03_Output     ← Runner đặt file kết quả vào đây
```

### Bước 6 — Chỉnh `settings.yaml`

Điền đường dẫn 3 folder trên vào (dùng đường dẫn tuyệt đối):

```yaml
folders:
  pending: "C:/Users/admin/OneDrive/SQL-BulkEx-Workspace/01_Pending"
  approved: "C:/Users/admin/OneDrive/SQL-BulkEx-Workspace/02_Approved"
  output: "C:/Users/admin/OneDrive/SQL-BulkEx-Workspace/03_Output"

onedrive_freeup:
  enabled: true
  approved_delay_hours: 2      # File đã chạy > 2 giờ → dọn về cloud-only
  output_delay_days: 7         # File output > 7 ngày → dọn về cloud-only

log:
  requests_csv: "log/requests.csv"
  runner_log: "log/runner.log"
  portal_log: "log/portal.log"

poll_seconds: 120              # Runner poll folder mỗi 2 phút
max_rows_auto: 300000
max_rows_hard: 3000000
```

### Bước 7 — Quét cột + giá trị từ database

3 lệnh, mỗi lệnh 1-2 phút:

```powershell
python runner.py --scan-columns --yes    # Quét tên cột từ DB → column.yaml
python runner.py --scan-values --yes     # Quét giá trị cột cardinality thấp → dropdown
python runner.py --make-template         # Sinh request_template.xlsx v6
```

### Bước 8 — Copy template lên OneDrive

Copy `request_template.xlsx` mới sinh vào folder `01_Pending` để Sales biết mẫu chuẩn tải về.

### Bước 9 — Cài 2 Task Scheduler (script tự chạy nền)

**Task 1 — Runner poll file duyệt mỗi 2 phút:**

```powershell
schtasks /create /tn "SQL BulkEx Runner" /sc minute /mo 2 ^
  /tr "\"C:\Python313\pythonw.exe\" \"C:\Users\admin\Downloads\GIT\sql-bulkex\runner.py\" --once" /f
```

**Task 2 — Cleanup OneDrive Files On-Demand mỗi giờ:**

```powershell
schtasks /create /tn "SQL BulkEx Cleanup" /sc hourly /mo 1 /st 00:30 ^
  /tr "\"C:\Python313\pythonw.exe\" \"C:\Users\admin\Downloads\GIT\sql-bulkex\runner.py\" --cleanup" /f
```

Chỉnh đường dẫn `pythonw.exe` và repo theo máy bạn (dùng `where pythonw` để tìm).

**Kiểm tra task đã cài chưa:**

```powershell
schtasks /query /tn "SQL BulkEx Runner"
schtasks /query /tn "SQL BulkEx Cleanup"
```

**Chạy thử ngay (không đợi 2 phút):**

```powershell
schtasks /run /tn "SQL BulkEx Runner"
```

**Tắt tạm task:**

```powershell
schtasks /change /tn "SQL BulkEx Runner" /disable
schtasks /change /tn "SQL BulkEx Cleanup" /disable
```

✅ Xong. Từ giờ máy admin chỉ cần bật (không cần đăng nhập ngồi ngoài terminal). Runner tự chạy nền.

---

## 📁 Quy trình 3 folder OneDrive

```
📁 01_Pending/       ← Sales upload file request (chờ duyệt)
   ↓ (Admin kéo file)
📁 02_Approved/      ← Runner poll folder này mỗi 2 phút
   ↓ (Chạy xong)
📁 03_Output/        ← Kết quả xuất hiện, Sales lấy về
```

**Nguyên tắc quan trọng:**
- ✅ Runner **CHỈ** đọc folder `02_Approved/` — file ở `01_Pending/` bị ignore hoàn toàn.
- ✅ File chạy xong → rename thành `[DONE] tên_file.xlsx` (nằm im ở `02_Approved/`, không di chuyển).
- ✅ File lỗi → rename thành `[LOI]_tên_file.xlsx` + file `.txt` giải thích cùng folder.

---

## 👩‍💼 Sales — Quy trình 1 request

### Bước 1 — Tải template về máy

Vào OneDrive folder `01_Pending`, download `request_template.xlsx` về máy tính.

### Bước 2 — Đổi tên file cho dễ tìm

Ví dụ: `hoa_20260709_HS8306.xlsx` (tên_ngày_mã_ngắn).

### Bước 3 — Mở file, điền sheet `Request`

| Ô | Cách điền |
|---|---|
| Người yêu cầu | Tên bạn (VD `Hoa`) |
| Bảng | `export` / `import` / `both` (chọn từ dropdown) |
| Năm | `2026` hoặc `2025,2026` hoặc `2025-2026` |
| Tháng | `06` hoặc `01-06` hoặc `01,03,05` |
| Tách file theo | Bỏ trống nếu không cần tách |
| Xác nhận lớn | Điền `YES` nếu request > 300k dòng (nếu không, để trống) |
| Ghi chú / tên request | VD `HS8306_CN_KR_2026Q1` |
| Người duyệt | Bỏ trống, admin điền sau |

### Bước 4 — Điền sheet `Cột Export` hoặc `Cột Import`

Mỗi dòng = 1 cột trong database. Có 6 cột toán tử kế nhau:

| Cột | Bằng | Trong danh sách | Trong khoảng | Bắt đầu bằng | Chứa | Kết thúc bằng | Digits | Lấy về? |
|-----|------|-----------------|--------------|--------------|------|---------------|--------|---------|

**Cách điền:**
- Điền value vào cell op muốn dùng (VD điền `CN, KR, JP` vào cell **Trong danh sách** của dòng `ma_nuoc`).
- Cell op nào để trống = op đó không active.
- Nhiều cell op có value cùng dòng → tự AND với nhau.
- **Digits**: số ký tự cho `Bắt đầu bằng` / `Kết thúc bằng` (dropdown 2/4/6/8/10/13).
- **Lấy về?**: `YES` = cột có trong file kết quả. Cột đã có op tự động được lấy về.

### Bước 5 — Save file, upload lên `01_Pending`

Kéo thả file vào OneDrive folder `01_Pending`.

### Bước 6 — Nhắn Zalo admin

Ví dụ: "Anh check giúp em file `hoa_20260709_HS8306.xlsx` với ạ".

### Bước 7 — Chờ file kết quả

Sau khi admin duyệt (~2-5 phút runner sẽ chạy), vào folder `03_Output` tìm file có pattern `20260709_hoa_HS8306.xlsx`.

---

## 👨‍💻 Admin — Quy trình duyệt

**Từ điện thoại (nhanh nhất):**
1. Mở app **OneDrive** trên điện thoại
2. Vào folder `01_Pending`, tap vào file để xem nội dung
3. Nếu OK → tap `...` (3 chấm) → **Move** → chọn `02_Approved` → **Move here**
4. Xong. Máy admin tại Hà Nội sẽ tự chạy trong 2 phút tới.

**Từ máy tính:**
1. Mở OneDrive trong browser hoặc File Explorer
2. Vào `01_Pending`, kéo thả file sang `02_Approved`
3. Xong.

**Kiểm tra request đã chạy chưa:**
- File gốc trong `02_Approved` được đổi tên thành `[DONE] tên_file.xlsx` → đã chạy xong
- File kết quả xuất hiện trong `03_Output` → báo Sales lấy

---

## 🔧 6 Toán tử — Bảng tra

| Toán tử VN | Ý nghĩa | Cách nhập giá trị | Ví dụ | Có Digits? |
|-----------|---------|-------------------|-------|------------|
| **Bằng** | Trùng đúng | 1 hoặc nhiều giá trị cách phẩy | `CN` hoặc `CN, KR, JP` | ❌ Không |
| **Trong danh sách** | Thuộc list | Nhiều giá trị cách phẩy | `CN, KR, JP` | ❌ Không |
| **Trong khoảng** | Giữa 2 mốc | Đúng 2 giá trị cách phẩy | `1000, 5000` | ❌ Không |
| **Bắt đầu bằng** | Prefix | 1 hoặc nhiều giá trị cách phẩy | `8306, 8307` | ✅ **Có** |
| **Chứa** | Substring | 1 hoặc nhiều giá trị cách phẩy | `laptop, gaming` | ❌ Không |
| **Kết thúc bằng** | Suffix | 1 hoặc nhiều giá trị cách phẩy | `00, 10` | ✅ **Có** |

💡 **Chú ý:** dùng comma `,` để nhập nhiều giá trị cùng 1 op — tool tự OR các giá trị.

---

## 🔗 Kết hợp nhiều toán tử cùng 1 cột

Vì mỗi op là 1 cell riêng, bạn có thể điền value vào **nhiều cell op cùng 1 dòng** — tool tự AND lại.

### Ví dụ 1 — HS Code prefix + suffix

Dòng `ma_so_hang_hoa`:
- **Bắt đầu bằng** = `84`
- **Kết thúc bằng** = `10`

→ SQL: `ma_so LIKE '84%' AND ma_so LIKE '%10'`
→ Nghĩa: mã bắt đầu bằng 84 và kết thúc bằng 10.

### Ví dụ 2 — Nhiều prefix cùng lúc

Dòng `ma_so_hang_hoa`:
- **Bắt đầu bằng** = `8306, 8307, 8308, 8309`
- **Digits** = `4`

→ SQL: `(ma_so LIKE '8306%' OR '8307%' OR '8308%' OR '8309%')`
→ Nghĩa: 4 heading HS code cấp 4 số.

### Ví dụ 3 — Filter list quốc gia

Dòng `ma_nuoc`:
- **Trong danh sách** = `CN, KR, JP` (chọn từ dropdown)

→ SQL: `ma_nuoc IN ('CN', 'KR', 'JP')`

---

## 🔢 Digits — Chọn số ký tự match

**Digits** = số ký tự user muốn match từ **bên trái** (Bắt đầu bằng) hoặc **bên phải** (Kết thúc bằng) của cột trong database.

### Quy tắc:
- **Digits trống** → tool không kiểm tra độ dài, dùng value nguyên
- **Digits có giá trị** → mọi value bạn điền **phải có đúng số ký tự = Digits**

### Ví dụ cụ thể — HS Code

| Bạn điền | Digits | SQL | Match gì |
|----------|--------|-----|----------|
| prefix=`8306` | `4` | `LIKE '8306%'` | Mọi HS bắt đầu bằng 8306 (kể cả 6 số, 8 số, 10 số) |
| prefix=`8306, 8307, 8308, 8309` | `4` | `(LIKE '8306%' OR ... OR '8309%')` | 4 heading cấp 4 |
| prefix=`830610` | `6` | `LIKE '830610%'` | Mọi HS bắt đầu bằng 830610 (cấp subheading) |
| prefix=`84` | `4` | ❌ **LỖI** | Value `84` chỉ có 2 ký tự, Digits yêu cầu 4 |

### Ví dụ MST 10 và 13 số

| Bạn điền | Digits | Match gì |
|----------|--------|----------|
| prefix=`0301234567` | `10` | Cả MST 10 số VÀ MST 13 số bắt đầu bằng 10 số này (đơn vị chính + phụ thuộc) |
| prefix=`0301234567001` | `13` | Chỉ MST 13 số cụ thể của đơn vị phụ 001 |

### Dropdown gợi ý:

- `2` — chapter HS
- `4` — heading HS
- `6` — subheading HS
- `8` — tariff code
- `10` — MST đơn vị chính hoặc HS national code
- `13` — MST đơn vị phụ thuộc

---

## 📋 Dropdown giá trị — Auto cho cột cardinality thấp

Khi bạn chạy `--scan-values`, tool quét database và tìm các cột có ít giá trị distinct (VD `ma_nuoc` có ~195 nước, `phuong_thuc_van_chuyen` có 3 phương thức).

Threshold config trong `column.yaml`:

```yaml
cardinality:
  threshold: 200          # Cột có ≤ 200 distinct → có dropdown
  sample_size: 1000
  skip_text_length: 100
  skip_columns:
    - so_to_khai          # Cột này không cần dropdown dù cardinality thấp
    - so_van_don
```

Sau khi quét xong + regen template, mở Excel:
- Cell **Bằng** và **Trong danh sách** cột `ma_nuoc` sẽ có dropdown 195 nước để chọn
- Cell **Bắt đầu bằng**, **Kết thúc bằng** không dropdown (chỉ text vì prefix/suffix không phải equality)

Muốn thay đổi threshold → sửa `column.yaml`, chạy lại 2 lệnh:

```powershell
python runner.py --scan-values --yes
python runner.py --make-template
```

---

## ☁️ OneDrive Cleanup — Không cho máy admin bị đầy ổ đĩa

Windows có tính năng **OneDrive Files On-Demand**: file lưu trên cloud, chỉ download khi cần.

Runner có CLI `--cleanup` tự động chạy `attrib +U -P` cho file cũ → biến thành cloud-only (icon ☁️ trên OneDrive Explorer).

Config trong `settings.yaml`:

```yaml
onedrive_freeup:
  enabled: true
  approved_delay_hours: 2      # File [DONE] > 2 giờ → cloud-only
  output_delay_days: 7         # File output > 7 ngày → cloud-only
```

Task Scheduler task 2 (đã cài ở Bước 9) chạy `--cleanup` mỗi giờ tự động.

**Muốn xem file cloud-only:** vào OneDrive Explorer, file có icon ☁️ = cloud-only (chưa download), icon ✅ = đang có trên máy. Click vào file cloud-only → OneDrive tự tải về.

**Muốn giữ file luôn có trên máy:** chuột phải file → `Always keep on this device`.

**Tắt cleanup:** đổi `enabled: false` trong `settings.yaml`.

---

## 📊 Log lịch sử request — `log/requests.csv`

Mỗi request xử lý xong, runner ghi 1 dòng vào `log/requests.csv` (CSV cấu trúc, mở bằng Excel được).

**Cột trong log:**

| Cột | Ý nghĩa |
|-----|---------|
| `timestamp` | Thời gian bắt đầu chạy |
| `requester_cell` | Ô "Người yêu cầu" trong sheet Request (VD `Hoa`) |
| `requester_meta` | Windows username từ metadata file Excel (VD `VSTREAM\hoa.nguyen`) |
| `file_name` | Tên file request gốc |
| `dataset` | `export`, `import`, hoặc `both` |
| `row_count` | Số dòng xuất được |
| `duration_sec` | Thời gian chạy (giây) |
| `status` | `success`, `rejected`, hoặc `error` |
| `output_file` | Tên file kết quả |
| `error` | Nội dung lỗi (nếu status=rejected/error) |

File encoding UTF-8-BOM → Excel mở tiếng Việt đúng luôn.

⚠️ **Đừng để Excel mở file này** khi runner đang chạy — runner sẽ retry 3 lần rồi bỏ qua log nếu file locked.

---

## 💻 Lệnh thường dùng

```powershell
# Quét cột từ DB → column.yaml (chạy lần đầu hoặc khi DB đổi schema)
python runner.py --scan-columns --yes

# Quét giá trị cardinality thấp → dropdown Excel
python runner.py --scan-values --yes

# Sinh request_template.xlsx v6
python runner.py --make-template

# Chạy 1 lần poll folder Approved (Task Scheduler chạy tự động, admin không cần gõ)
python runner.py --once

# Dọn file cũ về cloud-only (Task Scheduler chạy tự động)
python runner.py --cleanup

# Chạy test suite
python -m pytest -q
```

---

## 🚨 Xử lý lỗi thường gặp

| Vấn đề | Cách xử lý |
|--------|-----------|
| File bị đổi thành `[LOI]_xxx.xlsx` | Mở file `.txt` cùng tên xem lỗi gì, sửa file `.xlsx`, xoá prefix `[LOI]_`, thả lại `01_Pending` |
| File trong `01_Pending` không tự chạy | Đúng rồi, admin phải kéo sang `02_Approved` mới chạy |
| Excel không có dropdown giá trị | Chạy `python runner.py --scan-values --yes` rồi `--make-template` |
| Digits bị reject | Kiểm tra độ dài value có bằng Digits không (mọi element trong list phải cùng độ dài) |
| Cleanup không dọn file | Kiểm tra `onedrive_freeup.enabled: true` trong settings.yaml + OneDrive Files On-Demand đang bật |
| Log CSV không update | Đóng file `log/requests.csv` trong Excel, runner sẽ retry request kế tiếp |
| Runner không chạy background | Kiểm tra Task Scheduler: `schtasks /query /tn "SQL BulkEx Runner"` — status phải là `Ready` hoặc `Running` |
| Password sai | Kiểm tra file `.password` — chỉ 1 dòng, không có space đầu/cuối |

---

## ❓ FAQ

**Q: Máy admin có phải bật 24/7 không?**
→ Không. Bật khi làm việc là đủ. Sales upload file lúc nào cũng được, file nằm ở `01_Pending` chờ admin duyệt.

**Q: Có phải cài Power Automate hay Teams không?**
→ Không. Chỉ cần OneDrive + Task Scheduler (Windows built-in). Repo share với MNC được, zero dependency M365 add-on.

**Q: 1 request mất bao lâu?**
→ Từ lúc admin duyệt → runner phát hiện: tối đa 2 phút (poll interval). Query chạy: tuỳ data, thường vài giây → vài phút. Total: 2-5 phút cho request thường.

**Q: Nhiều Sales cùng lúc upload thì sao?**
→ OK, runner xử lý tuần tự từng file trong `02_Approved`. Admin duyệt file nào trước, file đó chạy trước.

**Q: File output cũ chiếm dung lượng?**
→ Task Scheduler `--cleanup` chạy mỗi giờ tự set file cũ về cloud-only. File vẫn tồn tại trên SharePoint, chỉ không tốn disk máy admin.

**Q: Sales quên nhắn admin thì sao?**
→ File nằm mãi ở `01_Pending`, không tự chạy. Admin cần chủ động check folder `01_Pending` mỗi ngày, hoặc setup SharePoint alert để nhận email khi có file mới.

**Q: Template v5 cũ có dùng được không?**
→ Có, runner v6 vẫn parse được file v5 (cột `Toán tử` dropdown). Sẽ có warning trong log, khuyến khích Sales download template v6 mới.

**Q: Muốn thêm operator mới (VD `Khác` / `Lớn hơn`)?**
→ Chỉ cần thêm entry vào `operators.yaml`, không đụng code Python. VD:
```yaml
neq:
  display: "Khác"
  hint: "1 giá trị"
  example: "CN"
  sql_single: "{col} != {val}"
  multi_value: false
  arity: 1
  supports_digits: false
```
Rồi thêm `neq` vào `display_order`. Regen template. Xong.

**Q: Repo có tương thích PostgreSQL bao nhiêu?**
→ Test trên PostgreSQL 14+ (psycopg2 driver). Query dùng `information_schema` + `pg_stats` chuẩn Postgres, không dùng function riêng.

---

## 🔧 Reference kỹ thuật (dành admin quan tâm)

### Files quan trọng

| File | Mục đích |
|------|----------|
| `runner.py` | Script chính, chạy qua CLI |
| `portal.py` | Terminal tool tương tác (giữ từ v5, không đổi) |
| `operators.py` + `operators.yaml` | Registry 6 operator, thêm op mới không cần sửa Python |
| `connection.yaml` | Config kết nối PostgreSQL (không chứa password) |
| `.password` | Password DB (gitignored) |
| `column.yaml` | Schema dataset, cột, cardinality cache, value cache |
| `settings.yaml` | Folder paths, cleanup config, log config |
| `request_template.xlsx` | Template Excel v6 (5 sheet) |
| `docs/SPEC.md` | Spec đầy đủ v6 (dài, cho technical review) |
| `docs/SPEC_v5_archived.md` | Spec v5 archive để reference |
| `tests/` | 103 test cases (99 pass, 4 skip pgserver Windows) |

### Registry operator pattern

Codex build v6 với nguyên tắc registry nghiêm ngặt: **KHÔNG hardcode operator ở logic runner**. Mọi op đi qua `OperatorBuilder`. Thêm op = thêm 1 dòng YAML.

Verify không hardcode:
```powershell
rg -n 'op == "eq"|VALID_OPS = |CELL_TO_OP = \{' runner.py operators.py
# Không có match = tốt
```

### Backward compatibility

- ✅ Template v5 (5 cột) vẫn parse được, warning "template v5"
- ✅ `settings.yaml` cũ (`input_dir`/`output_dir`) vẫn chạy, deprecation warning
- ✅ `portal.py` không đổi (terminal tool giữ nguyên)
- ✅ `jobs.yaml` saved jobs vẫn dùng được với `portal.py --job`

### Test

```powershell
# Toàn bộ test suite
python -m pytest -q

# Chỉ test v6
python -m pytest tests/test_v6_*.py -v

# Test coverage
python -m pytest --cov=runner --cov=operators
```

---

## 📞 Support

Có vấn đề? Mở issue trên GitHub: https://github.com/toan-chu/sql-bulkex/issues

---

**Made with ❤️ for logistics forwarders in Vietnam.**
