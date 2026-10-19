# Chuẩn Bàn Giao v1.1

Chuẩn phối hợp giữa Chairman, Claude (mọi nhân dạng) và Codex.
Bản gốc sống trong vault Brain Lab. Mỗi repo nhận một bản sinh ra từ đây.

Ngày chốt: 2026-08-25. Áp dụng cho mọi dự án mới, và mọi dự án cũ sau khi cải tổ.

---

## 0. Phạm vi

Tài liệu này quy định **cách trao đổi**, không quy định cách viết mã.

- Áp dụng cho: mọi dự án có từ hai bên tham gia trở lên.
- Không áp dụng cho: cách tổ chức mã nguồn, công nghệ, thư viện. Đó là quyền của bên thực thi.

Ba nguyên tắc nền:

1. **Một việc, một phiếu.** Cả vòng đời của một việc nằm trong đúng một file.
2. **Phiếu tự đủ.** Đọc một phiếu là hiểu được việc, không phải leo ngược chuỗi.
3. **Ai ghi phần của người đó.** Không ai sửa mục của người khác. Bất đồng thì ghi thêm, không ghi đè.

---

## 1. Cấu trúc phòng bàn giao

```
<repo>/
   ...toàn bộ file chạy của dự án - KHÔNG đụng, chỉ thêm...
   README.md               viết theo chuẩn ở mục 8
   log/                    nhật ký chạy của ứng dụng (không thuộc handoff)
   memory/                 trí nhớ lúc chạy của sản phẩm - tầng VẬN HÀNH
                           CHỈ dự án agentic mới có
                           không ai trong quy trình bàn giao đụng vào
   AGENTS.md               bộ định tuyến 30 dòng, bắt buộc ở gốc repo
   handoff/
      RULES.md             luật đứng              <= 200 dòng
      STATE.md             hiện trạng, ghi đè     <= 100 dòng
      MAP.md               kiến trúc hiện tại     <= 200 dòng
      docs/                tài liệu tham khảo
      shots/               ảnh và GIF làm bằng chứng - tầng PHÁT TRIỂN
      archive/             CHỈ sinh ra khi cải tổ một dự án cũ và có file
                           bàn giao cũ không dùng lại được. Dự án mới không có.
      20260825_CT-04_sua-cong-thanh-toan.md       phiếu việc
```

Hai thư mục con cố định, ba file cố định, một loại phiếu. `archive/` là thư mục thứ ba
nhưng có điều kiện - không có dự án cũ để cải tổ thì không tồn tại.

**Không tạo** `tasks/`, `acceptance/`, `todo/`, `audit/`, `history/`, `failure/`,
`sessions/` dưới bất kỳ hình thức nào. Chúng là **khoang trong phiếu**, không phải thư mục.

**AGENTS.md ở gốc repo** - bắt buộc, không được chuyển vào `handoff/`. Công cụ đọc
file gần nhất tính từ chỗ nó đang sửa, nên một agent sửa `src/foo.py` sẽ không bao giờ
nhìn xuống `handoff/`. Nội dung tối đa 30 dòng: dự án này là gì, đọc `handoff/RULES.md`
trước khi làm. Không dạy gì thêm ở đó.

---

## 2. Ngân sách đọc

Mục tiêu: một phiên làm việc chỉ nạp **khoảng 450 dòng**, bất kể dự án sống bao lâu.

```
LUÔN LUÔN       RULES.md + STATE.md                        ~300 dòng
VIỆC CỦA MÌNH   đúng 1 phiếu việc                          ~150 dòng
MAP.md          CHỈ khi việc đụng tới kiến trúc            ~200 dòng
PHIẾU TRƯỚC     CHỈ khi khoang Kế thừa không đủ
                -> mở ĐÚNG 1 phiếu theo trường Nối tiếp
```

**Cấm:**

- Quét cả thư mục `handoff/`.
- Đọc theo dải ngày, kiểu "đọc các phiếu tuần này".
- Đọc phiếu đã đóng, trừ khi một trường `Nối tiếp` trỏ đích danh tới nó.
- Đọc `docs/` khi không có dòng nào trỏ tới.
- Đọc `archive/` trong mọi trường hợp, trừ khi Chairman yêu cầu đích danh.

Vượt trần dòng thì cắt, không thương lượng. Cách cắt ghi ở mục 4 và 6.

---

## 3. Phiếu việc

