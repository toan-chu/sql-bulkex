# 📊 SQL BulkEx v7

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D6.svg?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Tests](https://img.shields.io/badge/tests-45%20passed-brightgreen.svg)](tests/v7)

> **Lấy dữ liệu tờ khai xuất nhập khẩu bằng một trang web, không cần biết SQL.**
> Mở `BulkEx.html` → chọn tháng, điều kiện, cột → bấm **Get the file** → vài phút sau có file Excel trong thư mục chung.
>
> 📘 **Người dùng:** bấm nút **Hướng dẫn** trên trang BulkEx để mở `Help.html` — bản hướng dẫn tiếng Việt, có ô tìm tên trường.

**Mục lục:** [Hướng dẫn người dùng](#-hướng-dẫn-người-dùng) · [Detail và Summary khác gì](#-detail-và-summary-khác-gì) · [Bảng tra tên trường](#-bảng-tra-tên-trường) · [Câu hỏi thường gặp](#-câu-hỏi-thường-gặp) · [Phần cho admin](#-phần-cho-admin)

---

## 👩‍💼 Hướng dẫn người dùng

### Trang trông như thế nào

```text
┌──────────────────────────────────────────────┬─────────────────────────────┐
│ ① Data      Export / Import / Export+Import  │ ⑤ Your request              │
│             bấm chọn tháng                   │    Request name   [.......] │
├──────────────────────────────────────────────┤    Requested by   [.......] │
│ ② Filters   điều kiện lọc (HS, nước, công ty)│    [Check row count]        │
├──────────────────────────────────────────────┤    [Get the file]           │
│ ③ Result    Detail rows  /  Summary          │─────────────────────────────│
│             chọn cột muốn có trong file      │ ④ My presets (mẫu đã lưu)   │
│                                              │ ⑥ Recent requests (kết quả) │
└──────────────────────────────────────────────┴─────────────────────────────┘
```

### Lần đầu tiên (làm 1 lần)

1. Vào thư mục **BulkEx** trên OneDrive, nháy đúp **`BulkEx.html`**. Nên dùng **Chrome** hoặc **Edge**.
2. Ở khung tím bên phải, bấm **Choose BulkEx folder** rồi chọn đúng thư mục **BulkEx** (thư mục có `input` và `output` bên trong) → bấm **Allow / Cho phép**.
   - Đúng: khung hiện ✓ *Requests go straight to the BulkEx folder*.
   - Sai: báo *Pick the BulkEx folder* → bạn đang chọn nhầm thư mục con, chọn lại thư mục cha.
3. Gõ tên bạn vào ô **Requested by**. Trang nhớ tên này cho các lần sau.

### Mỗi lần lấy dữ liệu: 6 bước

**① Data — lấy bảng nào, tháng nào**
- **Export** = tờ khai xuất khẩu, **Import** = tờ khai nhập khẩu, **Export + Import** = cả hai.
- Bấm vào ô tháng để chọn (ô cam = đã chọn). Bấm **số năm** để chọn cả năm. **Quick pick** chọn nhanh 3 / 6 / 9 / 12 tháng gần nhất.
- Ô tháng mờ = chưa có dữ liệu tháng đó.

**② Filters — chỉ lấy những dòng nào**
- Bấm **+ Add condition** → chọn trường (ví dụ *HS Code*) → chọn cách so → gõ giá trị, **Enter** sau mỗi giá trị.
- Có sẵn danh sách trong Excel? Copy cả cột rồi **dán** vào ô giá trị — mỗi ô thành một giá trị.
- Một điều kiện có nhiều giá trị = dòng khớp **bất kỳ** giá trị nào (VN *hoặc* IN).
- Chọn bảng Export + Import thì mỗi bảng có **tab bộ lọc riêng** (tab để trống = lấy toàn bộ bảng đó). Nút **Copy to Import / Copy to Export** chép bộ lọc sang bảng kia; trường người xuất / nhập khẩu tự đổi vai (*Exporter Code* ở Export → *Importer Code* ở Import, vì công ty Việt Nam là bên xuất ở Export, bên nhập ở Import).

Cách so (chọn trong ô thứ hai):

| Trên trang | Nghĩa | Dùng khi |
|---|---|---|
| is | đúng bằng một trong các giá trị | mã nước, mã đơn vị, phương thức vận chuyển |
| is not | khác tất cả các giá trị | loại trừ vài nước |
| starts with | bắt đầu bằng | **mã HS** (gõ `3002` là lấy mọi mã 3002xxxx), mã số thuế |
| contains | có chứa ở bất kỳ đâu | tên công ty, mô tả hàng |
| doesn't contain / doesn't start with | ngược lại hai cái trên | loại bỏ |
| ends with | kết thúc bằng | ít dùng |
| has exactly … characters | đúng số ký tự | lọc mã HS đủ 8 số |
| is empty / is not empty | ô trống / có dữ liệu | |
| is between / more than / at least / less than / at most | so sánh số | trị giá, số lượng, trọng lượng |

> ⚠️ **"Keep rows that match all / any"** — quan trọng nhất trang.
> - **all** (mặc định) = dòng phải khớp **tất cả** điều kiện. *HS 3002 **và** đến Ấn Độ* = thuốc 3002 đi Ấn Độ. → **Hầu như luôn chọn cái này.**
> - **any** = khớp **một** điều kiện là đủ. *HS 3002 **hoặc** đến Ấn Độ* = mọi lô 3002 đi mọi nước **cộng** mọi lô hàng gì cũng được đi Ấn Độ → rất nhiều dòng, dễ quá 15 phút và bị dừng. Trang hiện cảnh báo cam khi bạn chọn **any**.
> - Cần "hoặc" cho một phần thôi? Dùng **+ Add group (either / or)**: ví dụ *HS 3002 **và** (đến IN **hoặc** đến VN)*.

**③ Result — muốn nhận gì** (xem kỹ ở [Detail và Summary khác gì](#-detail-và-summary-khác-gì))
- Tick **Detail rows** để có danh sách từng tờ khai; tick **Summary** để có bảng tổng hợp; tick cả hai được.
- Detail: chọn cột bằng **Essentials** (bộ cột hay dùng), **All columns**, hoặc **Add a column…**. Trường nào đã dùng để lọc sẽ tự có trong file (chip có khóa).
- File luôn có thêm 2 cột đầu **Year**, **Month** để biết dòng đó thuộc tháng nào.

**④ My presets — lưu để lần sau dùng lại** (không bắt buộc)
- Bấm **Save as new** để lưu cả yêu cầu (tháng, bộ lọc, cột) dưới một cái tên. Lần sau chọn tên đó là có lại y nguyên.
- Mẫu lưu trong trình duyệt trên máy bạn. **Back up** để giữ một bản, **Restore** để nạp lại / chuyển sang máy khác.

**⑤ Your request — đặt tên và gửi**
- **Request name**: đặt tên dễ nhớ (*Pharma 3002 sang Ấn Độ 2025*). Bắt buộc.
- Đọc câu tóm tắt màu trắng phía trên: đó là đúng điều bạn đang xin. Thấy chữ **or** chỗ bạn muốn **and** → quay lại bước ②.
- Bấm **Check row count** trước: chỉ đếm số dòng, không làm file, 1–2 phút. Nếu số dòng quá lớn hoặc 0 → sửa bộ lọc.
- Ổn rồi thì bấm **Get the file**.

**⑥ Recent requests — chờ và mở kết quả**
- Yêu cầu đi qua các trạng thái: **sent, waiting for the runner** (đã gửi) → **running** (đang chạy) → **ready** (xong, chữ xanh) hoặc **couldn't run** (lỗi, chữ đỏ, kèm lý do).
- Thường mất 2–5 phút; yêu cầu lớn (nhiều năm, hàng trăm nghìn dòng) có thể 10–15 phút.
- Xong thì bấm **Open file** (hoặc **Open CSV**). File nằm trong thư mục **output**.
- Tab **Done / Failed** tách việc xong và việc lỗi. **Only mine / Show everyone** để xem của riêng bạn hay của cả nhóm.
- **Use again** nạp lại yêu cầu cũ vào trang để sửa và gửi lại (chỉ có với yêu cầu gửi từ chính máy bạn).

### Ví dụ hoàn chỉnh

*"Danh sách nhập khẩu hàng mã HS 3002 và 3004, gửi từ Ấn Độ, năm 2025"*

| Bước | Làm gì |
|---|---|
| ① | **Import** → bấm **2025** |
| ② | Match **all**. Điều kiện 1: *HS Code* · **starts with** · `3002` ↵ `3004` ↵. Điều kiện 2: *Shipped From Country Code* · **is** · `IN` ↵ |
| ③ | Tick **Detail rows** → **Essentials**. Muốn thêm bảng tổng hợp theo nhà nhập khẩu: tick **Summary** → *One row for each* = **Importer Name** |
| ⑤ | Request name `Thuoc 3002-3004 tu IN 2025` → **Check row count** → thấy số hợp lý → **Get the file** |
| ⑥ | Đợi chữ xanh **ready** → **Open file** |

---

## 📑 Detail và Summary khác gì

|  | **Detail rows** | **Summary** |
|---|---|---|
| Là gì | Danh sách **từng tờ khai / từng dòng hàng** | Bảng **tổng hợp**: gom các dòng giống nhau thành một dòng, đếm và cộng tổng |
| Mỗi dòng trong file là | một dòng hàng trên tờ khai | một nhóm (ví dụ một nhà nhập khẩu) |
| Bạn chọn | **các cột** muốn xem | **gom theo trường nào** (*One row for each*) và **cộng tổng cột số nào** (*Add up*) |
| Số dòng | có thể rất nhiều (hàng trăm nghìn) | ít, gọn (có thể giới hạn **top N**) |
| Dùng khi | cần soi chi tiết, lọc tiếp trong Excel | cần trả lời nhanh "ai nhập nhiều nhất", "nước nào lớn nhất" |
| Tên sheet | **Detail** | **Summary** |

**Summary chọn thế nào — 3 ô:**

1. **One row for each** — gom theo trường nào. Mỗi tổ hợp giá trị khác nhau thành một dòng.
   - Chọn *Importer Name* → mỗi nhà nhập khẩu một dòng.
   - Chọn *Importer Name* + *HS Code* → mỗi cặp (nhà nhập khẩu, mã HS) một dòng.
   - Càng nhiều trường → càng nhiều dòng, càng chi tiết. Thường chọn **1–2 trường** là đủ.
2. **Add up** — cột số muốn cộng tổng (*Invoice Value*, *Quantity 1*, *Total Gross Weight*…). Cột **Records** (số dòng) luôn có sẵn.
3. **Keep only the top** — chỉ giữ N dòng lớn nhất (xếp theo số Records). Để trống = lấy hết.

Ví dụ: *One row for each* = **Importer Name**, *Add up* = **Invoice Value**, *top* = **20** → file có sheet:

| Importer Name | Records | Total Invoice Value |
|---|---|---|
| Công ty A | 312 | 1,250,000 |
| Công ty B | 205 | 980,000 |
| … (20 dòng) | | |

> Summary dùng **cùng bộ lọc và cùng tháng** với Detail. Summary hiện gộp tất cả các tháng đã chọn (không tách theo tháng).
> Tick cả hai → một file Excel có cả sheet Detail và sheet Summary.

---

## 📖 Bảng tra tên trường

★ = có sẵn trong bộ cột **Essentials**. Rê chuột lên tên trường trên trang cũng thấy tên gốc.
Một số trường chỉ có ở Export hoặc chỉ có ở Import (ví dụ thuế xuất khẩu chỉ có ở Export).

| Tên gốc (database) | Tên trên trang (English) | Tiếng Việt | Nhóm trên trang |
|---|---|---|---|
| `ma_so_hang_hoa` | HS Code ★ | Mã số hàng hóa (mã HS) | Goods |
| `mo_ta_hang_hoa` | Goods Description ★ | Mô tả hàng hóa | Goods |
| `so_luong_1` | Quantity 1 ★ | Số lượng (1) | Goods |
| `ma_don_vi_tinh_1` | Unit Code 1 ★ | Mã đơn vị tính (1) | Goods |
| `don_vi_cua_don_gia_va_so_luong` | Unit Price and Quantity Unit | Đơn vị của đơn giá và số lượng | Goods |
| `ma_nuoc_xuat_xu` | Country of Origin Code ★ | Mã nước xuất xứ (nơi sản xuất) | Goods |
| `phan_loai_giay_phep_nhap_khau_1` | Import License Type 1 | Phân loại giấy phép nhập khẩu (1) | Goods |
| `ma_nguoi_xuat_khau` | Exporter Code ★ | Mã người xuất khẩu | Parties |
| `ten_nguoi_xuat_khau` | Exporter Name ★ | Tên người xuất khẩu | Parties |
| `ma_nguoi_nhap_khau` | Importer Code ★ | Mã người nhập khẩu | Parties |
| `ten_nguoi_nhap_khau` | Importer Name ★ | Tên người nhập khẩu | Parties |
| `so_dien_thoai_nguoi_nhap_khau` | Importer Phone Number | Số điện thoại người nhập khẩu | Parties |
| `ten_nguoi_uy_thac_nhap_khau` | Entrusted Importer Name | Tên người ủy thác nhập khẩu | Parties |
| `ma_nuoc` | Destination Country Code (Export) / Shipped From Country Code (Import) ★ | Mã nước bên kia giao dịch — Export: nước hàng đến; Import: nước hàng gửi từ | Parties |
| `tri_gia_hoa_don` | Invoice Value ★ | Trị giá hóa đơn | Value |
| `don_gia_hoa_don` | Invoice Unit Price ★ | Đơn giá hóa đơn | Value |
| `ma_dong_tien_cua_don_gia_hoa_don` | Invoice Currency Code ★ | Mã đồng tiền của đơn giá hóa đơn | Value |
| `ma_dong_tien_cua_don_gia` | Unit Price Currency Code ★ | Mã đồng tiền của đơn giá | Value |
| `tong_gia_tri_hoa_don` | Total Invoice Value | Tổng giá trị hóa đơn | Value |
| `tong_tri_gia_hoa_don` | Total Invoice Value | Tổng trị giá hóa đơn | Value |
| `phuong_thuc_thanh_toan` | Payment Method | Phương thức thanh toán | Value |
| `tri_gia_tinh_thue_s` | Taxable Value S | Trị giá tính thuế (S) | Duty & Tax |
| `tri_gia_tinh_thue_m` | Taxable Value M | Trị giá tính thuế (M) | Duty & Tax |
| `don_gia_tinh_thue` | Taxable Unit Price | Đơn giá tính thuế | Duty & Tax |
| `tong_gia_tri_tinh_thue` | Total Taxable Value | Tổng giá trị tính thuế | Duty & Tax |
| `tong_tri_gia_tinh_thue` | Total Taxable Value | Tổng trị giá tính thuế | Duty & Tax |
| `thue_suat_thue_xuat_khau` | Export Duty Rate | Thuế suất thuế xuất khẩu | Duty & Tax |
| `thue_suat_thue_nhap_khau` | Import Duty Rate | Thuế suất thuế nhập khẩu | Duty & Tax |
| `phan_loai_nhap_thue_suat_thue_xuat_khau` | Export Duty Rate Input Type | Phân loại nhập thuế suất thuế xuất khẩu | Duty & Tax |
| `so_tien_thue_xuat_khau` | Export Duty Amount | Số tiền thuế xuất khẩu | Duty & Tax |
| `so_tien_thue_nhap_khau` | Import Duty Amount | Số tiền thuế nhập khẩu | Duty & Tax |
| `tong_so_tien_thue_xuat_khau` | Total Export Duty Amount | Tổng số tiền thuế xuất khẩu | Duty & Tax |
| `tong_tien_thue_phai_nop` | Total Tax Payable | Tổng tiền thuế phải nộp | Duty & Tax |
| `ma_mien_giam_khong_chiu_thue_xuat_khau` | Export Duty Exemption Reduction Code | Mã miễn / giảm / không chịu thuế xuất khẩu | Duty & Tax |
| `ma_mien_giam_khong_chiu_thue_nhap_khau` | Import Duty Exemption Reduction Code | Mã miễn / giảm / không chịu thuế nhập khẩu | Duty & Tax |
| `ma_bieu_thue_nhap_khau` | Import Tariff Code | Mã biểu thuế nhập khẩu | Duty & Tax |
| `phuong_thuc_van_chuyen` | Transport Mode | Phương thức vận chuyển | Logistics |
| `so_van_don` | Bill of Lading Number | Số vận đơn | Logistics |
| `so_van_don_1` | Bill of Lading Number 1 | Số vận đơn (1) | Logistics |
| `so_van_don_2` | Bill of Lading Number 2 | Số vận đơn (2) | Logistics |
| `so_van_don_3` | Bill of Lading Number 3 | Số vận đơn (3) | Logistics |
| `so_van_don_4` | Bill of Lading Number 4 | Số vận đơn (4) | Logistics |
| `so_van_don_5` | Bill of Lading Number 5 | Số vận đơn (5) | Logistics |
| `so_luong` | Quantity | Số lượng kiện | Logistics |
| `ma_don_vi_tinh` | Package Type | Mã đơn vị tính (loại kiện) | Logistics |
| `tong_trong_luong_hang` | Total Gross Weight ★ | Tổng trọng lượng hàng (gross) | Logistics |
| `ma_don_vi_tinh_trong_luong` | Weight Unit | Mã đơn vị tính trọng lượng | Logistics |
| `so_luong_container` | Container Count | Số lượng container | Logistics |
| `ma_dia_diem_xep_hang` | Loading Location Code | Mã địa điểm xếp hàng | Logistics |
| `ma_dia_diem_do_hang` | Unloading Location Code | Mã địa điểm dỡ hàng | Logistics |
| `ma_dia_diem_nhan_hang_cuoi_cung` | Final Destination Code | Mã địa điểm nhận hàng cuối cùng | Logistics |
| `ten_phuong_tien_van_chuyen` | Transport Vehicle Name | Tên phương tiện vận chuyển | Logistics |
| `so_to_khai` | Declaration Number | Số tờ khai | Declaration |
| `ma_chi_cuc_hai_quan_tao_moi` | Customs Sub Department Code | Mã chi cục hải quan tạo mới | Declaration |
| `ma_loai_hinh` | Declaration Type Code | Mã loại hình | Declaration |
| `phan_ghi_chu` | Remarks | Phần ghi chú | Declaration |

---

## ❓ Câu hỏi thường gặp

| Bạn thấy | Nghĩa là | Làm gì |
|---|---|---|
| Nút **Get the file** mờ, không bấm được | Thiếu thông tin | Đọc dòng chấm cam trong khung tím: thường là thiếu *Request name*, *Requested by* hoặc chưa chọn tháng |
| Nằm mãi ở **sent, waiting for the runner** | Máy chạy dữ liệu chưa nhận được yêu cầu | Đợi 5 phút. Vẫn vậy → báo admin (máy có thể đang tắt, hoặc OneDrive chưa đồng bộ) |
| **couldn't run** – *took longer than 15 minutes* | Yêu cầu quá lớn | Chọn ít tháng hơn, thêm điều kiện, và kiểm tra đang để **all** chứ không phải **any** |
| **couldn't run** – *there is no data for the chosen months* | Tháng đó chưa có dữ liệu | Chọn tháng khác |
| Ra **0 rows** | Bộ lọc quá chặt hoặc gõ sai | Mã HS nên dùng **starts with**; tên công ty nên dùng **contains**; mã nước dùng **is** với mã 2 chữ (`IN`, `VN`, `CN`) |
| Ra cả nước khác dù đã lọc nước | Đang nhìn nhầm cột | Import có 2 cột nước: *Shipped From Country Code* (nước gửi hàng) và *Country of Origin Code* (nước sản xuất). Xem bảng tra bên dưới |
| Nhận file **CSV** thay vì Excel | Kết quả trên 3 triệu dòng | CSV mở bằng Excel bình thường. Muốn Excel thì lọc hẹp lại |
| **couldn't run** – *… rows is over the 10,000,000 limit* | Thường do chọn **Export + Import** nhưng chỉ lọc ở một tab, tab kia lấy toàn bộ | Thêm điều kiện ở tab còn lại, hoặc chỉ chọn một bảng. Cùng một công ty: Export là *Exporter Code*, Import là *Importer Code* |
| Thấy yêu cầu của người khác | Danh sách dùng chung cả nhóm | Bấm **Only mine** |

---

## 🛠️ Phần cho admin

### Ai làm gì

| Vai trò | Việc | Cần biết code? |
|---|---|---|
| 👩‍💼 Người dùng (Sales / MKT…) | Mở `BulkEx.html`, chọn điều kiện, bấm nút, mở file kết quả | Không |
| 👨‍💻 Admin (người giữ máy có database) | Nháy đúp `CAI-DAT.bat` một lần, giữ máy bật | Không |
| 🖥️ Runner (chạy nền mỗi 2 phút) | Quét bảng, đọc yêu cầu, chạy truy vấn an toàn, ghi file Excel / CSV | — |

### Luồng chạy

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

### Cài đặt (một lần)

1. Máy cần **Python 3.11+** (nếu chưa có, `CAI-DAT.bat` sẽ mở trang tải và chỉ cách cài).
2. Nháy đúp **`CAI-DAT.bat`** ở thư mục gốc. Trình cài đặt tự:
   - đăng nhập PostgreSQL bằng mật khẩu đã lưu trên máy — **chỉ hỏi mật khẩu khi không tìm được cái nào dùng được**;
   - tìm bảng Export / Import trong mọi database (tên database, schema, bảng khác nhau cũng được);
   - cho chọn thư mục chung (OneDrive để dùng thật, hoặc Downloads để thử) và đặt `BulkEx.html` vào đó;
   - đặt OneDrive: `input/` + `_system/` luôn trên máy, `output/` chỉ giữ trên mây;
   - cài lịch chạy nền mỗi 2 phút, gỡ lịch cũ của v6.
3. Chia sẻ thư mục chung trên OneDrive cho người dùng (quyền **Can edit**).

Cập nhật: chỉ cần **Pull** code mới trên máy có database. Mỗi lượt (2 phút) runner tự chép `BulkEx.html` và `Help.html` mới ra thư mục chung và đọc lại `app/labels.yaml`. Chạy lại `CAI-DAT.bat` chỉ khi đổi thư mục, đổi mật khẩu hoặc cài máy mới.

### Hỏng thì làm gì

| Hiện tượng | Cách xử lý |
|---|---|
| Trang báo không có danh sách trường | Runner chưa chạy lần nào: chạy lại `CAI-DAT.bat` |
| Yêu cầu nằm mãi ở "sent, waiting" | Máy có database đang tắt / ngủ, hoặc OneDrive chưa đồng bộ |
| "The database can't be reached" | PostgreSQL chưa chạy; yêu cầu sẽ tự chạy lại khi database lên |
| Thiếu tháng mới | Bảng tháng đó chưa có, hoặc tên bảng không có năm-tháng (xem `_system/tables.json`) |
| Yêu cầu nằm mãi ở "waiting", log ghi "Waiting for OneDrive" | Trên máy có database: chuột phải thư mục BulkEx → **Always keep on this device**; kiểm tra ổ còn chỗ và OneDrive không bị tạm dừng |
| "The database computer is almost out of disk space" | Ổ máy có database còn dưới 5 GB trống: dọn ổ rồi gửi lại (ngưỡng `min_free_gb` trong `config/bulkex.yaml`) |
| Cột hiện tên gốc tiếng Việt | Thêm tên tiếng Anh vào `app/labels.yaml` |

### Kết quả lớn cỡ nào thì ra gì

| Số dòng Detail | File nhận được |
|---|---|
| đến 1 triệu | Excel, 1 sheet Detail |
| 1 – 3 triệu | Excel, chia sheet Detail (1), (2), (3) |
| trên 3 triệu | toàn bộ CSV (Detail + Summary), không có Excel |
| trên 10 triệu | từ chối, khuyên lọc hẹp hơn |

Các ngưỡng chỉnh trong `config/bulkex.yaml` (`xlsx_max_rows`, `max_rows`, `csv_max_rows`, `query_timeout_minutes`). **Check row count** báo trước bằng chữ cam khi kết quả sẽ lớn.

### Dọn dẹp

- **Recent requests** đọc thẳng từ `_system/done` và `_system/failed`: xoá file ở đó là sau ~2 phút mọi người hết thấy dòng đó.
- File kết quả trong `output/` không tự xoá: admin xoá tay khi cần.
- Nhật ký nằm trong thư mục chung, không nằm trong repo: `_system/log/bulkex.log` (lỗi chi tiết) và `_system/log/requests.csv` (ai lấy gì, lúc nào).

### Đổi tên trường

Tên trên trang lấy từ `app/labels.yaml`: `en` là tên tiếng Anh (viết thường, gạch dưới), `vi` là tên tiếng Việt hiện ở trang Help, `swap_with` là trường cùng vai ở bảng kia (dùng khi Copy to Import/Export), `group` là nhóm, `essential: true` đưa vào bộ Essentials, `default_op` là cách so mặc định. Trường có nghĩa khác nhau giữa hai bảng ghi `en: {export: ..., import: ...}`. Sửa xong thì cập nhật luôn bảng tra trong README này.

### Cấu trúc

```text
CAI-DAT.bat            trình cài đặt (nháy đúp)
app/web/BulkEx.html    trang người dùng (bản gốc; runner tự chép ra thư mục chung)
app/web/Help.html      trang hướng dẫn tiếng Việt (bảng tra tên trường đọc từ catalog)
app/bulkex/            runner: scan, catalog, query, runner, setup, onedrive
app/labels.yaml        tên tiếng Anh, tên tiếng Việt (vi), nhóm, cột Essentials, cách so sánh mặc định
app/datasets.yaml      cách nhận bảng Export / Import, cột số lưu dạng chữ
config/                cấu hình riêng máy (mật khẩu, kết nối) - không lên Git
tests/v7/              phép thử (cần PostgreSQL: đặt BULKEX_TEST_PG)
handoff/               hồ sơ điều phối dự án
```
