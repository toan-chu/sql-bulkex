# 📊 SQL BulkEx v7

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D6.svg?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Tests](https://img.shields.io/badge/tests-40%20passed-brightgreen.svg)](tests/v7)

> **Lấy dữ liệu tờ khai xuất nhập khẩu từ PostgreSQL bằng một trang web — không cần biết SQL.**
> Người dùng mở `BulkEx.html` → chọn tháng, điều kiện lọc, cột → bấm "Get the file" → file Excel (hoặc CSV khi quá lớn) tự xuất hiện trong thư mục chung.

## 🎯 Ai làm gì

| Vai trò | Việc | Cần biết code? |
|---|---|---|
| 👩‍💼 Người dùng (Sales / MKT…) | Mở `BulkEx.html`, chọn điều kiện, bấm nút, mở file kết quả | Không |
| 👨‍💻 Admin (người giữ máy có database) | Nháy đúp `CAI-DAT.bat` một lần, giữ máy bật | Không |
| 🖥️ Runner (chạy nền mỗi 2 phút) | Quét bảng, đọc yêu cầu, chạy truy vấn an toàn, ghi file Excel / CSV | — |

## 🔄 Luồng chạy

```text
Người dùng (máy nào cũng được)          Thư mục chung (OneDrive)            Máy có database
------------------------------          ------------------------            ---------------
mở BulkEx.html  ── đọc ──────────────▶  _system/catalog.js   ◀── ghi ──  runner: quét mọi database,
  chọn tháng / bộ lọc / cột                                              nhận bảng Export/Import theo bộ cột,
  bấm "Get the file" ── ghi ─────────▶  input/<yêu cầu>.json ── đọc ──▶  dịch yêu cầu thành SQL (chỉ đọc,
                                                                          giới hạn thời gian + số dòng)
  Recent requests (Done / Failed) ◀──  _system/status.js    ◀── ghi ──  dựng lại mỗi lượt từ
                                                                          _system/done + _system/failed
  Open file ─────────────────────────▶ output/<file>.xlsx|csv ◀── ghi ──
```

## 🚀 Cài đặt (admin, một lần)

1. Máy cần **Python 3.11+** (nếu chưa có, `CAI-DAT.bat` sẽ mở trang tải và chỉ cách cài).
2. Nháy đúp **`CAI-DAT.bat`** ở thư mục gốc. Trình cài đặt tự:
   - đăng nhập PostgreSQL bằng mật khẩu đã lưu trên máy — **chỉ hỏi mật khẩu khi không tìm được cái nào dùng được**;
   - tìm bảng Export / Import trong mọi database (tên database, schema, bảng khác nhau cũng được);
   - cho chọn thư mục chung (OneDrive để dùng thật, hoặc Downloads để thử) và đặt `BulkEx.html` vào đó;
   - cài lịch chạy nền mỗi 2 phút, gỡ lịch cũ của v6.
3. Chia sẻ thư mục `SQL-BulkEx` trên OneDrive cho người dùng.

Chạy lại `CAI-DAT.bat` bất cứ lúc nào để đổi thư mục, đổi mật khẩu hay cập nhật trang.

## 📋 Dùng thế nào

1. Mở `BulkEx.html` bằng Chrome hoặc Edge. Lần đầu bấm **Choose BulkEx folder** để trang tự gửi yêu cầu vào thư mục.
2. **Data**: Export, Import hoặc cả hai; bấm chọn các tháng (bấm số năm để lấy cả năm).
3. **Filters**: mỗi điều kiện nhận nhiều giá trị (dán cả cột từ Excel được); nhóm điều kiện để làm "hoặc".
4. **Result**: Detail (từng dòng, chọn cột) và/hoặc Summary (gom theo, cộng tổng, top N).
5. **Check row count** để xem số dòng trước, **Get the file** để lấy file. Kết quả hiện ở **Recent requests**.

## ❓ Hỏng thì làm gì

| Hiện tượng | Cách xử lý |
|---|---|
| Trang báo không có danh sách trường | Runner chưa chạy lần nào: chạy lại `CAI-DAT.bat` |
| Yêu cầu nằm mãi ở "sent, waiting" | Máy có database đang tắt / ngủ, hoặc OneDrive chưa đồng bộ |
| "The database can't be reached" | PostgreSQL chưa chạy; yêu cầu sẽ tự chạy lại khi database lên |
| Thiếu tháng mới | Bảng tháng đó chưa có, hoặc tên bảng không có năm-tháng (xem `_system/tables.json`) |
| Yêu cầu nằm mãi ở "waiting", log ghi "Waiting for OneDrive" | Trên máy có database: chuột phải thư mục BulkEx → **Always keep on this device** (setup và runner tự làm việc này; chỉ cần làm tay khi Windows chặn) |
| "The database computer is almost out of disk space" | Ổ máy có database còn dưới 5 GB trống: dọn ổ rồi gửi lại (ngưỡng `min_free_gb` trong `config/bulkex.yaml`) |
| Cột hiện tên gốc tiếng Việt | Thêm tên tiếng Anh vào `app/labels.yaml` |

## 📦 Kết quả lớn cỡ nào thì ra gì

| Số dòng Detail | File nhận được |
|---|---|
| đến 1 triệu | Excel, 1 sheet Detail |
| 1 – 3 triệu | Excel, chia sheet Detail (1), (2), (3) |
| trên 3 triệu | toàn bộ CSV (Detail + Summary), không có Excel |
| trên 10 triệu | từ chối, khuyên lọc hẹp hơn |

Các ngưỡng chỉnh trong `config/bulkex.yaml` (`xlsx_max_rows`, `max_rows`, `csv_max_rows`). **Check row count** báo trước bằng chữ cam khi kết quả sẽ lớn.

## 🧹 Dọn dẹp (admin)

- **Recent requests** đọc thẳng từ `_system/done` và `_system/failed`: xoá file ở đó là sau ~2 phút mọi người hết thấy dòng đó.
- File kết quả trong `output/` không tự xoá: admin xoá tay khi cần. Trên máy có database, `output/` chỉ giữ trên mây (OneDrive tải lên xong là giải phóng ổ); `input/` và `_system/` luôn nằm trên máy.

Nhật ký nằm trong thư mục chung, không nằm trong repo: `_system/log/bulkex.log` (lỗi chi tiết) và `_system/log/requests.csv` (ai lấy gì, lúc nào).

## 🗂️ Cấu trúc

```text
CAI-DAT.bat            trình cài đặt (nháy đúp)
app/web/BulkEx.html    trang người dùng (bản gốc; setup chép ra thư mục chung)
app/bulkex/            runner: scan, catalog, query, runner, setup
app/labels.yaml        tên tiếng Anh, nhóm, cột Essentials, cách so sánh mặc định
app/datasets.yaml      cách nhận bảng Export / Import, cột số lưu dạng chữ
config/                cấu hình riêng máy (mật khẩu, kết nối) - không lên Git
tests/v7/              phép thử (cần PostgreSQL: đặt BULKEX_TEST_PG)
handoff/               hồ sơ điều phối dự án
```