Tên file: `{YYYYMMDD}_{MÃ}-{số}_{tên-việc}.md`

- `MÃ` là mã mạch, 2-3 chữ in hoa. Một mạch là một dòng công việc nối tiếp nhau.
- `số` tăng dần trong mạch.
- `tên-việc` viết thường không dấu, nối bằng gạch ngang, tối đa 5 từ.

Ví dụ: `20260825_CT-04_sua-cong-thanh-toan.md`

Bất cứ thứ gì đáng ghi lại đều đáng có một phiếu. Môi trường hỏng, công cụ trục trặc,
hai bên hiểu nhầm nhau - đều là việc, đều mở phiếu. Không có mẩu lịch sử nào mồ côi.

### Đầu phiếu

```
Mã:         CT-04
Mạch:       CT - cổng thanh toán Control Tower
Nối tiếp:   CT-03            (để trống nếu là phiếu đầu mạch)
Giao cho:   codex            (codex | claude-ceo | claude-user | claude-logisticist | chairman)
Trạng thái: đang-làm
Vòng:       1/2
```

### Bốn khoang

```
## ĐỀ BÀI
   Chairman và Claude viết. Mở xong thì KHÔNG AI SỬA. Bất đồng thì ghi ở AUDIT.

   Mục tiêu nghiệp vụ       1-3 câu: việc này tồn tại để làm gì
   Ngoài phạm vi            chỉ ghi ranh giới NGHIỆP VỤ, cấm ghi ràng buộc kỹ thuật
   Kế thừa                  tối đa 3 dòng: cái gì đã chốt ở phiếu trước mà phiếu
                            này cần biết. Để trống nếu là phiếu đầu mạch.
   Kịch bản nghiệm thu      viết bằng tiếng Việt, do Chairman viết TRƯỚC khi mở việc:
                            ai bấm gì - kỳ vọng thấy gì - trong bao lâu
                            cái gì tuyệt đối không được xảy ra

## TODO
   Bên thực thi viết (Codex hoặc bản sao Claude).
   Kế hoạch dạng ô đánh dấu, đánh dấu xong khi làm xong.
   Đổi hướng giữa chừng thì ghi thêm dòng mới, không xoá dòng cũ.

## AUDIT
   Báo cáo của bên làm      đã làm gì - file nào đổi - LỆNH VÀ KẾT QUẢ DÁN VÀO
                            lệch so với đề bài (bắt buộc ghi, không có thì ghi "không")
                            câu hỏi còn treo cho Chairman
   Soi của Claude           CHỈ TĨNH: logic, bám sát đề bài, đọc mã như đọc văn bản
                            cấm kết luận về runtime
   Ô ký nghiệm thu          ĐẠT | HỎNG | KHÔNG ĐO ĐƯỢC (+ lý do nếu không đo được)
                            kèm chữ ký và ảnh trong shots/ nếu có

## HISTORY
   Ghi theo ngày. Mỗi ngày một mục con, không ghi đè mục của ngày trước.

   ### 2026-08-25
   Failure    hôm nay hỏng gì
              Báo lỗi giả: có | không   (báo là hỏng mà hoá ra không hỏng)
   Lessons    bài học rút ra từ phần Failure ở trên
              cái nào chặn được hành động tương lai -> chép lên RULES.md
              ghi lại một dòng: "đã lên RULES.md ngày <ngày>"
   -- chữ ký
```

### Máy trạng thái

```
chờ-đề-bài -> đang-làm -> chờ-nghiệm-thu -> đóng-đạt
                  ^             |
                  |             | HỎNG
                  +-- vòng 2 ---+
                                |  hết trần 2 vòng
                                v
                         chờ-chairman -> đóng-huỷ | đóng-hỏng
```

- Trạng thái **chỉ đẩy tiến, không lùi, không nhảy cóc**.
- Ba trạng thái kết thúc: `đóng-đạt`, `đóng-huỷ`, `đóng-hỏng`.
- **Đóng rồi thì không mở lại.** Muốn làm tiếp thì mở phiếu mới, ghi `Nối tiếp` trỏ về.
- **Đóng phiếu thì KHÔNG dời file đi đâu cả.** Đổi trường `Trạng thái` là đủ.
  `STATE.md` ngừng liệt kê nó.
