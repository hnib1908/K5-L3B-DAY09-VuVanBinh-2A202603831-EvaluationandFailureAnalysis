# Eval card — LogiX-VN refund agent

## Core v1

Harness `pydantic-evals`, MockLLM, Python 3.13.9 và metric spec 1.0. Eval set SHA `75efc8afcdad` gồm 14 claim từ bộ public Day 8, mỗi claim chạy với seed 11, 22, 33, 44 và 55. Nhãn nằm trong `labels_v1.json`. SHA của JSONL dùng dòng kết thúc LF chuẩn hóa để giống nhau trên Windows và Linux. Code, grader và report đã kiểm tra nằm ở commit `e924b03`. Nguồn Day 8 được đưa vào ở commit `eec4ad8`.

| Shape | Run ID | `pass_rate` | Δ so với baseline, CI 95% | `refund_amount_correct` | `reply_matches_ledger` | Gate |
|---|---|---:|---|---:|---:|---|
| `swarm` | [`E-swarm-20261118-75ef`](../src/reports/baseline_v1.json) | 0.9857 | 0.000 [0.000, 0.000] | 0.9857 | 1.0000 | Exit 0, đối chiếu với chính nó |
| `fixed` | [`E-fixed-20261118-75ef`](../src/reports/eval_fixed.json) | 1.0000 | +0.014 [0.000, +0.043] | 1.0000 | 1.0000 | Exit 0 |
| `seeded_regression` | [`E-seeded_regression-20261118-75ef`](../src/reports/eval_seeded_regression.json) | 0.7143 | −0.271 [−0.500, −0.057] | 0.8571 | 0.7857 | Exit 1 |

Sàn v1 là `pass_rate` ≥ 0.85 và `refund_amount_correct` ≥ 0.95, đồng thời cận trên CI của hiệu không được âm cho hai metric này. `approval_bypass` và `secret_leak` có tối đa 0 vi phạm, với cả ba report đều ghi 0. `reply_matches_ledger` có sàn 1.00 cho các reply quan sát được. Grader đề xuất tiền giải thích thêm trường hợp `C-013`, nơi ledger khớp nhãn dù agent gửi đề xuất sai. [Metric spec v1](../src/config/metric_spec.yaml)

`python -m lab9.mutation --detect` giải thích 20/20 trial bị grader Lab 8 đánh fail trên `seeded_regression` và báo nhầm 0/70 trial trên `fixed`.

Judge giọng điệu đạt κ 0.757, precision 0.857, recall 0.800. Judge `helpful` có κ 0.375 và recall 0.300, nên không dùng làm gate. [Judge audit](judge_audit.md)

[Trace case C-002@11](trace_case.md) tìm thấy lỗi đầu tiên ở event 3 `model_override`. Regression test xác nhận `DbFactKept` phát hiện lỗi ở variant và cho qua đối chứng. Eval owner chịu trách nhiệm xử lý gate đỏ cho pilot ticket giao trễ và hư hỏng đã xác minh. [Phạm vi và trách nhiệm](PRD_v1.1.md)

## Advanced và Expert v2

Baseline [`E-swarm-20261118-3c3f`](../src/reports/baseline_v2.json), eval set SHA `3c3f8b8f2cdb`. Bộ này có 28 item, gồm 14 claim v1 và 14 claim adversarial. Baseline có `pass_rate` 0.9786 và `pass_hat_5` 0.8929, tự so với chính nó cho exit 0. [Metric spec v2](../src/config/metric_spec_v2.yaml)

| Kiểm tra | Kết quả |
|---|---|
| `slice_regression` | [Run `E-slice_regression-20261118-3c3f`](../src/reports/eval_slice_regression.json) có `pass_rate` 0.9357, Δ −0.043, CI [−0.121, +0.029]. Slice `money_movement` giảm từ 1.0000 xuống 0.8500, dưới sàn 0.90. Đây là điều kiện chặn duy nhất ở trial này. |
| `adversarial` | Sàn 0.90 và yêu cầu không giảm có ý nghĩa. Với `slice_regression` điểm 0.9143 nên qua. Slice này phát hiện suy giảm ở nhóm ticket và tình huống đối nghịch, đồng thời chặn `seeded_regression`. |
| `flaky_regression` | `pass_rate` 0.9143 vượt sàn 0.85, còn `pass_hat_5` 0.5714 thấp hơn sàn 0.80 và tự chặn được variant. Paired CI của `pass_rate` cũng chặn trên hai bộ report được so sánh trong lần chạy này. |
| Ghi đè dữ kiện âm thầm | Replay cục bộ `quiet_override` có `db_fact_kept` 1.0000 vì thiếu event ghi đè. Gate vẫn chặn theo `refund_amount_correct` và hai slice `denial`, `adversarial`. |
| Scorecard | Chặn 3/3 hồi quy. `fixed` và `honest_refactor` qua, 0 báo nhầm. |
| A/A | Seed 11, 22, 33, 44, 55 so với 66, 77, 88, 99, 110. `pass_rate` 0.9786 ở cả hai bộ, `pass_hat_5` 0.8929 ở cả hai bộ. Δ bằng 0 trên các metric in ra. |

Sàn `pass_hat_5` 0.80 thấp hơn điểm A/A 0.8929 một khoảng 0.0929. MockLLM trong hai bộ seed có cùng kết quả tổng hợp. Model thật có thể dao động qua lần chạy, nên cần đo dải nhiễu trên nhiều lần A/A và đặt sàn dưới mép dưới của dải trước khi dùng gate. Năm seed mỗi claim cho ít quan sát, nên một lỗi chỉ biểu hiện ở khoảng một phần ba seed, nhất là trên một lát cắt hẹp, chưa phát hiện ổn định được. `pass@5` đo có ít nhất một lần qua, còn `pass^5` đo cả năm lần đều qua.

### Bằng chứng kiểm tra gate

```text
seeded_regression v1 → exit 1 — blocked: refund_amount_correct, pass_rate, reply_matches_ledger
mutation score 3/3 · false alarms 0
A/A pass_rate Δ +0.0000, pass_hat_5 Δ +0.0000
evaluator_errors_as_nan → exit 1 — blocked: integrity
dropped_failing_rows → exit 1 — blocked: integrity
cherry_picked_seeds → exit 1 — blocked: integrity
loosened_spec → exit 1 — blocked: integrity (ratchet)
```

Report phải có đúng một hàng cho mỗi cặp item và seed, cùng các slice với baseline và đủ điểm grader hợp lệ. Gate đối chiếu metric tổng hợp với điểm từng hàng và kiểm tra lỗi evaluator kể cả khi metric tổng hợp đạt ngưỡng. Khi chạy trên PR, ratchet lấy spec từ commit đích và chặn việc nới ngưỡng hoặc bỏ điều kiện trên cùng phiên bản eval set.

## Giới hạn của bằng chứng

- MockLLM và các bộ 14/28 claim đều là mô phỏng. Chưa đo trên người dùng thật hoặc model production.
- Swarm Day 8 không phát sự kiện reply. Điểm `reply_matches_ledger` của baseline chỉ thể hiện không thấy số tiền mâu thuẫn trong dữ liệu đã thu. Grader hiện đọc số tiền VND có đơn vị trong reply được ghi nhận.
- Judge dùng dữ liệu replay công khai. Khi có người gán nhãn mới, cần tập held-out trước khi đổi rubric hoặc chọn judge cho release.
- Khi đổi claim, nhãn hoặc provenance liên quan đến mục đích chấm, tăng phiên bản eval set và sinh baseline cùng seed trước khi so sánh tiếp.
