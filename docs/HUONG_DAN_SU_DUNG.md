# Hướng Dẫn Sử Dụng SQL BulkEx v6

Tài liệu này dành cho Sales/Marketing. Bạn không cần biết SQL.

---

## 1. Việc Bạn Cần Làm

Mỗi request đi qua 4 bước:

1. Mở file `request_template.xlsx`.
2. Điền thông tin và các cột cần lọc/lấy về.
3. Upload file vào folder OneDrive `01_Pending/`.
4. Nhắn Zalo admin để approve.

Sau khi admin approve, runner sẽ tự xử lý. Kết quả nằm trong `03_Output/`.

---

## 2. Ba Folder OneDrive

```text
01_Pending   -> Nơi Sales upload request
02_Approved  -> Admin kéo file vào đây sau khi approve
03_Output    -> Nơi nhận kết quả
```

Bạn chỉ cần upload vào `01_Pending/`. Không tự kéo sang `02_Approved/` trừ khi admin yêu cầu.

Nếu request thành công, file gốc sẽ được rename:

```text
[DONE] ten_file_cua_ban.xlsx
```

Nếu request sai, file gốc sẽ được rename:

```text
[LOI]_ten_file_cua_ban.xlsx
[LOI]_ten_file_cua_ban.txt
```

Mở file `.txt` để xem lỗi và cách sửa.

---

## 3. Điền Sheet Request

Trong sheet `Request`, điền các ô cột B:

| Dòng | Cần điền | Ví dụ |
|---|---|---|
| 1 | Người yêu cầu | Hoa |
| 2 | Bảng | `export`, `import`, hoặc `both` |
| 3 | Năm | `2026`, `2025,2026`, hoặc `2025-2026` |
| 4 | Tháng | `06`, `01-03`, hoặc `01,03,12` |
| 5 | Tách file theo | Để trống nếu không biết |
| 6 | Xác nhận lớn | Điền `YES` nếu admin yêu cầu |
| 7 | Ghi chú / tên request | `hs8471_cn` |
| 8 | Người duyệt | Admin có thể điền sau |

Chọn `both` khi bạn muốn chạy cả Export và Import trong cùng một request. Kết quả sẽ có 2 sheet: `Export` và `Import`.

---

## 4. Điền Sheet Cột Export / Cột Import

Mỗi dòng là 1 cột dữ liệu. Cột A đã có sẵn tên cột, bạn không cần sửa.

Layout v6:

| Cột | Bằng | Trong danh sách | Trong khoảng | Bắt đầu bằng | Chứa | Kết thúc bằng | Digits | Lấy về? |
|---|---|---|---|---|---|---|---|---|
| ma_nuoc | CN | | | | | | | |
| ma_so_hang_hoa | | | | 8471 | | | 4 | YES |
| phuong_thuc_van_chuyen | | Air, Ocean | | | | | | YES |

Ý nghĩa:

- Điền vào một trong 6 cột toán tử để lọc dữ liệu.
- Nếu dòng có filter, cột đó tự động được lấy về trong output.
- Nếu chỉ muốn lấy cột mà không lọc, điền `YES` ở cột `Lấy về?`.
- Có thể điền nhiều toán tử trên cùng một dòng; các điều kiện sẽ kết hợp với nhau.

---

## 5. 6 Toán Tử

| Toán tử | Khi nào dùng | Ví dụ |
|---|---|---|
| Bằng | Cần đúng 1 giá trị | `CN` |
| Trong danh sách | Chấp nhận nhiều giá trị | `CN, KR, JP` |
| Trong khoảng | Từ mốc A đến mốc B | `1000, 5000` |
| Bắt đầu bằng | Mã bắt đầu bằng chuỗi nào đó | `8471` |
| Chứa | Mô tả có chứa từ khóa | `laptop` |
| Kết thúc bằng | Mã kết thúc bằng chuỗi nào đó | `0010` |

Bạn không cần gõ code `eq`, `prefix`, `contains`. Chỉ điền giá trị vào cột toán tử tiếng Việt tương ứng.

---

## 6. Combine 2 Toán Tử Cùng Một Cột

Có thể kết hợp nhiều điều kiện trên cùng một cột.

Ví dụ HS code:

| Cột | Bắt đầu bằng | Kết thúc bằng |
|---|---|---|
| ma_so_hang_hoa | 84 | 10 |

Nghĩa là: lấy các mã bắt đầu bằng `84` và kết thúc bằng `10`.

Dùng cách này khi bạn muốn lọc hẹp hơn mà không cần viết SQL.

---

## 7. Digits Là Gì?

`Digits` dùng để kiểm tra độ dài giá trị bạn nhập cho:

- `Bắt đầu bằng`
- `Kết thúc bằng`

Digits không phải điều kiện đếm độ dài trong database. Nó chỉ giúp chặn nhập sai độ dài.

