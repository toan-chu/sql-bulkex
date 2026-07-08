# Lệnh cho Codex — Build SQL BulkEx v6 end-to-end

**Từ:** Ryan (qua Cowork/Claude)
**Ngày:** 2026-07-08
**Task:** Build hoàn chỉnh v6 theo `docs/SPEC_v6.md`, chạy full đầu cuối, không dừng giữa chừng chờ Ryan trừ khi gặp ambiguity thật sự.

---

## Prompt (paste vào Codex)

```
Bạn là Codex đang làm việc trên repo sql-bulkex (branch mới: v6). Đọc kỹ docs/SPEC_v6.md từ đầu tới cuối trước khi code — spec dài 14 section, mọi quyết định thiết kế đã chốt với Ryan qua nhiều vòng trao đổi.

MỤC TIÊU: Build v6 end-to-end. 9 step (Section 10 spec). Build tuần tự — hoàn tất step N + test pass trước khi qua N+1. Sau mỗi step: chạy pytest, verify Green. Không dùng skip hàng loạt để "pass giả".

NGUYÊN TẮC CỐT LÕI (đọc kỹ):

1. **Registry pattern nghiêm ngặt.** Sau khi Step 1 xong, không được có `if op == "eq"` hay `elif op == "prefix"` hardcode ở bất kỳ đâu trong runner.py hoặc code path build SQL. Tất cả logic operator phải đi qua `OperatorBuilder`. Nếu tôi (Ryan) sau này thêm entry `neq` vào operators.yaml → phải hoạt động ngay mà không đụng code Python. Test T32 verify.

2. **Backward compat v5.** File request v5 (cột Toán tử là code text "eq/in/prefix/contains/between", không có cột Digits) phải vẫn parse được với runner v6. Warning "template v5, khuyến nghị download v6" — không reject.

3. **PostgreSQL, không SQL Server.** Repo dùng psycopg2. SPEC dùng `LENGTH()` (PostgreSQL) không phải `LEN()` (SQL Server). Nếu Ryan có nói SQL Server ở chỗ khác → sai, giữ PostgreSQL.

4. **Không dùng Power Automate, không SMTP, không Teams.** Approval qua drag-drop OneDrive folder. Requester tự nhắn admin qua Zalo. Không code integration nào ngoài `attrib +U -P` cho Files On-Demand.

5. **KHÔNG đổi:** portal.py, connection.yaml, .password, jobs.yaml, core query engine. Chỉ đổi runner.py, thêm operators.yaml/py, update column.yaml/settings.yaml schema, regen request_template.xlsx.

6. **`attrib +U -P` chỉ chạy trên Windows với OneDrive Files On-Demand.** Nếu fail (VD Linux CI hoặc OneDrive không active) → log warning, không raise. Test T61 mock subprocess.

7. **File `[DONE] ` prefix có khoảng trắng sau `]`** — quan trọng để visual dễ đọc trên OneDrive Explorer. Runner filter chính xác `startswith("[DONE] ")`.

8. **Sheet Values hidden** (`sheet_state = 'hidden'`) — không phải `veryHidden`. Admin có thể unhide qua Excel nếu cần edit tay.

9. **Log CSV append-only.** Không rotate, không lock file. Nếu file đang mở (Excel) → catch PermissionError → retry sau 1s × 3 lần → nếu vẫn fail thì log ra runner.log và tiếp tục.

10. **Test verify thật, không mock quá đà.** Test operator builder + parse + folder flow dùng logic thật. Chỉ mock:
    - `subprocess.run(["attrib", ...])` (Windows-only)
    - `wb.properties.lastModifiedBy` (khi test file test không có)
    - pg_stats query nếu pgserver không có ANALYZE

BUILD ORDER (nghiêm ngặt tuần tự — Section 10 spec):

Step 1: operators.yaml + operators.py + refactor runner.py loại hardcode operator. Tests T30-T37 pass.
Step 2: --scan-values CLI + column.yaml schema mở rộng. Tests T38-T41 pass.
Step 3: Excel template v6 (5 sheet, dropdown VN, cột Digits, sheet Values, named range). Tests T42-T47 pass.
Step 4: parse_column_sheet_v6 với 5 cột + map VN + validate Digits + backward compat. Tests T48-T54 pass.
Step 5: settings.yaml folders schema + poll folders.approved/ + rename [DONE] + [LOI]_ trong 02_Approved/. Tests T55-T58 pass.
Step 6: --cleanup CLI với attrib +U -P. Tests T59-T61 pass.
Step 7: log/requests.csv structured + lastModifiedBy + requester tracking. Tests T62-T64 pass.
Step 8: E2E integration test với pgserver + folder mock + attrib mock. Tests T65-T67 pass.
Step 9: Update README song ngữ v6, archive docs/SPEC.md → docs/SPEC_v5_archived.md, update docs/HUONG_DAN_SU_DUNG.md (nếu Cowork chưa update thì để nguyên, không xoá).

VERIFICATION CUỐI:

- Chạy `pytest -v` → 99/99 pass (61 v5 + 38 v6). Nếu skip: chỉ skip pgserver Windows (existing exemption v5).
- Grep verify không còn hardcode operator:
  ```
  grep -n 'op == "eq"\|op == "in"\|op == "prefix"\|op == "contains"\|op == "between"\|op == "suffix"' runner.py
  ```
  → chỉ được match trong docstring hoặc comment, không match trong code logic.
- Chạy verification checklist Section 14 spec (14 mục checkbox).

BÁO CÁO KHI XONG:

Format báo cáo:
```
## Step 1: [status] [x/y tests] [duration]
Diff: +N/-M dòng, +K files
Notes: [nếu có ambiguity/decision]

## Step 2: ...
...

## Final:
- Total diff: +N/-M dòng
- Total files changed: X
- Tests: 99/99 pass
- Verification checklist: 14/14 ✓
- Commits: [list SHA + message]
- Branch: v6, chưa push (chờ Ryan review push)
```

KHI GẶP AMBIGUITY:

Dừng lại. Ghi vào `docs/CODEX_QUESTIONS_v6.md` câu hỏi cụ thể + option đề xuất. Không tự quyết. Ping bằng cách echo "PING Ryan" ở output cuối và exit non-zero.

Được rồi, bắt đầu. Đọc SPEC_v6.md → xác nhận hiểu → build Step 1.
```

---

## Cách gọi Codex (từ terminal của Ryan)

```powershell
cd C:\Users\RYAN TOAN\Downloads\GIT\sql-bulkex
git checkout -b v6
# Paste prompt ở trên vào Codex CLI hoặc IDE
codex "$(cat docs/CODEX_ORDER_v6.md | sed -n '/^## Prompt/,/^---/p')"
```

Hoặc mở Codex trong IDE, paste block `## Prompt (paste vào Codex)` → chạy.

---

## Sau khi Codex báo cáo xong

Cowork review từng step diff → merge nếu OK → Ryan push GitHub → pilot test trên máy admin Hà Nội.

Không tự động merge master. v6 là branch riêng.
