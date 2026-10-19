Mã:         BX-01
Mạch:       BX - SQL BulkEx
Nối tiếp:
Giao cho:   claude-ceo [COWORK-EXEC]
Trạng thái: chờ-nghiệm-thu
Vòng:       1/2

## ĐỀ BÀI

**Mục tiêu nghiệp vụ**

Đưa repo SQL BulkEx về đúng Chuẩn Bàn Giao v1.1 để mọi phiên làm việc sau (bản v7 với BulkEx.html)
chỉ có một phòng điều phối duy nhất, đọc nhanh, không lạc vào tài liệu cũ.

**Ngoài phạm vi**

- Không đổi hành vi của runner, portal, trình cài đặt hay file mẫu Excel đang chạy ở máy HAN.
- Không làm tính năng mới (BulkEx.html, quét tự động - để phiếu sau).

**Kế thừa**

(phiếu đầu mạch)

**Kịch bản nghiệm thu**

Chairman chưa viết kịch bản riêng. Lệnh gốc của Chairman ngày 2026-10-19: "Cải tổ lại hết đi. Theo chuẩn mới".
Đề xuất để Chairman kiểm khi ký: mở thư mục repo -> thấy `AGENTS.md` ở gốc và `handoff/` chỉ gồm
RULES/STATE/MAP, `docs/`, `shots/`, `archive/` và phiếu này; không còn todo/audit/history/failure ở chỗ cũ;
runner vẫn chạy như trước.

## TODO

- [x] Đọc chuẩn v1.1 và mẫu đã cải tổ ở repo aog-watcher-extension (RF-01) để làm cùng một kiểu.
- [x] Liệt kê dấu vết bàn giao cũ và lập bảng ánh xạ (Chairman duyệt trong chat 2026-10-19 10:21).
- [x] Kiểm toàn vẹn file trước/sau khi dời.
- [x] Dời file theo bảng ánh xạ; tạo `AGENTS.md`, `RULES.md`, `STATE.md`, `MAP.md`, `docs/`, `shots/`, `archive/README.md`.
- [x] Lọc luật còn sống từ `log/failure.md` và `handoff/handoff.md` lên `RULES.md`.
- [x] Sửa `.gitignore` để phòng bàn giao đi theo Git; sửa 2 dòng trỏ đường dẫn cũ trong README.
- [x] Quét toàn repo tìm đường dẫn cũ còn sót.
- [x] Chạy lại test trên bản sao.
- [ ] Commit (chờ Chairman - không commit từ phiên Linux).

## AUDIT

### Ghi chú trước thao tác

- Việc gì: dời 13 file (2 file > 5 KB là `.xlsx` 794 KB và `.docx`), không xoá file nào.
- Lý do: hợp nhất về một phòng bàn giao theo chuẩn v1.1.
- Phạm vi ảnh hưởng: chỉ tài liệu và file điều phối; không chạm `*.py`, `*.yaml`, `*.bat`, `request_template.xlsx`, `tests/`.
- Cách lùi lại: `git checkout -- docs/` cho file đã theo dõi; file chưa theo dõi chuyển ngược theo `handoff/archive/README.md`.
- Phát hiện: `.gitignore` từng loại `handoff/` và `log/*` -> todo/audit/handoff/history/failure chưa từng vào Git.
  Vì vậy chuẩn "repo có Git thì xoá thẳng" KHÔNG áp dụng; các file này được chuyển vào `archive/`, không xoá.

### Báo cáo của bên làm

**Đã làm - bảng ánh xạ**