| Bạn điền | Kết quả |
|---|---|
| `Bắt đầu bằng=8471`, `Digits=4` | Hợp lệ |
| `Bắt đầu bằng=84`, `Digits=4` | Lỗi, vì `84` chỉ có 2 ký tự |
| `Kết thúc bằng=0010`, `Digits=4` | Hợp lệ |
| `Bằng=CN`, `Digits=4` | Digits bị bỏ qua |

MST:

| Cần lọc | Cách điền |
|---|---|
| MST 10 số | `Bắt đầu bằng=0301234567`, `Digits=10` |
| MST 13 số | `Bắt đầu bằng=0301234567890`, `Digits=13` |

Nếu quên điền Digits, request vẫn chạy; chỉ là không có bước kiểm tra độ dài giá trị nhập.

---

## 8. Ví Dụ Thường Gặp

### Ví dụ 1: Lấy hàng Export HS 8471 từ CN/KR

Sheet `Request`:

| Field | Giá trị |
|---|---|
| Bảng | `export` |
| Năm | `2026` |
| Tháng | `06` |
| Ghi chú / tên request | `hs8471_cn_kr` |

Sheet `Cột Export`:

| Cột | Trong danh sách | Bắt đầu bằng | Digits | Lấy về? |
|---|---|---|---|---|
| ma_nuoc | `CN, KR` | | | |
| ma_so_hang_hoa | | `8471` | `4` | |
| phuong_thuc_van_chuyen | | | | `YES` |

### Ví dụ 2: Chạy cả Export và Import

Sheet `Request`:

| Field | Giá trị |
|---|---|
| Bảng | `both` |
| Năm | `2026` |
| Tháng | `06` |

Sau đó điền cả sheet `Cột Export` và `Cột Import`. Output sẽ có 3 sheet:

- `Export`
- `Import`
- `NOTE`

---

## 9. Upload Và Nhận Kết Quả

1. Save file request với tên dễ hiểu, ví dụ `hoa_hs8471_202606.xlsx`.
2. Upload vào `01_Pending/`.
3. Nhắn Zalo admin: "Em đã upload request hoa_hs8471_202606.xlsx, nhờ anh/chị approve."
4. Chờ admin approve.
5. Vào `03_Output/` để tải file kết quả.

Nếu cần sửa request lỗi:

1. Mở file `[LOI]_...txt`.
2. Sửa file Excel theo hướng dẫn.
3. Save thành tên mới hoặc bỏ prefix `[LOI]_`.
4. Upload lại vào `01_Pending/` hoặc gửi admin theo quy trình team.

---

## 10. Mô Tả Giao Diện Excel

Không có screenshot thật trong repo, nhưng template nhìn như sau:

- Sheet `Request`: cột A là tên field, cột B là nơi bạn điền.
- Sheet `Cột Export` / `Cột Import`: cột A là tên cột có sẵn, cột B-G là 6 toán tử, cột H là `Digits`, cột I là `Lấy về?`.
- Sheet `Values`: bị ẩn, chứa danh sách dropdown như `CN`, `KR`, `JP`.
- Sheet `Tham chiếu`: giải thích lại toán tử và ví dụ.

Nếu thấy ô màu xám trong cột `Digits`, nghĩa là Digits đang không active cho dòng đó.

---

## 11. FAQ

### Quên điền Digits thì sao?

Request vẫn chạy. Digits chỉ giúp kiểm tra độ dài giá trị nhập. Nếu không chắc, để trống và nhờ admin review.

### Combine 2 op cùng cột được không?

Được. Điền nhiều ô toán tử trên cùng một dòng. Ví dụ `Bắt đầu bằng=84` và `Kết thúc bằng=10`.

### Excel dropdown Toán tử ở đâu?

v6 không còn dropdown `Toán tử` một cột riêng. Mỗi toán tử là một cột riêng: `Bằng`, `Trong danh sách`, `Trong khoảng`, `Bắt đầu bằng`, `Chứa`, `Kết thúc bằng`.

### Tại sao có dropdown giá trị như CN/KR?

Admin đã chạy scan-values. Các cột có ít giá trị sẽ có dropdown để bạn chọn nhanh.

### File ở Pending lâu mà chưa có output?

Runner không xử lý `01_Pending/`. Admin phải approve bằng cách move file sang `02_Approved/`.

### File output nằm ở đâu?

Trong `03_Output/`.

### File request của tôi thành `[DONE]` là gì?

Nghĩa là request đã xử lý xong.

### File request của tôi thành `[LOI]_` là gì?

Nghĩa là request bị lỗi. Mở file `.txt` cùng tên để xem lý do.

---

## 12. Khi Cần Hỏi Admin

Hỏi admin nếu:

- Không biết chọn `export`, `import`, hay `both`.
- Không biết tên cột cần lấy về.
- File bị `[LOI]_` nhưng bạn không hiểu lỗi.
- Output quá lớn hoặc cần tách file.
- Cần thêm dropdown giá trị cho cột nào đó.