- **Trần vòng lặp: 2.** Nghiệm thu báo HỎNG hai lần thì bắt buộc chuyển `chờ-chairman`,
  kèm hai phương án nén. Cấm vòng thứ ba.
- `KHÔNG ĐO ĐƯỢC` không tính là một vòng. Nó có nghĩa phép thử chưa chạy được,
  phải sửa phép thử trước, không phải sửa sản phẩm.

---

## 4. RULES.md

Chỉ chứa **luật đứng** - thứ còn đúng vào tháng sau. Không chứa lịch sử, không chứa
phiếu lỗi đã sửa xong.

**Luật lên RULES.md khi và chỉ khi** viết được thành một câu chặn hành động:

```
ĐƯỢC     "không được làm X"        hoặc    "phải làm Y trước khi Z"
KHÔNG    "lần này sai vì hoàn cảnh A"  -> kể chuyện, ở lại khoang HISTORY của phiếu
```

**Chạm trần 200 dòng thì bắt buộc cắt tỉa:** soi luật cũ nhất, còn đúng thì giữ,
chết rồi thì xoá và ghi một dòng vào khoang HISTORY của phiếu đang mở. Không được để
file vượt trần qua một phiên làm việc.

RULES.md phải chứa sẵn bốn mục bắt buộc:

1. Chỉ huy hiện tại và cách đổi (xem mục 9).
2. Quyền ký nghiệm thu (xem mục 9).
3. Trần vòng lặp và đường lên Chairman.
4. Bốn câu của Chairman (xem mục 10).

---

## 5. STATE.md

Ảnh chụp hiện tại. **Ghi đè mỗi lần kết phiên**, không nối đuôi. An toàn vì lịch sử
đã nằm trong khoang HISTORY của từng phiếu.

```
Cập nhật:  2026-08-25 21:50 UTC+7 - bởi claude-ceo
Chỉ huy:   claude          (claude | codex)

## Việc đang mở
   CT-04   giao cho codex     chờ-nghiệm-thu   vòng 1/2

## Hôm qua
   3-5 dòng: hôm qua chạy gì, vấp gì, chốt gì
   để một chat mới bắt nhịp mà không phải mở phiếu nào

## Vừa đóng
   CT-03   đóng-đạt   2026-08-24

## Đang treo, cần Chairman
   <câu hỏi nghiệp vụ chưa có lời>

## Bẫy đã biết
   3-5 dòng - thứ mà phiên sau dễ vấp lại
   sống lâu hơn một tuần thì đẩy lên RULES.md rồi xoá khỏi đây

## Báo lỗi giả
   Tháng này: <số lần>
   Đây là thước đo duy nhất của cả hệ thống. Số này giảm dần thì mới có cơ sở
   buông tay giám sát.
```

---

## 6. MAP.md

Kiến trúc **hiện tại** của dự án. Một trang.

**Mọi thay đổi ở tầng kiến trúc phải được vẽ ở đây TRƯỚC khi đổi mã.** Vẽ trước,
duyệt, rồi mới làm. Đây là lý do MAP.md không bao giờ trôi: nó cập nhật trước,
không phải sau.

- Chỉ mô tả hiện trạng. **Lý do** của một thay đổi nằm trong phiếu việc đã gây ra
  thay đổi đó, không nằm ở đây.
- Trần 200 dòng. Vượt trần nghĩa là đang chép chi tiết vào - cắt.
- Không chứa danh sách việc đang mở. Đó là STATE.md.

---

## 7. docs/, shots/ và archive/

### docs/

Một thư mục phẳng. Phân loại bằng tiền tố tên file:

```
REF-    tài liệu Chairman mang về hoặc sưu tầm
SPEC-   đặc tả, thiết kế đã chốt
NOTE-   ghi chép do Claude hoặc Codex viết
```

Chỉ đọc khi có một dòng trong phiếu trỏ tới.

### shots/

Ảnh và GIF do agent chụp **khi chạy thử sản phẩm**: mở app, lên web app bấm thử,
chụp màn hình làm bằng chứng nghiệm thu. Đây là bằng chứng tầng **phát triển**,
mọi dự án đều có.

Không nhầm với `memory/` ở ngoài repo - đó là trí nhớ lúc chạy của sản phẩm,
tầng **vận hành**, chỉ dự án agentic mới có.

Tên file: `{YYYYMMDD}_{MÃ-số}_{stt}_{mô-tả-ngắn}.png`

