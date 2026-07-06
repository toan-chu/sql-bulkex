# SPEC v4 — SQL BulkEx: Saved Jobs + Request Runner (public repo)

Cho Codex build. Đọc `handoff/HANDOFF.md` TRƯỚC — đặc biệt mục "Quirks PHẢI biết". Spec này không lặp lại quirks.
Bản 2026-07-06 rev 2 — sau feedback 9 điểm của user.

## 1. Mục tiêu

1. **Generic hóa repo để public lên git**: ai clone về cũng dùng được với PostgreSQL của họ. Không hardcode gì của DB hải quan.
2. **v4a — Saved jobs + CLI + password trong config**: lưu job từ portal, chạy lại không cần menu, không gõ password mỗi lần.
3. **v4b — runner.py**: hàng đợi request qua folder sync (OneDrive / Google Drive). Requestor thả file xlsx vào folder → máy giữ DB tự query → kết quả xuất hiện trong folder share.

**Non-goals**: web UI, API cloud, multi-server, phân quyền, real-time, cache, memory.

## 2. Nguyên tắc thiết kế

- **$0 / zero-API**: tool CHỈ đọc/ghi folder local; OneDrive/GDrive Desktop sync lo vận chuyển. Tool không biết cloud nào.
- **Không mở port DB**. Runner chạy trên chính máy giữ DB, connect localhost.
- **Secrets không vào git**: repo chỉ chứa `*.example`. Config thật (kể cả password) nằm local, trong `.gitignore`.
- **Không đổi hành vi portal.py hiện tại** (v3.2 đang dùng thật), trừ 1 thay đổi được duyệt: đọc password từ `connection.yaml` (mục 4).
- **Kiến trúc**: `portal.py` (UI terminal, admin dùng tại chỗ) và `runner.py` (headless) là 2 lớp vỏ **độc lập, ngang hàng**, cùng import chung lõi build query. Runner KHÔNG gọi/điều khiển portal.
- **Sạch runtime**: không rác sinh ra ngoài chỗ quy định (mục 3.1).

## 3. Repo layout

```
sql-bulkex/
├── portal.py                 # UI terminal (giữ nguyên flow) + --job/--list-jobs
├── runner.py                 # watcher headless
├── requirements.txt
├── README.md
├── .gitignore
├── connection.yaml.example   # host/port/user/password/databases (placeholder)
├── settings.yaml.example     # input_dir, output_dir, poll, ngưỡng an toàn, filename pattern
├── templates.yaml.example    # query templates do admin định nghĩa (mục 5)
├── request_template.xlsx     # file mẫu cho requestor — SINH RA từ templates.yaml
├── docs/                     # blueprint, spec, tài liệu phase (SPEC.md ở đây)
├── handoff/                  # HANDOFF.md + file trao đổi Claude ↔ Codex
└── log/                      # runner.log, state, tmp — chỉ .gitkeep lên git
```

Codex được phép thêm folder khi cần (vd `tests/`) — báo trong handoff. KHÔNG thêm folder memory.

### 3.1 Vệ sinh runtime (feedback #1)

- Mọi entry point set `sys.dont_write_bytecode = True` → không sinh `__pycache__/`.
- Log, state file → chỉ trong `log/`. KHÔNG đặt log trong folder sync.
- Export ghi ra **file tạm local** (`log/tmp/`) rồi `shutil.move` sang `output_dir` khi xong — folder sync không bao giờ chứa file dở dang.
- `.gitignore`: `connection.yaml`, `settings.yaml`, `templates.yaml`, `jobs.yaml`, `log/*` (trừ `.gitkeep`), `__pycache__/`, `*.pyc`, `exports/`.

## 4. v4a — Saved jobs + CLI + password

