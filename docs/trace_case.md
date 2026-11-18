# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Trace case đã kiểm tra

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run `E-seeded_regression-20261118-75ef`, item `E-002`. |
| Triệu chứng | `TrialPass` fail do `resolved` khác `denied`. Reply báo hoàn 20.000đ, ledger đã ghi 20.000đ trong khi nhãn yêu cầu 0đ và 0 lần hoàn. |
| Bước sai đầu tiên | Event **3**, `model_override`, payload `{"delay_days": 5}`. |
| Vì sao là bước đầu tiên | Event 1 giao đúng claim trong phạm vi chủ sở hữu. Event 2 tra đúng đơn O-202 từ DB. Event 3 ghi đè số ngày trễ bằng nội dung ticket. Event 4 mới tính khoản hoàn 20.000đ từ dữ kiện đã bị đổi. |
| Failure mode | [FM-03 `ticket_trust`](failure_taxonomy.md) |
| Đối chứng | `fixed C-002@11`, run `E-fixed-20261118-75ef`. Sau tra cứu, event 3 là quote 0đ với lý do `no_entitlement`. Ledger giữ 0đ và trạng thái là `denied`. |
| Regression test | `test_grader_distinguishes_regression_from_fixed` trong [test_lab9_trace_case.py](../src/tests/test_lab9_trace_case.py). `DbFactKept` trả `False` trên variant lỗi và `True` trên `fixed`. Test thứ hai dùng cùng cơ chế để kiểm tra FM-08 trên C-008. |
| Chưa chắc chắn | Trace ghi nhận lần override này. Muốn phát hiện variant ghi đè âm thầm, đối chiếu thêm kết quả và ledger với nhãn. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- Ghi số event và payload của bước sai đầu tiên.
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