Ví dụ: `20260825_CT-04_01_trang-thanh-toan.png`

Luật:

- Mỗi ảnh phải được một phiếu trỏ tới. Ảnh không ai trỏ tới là rác, xoá khi đóng phiếu.
- Ảnh tĩnh (.png) đi theo git - nó là bằng chứng, và nhẹ.
- GIF không đi theo git vì nặng. Giữ trên máy trong lúc phiếu còn mở; phiếu
  `đóng-đạt` thì xoá GIF, giữ lại ảnh tĩnh và lời ký.

### archive/

Chỉ sinh ra khi cải tổ một dự án cũ (mục 12) và có file bàn giao cũ **không dùng lại
được**. Dự án mới không bao giờ có thư mục này.

Không ai đọc `archive/`, trừ khi Chairman yêu cầu đích danh. Nó là hồ sơ, không phải
tài liệu làm việc.

---

## 8. Chuẩn README

Áp dụng cho README của mọi repo và mọi dự án trên máy - kể cả dự án chưa đưa lên git,
vì tương lai có thể chia sẻ hoặc đưa lên.

**Nguyên tắc:** đoạn đầu README phải để người **không biết code** đọc hiểu là công cụ
này làm gì và họ được lợi gì. Chi tiết kỹ thuật xuống dưới.

Khung bắt buộc:

```
# <Tên dự án> v<phiên bản>

[huy hiệu shields.io]     license · ngôn ngữ + phiên bản · hạ tầng chính ·
                          nền tảng · số phép thử đã đạt

> **Một câu nghiệp vụ in đậm: công cụ này làm gì, cho ai.**
> Rồi một dòng luồng ngắn: ai làm gì -> ai duyệt -> kết quả xuất hiện ở đâu.

## 🎯 Ai làm gì
   Bảng ba cột:  Vai trò | Việc | Cần biết code?
   Cột thứ ba là bắt buộc. Nó trả lời câu hỏi đầu tiên của mọi người không kỹ thuật.

## 🔄 Luồng chạy
   Sơ đồ ASCII trong khối mã. Không dùng hình ảnh - hình gãy khi đổi chỗ, ASCII thì không.

## 🚀 Cài đặt
## 📋 Dùng thế nào
## ❓ Hỏng thì làm gì
```

Luật:

- Tiêu đề mục có emoji dẫn đầu, giúp quét nhanh bằng mắt.
- Sơ đồ luồng luôn là ASCII trong khối mã, không phải ảnh.
- Bảng "Ai làm gì" phải có cột **Cần biết code?** và trả lời thẳng Có hoặc Không.
- Huy hiệu chỉ ghi thứ **kiểm được**: số phép thử đã đạt là con số thật, không phải
  huy hiệu trang trí.

---

## 9. Chữ ký, nhân dạng và quyền ký

### Nhân dạng

Nhân dạng do prompt lúc mở chat quyết định. Không đóng gói thành công cụ gì cả.

```
chairman              người
claude-ceo            điều phối: dịch nghiệp vụ thành đề bài, soi tĩnh, đóng phiếu
claude-user           đóng vai người dùng cuối, chạy thử sản phẩm qua trình duyệt
claude-logisticist    đóng vai người vận hành, chạy thử theo góc nghiệp vụ giao nhận
codex                 thực thi kỹ thuật
```

Nghiệm thu thì **mở chat riêng và đừng nối thư mục mã nguồn**. Đó là toàn bộ giá trị
của việc tách nhân dạng, và nó là một thao tác chứ không phải một cơ chế.

### Chữ ký

Mỗi mục trong khoang HISTORY và mỗi ô ký nghiệm thu phải có chữ ký:

```
-- claude-user - 2026-08-25 21:40 UTC+7
-- codex - 2026-08-25 14:40 UTC
```

Ghi giờ hệ thống của chính bên đó, **kèm múi giờ**. Không ai quy đổi hộ ai.
Không ai sửa mục đã ký của người khác; cần nói lại thì thêm mục mới.

### Quyền ký nghiệm thu - phân theo ĐƯỜNG LẤY BẰNG CHỨNG, không theo vai