- `connection.yaml` thêm trường `password`. Portal/runner đọc từ đây; **thiếu trường mới hỏi getpass** (fallback, giữ tương thích). Bỏ getpass bắt buộc ở `main()` hiện tại.
- Sau bước review trong portal: hỏi "Lưu job này?" → tên → serialize **state** (db, schema, tables, cols, filters, split, split_len, sort, merged) vào `jobs.yaml`. KHÔNG serialize SQL.
- `python portal.py --job <tên>` chạy không menu; `--list-jobs` liệt kê.
- Chạy lại luôn build SQL mới từ state. Bảng không còn tồn tại → interactive: hỏi; headless: skip + log.
- Format khi chạy `--job`: đọc `job_export_format` từ connection.yaml, default `xlsx` (đã chốt 2026-07-06 — format không thuộc job state).
- Prompt "Lưu job?" chỉ hiện sau khi user chọn export/queue ở review — không hỏi trước fix/drop.

## 5. templates.yaml — hợp đồng giữa admin và requestor

Admin định nghĩa mỗi loại request 1 template. **Thêm loại request mới = thêm entry YAML, không sửa code** (feedback #2).

```yaml
templates:
  hs_code:
    label: "Tra theo HS code"            # hiện trong dropdown Excel
    type: select                          # v4 chỉ có select; xem 5.1
    database: my_db
    schema: public
    tables: "x_y{year}_{month}"           # pattern: {year}, {month} = 2 chữ số (01..12)
    columns: ALL                          # default khi requestor bỏ trống ô Cột
    merge: union                          # union | separate
    filters:                              # thứ tự = Giá trị 1, 2, 3 trong file request
      - column: ma_so_hang_hoa
        type: prefix                      # eq | in | prefix | contains | between
        label: "Mã HS (2/4/6 số, nhiều mã cách phẩy)"
        required: true
    split: null                           # default; requestor override được (mục 6)
      # hoặc: {column: ma_dia_diem_dich, chars: 2}  → mỗi mã nước 1 file (lõi đã có)
```

- `tables` không có placeholder → dùng nguyên văn (glob `*` cho phép). Có placeholder → expand theo ô Năm/Tháng của request (feedback #3), check tồn tại qua information_schema; bảng thiếu → ghi vào sheet NOTE, chạy phần còn lại.
- Validate templates lúc runner khởi động → warning vào log, không crash.

### 5.0 Phân biệt 3 khái niệm (chống nhầm — ghi cả vào README)

- **Template** (`templates.yaml`): kiểu request, admin định nghĩa, form Excel sinh ra luôn TRẮNG.
- **Request file đã điền**: "job" của requestor. Lịch sử nằm ở `processed/` trong folder share — requestor copy file cũ, sửa giá trị, thả lại = chạy lại job. Không có cơ chế nào ghi ngược vào file template gốc.
- **`jobs.yaml`**: saved jobs của portal trên máy DB (v4a) — độc lập hoàn toàn với flow requestor.

`templates.yaml.example` phải chứa 2 template mẫu phản ánh request thực tế:
(a) bộ cột rút gọn — `columns` là list ~15 cột do admin chốt, 1 filter MST prefix;
(b) 3 filter AND — MST prefix + phương thức vận chuyển eq + HS prefix, `columns: ALL`.
Quy luật: mỗi kiểu request lặp lại = 1 entry YAML; ô "Cột cần lấy" trong form chỉ dành cho ca lẻ.

### 5.1 Điểm mở rộng loại query (feedback #2)

Runner build job qua registry: `TYPE_BUILDERS = {"select": build_select_jobs}`. Loại query tương lai (aggregate, top-N, join...) = viết 1 hàm builder + đăng ký vào dict + thêm template `type` mới. File Excel mẫu sinh tự động nên form luôn khớp template — không bao giờ lệch tay.

**Triết lý (đọc kỹ trước khi build):** lõi = mechanism, tham số hóa 6 chiều (schema × tháng × cột × filters AND × split × sort) — cover toàn bộ ma trận request, code 1 lần. `templates.yaml` = policy, chỉ đặt tên các điểm hay dùng cho common user. KHÔNG hardcode bất kỳ tổ hợp nào vào code.

**Định hướng tương lai — KHÔNG build ở v4:** template `type: custom` cho power user tự khai cột/phép/giá trị từng dòng trong file request (expose nguyên ma trận từ xa). Yêu cầu duy nhất ở v4: parser request file thiết kế theo dạng key-value mở rộng được, không chặn đường thêm `custom` sau này.

## 6. Request file (input của requestor)

`request_template.xlsx` — **sinh tự động** bằng `python runner.py --make-template` (dropdown data-validation lấy từ templates.yaml; admin chạy lại mỗi khi thêm template). Layout dọc, cột A label, cột B nhập:

| Ô | Bắt buộc | Ghi chú |
|---|---|---|
| Người yêu cầu | ✔ | dùng đặt tên file output |
| Loại request | ✔ | dropdown từ templates |
| Năm | khi template có `{year}` | vd `2025` |
| Tháng | khi template có `{month}` | `all` / `1,3,5` / `1-6` (feedback #3) |
| Giá trị 1..3 | theo template | nhiều giá trị cách phẩy |
| Cột cần lấy | ✗ | trống = theo template; hoặc tên cột cách phẩy — sai tên → error kèm danh sách cột hợp lệ (feedback #4) |
| Tách file theo | ✗ | trống = theo template; `<cột>` hoặc `<cột>:<N>` vd `ma_dia_diem_dich:2` = tách theo 2 ký tự đầu (feedback #4) |
| Xác nhận dữ liệu lớn | ✗ | `YES` để vượt ngưỡng auto (mục 8) |
| Ghi chú / tên request | ✔ | dùng đặt tên file output |

Mỗi request = 1 file (tránh conflict sync). **Tái sử dụng job (feedback #9)**: file request cũ chính là job — runner move file đã xử lý vào `processed/` (giữ nguyên nội dung, thêm prefix timestamp). Requestor copy file cũ từ `processed/` (hoặc bản họ tự giữ), sửa giá trị, thả lại vào `requests/`. Không có state phía server. README phải có mục "Chạy lại request cũ" hướng dẫn đúng 3 bước này.

## 7. Runner logic

```
loop poll_seconds (default 120)   |   hoặc --once cho Task Scheduler
  quét input_dir/*.xlsx  (bỏ "~$*", processed/, error/; size bất biến giữa 2 lần đọc cách 5s)
  mỗi file:
    parse → validate (template, required, năm/tháng, cột, split)
    expand tables → build jobs qua TYPE_BUILDERS (tái dùng lõi portal: where_clause,
      build_query, build_merged_query, distinct_values — logic tương đương make_jobs)
    count_rows → kiểm ngưỡng (mục 8)
    export → log/tmp/ → move sang output_dir
      tên file: {yyyymmdd_HHMM}_{requestor}_{ghi chú}[_{giá trị split}].xlsx
      (safe_name toàn bộ; pattern config trong settings — feedback #2; trùng tên → _2, _3)
    0 dòng → vẫn xuất, thêm sheet NOTE: hint kiểm tra giá trị lọc
    sheet NOTE mọi file: tham số request gốc (template, giá trị, tháng) — tự document
    xong → move request vào processed/{timestamp}_{tên gốc}
    lỗi → move vào error/ + file .txt cùng tên, lý do tiếng Việt dễ hiểu
  DB down → log, GIỮ request file, thử lại vòng sau (không error/)
  crash giữa chừng → file còn trong input_dir → vòng sau chạy lại (idempotent nhờ _2)
  1 connection cho cả batch, conn.rollback() sau mỗi export (quirk #3)
```

## 8. Cơ chế chặn output quá lớn (feedback #5)

`count_rows` TRƯỚC khi export, so với 2 ngưỡng trong settings:

| Ngưỡng | Default | Hành vi |
|---|---|---|
| `max_rows_auto` | 300_000 | Vượt → KHÔNG chạy. Move request → `error/` + txt: "Query ra X dòng (ước ~Y MB). Nếu chắc chắn, điền ô 'Xác nhận dữ liệu lớn' = YES rồi gửi lại." → **stop, chờ người can thiệp** |
| `max_rows_hard` | 3_000_000 | Vượt → từ chối kể cả YES, yêu cầu lọc hẹp hơn / tách file |

- Có YES + dưới hard cap → chạy. Kết quả > 1_000_000 dòng (giới hạn sheet xlsx) → tự chuyển CSV, giải thích trong file .txt đi kèm.
- Ước lượng MB: rows × số cột × 15 byte (thô, đủ để cảnh báo).

## 9. settings.yaml.example

```yaml
input_dir: "C:/Users/you/OneDrive/DataRequests"
output_dir: "C:/Users/you/OneDrive/Data-Analysis"
poll_seconds: 120
filename_pattern: "{ts}_{user}_{request}"   # ts = yyyymmdd_HHMM
max_rows_auto: 300000
max_rows_hard: 3000000
```

## 10. Vận hành trên máy giữ DB (feedback #6)

Setup 1 lần, sau đó tự chạy ngầm khi Windows bật:

- Task Scheduler: trigger **At log on** + repeat every 2 minutes, action `pythonw.exe runner.py --once` (pythonw = không cửa sổ). README kèm lệnh `schtasks /create ...` copy-paste được.
- Người dùng máy đó vẫn làm việc bình thường; requestor chỉ thả file, output tự sinh.

## 11. Bảo mật

- `connection.yaml` (có password) trong `.gitignore` — điền 1 lần lúc setup. README cảnh báo: KHÔNG commit, không đặt repo trong folder cloud sync.
- Không mở port PostgreSQL; runner cùng máy DB.
- Quyền xem data = quyền truy cập folder share — quản bằng cloud, không bằng tool.

## 12. README (public) — quick start

1. Clone + `pip install -r requirements.txt`
2. Copy 3 file `.example` → bỏ đuôi, điền connection (password tại đây, chỉ máy này)
3. Admin định nghĩa `templates.yaml`
4. Trỏ `input_dir`/`output_dir` vào folder OneDrive/Google Drive đã share
5. `python runner.py --make-template` → gửi file mẫu cho team
6. Đăng ký Task Scheduler (lệnh mẫu trong README) — xong, chạy ngầm

Kèm mục: "Chạy lại request cũ" (mục 6), "Request bị từ chối vì quá lớn thì làm gì" (mục 8). Tiếng Việt + Quick Start EN ngắn cuối file.

## 13. Test (pattern pgserver + monkeypatch — xem handoff/HANDOFF.md)

**Phân tầng (chốt 2026-07-06):** unit test dùng monkeypatch (chạy mọi máy, kể cả Windows). Integration test dùng pgserver đặt file riêng, mở đầu `pytest.importorskip("pgserver")` — pgserver KHÔNG có wheel Windows, sẽ tự skip trên máy user; Claude chạy phần này trong sandbox Linux khi review.

Tối thiểu: request hợp lệ end-to-end; template không tồn tại; thiếu required; tháng `all`/`1,3`/`2-4` expand đúng + bảng thiếu ghi NOTE; cột sai tên → error liệt kê cột; split override `col:2`; 0 dòng → NOTE; vượt `max_rows_auto` → error + txt; YES → chạy; vượt hard cap → từ chối; >1M dòng → CSV; file `~$` bỏ qua; file size đang đổi → hoãn; DB down → giữ file; `--once` × 2 không xử lý trùng; `--job` CLI; password từ yaml + fallback getpass; dbname có `/`; không sinh `__pycache__`.

## 14. Thứ tự build & DoD

1. Password từ connection.yaml + `sys.dont_write_bytecode` + xác nhận `import portal` không side-effect → portal chạy y hệt v3.2 (trừ không hỏi password)
2. v4a saved jobs + `--job`/`--list-jobs` → test pass
3. templates.yaml + TYPE_BUILDERS + runner + `--make-template` → test mục 13 pass
4. `.gitignore` + examples + request_template.xlsx + README → clone sạch máy mới, theo README chạy được

Xong mỗi bước: cập nhật `handoff/HANDOFF.md` (trạng thái + quirks mới nếu có).
