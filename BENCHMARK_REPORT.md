# Benchmark & Observability Report — Day 14

**Họ tên:** Doan Van Tu  
**Ngày chạy CP7:** 25/11/2026 (GMT+7)  
**Môi trường CP7:** macOS arm64, Python 3.11.15, Uvicorn local, model `mock-llm-small`.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Ngưỡng mặc định của load test để theo dõi phần đuôi phân phối. |
| Error rate `/ask` | ≤ 2% | Ngưỡng mặc định của load test, tính trên mọi request đã gửi. |
| Accuracy trên golden dataset | ≥ 100% | Quality gate nộp bài CP7 yêu cầu đúng 23/23 và không regression so với baseline v2. |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

Mỗi lượt gửi 300 request, bỏ request warm-up. Bản v2 gốc chạy với `MOCK_SLOW_RATE=0.03` và `MOCK_ERROR_RATE=0.01`. Script tính percentile trên các phản hồi `200` và error rate trên toàn bộ request.

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 3,97 | 195,8 | 223,9 | 1.697,0 | 0,67% | PASS |
| 10 | 38,10 | 189,0 | 223,3 | 1.697,4 | 0,67% | PASS |
| 50 | 102,82 | 199,4 | 342,6 | 1.713,1 | 1,33% | PASS |
| 100 | 63,75 | 463,7 | 3.746,4 | 4.256,8 | 1,00% | FAIL p95 |

**Nhận xét:** RPS có tăng tuyến tính theo concurrency không? Vì sao?

RPS tăng đến concurrency 50 rồi giảm ở 100. Khi tăng từ 50 lên 100, p95 tăng từ 342,6 ms lên 3.746,4 ms dù error rate vẫn trong ngưỡng. Tải chạy cùng máy trên một tiến trình Uvicorn. Kết quả cho thấy chi phí chờ và xử lý đồng thời tăng ở cấu hình này, nhưng số liệu hiện tại chưa định vị được nút thắt ở client hay server.

### 2.2 Tail latency

Mỗi mức chạy 300 request với concurrency 20. Giữ các cấu hình khác như ở 2.1.

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 191,0 | 218,5 | 226,1 |
| 0.03 (mặc định) | 243,2 | 224,7 | 1.703,7 |
| 0.1 | 336,5 | 1.695,9 | 1.713,6 |

**Nhận xét:** Chỉ số nào nhạy nhất với request chậm? Vì sao SLO không nên đặt theo average?

p99 nhạy nhất khi chỉ một phần nhỏ request chậm. Từ slow rate 0 lên 3%, average tăng 52,2 ms, còn p99 tăng 1.477,6 ms. Khi slow rate lên 10%, p95 tăng đến 1.695,9 ms và vi phạm SLO dù average vẫn dưới 500 ms. Percentile làm rõ số người dùng ở phần đuôi mà average dễ che khuất.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

Chạy v1 ở cổng `8001` và v2 ở cổng `8002`. Dùng cùng 23 câu, `MOCK_ERROR_RATE=0` và ngưỡng tối thiểu 60% keyword cho từng câu để đo chất lượng nội dung. So v2 gốc với v1 ở ngưỡng 80%, sau đó so v2 đã sửa với v2 gốc ở ngưỡng 100%.

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4,3% (1/23) | 91,3% (21/23) | 100% (23/23) |
| Avg tokens / câu | 57,1 | 109,1 | 113,9 |
| Tổng cost (USD) | 0,000404 | 0,000762 | 0,000793 |
| Cost / câu đúng (USD) | 0,00040395 | 0,00003627 | 0,00003446 |
| p95 latency (ms) | 191,7 | 217,2 | 219,9 |
| Quality gate | FAIL (ngưỡng 80%) | PASS (ngưỡng 80%, 0 regression) | PASS (ngưỡng 100%, 0 regression) |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| `security-02` | `token`, `hết hạn`, `chữ ký` | Bổ sung mục JWT giải thích claim `exp`, xác minh chữ ký và cách máy chủ tra cứu API key. |
| `scaling-03` | `cpu`, `memory`, `custom metrics` | Bổ sung mục Kubernetes HPA giải thích cách đổi số replica dựa trên metric cấu hình. |

