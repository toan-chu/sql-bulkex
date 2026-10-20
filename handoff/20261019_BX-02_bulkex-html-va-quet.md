Mã:         BX-02
Mạch:       BX - SQL BulkEx
Nối tiếp:   BX-01
Giao cho:   claude-ceo [COWORK-EXEC]
Trạng thái: đang-làm
Vòng:       1/2

## ĐỀ BÀI

**Mục tiêu nghiệp vụ**

Người không biết SQL tự lấy dữ liệu xuất/nhập khẩu bằng một trang web dễ dùng, ghép được nhiều điều kiện
(và/hoặc, loại trừ), không phải điền file Excel dạng lưới. Cài đặt bằng nháy đúp, tự quét database dù tên
database/schema/bảng mỗi máy mỗi khác, không phải mở cmd.

**Ngoài phạm vi**

- Không mở database ra internet; vẫn đi qua OneDrive (hoặc thư mục bất kỳ khi thử).
- Không có bước admin duyệt (Chairman bỏ ngày 2026-10-19).
- Không làm phân quyền theo người dùng ở phiếu này.

**Kế thừa**

- BX-01: phòng bàn giao theo chuẩn v1.1; file cũ không dùng lại -> `handoff/archive/`, Chairman xoá tay.
- Giao diện tiếng Anh, theo màu Trustana (#4d148c tím, #ff6200 cam), chữ Quicksand/Montserrat.
- Máy HAN đang chạy v6; v7 không được làm hỏng v6 cho tới khi cài lại bằng trình cài đặt mới.

**Kịch bản nghiệm thu**

Lời Chairman ngày 2026-10-19: "tôi tự chạy thử máy tôi, pull vài hs code + vài mặt hàng ra xem thử work ko là bik ngay".
Diễn giải để đo: Chairman cài trên máy mình bằng nháy đúp -> mở BulkEx.html -> lọc theo vài mã HS và vài
mô tả mặt hàng -> nhận file kết quả đúng các dòng đó trong output/. Không được phải gõ lệnh nào.

## TODO

- [x] Vẽ kiến trúc v7 vào MAP.md trước khi code.
- [x] Vòng góp ý 1: `app/web/BulkEx.html` chạy bằng danh mục mẫu `app/web/_system/catalog.js` (sinh từ column.yaml máy Chairman) -> chờ Chairman góp ý.
- [x] Vòng góp ý 2 (Chairman 11:13): chọn cả Export + Import; chọn tháng lẻ bằng lưới năm × tháng; tên cột theo bản dịch
      của Chairman (`app/labels.yaml`, Title Case, HS viết hoa); bố cục mới: nhóm Goods/Parties/Value/Duty & Tax/Logistics/Declaration,
      cột kết quả dạng thẻ + bộ Essentials thay cho tường checkbox. Danh mục mẫu: `python app/tools/sample_catalog.py`.
- [x] Vòng góp ý 3 (Chairman 11:29): ô tháng thẳng hàng, chọn = cam; Export + Import chọn tháng riêng từng bảng;
      Summary đổi chữ ("One row for each", "Add up") + bảng xem trước cột kết quả; rê chuột hiện tên cột gốc;
      cột thiếu tên -> hiện tên gốc + báo ở chân trang (`label_report`).
- [x] Dọn gốc: code v6 -> `app/v6/`, cấu hình -> `config/`, `request_template.xlsx` -> archive, `conftest.py` -> `tests/`.
- [x] Vòng góp ý 4 (Chairman 12:00): Detail và Summary tick được cùng lúc (1 file 2 sheet); "My columns" riêng từng người
      + Essentials chung của công ty (`essential: true` trong labels.yaml); My presets lưu trên máy người dùng: mở, sửa, Update,
      Save as new, Delete, Back up/Restore ra file. Kiểm: lưu preset + My columns -> tải lại trang -> còn nguyên, ERRORS [].
- [x] Vòng góp ý 5 (Chairman 12:15): bỏ "My columns" - cột/kết quả tự nhớ theo từng bảng trên máy người dùng, Essentials là điểm xuất phát;
      mọi dropdown dùng chung một mũi tên, cùng lề; Recent requests hiện câu mô tả + Open file + Use again, lọc "của tôi / mọi người";
      My presets và Recent requests gập/mở được (nhớ trạng thái). Kiểm: gửi -> tải lại -> cột còn 9, Use again nạp lại đúng câu, ERRORS [].
- [x] Vòng góp ý 6 (Chairman 12:35): khung gập/mở trượt mượt (220-260ms, tắt khi máy bật giảm chuyển động); Quick pick 3/6/9/12 tháng;
      trường ghép cặp VN Company Tax Code / VN Company Name / Foreign Partner Name cho Export + Import; nút đổi tên
      "Check row count" / "Get the file" kèm giải thích; "Link folder" thành bước một lần có nút "Choose BulkEx folder".
      Ghi chú: danh sách xổ xuống của ô chọn là của trình duyệt, không tạo hiệu ứng được nếu không tự dựng lại ô chọn.
- [x] Vòng góp ý 7 (Chairman 12:45): bỏ trường ghép cặp; Export + Import -> Filters và Result tách riêng từng bảng (tab trượt),
      nút "Copy to Import/Export" (bỏ qua trường bảng kia không có); trường đã lọc tự vào file (thẻ cam "filter", không gỡ được);
      nút chuyển có viên chọn trượt (0,34s). Request đổi sang `parts[]`. Preset kiểu cũ vẫn mở được.
      Kiểm: 2 bảng + copy (bỏ qua Exporter Code) -> JSON đúng 2 phần; 1 bảng; preset lưu/mở; preset cũ; ERRORS [].
- [x] Runner v7 (`app/bulkex/`): quét mọi DB/schema/bảng theo bộ cột (`app/datasets.yaml`), đọc năm-tháng trong tên bảng,
      ghi catalog.js (không chứa tên DB) + status.js; đọc input/*.json -> kiểm danh mục -> SQL tham số -> Excel (Request/Detail/Summary,
      >1 triệu dòng thành CSV) -> output/; kết nối chỉ đọc + statement_timeout; giới hạn số dòng; khoá 1 lượt; DB mất kết nối thì giữ lại thử sau.
      Cách so sánh mặc định (HS starts with...) chuyển vào labels.yaml (`default_op`).
- [x] Trình cài đặt `CAI-DAT.bat` -> `app/bulkex/setup.py`: mật khẩu đã lưu (config/.password, pgpass.conf, PGPASSWORD) dùng luôn,
      chỉ hỏi (gõ ẩn) khi không cái nào đăng nhập được; quét; chọn thư mục (OneDrive / Downloads / tự gõ); chép BulkEx.html;
      values.json; chạy lượt đầu; gỡ lịch v6, cài "BulkEx Runner" 2 phút. README viết lại cho v7.
- [x] Dọn gốc: mọi file v6 -> `handoff/archive/v6-retired/` (cả thư mục archive đã gitignore, chờ Chairman xoá).
- [ ] Test trên bản sao; bàn giao chờ nghiệm thu.

## AUDIT

### Báo cáo của bên làm (vòng góp ý giao diện)

- File mới: `app/web/BulkEx.html` (1 file, không cần cài gì); `app/web/_system/catalog.js`, `status.js` là dữ liệu MẪU (đã gitignore).
- Kiểm bằng Chromium headless trên Linux: điền HS 8471/8473 + nhóm (mô tả chứa laptop/notebook/máy tính xách tay HOẶC exporter chứa DELL) + nước không phải CN.
```text
Get export records from Jul 2026 to Sep 2026 where HS code starts with 8471 or 8473 and (Product description contains
laptop, notebook or máy tính xách tay or Exporter name contains DELL) and Partner country is not CN.
no problems
ERRORS ["Failed to load resource: net::ERR_TUNNEL_CONNECTION_FAILED"]   <- Google Fonts bị chặn trong môi trường thử, không phải lỗi trang
```
- `[RUNTIME CHƯA KIỂM]`: ghi thẳng vào thư mục khi mở bằng nháy đúp trên Chrome/Edge Windows; nếu bị chặn trang tự tải file về.

### Báo cáo dọn gốc (vòng 3)

```text
> pytest trên bản sao sau khi dời (lần 1)
9 failed, 98 passed, 4 skipped     <- test_v6_operators đọc "operators.yaml" theo đường dẫn tương đối
> sửa test trỏ operators.OPERATORS_FILE (không đổi logic), chạy lại
107 passed, 4 skipped in 3.20s     <- bằng đúng trước khi dời
> sample_catalog.build với 1 cột không có tên + 1 tên thừa
[('phan_ghi_chu', 'phan_ghi_chu', 'Other'), ('cot_moi_xyz', 'cot_moi_xyz', 'Other')] {'unlabeled': ['cot_moi_xyz', 'phan_ghi_chu'], 'unused': ['ghost_col']}
```

### Báo cáo runner v7

```text
> BULKEX_TEST_PG=... pytest -q tests/v7       (PostgreSQL 16 thật, môi trường Linux của Claude)
21 passed in 2.23s
> làm hỏng: starts_with -> contains            lần đầu: 21 passed  <- phép thử trang trí, dữ liệu không có mã chứa 8471 ở giữa
  thêm TK8 '30847100', làm hỏng lại            2 failed (đúng)
> làm hỏng: ghép giá trị thẳng vào SQL         1 failed: test_quote_in_a_value_is_just_text (đúng)
> trọn vòng: python app/bulkex scan/values/once + BulkEx.html (Chromium) -> gửi "HS Code starts with 8471"
  recent: HS 8471 test | Ryan, ready, 4 rows | Open file | Use again        ERRORS []
> pytest -q trên bản sao repo (máy Chairman, Linux VM, không có PostgreSQL)
  v6: 107 passed; v7: skipped (không có BULKEX_TEST_PG)
```
Lỗi phép thử bắt được trước khi giao: trường đã lọc chưa tự vào cột phía runner; sắp xếp khi tháng nằm ở 2 database bị sai thứ tự (đã trộn theo khoá).
`[RUNTIME CHƯA KIỂM]` trên Windows + PostgreSQL thật của Chairman.

### Báo cáo trình cài đặt

```text
> pytest -q tests/v7 (PostgreSQL thật)            26 passed
> làm hỏng: bỏ qua mật khẩu đã lưu                3 failed (đúng: không-hỏi / pgpass / cài trọn vòng)
> python app/bulkex setup (Linux, chọn Downloads)  [1/5] OK đăng nhập bằng mật khẩu đã lưu - không cần nhập ... [5/5] Bỏ qua: không phải Windows
> pytest -q trên bản sao repo máy Chairman        (xem dòng dưới)
```
Chairman chạy thật trên máy mình 2026-10-19 13:30 (ảnh chat): đếm HS 8471 Aug-Oct 2025 = 535.146 dòng; cả tháng 12/2025 = 6.894.930 dòng.
Vòng 8 (Chairman 13:32): Recent requests có nút × và "Clear list" (ẩn trên máy người dùng); đếm hiện "counted", hết chữ đỏ;
runner bỏ trạng thái > 30 ngày. Lỗi thật lộ ra khi PostgreSQL phía Claude tắt: database không vào được thì runner ghi đè
catalog rỗng -> trang mọi người hỏng. Đã sửa: giữ catalog cũ, yêu cầu nằm chờ. Phép thử mới đỏ khi bỏ chặn. 28/28 đạt.
Vòng 9 (Chairman 13:34-13:38): chữ xanh = xong, đỏ = lỗi; bắt buộc tên yêu cầu + tên người (trang chặn nút, runner từ chối);
>1 triệu dòng không còn ra CSV mà chia nhiều sheet Detail (1),(2),(3) trong 1 file Excel, trần vẫn 3 triệu; Check row count
cảnh báo màu cam khi lớn / vượt trần. 31/31 đạt.
Vòng 10 (Chairman 13:48, chốt): >3 triệu dòng ra TOÀN BỘ CSV (Detail + Summary, UTF-8 BOM, không Excel); trần cứng 10 triệu
(csv_max_rows, chỉnh trong config/bulkex.yaml). Log ra <thư mục chung>/_system/log, không ghi vào repo; log/ cũ chuyển vào archive.
Bỏ Clear list / ×: Recent requests dựng lại mỗi lượt từ _system/done + _system/failed (kết quả ghi luôn vào file yêu cầu, khoá _result);
admin xoá file ở đó là mọi người hết thấy. Trang chia 2 tab Done / Failed, việc đang chạy luôn hiện trên cùng. Chairman tự xoá tay
-> bỏ câu hỏi dọn 30 ngày. 34/34 đạt; 3 phép đột biến (bỏ CSV, không xoá file input, bỏ BOM) đều làm đỏ phép thử.
Vòng 11 (máy HAN 14:46-14:50, log Chairman gửi): runner chạy đều nhưng 2 file yêu cầu ở dạng đám mây OneDrive -> đọc báo
[Errno 22] Invalid argument; code cũ coi là file hỏng, ghi lỗi lặp mỗi lượt. Sửa: file chưa tải về -> trạng thái 'waiting', giữ trong input,
runner gọi attrib +P (Always keep on this device) cho thư mục chung; setup cũng đặt +P lúc cài; ghi chú quét chỉ ghi log khi thay đổi.
37/37 đạt; 2 phép đột biến đỏ. Ghi nhận nghiệp vụ: 2025-01..09 có cả vietnam_export và vn_export (runner lấy vietnam_*) - chờ Chairman xác nhận.
`[RUNTIME CHƯA KIỂM]`: attrib +P trên OneDrive/SharePoint thật ở HAN.
Vòng 12 (2026-10-20, Chairman: máy HAN hết ổ -> OneDrive không kéo được file về): pin cả thư mục chung là sai vì output/ cũng nằm
vĩnh viễn trên máy. Sửa: chỉ input/ + _system/ + BulkEx.html luôn trên máy; output/ đặt online-only (OneDrive tải lên xong giải phóng ổ);
Get the file bị từ chối khi ổ còn < 5 GB (min_free_gb), Check row count vẫn chạy. 38/38 đạt; đột biến bỏ chặn ổ -> đỏ.
`[RUNTIME CHƯA KIỂM]`: attrib -P +U trên output/ thật có giải phóng ổ sau khi tải lên hay không.
Vòng 13 (2026-10-20 16:15, Chairman sau lần export thật đầu tiên từ HAN): dòng Detail không biết thuộc tháng nào.
Sửa: mọi sheet / CSV Detail có thêm 2 cột đầu Year, Month (số, lấy từ tên bảng). Trang ghi rõ 'Year and Month are always added first'.
Nút × chỉ cho dòng 'sent' (chỉ có trong trình duyệt, chưa tới runner). 39/39 đạt.
`[RUNTIME CHƯA KIỂM]`: CAI-DAT.bat, Task Scheduler, os.startfile, ghi thẳng thư mục từ trang - chỉ Windows phán được.

## HISTORY

### 2026-10-19

Mở phiếu, gộp BX-02 (cài đặt + quét) và BX-03 (HTML + runner) theo lệnh Chairman.
-- claude-ceo - 2026-10-19 10:55 UTC+7
