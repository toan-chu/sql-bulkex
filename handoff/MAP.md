# SQL BulkEx v7 - kiến trúc hiện tại

Nguồn sự thật: file này. Vẽ lại TRƯỚC khi đổi mã cấp kiến trúc (bản BulkEx.html/JSON sắp tới
phải được vẽ ở đây trước). Lập ngày 2026-10-19 từ mã ở commit `41c0b91` (nhánh `master`;
còn nhánh `v6` song song trên remote).

## Mục đích

Cho Sales/MKT không biết SQL lấy dữ liệu tờ khai xuất/nhập khẩu từ PostgreSQL nằm trên một máy
Windows ở Hà Nội. Không có server: OneDrive vừa là giao diện vừa là đường vận chuyển.

## Ghi chú

Phần dưới mô tả v7. Kiến trúc v6 (Excel request, 01_Pending/02_Approved/03_Output, operators.yaml) đã nghỉ,
code nằm trong `handoff/archive/v6-retired/`.

## v7 (phiếu BX-02)

```text
Cài đặt 1 lần (máy có SQL)  CAI-DAT.bat
   quét DB/schema/bảng theo BỘ CỘT (không theo tên) -> config/ (riêng máy)
   tạo thư mục chung: BulkEx.html  input/  output/  _system/
   cài lịch chạy nền runner

Runner chạy nền (2 phút/lần)
   1. xem lại danh sách bảng -> tháng mới tự xuất hiện
   2. ghi _system/catalog.js   (trường + tên tiếng Anh từ app/labels.yaml, kiểu, giá trị gợi ý, các tháng có dữ liệu - KHÔNG chứa tên DB)
   3. đọc input/*.json -> kiểm theo danh mục -> dịch ra SQL của CHÍNH máy đó -> output/
   4. ghi _system/status.js    (đang chờ / đang chạy / xong / lỗi + chép lại `description` của request để trang hiện người dùng đã hỏi gì)

BulkEx.html (máy người xin, mở bằng Chrome/Edge)
   đọc _system/catalog.js + status.js bằng thẻ <script> (chạy được khi mở bằng nháy đúp)
   xuất request JSON (schema "bulkex-request/1") -> ghi thẳng vào input/ nếu trình duyệt cho phép,
   không thì tải file về để kéo vào input/
```

Request JSON (`bulkex-request/1`): `requester` · `name` · `action` (count|export) · `description` (câu tiếng Anh trang tự ghép) ·
`parts`: một phần cho mỗi bảng (Export + Import = 2 phần, 1 file):
{`dataset`, `period` {months: [YYYY-MM...]}, `filter` cây nhóm {match: all|any, items: [điều kiện {field, op, values} | nhóm con]},
`output` {rows: {columns, sort, distinct} | null, summary: {group_by, measures, top} | null}}.
Mỗi bảng có bộ lọc + kết quả riêng; trường đã lọc luôn nằm trong `columns`.
Bố cục repo (2026-10-19, sau khi gom file v6 vào `handoff/archive/v6-retired/`):

```text
CAI-DAT.bat                trình cài đặt nháy đúp -> `python app\bulkex setup`
README.md AGENTS.md LICENSE requirements.txt pytest.ini .gitignore
app/web/BulkEx.html        trang người dùng (bản gốc; setup chép ra thư mục chung)
app/bulkex/                config · scan · catalog · query · runner · setup · __main__ (once | scan | values | setup)
app/labels.yaml            tên tiếng Anh, nhóm, Essentials, default_op
app/datasets.yaml          chữ ký nhận bảng, cột số lưu dạng chữ, ngưỡng gợi ý
config/                    connection.yaml, .password, bulkex.yaml, values.json (riêng máy, không commit; chỉ connection.example.yaml)
tests/v7/                  phép thử (cần BULKEX_TEST_PG)
log/                       bulkex.log, requests.csv
```
Lịch chạy nền: Task Scheduler "BulkEx Runner" mỗi 2 phút -> `pythonw app\bulkex once` (setup gỡ "SQL BulkEx Runner/Cleanup" của v6).
