# Standing rules - SQL BulkEx

Sinh từ: Chuẩn Bàn Giao v1.1 (2026-08-25). Bản tham chiếu: `handoff/docs/REF-handoff-standard-v1.1.md`;
bản gốc sống trong vault. Lệch phiên bản thì đề xuất cập nhật, không tự sửa.

## Chế độ chỉ huy

- Chỉ huy hiện tại ghi ở `STATE.md` (`claude` hoặc `codex`), không ghi ở đây.
- `Chỉ huy: claude` - Claude viết đề bài, Codex thực thi, Claude soi tĩnh và đóng.
  `Chỉ huy: codex` - Codex tự viết đề bài, tự thực thi, gắn `[AUTO]`; Claude soi tĩnh khi quay lại.
- Khi Codex hết usage/bận hoặc Chairman yêu cầu trực tiếp, Claude được giải trừ: toàn quyền kỹ thuật
  và thực thi, phiếu gắn `[COWORK-EXEC]`. Phạm vi nghiệp vụ vẫn chờ Chairman; kết luận runtime trên
  Windows vẫn gắn `[RUNTIME CHƯA KIỂM]` cho tới khi có lệnh + kết quả chạy trên Windows dán vào.
- Quyết định nghiệp vụ và phạm vi luôn thuộc Chairman.

## Quyền ký nghiệm thu - theo đường lấy bằng chứng

- Claude được ký thứ nhìn thấy qua trình duyệt thật trên máy Chairman, bắt buộc kèm ảnh trong `shots/`.
- Claude không được ký thứ chỉ máy Windows phán được (phép thử đạt/hỏng, toàn vẹn file, mã hoá ký tự,
  kết quả lệnh) - bên thực thi chứng minh bằng lệnh + kết quả dán vào.
- Chairman ký nghiệm thu nghiệp vụ. Kết quả chỉ dùng `ĐẠT`, `HỎNG`, `KHÔNG ĐO ĐƯỢC` (+ lý do).
- Mỗi mục HISTORY và ô ký có chữ ký kèm giờ và múi giờ: `-- claude-ceo - 2026-10-19 10:40 UTC+7`.

## Trần lặp và leo thang

- Tối đa hai vòng sau `HỎNG`. Hai lần `HỎNG` -> `chờ-chairman` kèm hai phương án nén; không có vòng ba.
- `KHÔNG ĐO ĐƯỢC` không tính là một vòng; sửa phép đo, không sửa sản phẩm theo phỏng đoán.

## Bốn câu của Chairman

```
1  "Kịch bản nghiệm thu là gì? Đọc cho tôi bằng tiếng Việt: ai bấm gì, thấy gì,
    trong bao lâu."
    -> không đọc được bằng ngôn ngữ nghiệp vụ = việc chưa đủ rõ để bắt đầu

2  "Đã chạy chưa? Dán lệnh và kết quả vào."
    -> không có kết quả dán vào = chưa xong. Không tranh luận.

3  "Làm hỏng thử một chỗ đi - phép thử có đỏ lên không?"
    -> chống phép thử giả. Đập vỡ mà đèn vẫn xanh thì phép thử đó là đồ trang trí.

4  "Có chỗ nào KHÔNG ĐO ĐƯỢC không? Vì sao?"
    -> chống trường hợp cửa bị chặn quyền nên không trả dữ liệu, mà phép thử báo
       trông y hệt lỗi khuôn.
```

Luật kèm theo: Claude không được đề xuất kiến trúc, thư viện, cấu trúc file hay khuôn thiết kế
(trừ khi đang `[COWORK-EXEC]`). Vi phạm thì Chairman xoá, không chuyển tiếp.

## Luật phòng bàn giao

- Phiếu: `{YYYYMMDD}_{MÃ}-{số}_{tên-việc}.md`. Mạch hiện có: `BX` (SQL BulkEx).
- Trạng thái chỉ đẩy tiến: `chờ-đề-bài -> đang-làm -> chờ-nghiệm-thu -> đóng-đạt | chờ-chairman ->
  đóng-huỷ | đóng-hỏng`. Đóng rồi không mở lại, không dời file.
- Ảnh: `shots/{YYYYMMDD}_{MÃ-số}_{stt}_{mô-tả}.png`; ảnh không phiếu nào trỏ tới thì xoá khi đóng phiếu.
- Mỗi phiên chỉ đọc `RULES.md` + `STATE.md` + đúng một phiếu; `MAP.md` khi đụng kiến trúc;
  không đọc `archive/` trừ khi Chairman chỉ định.
- Dời hoặc xoá file > 5 KB, hoặc > 10 file một lần: ghi "Ghi chú trước thao tác" (việc gì, lý do,
  phạm vi ảnh hưởng, cách lùi lại) vào AUDIT của phiếu TRƯỚC khi làm.
- Phiên chạy từ môi trường Linux lên thư mục Windows: đọc Git bằng `--no-optional-locks`, không
  commit từ đó; chạy test trên bản sao riêng, không chạy trong thư mục repo.
- So khớp file Windows từ Linux phải bỏ qua ký tự CR trước khi kết luận file khác/hỏng.
- Trước khi xoá bản cũ theo luật "repo có Git thì xoá thẳng", kiểm file đó có thật sự được Git theo dõi
  (`git ls-files`); file bị `.gitignore` loại thì chuyển vào `archive/`, không xoá.

- File cũ (mã hoặc tài liệu) không tận dụng được: chuyển vào `handoff/archive/`, không xoá.
  Chairman tự xoá tay thư mục này (quyết định 2026-10-19). `archive/` có thể trống bất cứ lúc nào.

## Luật sản phẩm còn hiệu lực

- Mọi câu SQL dựng bằng `psycopg2.sql` (Identifier cho tên bảng/cột, tham số cho giá trị).
  Không bao giờ ghép chuỗi SQL từ nội dung người dùng gửi lên.
- Tên trường và phép so sánh từ request phải nằm trong danh mục đã quét; ngoài danh mục thì từ chối.
- Runner chạy nền không bao giờ hỏi mật khẩu bằng bàn phím: đọc YAML, rồi `.password`, không có thì
  thoát với log rõ ràng.
- Đọc `.password` bằng `utf-8-sig` (PowerShell có thể ghi BOM).
- Mọi entry point in tiếng Việt ra console phải gọi `configure_stdio()` trước khi in.
- Workbook mở bằng `openpyxl.load_workbook(..., read_only=True)` phải đóng trong `finally` trước khi
  dời/xoá file đó (Windows khoá file đang mở).
- Tham số mặc định trỏ tới hằng đường dẫn của module phải là `None` và resolve lúc gọi hàm.
- Config tiêm vào để test phải kiểm bằng `is None`; `{}` có thể là giá trị cố ý.
- Không commit `.password`, `connection.yaml`, `settings.yaml`, `column.yaml`, `jobs.yaml` -
  chúng là cấu hình riêng từng máy.
- Trước khi dùng một API thư viện chưa từng dùng trong repo (ví dụ named range của openpyxl),
  kiểm phiên bản đã cài, không đoán.
