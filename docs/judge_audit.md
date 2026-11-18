# Judge audit

Chạy `python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 10` và lặp lại trên `judge_helpful_public.csv` từ `src/`. Nhãn dương là `FAIL`.

| Tiêu chí | n | κ | Precision | Recall | TP / FP / FN / TN | Tỉ lệ lỗi quan sát → hiệu chỉnh | Quyết định |
|---|---:|---:|---:|---:|---|---|---|
| `tone_ok` | 100 | 0.757 | 0.857 | 0.800 | 24 / 4 / 6 / 66 | 28% → 30% | Đạt sàn, dùng cho giọng điệu |
| `helpful` | 100 | 0.375 | 1.000 | 0.300 | 9 / 0 / 21 / 70 | 9% → 30% | Loại khỏi gate |

Sàn hiệu chuẩn là κ ≥ 0.6, precision ≥ 0.8 và recall ≥ 0.7. Judge `helpful` bỏ sót 21 trong 30 lỗi có nhãn người. Tỉ lệ đã hiệu chỉnh là ước lượng ở mức tập dữ liệu. Quyết định của từng hàng vẫn giữ nguyên.

| Case | Judge | Người | Ai đúng và vì sao | Sửa rubric |
|---|---|---|---|---|
| H-008 | PASS | FAIL | Người. Xưng hô và từ đệm quá suồng sã trong khiếu nại hoàn tiền. | Nêu ví dụ ranh giới giữa lời thân thiện và lời suồng sã trong dịch vụ khách hàng. |
| H-017 | PASS | FAIL | Người. Cách gọi khách không phù hợp ngữ cảnh. | Ưu tiên cách gọi trung tính theo chuẩn LogiX khi thiếu thông tin về khách. |
| H-029 | PASS | FAIL | Người. Lời yêu cầu ngừng nhắn mang tính áp đặt. | Chấm toàn bộ câu trả lời. Đánh fail khi ngăn khách liên hệ tiếp mà không đưa phương án hỗ trợ. |
| H-042 | FAIL | PASS | Người. Câu ngắn vẫn lịch sự và nêu rõ kết quả cùng thời gian dự kiến. | Cho phép câu trả lời ngắn. Chỉ yêu cầu xin lỗi khi rubric và tình huống có căn cứ. |
| H-051 | FAIL | PASS | Người. Từ “refund” được LogiX chấp nhận và câu vẫn rõ ràng. | Thêm ví dụ cho các thuật ngữ nghiệp vụ tiếng Anh được chấp nhận. |
| H-070 | PASS | FAIL | Người. Emoji cười không phù hợp khi trả lời khiếu nại. | Nêu emoji cười trong ngữ cảnh khiếu nại làm ví dụ fail. |
| HL-015 | PASS | FAIL | Người. Reply báo 55.000đ, ledger ghi 40.000đ. | Bắt buộc đối chiếu số tiền với ledger trước khi xét độ hữu ích. |
| HL-016 | PASS | FAIL | Người. Lời xin lỗi dài nhưng số 55.000đ sai với ledger 35.000đ. | Tách kiểm tra chính xác nghiệp vụ bằng code khỏi chấm nội dung bằng judge. |

Hai CSV là replay công khai. Trước khi dùng một rubric đã chỉnh cho release, lấy nhãn người trên tập held-out mới và chạy lại cả ba chỉ số.