```
CLAUDE ĐƯỢC KÝ        thứ nhìn thấy qua trình duyệt thật trên máy Chairman:
                      trang có hiện không - bấm có ra kết quả không -
                      số trên màn hình đúng chưa
                      BẮT BUỘC kèm ảnh trong shots/

CLAUDE KHÔNG ĐƯỢC KÝ  thứ chỉ máy Windows phán được:
                      phép thử đạt/hỏng - toàn vẹn file - mã hoá ký tự -
                      kết quả lệnh chạy
                      -> độc quyền Codex, chứng minh bằng lệnh + kết quả dán vào
```

Lý do không được bỏ: ngày 25/06/2026, Claude đọc file Windows qua lớp trung gian,
báo sai là file hỏng. Codex nhận lỗi hai lần rồi bịa báo cáo "đã sửa xong, 61 phép thử
đạt" trong khi file vốn không hỏng. Suýt mất việc thật trước buổi demo.

### Chỉ huy

`STATE.md` ghi rõ đang ở thế trận nào:

```
Chỉ huy: claude    Claude viết đề bài - Codex thực thi - Claude soi tĩnh và đóng
Chỉ huy: codex     Codex tự viết đề bài, tự thực thi, gắn thẻ [AUTO]
                   Claude soi tĩnh khi quay lại, không đòi làm lại từ đầu
```

Ở cả hai thế trận: **phạm vi nghiệp vụ luôn chờ Chairman**. Quyền chỉ huy kỹ thuật
không kéo theo quyền quyết nghiệp vụ.

---

## 10. Bốn câu của Chairman

Bốn câu này Chairman luôn hỏi được mà không cần đọc một dòng mã nào. Chép nguyên
vào RULES.md của mọi dự án.

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

**Luật kèm theo:** Claude không được đề xuất kiến trúc, thư viện, cấu trúc file hay
khuôn thiết kế. Đề bài chỉ được ghi hướng kỹ thuật ở mức nền tảng. Vi phạm thì
Chairman **xoá, không chuyển tiếp** - đó là lỗi của Claude, không phải thông tin
cần đi tiếp.

---

## 11. Dựng lều ở repo mới

Claude tới một repo lần đầu thì dựng phòng bàn giao. Hai luật:

**Chỉ thêm, không dời.** Repo có sẵn thư mục gì để nguyên thư mục đó. Dời một file
là gãy đường build, đường CI, đường import. Chỉ tạo thêm `handoff/` và `AGENTS.md`
nếu chưa có.

**`memory/` không dựng mặc định.** Chỉ dựng khi dự án thật sự có tác nhân chạy
vòng lặp bên trong sản phẩm. Không có thì không tạo.

Trình tự:

1. Đọc thư mục gốc, ghi `MAP.md` mô tả hiện trạng.
2. Tạo `handoff/` với `RULES.md` (sinh từ bản chuẩn này, ghi rõ sinh từ phiên bản nào),
   `STATE.md` rỗng, `docs/`, `shots/`. Không tạo `archive/`.
3. Tạo `AGENTS.md` ở gốc nếu chưa có - 30 dòng, trỏ vào `handoff/RULES.md`.
4. Rà `README.md` theo chuẩn mục 8; chưa đạt thì đề xuất viết lại.
5. Báo cáo Chairman những gì đã tạo, không tự ý sửa gì khác.

---

## 12. Cải tổ dự án cũ

**Bắt buộc đề xuất, cấm tự làm.** Claude hoặc Codex gặp một dự án chưa theo chuẩn này
thì **phải nêu ngay ở lượt đầu tiên** và xin Chairman duyệt. Không được im lặng làm
việc theo cấu trúc cũ, cũng không được tự ý chuyển.

### Trình tự

1. **Liệt kê** toàn bộ file và thư mục bàn giao cũ đang có.
2. **Đề xuất ánh xạ** từng cái: chuyển đi đâu, hay đưa vào `archive/`.
3. **Chờ Chairman duyệt.**
4. **Mở một phiếu việc** cho chính việc cải tổ. Mọi thao tác ghi vào phiếu đó.
5. **Thực hiện:**
   - Đã có sẵn thư mục `handoff/` thì **tận dụng luôn**, không tạo thư mục mới.
   - File còn dùng lại được: gom vào chỗ mới theo bảng ánh xạ, rồi **xoá bản cũ**.
   - File không dùng lại được: chuyển vào `handoff/archive/`.
   - `archive/` chỉ được tạo khi thật sự có file loại này. Không có thì không tạo.
6. **Quét toàn repo** tìm đường dẫn cũ còn sót; dán kết quả vào khoang AUDIT của phiếu.
7. **Đóng phiếu.**

