Cập nhật:  2026-10-19 13:45 UTC+7 - bởi claude-ceo
Chỉ huy:   claude [COWORK-EXEC] (Codex bận, Chairman giải trừ 2026-10-19)

## Việc đang mở

BX-01  chờ-nghiệm-thu  vòng 1/2  Cải tổ phòng bàn giao theo chuẩn v1.1
BX-02  chờ-nghiệm-thu  vòng 1/2  BulkEx.html + runner v7 + CAI-DAT.bat

## Hôm qua

- Review repo 2026-10-13: lõi ổn (107/111 test đạt trên bản sao Linux), SQL dựng an toàn, mật khẩu chưa từng lên Git.
- Chairman chốt hướng v7: giữ OneDrive; thay Excel bằng `BulkEx.html` (English UI) xuất request JSON vào `input/`,
  runner HAN đọc JSON -> SQL -> `output/`; bỏ bước admin duyệt; Claude thực thi (Claude Code trên máy Windows).
- Cải tổ BX-01 xong phần chuyển file; chưa commit.

## Vừa đóng

(chưa có)

## Đang treo, cần Chairman

- BX-01: ký nghiệm thu; commit thay đổi (nên commit từ Claude Code hoặc máy Windows, không từ phiên Linux).
- BX-02: Chairman nháy đúp CAI-DAT.bat trên máy mình -> mở BulkEx.html -> lấy vài mã HS + vài mặt hàng -> ký.
  Cần xem trên Windows: Task Scheduler chạy được; nút Choose BulkEx folder ghi thẳng được vào input/.
- Xoá tay `handoff/archive/` (đã gitignore). Commit từ máy Windows / Claude Code.
- `REF-handoff-standard-v1.1.md` là bản chép của tài liệu còn sống (chuẩn mục 13 cấm chép); giữ theo ý Chairman.

## Bẫy đã biết

- Code v6 đã dời vào `app/v6/`, cấu hình vào `config/`. Chairman (2026-10-19 12:00) sẽ xoá bản cũ ở HAN, tắt lịch chạy cũ
  và cài lại từ đầu bằng v7 -> không cần giữ tương thích v6; `app/v6/` chỉ là nguồn để v7 lấy lại code, xong thì vào archive.
- Presets và "My columns" lưu trong trình duyệt của từng người (localStorage của trang mở bằng file://);
  xoá dữ liệu trình duyệt là mất -> có nút Back up / Restore. `[RUNTIME CHƯA KIỂM]` trên Chrome/Edge Windows.
- README và `docs/HUONG_DAN_SU_DUNG.md` còn mô tả bố cục/luồng v6 - viết lại khi v7 xong.

- Chạy pytest trong thư mục repo sẽ ghi dòng giả vào `log/requests.csv` thật (21 dòng "rejected" hiện có là
  dữ liệu test). Chỉ chạy test trên bản sao cho tới khi sửa.
- Truy vấn không có giới hạn thời gian; Task Scheduler `IgnoreNew` -> một lượt treo chặn mọi lượt sau.
- Năm file trong `handoff/archive/legacy-coordination/` trước đây bị `.gitignore` loại -> đó là bản duy nhất.
- Huy hiệu README ghi 103 test đạt; số kiểm được là 107 đạt + 4 bỏ qua (trên Linux, chưa chạy trên Windows).

## Báo lỗi giả

Tháng này: 0