```
handoff/handoff.md, todo.md, audit.md     -> handoff/archive/legacy-coordination/
log/history.md, log/failure.md            -> handoff/archive/legacy-coordination/
docs/CODEX_ORDER_v6.md, _v6_1.md          -> handoff/archive/legacy-docs/
docs/SPEC_v5_archived.md                  -> handoff/archive/legacy-docs/
docs/SPEC.md                              -> handoff/docs/SPEC-bulkex-v6.md
docs/20260530_Automate_Query_SQL.docx     -> handoff/docs/REF-20260530_Automate_Query_SQL.docx
docs/SQL_Code-Standardization.xlsx        -> handoff/docs/REF-SQL_Code-Standardization.xlsx
handoff/handoff-standard-v1.1.md          -> handoff/docs/REF-handoff-standard-v1.1.md
docs/HUONG_DAN_SU_DUNG.md, log/requests.csv, log/runner.log  -> giữ nguyên (thuộc sản phẩm)
.gitignore: bỏ "handoff/" và "AGENTS.md"; "docs/*.docx" -> "handoff/docs/*.docx"; thêm "handoff/shots/*.gif"
```

**Lệnh và output** (chạy từ phiên Linux nối vào thư mục Windows)

```text
> so khớp file đã dời với bản trong HEAD (git rev-parse HEAD:<cũ> vs git hash-object <mới>)
MATCH docs/CODEX_ORDER_v6_1.md
MATCH docs/SQL_Code-Standardization.xlsx
DIFF  docs/CODEX_ORDER_v6.md, docs/SPEC_v5_archived.md, docs/SPEC.md
> so lại 3 file DIFF sau khi bỏ ký tự CR (xuống dòng kiểu Windows)
MATCH (bỏ qua CRLF) docs/CODEX_ORDER_v6.md
MATCH (bỏ qua CRLF) docs/SPEC_v5_archived.md
MATCH (bỏ qua CRLF) docs/SPEC.md
=> 5/5 nội dung nguyên vẹn

> git diff --stat -- '*.py' '*.yaml' '*.bat' '*.xlsx' tests
 docs/SQL_Code-Standardization.xlsx | Bin 793678 -> 0 bytes   (chính là file đã dời, không phải file chức năng)

> python -m pytest -q   (trên bản sao, sau cải tổ)
107 passed, 4 skipped in 3.30s

> grep đường dẫn cũ ngoài archive/
AGENTS.md:15-16                         lệnh cấm tái tạo - cố ý
REF-handoff-standard-v1.1.md:483-484   nội dung của bản chuẩn - cố ý
README.md:522                           trỏ đường dẫn mới trong archive - cố ý
SPEC-bulkex-v6.md (6 chỗ "docs/SPEC")  nội dung lịch sử của đặc tả đã chốt - giữ nguyên văn
```

**Lệch so với đề bài:** Có một điểm - `REF-handoff-standard-v1.1.md` là bản chép của tài liệu còn sống
(chuẩn mục 13 cấm chép). Giữ lại vì Chairman chủ động đặt vào; ghi ở STATE để Chairman quyết.
Phép thử chạy trên Linux, chưa chạy trên Windows: `[RUNTIME CHƯA KIỂM]` cho phần "runner vẫn chạy như trước".

**Câu hỏi treo cho Chairman:** giữ hay bỏ bản chép chuẩn trong repo; ai commit (đề xuất: Claude Code trên máy Windows).

### Soi của Claude

Không áp dụng - Claude là bên làm phiếu này; soi tĩnh độc lập cần một phiên khác.

### Ô ký nghiệm thu

(chờ Chairman)

## HISTORY

### 2026-10-19

Failure    Không hỏng gì. Suýt áp sai luật "repo có Git thì xoá thẳng": các file bàn giao cũ bị .gitignore loại
           nên không có trong Git; xoá sẽ mất vĩnh viễn.
           Báo lỗi giả: không   (3 file báo DIFF hoá ra chỉ khác ký tự xuống dòng - đã kiểm lại trước khi kết luận)
Lessons    Trước khi xoá theo luật "có Git", kiểm file đó có thật sự được Git theo dõi không.
           So khớp file Windows từ Linux phải bỏ qua CRLF trước khi kết luận hỏng.
           -> đã lên RULES.md ngày 2026-10-19 (mục "Phiên chạy từ môi trường Linux")
-- claude-ceo - 2026-10-19 10:50 UTC+7