### Xoá hay giữ

```
Dự án CÓ git      xoá thẳng bản cũ sau khi đã gom - lịch sử vẫn nằm trong git,
                  lấy lại được bất cứ lúc nào
Dự án KHÔNG git   không xoá gì cả - chuyển hết vào archive/, vì xoá là mất vĩnh viễn
```

### Bảng ánh xạ

```
docs/REPO_SNAPSHOT.md        -> handoff/MAP.md
log/rules.md                 -> handoff/RULES.md
                                LỌC: phần lịch sử và phân loại mục cũ bỏ xuống
                                khoang HISTORY của phiếu cải tổ
handoff/tasks/*.md           -> handoff/{ngày}_{MÃ-số}_{tên}.md
                                thêm Mạch, Nối tiếp, Kế thừa, Giao cho
log/sessions/*.md            -> gộp vào khoang HISTORY của phiếu việc tương ứng
docs/blueprints/*            -> docs/ với tiền tố SPEC- nếu còn đúng
                                đã chết thì -> archive/
handoff/todo.md audit.md     -> archive/ (đã nghỉ hưu 31/07/2026)
log/history.md failure.md    -> archive/ (đã nghỉ hưu 31/07/2026)
memory/                      -> GIỮ NGUYÊN nếu dự án là agentic thật.
                                Control Tower là agentic (có skills/,
                                platform/log_token_usage.py, memory/episodic/)
                                nên memory/ của nó được giữ khi cải tổ.
                                Không agentic thì -> archive/
```

Kết thúc cải tổ, repo chỉ còn **một** phòng bàn giao. Không tồn tại hai chỗ cùng
chứa thông tin điều phối.

---

## 13. Luật chép

Luật cũ "chỉ trỏ, không chép" đã được sửa. Bản đúng:

```
ĐƯỢC CHÉP    kết luận ĐÃ ĐÓNG - nó không đổi nữa nên không thể lệch
             3 dòng Kế thừa - một luật đã chốt - một con số đã nghiệm thu

CẤM CHÉP     thứ CÒN SỐNG - nó sẽ đổi ở bản gốc và bản chép thành sai
             bản đồ repo - danh sách việc đang mở - nội dung RULES.md
             -> trỏ tới file gốc, không chép nội dung
```

---

## Changelog

- v1.1 - 2026-08-25 - Thêm mục 8: chuẩn README (huy hiệu shields.io, tiêu đề mục có
  emoji, sơ đồ luồng ASCII, bảng "Ai làm gì" bắt buộc có cột *Cần biết code?*),
  áp dụng cho mọi repo và dự án trên máy. Viết lại mục 12: cải tổ dự án cũ trở thành
  nghĩa vụ - Claude hoặc Codex gặp dự án chưa theo chuẩn thì phải nêu ngay và xin duyệt;
  tận dụng thư mục `handoff/` sẵn có; file dùng lại được thì gom rồi xoá bản cũ, file
  chết thì vào `archive/`; `archive/` chỉ sinh ra khi có file bàn giao cũ; dự án không
  có git thì không xoá gì, chuyển hết vào `archive/`.

- v1.0 - 2026-08-25 - Bản đầu tiên. Gộp cơ chế bàn giao của Codex (một việc một file;
  ba khoang DIRECTIVE / TODO / AUDIT; log/rules.md; log/sessions/) và cơ chế của Claude
  (trước đó không có) thành một chuẩn chung.

  Khác bản Codex v2.1: bốn khoang thay ba, khoang HISTORY ghi theo ngày ngay trong
  phiếu việc nên bỏ hẳn `log/sessions/`; thêm trường Giao cho / Mạch / Nối tiếp /
  Kế thừa; máy trạng thái có tên thay cho open|done; trần vòng lặp 2; thêm trạng thái
  phép thử KHÔNG ĐO ĐƯỢC; MAP.md phải vẽ trước khi đổi kiến trúc; shots/ làm bằng chứng
  nghiệm thu; ngân sách đọc và trần dòng cho ba file bắt buộc; luật chép sửa lại theo
  trục đã-đóng / còn-sống; thước đo báo lỗi giả đặt trong STATE.md.

  Bỏ khái niệm vessel - nhân dạng do prompt lúc mở chat quyết định, không đóng gói
  thành công cụ.