Tham khảo [RFC 7519](https://www.rfc-editor.org/info/rfc7519/) và [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/) cho hai mục bổ sung.

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**

Retrieval giúp v2 gốc trả lời đúng 21/23 câu, với số token trung bình tăng từ 57,1 lên 109,1 và p95 tăng 25,5 ms. Dù tổng chi phí mô phỏng tăng, chi phí trên mỗi câu đúng giảm khoảng 91%. Sau khi bổ sung hai mục còn thiếu, v2 đúng thêm hai câu và chi phí trên mỗi câu đúng giảm tiếp, xuống 0,00003446 USD.

**Quality gate trong CI:** Khởi động v2 với `MOCK_ERROR_RATE=0` và chờ `/health`. Đặt lệnh dưới đây thành một bước bắt buộc của CI để chặn merge. Script trả `0` khi accuracy đạt 100% và không có câu từng đúng chuyển thành sai. Exit code `1` làm job thất bại, còn JSON được lưu để xem câu bị lỗi.

```bash
python eval/run_eval.py --url http://localhost:8002 --min-accuracy 1.0 \
  --baseline reports/eval_v2.json --out reports/eval_v2_fixed.json
```

---

## 4. Observability stack (production)

**Môi trường CP8:** Docker Desktop trên macOS arm64. Docker Hub trả `429`, nên lượt chạy dùng file Compose bổ sung nằm ngoài repo. Các phiên bản Nginx 1.28, Prometheus 3.16.0 và Jaeger 2.23.0 được lấy từ registry thay thế. Locust cài đúng phiên bản 2.47.0 từ PyPI trong image Python local. Dockerfile của agent được bổ sung `PYTHONUSERBASE` để user trong container tìm thấy các gói đã cài.

`promtool test rules` báo `SUCCESS`. `GET /metrics` qua Nginx trả `404`, còn Prometheus scrape trực tiếp agent trong mạng Compose. Cách này giới hạn truy cập vào metrics, vốn có thể tiết lộ lưu lượng, route và thông tin instance.

### 4.1 Screenshot

- [x] [Dashboard Grafana khi đang có tải](screenshots/grafana-dashboard.png)
- [x] [Trace chậm trong Jaeger](screenshots/jaeger-slow-trace.png)
- [x] [Trace lỗi trong Jaeger](screenshots/jaeger-error-trace.png)
- [x] [Hai alert đồng thời firing trên Prometheus](screenshots/prometheus-alert-firing.png)

Khi chụp Grafana, `/ask` đạt 61,6 req/s, error rate 0,53%, p95 293,22 ms và có 3 instance. Một lần truy vấn Prometheus trong cùng lượt tải cho khoảng 20,53, 20,51 và 20,49 req/s theo ba instance. p95 cao hơn average vì một số request chậm kéo phần đuôi lên. Lần truy vấn ghi nhận khoảng 4.522 input token/s và 2.402 output token/s. Bản v2 đưa system prompt, câu hỏi và tài liệu retrieve vào đầu vào, còn đầu ra chỉ gồm câu trả lời.

### 4.2 Thí nghiệm "phá hệ thống"

A và B được bật đồng thời trên 3 replica đang dùng model `mock-llm-small`, với Locust headless ở 30 user. Bắt đầu tính thời gian trước lệnh áp dụng cấu hình lỗi. Dùng một lượt Prometheus mới để tránh đếm trạng thái alert còn từ phép thử trước. Poll API alert khoảng mỗi 4 giây.

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` | 74,7 giây | Error rate |
| B | `MOCK_SLOW_RATE=0.3` | `AgentHighLatencyP95` | 134,8 giây | Latency p95 |
| C | `LLM_MODEL=mock-llm-large` | Chưa chạy | — | Cost burn rate |
| D | `docker pause` 1 instance | Chưa chạy | — | Instances up |
| E | `AGENT_VERSION=v1` | Chưa chạy | — | Phiên bản đang chạy, Retrieval hit ratio |

Khi cả hai alert đang firing, API Prometheus ghi error rate khoảng 18,44% và p95 khoảng 1,894 giây. Hai rule yêu cầu điều kiện duy trì 1 phút và 2 phút. Khởi động lại agent, scrape và chu kỳ đánh giá góp thêm thời gian vào kết quả quan sát.

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

CPU, latency và mã HTTP có thể vẫn trong ngưỡng khi agent trả câu sai. Dùng golden dataset và quality gate để kiểm tra trước khi deploy, rồi chạy eval định kỳ và cảnh báo khi accuracy hoặc tỷ lệ câu đúng theo chủ đề giảm. Với lỗi `504` do Nginx tạo, kiểm tra metric và log ở Nginx hoặc từ một probe bên ngoài vì agent chỉ đếm các phản hồi của chính nó.

### 4.3 Debug bằng trace

**Trace chậm** `5adc2f1361655b8690b4a2e83f2a2e67`. Span gốc `POST /ask` mất 1.723,546 ms và trả `200`. Span `chat mock-llm-small` mất 1.696,461 ms, chiếm 98,43% thời gian của span gốc. Retrieval mất 23,334 ms. Bước gọi mock LLM chiếm phần lớn độ trễ của request này.

Log `llm_call` đối chiếu theo `trace_id`:

```json
{"ts":"2026-11-25T09:00:13.424432+00:00","level":"INFO","service":"observable-agent","instance":"790587e4e80e","event":"llm_call","trace_id":"5adc2f1361655b8690b4a2e83f2a2e67","span_id":"f92bc756f18abd01","request_id":"cp8-evidence-14","model":"mock-llm-small","agent_version":"v2","input_tokens":81,"output_tokens":46,"cost_usd":0.00004,"llm_ms":1692.2}
```

**Trace lỗi** `21b31ee3885a221ca280b2620f22b9c1`. Span gốc trả `503` sau 865,501 ms. Span `chat mock-llm-small` mất 840,417 ms và ghi event `exception` cho lỗi upstream mô phỏng.

```json
{"ts":"2026-11-25T09:00:10.873239+00:00","level":"INFO","service":"observable-agent","instance":"790587e4e80e","event":"llm_error","trace_id":"21b31ee3885a221ca280b2620f22b9c1","span_id":"5d6a0622b60caf4e","request_id":"cp8-evidence-3","error":"Upstream LLM error: 503 Service Unavailable (mock)"}
```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

Dùng Locust 2.47.0 với 100 user, ramp-up 10 user/s và 2 phút cho mỗi lượt. Các hàng bên dưới lấy từ `Aggregated`, gồm cả `/ask` và `/health`, trong hai file `scale_1_stats.csv` và `scale_3_stats.csv`. Cả hai lượt dùng v2, `mock-llm-small`, `MOCK_SLOW_RATE=0.03` và `MOCK_ERROR_RATE=0.01`.

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 66,18 | 190 | 230 | 1.700 | 62 / 7.906 (0,78%) |
| 3 | 65,55 | 190 | 230 | 1.700 | 63 / 7.827 (0,80%) |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

p95 và p99 giữ nguyên, còn RPS chênh dưới 1%. Grafana cho thấy tải phân bố đều khi có ba replica, nhưng việc thêm replica không rút ngắn độ trễ của từng lần gọi mock LLM. Số user và khoảng nghỉ 0,5–2 giây mỗi user cũng giữ nguyên, nên ở mức tải này chưa đo được lợi ích về công suất tối đa. Cả hai lượt đều có lỗi `503` từ upstream mô phỏng, vì vậy Locust thoát với mã `1` và vẫn ghi CSV.

---

## 6. Kết luận

1. Đo nhiều mức concurrency để thấy điểm throughput bắt đầu giảm và latency tăng.
2. Theo dõi cả p95 và p99 vì tỷ lệ nhỏ request chậm có thể làm p99 tăng mạnh trong khi p95 vẫn đạt SLO.
3. Ghép accuracy với chi phí trên mỗi câu đúng để đánh giá lợi ích của retrieval.

Khi chạy production, có thể thêm cảnh báo regression dựa trên eval định kỳ. Các chỉ số latency và error rate phản ánh việc API chạy, còn bộ eval kiểm tra nội dung trả lời.
