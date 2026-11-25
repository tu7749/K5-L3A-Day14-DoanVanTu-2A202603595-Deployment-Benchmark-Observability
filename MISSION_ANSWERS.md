# Day 14 — Mission Answers

## CP0 — Môi trường

- Python 3.11.15 trong `.venv/`, Docker 29.9.3 và Docker Compose v5.7.0.
- `docker run --rm hello-world` chạy thành công trên arm64.

## Part 1 — Localhost vs Production

### Exercise 1.1 — Các vấn đề quan sát được

Trong [`develop/app.py`](01-localhost-vs-production/develop/app.py):

1. Dòng 17–18 ghi API key mẫu và chuỗi kết nối có mật khẩu trực tiếp trong mã nguồn. Với thông tin xác thực thật, Git sẽ lưu chúng trong lịch sử.
2. Dòng 33–38 dùng `print()` và in cả giá trị key mẫu ra log. Người có quyền đọc log sẽ thấy key nếu dùng cách này với thông tin xác thực thật.
3. Dòng 42–43 ghi chú rằng app thiếu health check. Kiểm tra HTTP thực tế cho thấy `GET /health` trả `404`.
4. Dòng 51 chỉ bind vào `localhost`, nên app trong container sẽ không nhận lưu lượng qua cổng publish.
5. Dòng 52 cố định cổng `8000`. Nền tảng cấp cổng khác qua `PORT` sẽ không kết nối đúng.
6. Dòng 53 luôn bật reload. Thay đổi file có thể khởi động lại tiến trình khi đang phục vụ.

### Exercise 1.2 — Kết quả chạy bản develop

Gửi `POST /ask?question=Hello` trên localhost. Kết quả thực tế:

```text
HTTP 200
{"answer": "Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

### Exercise 1.3 — So sánh hai bản

| Hạng mục | Develop | Production | Tại sao quan trọng? |
| --- | --- | --- | --- |
| Cấu hình | Giá trị cố định trong `app.py` | `config.py` đọc biến môi trường. `app.py` dùng `settings.port` khi khởi động | Đổi cổng và cấu hình giữa các môi trường mà không sửa mã nguồn. |
| Health và readiness | `/health` trả `404` | `/health` và `/ready` đều trả `200` sau startup | Liveness cho biết tiến trình còn sống. Readiness cho biết nó có thể nhận lưu lượng. |
| Logging | `print()` cả câu hỏi và key mẫu | Dùng `logging` và cấu hình định dạng JSON trong mã. Lần chạy thử không thấy thông báo INFO riêng `Shutdown complete` của app | Log có cấu trúc giúp truy vấn và đối chiếu sự kiện. Cần kiểm tra đầu ra thực tế trước khi dựa vào cấu hình trong mã. |
| Shutdown | Không có cleanup qua lifespan riêng | Có cleanup qua lifespan. Khi gửi SIGTERM, Uvicorn báo `Application shutdown complete.` và tiến trình thoát với mã `0` | Cho phép tiến trình dọn tài nguyên khi dừng. Lần chạy này xác minh shutdown sau khi request đã kết thúc. |

Bản production nhận JSON ở `POST /ask`. Thử với `{"question":"Hello"}` trả `200`, có `answer` từ mock LLM.

## Part 2 — Docker Containerization

### Exercise 2.1 — Dockerfile cơ bản

1. Base image là `python:3.11`, cung cấp Python 3.11 và môi trường hệ điều hành cho container.
2. `WORKDIR /app` đặt thư mục làm việc cho các lệnh build sau đó và cho app lúc khởi động.
3. Copy `requirements.txt` rồi cài dependency trước khi copy mã nguồn để Docker tái sử dụng layer cài đặt khi chỉ `app.py` thay đổi.
4. `CMD ["python", "app.py"]` đặt lệnh mặc định và có thể được thay bằng đối số sau tên image trong `docker run`. `ENTRYPOINT` đặt chương trình chính. Nếu có cả hai ở dạng exec, `CMD` cung cấp các đối số mặc định cho `ENTRYPOINT`.

### Exercise 2.2 — Build và chạy image develop

Build từ gốc repo bằng `docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .`. Container publish cổng `8000` sang một cổng tạm trên loopback. `GET /health` trả `200` và `container: true`. `POST /ask?question=What%20is%20Docker%3F` trả:

```text
HTTP 200
{"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}
```

### Exercise 2.3 — Multi-stage và kích thước image

Build từ gốc repo bằng `docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .`. Stage `builder` dùng `python:3.11-slim`, cài `gcc`, `libpq-dev` và các dependency Python vào `/root/.local`. Stage `runtime` bắt đầu từ một base `python:3.11-slim` mới, chép dependency đã cài và mã app, rồi chạy Uvicorn bằng `appuser`. Base slim và việc để công cụ build ở stage đầu giúp giảm dung lượng image cuối.

Kết quả đo bằng Docker 29.9.3 trên `linux/arm64`:

| Image | `DISK USAGE` trong `docker image ls` | Số byte từ `docker image inspect` | `CONTENT SIZE` |
| --- | ---: | ---: | ---: |
| `my-agent:develop` | 1.67 GB | 1,672,169,653 | 415 MB |
| `my-agent:advanced` | 265 MB | 265,489,069 | 57.5 MB |

Tính trên cùng chỉ số dung lượng, bản advanced giảm **84,12%** so với develop. `CONTENT SIZE` là cột riêng và không được dùng trong phép tính này.

### Exercise 2.4 — Compose và Nginx

File `02-docker/production/.env.local` được tạo để Compose đọc. Chạy từ gốc repo bằng `docker compose -p k5-day14-docker -f 02-docker/production/docker-compose.yml up -d --build --wait`. Bốn service hoạt động trên mạng bridge nội bộ:

```text
Client ── HTTP :80 ──> Nginx ── HTTP ──> agent:8000
                                         ├─ Redis:6379  (URL cấu hình)
                                         └─ Qdrant:6333 (URL cấu hình)
```

Compose chờ Redis và Qdrant vượt health check rồi mới khởi động agent. Chỉ Nginx publish cổng ra host. Agent mẫu gọi mock LLM cho `/ask`, nên request này kiểm chứng đường đi qua Nginx đến agent. Hai backend được xác nhận riêng qua health check của Compose.

| Request qua Nginx | Kết quả thực tế |
| --- | --- |
| `GET /health` | `HTTP 200`, `Server: nginx`, JSON có `"status":"ok"` và `"version":"2.0.0"` |
| `POST /ask` với JSON `{"question":"Explain microservices"}` | `HTTP 200`, `Server: nginx`, JSON có câu trả lời mock |

## Part 3 — Cloud Deployment

### Exercises 3.1–3.2 — Railway và Render

Đã deploy agent Part 6 lên Railway tại [day14-api-production.up.railway.app](https://day14-api-production.up.railway.app). Cấu hình [`railway.toml`](06-lab-complete/railway.toml) dùng `DOCKERFILE` làm builder và `/health` làm health check. `PORT`, `AGENT_API_KEY` và tham chiếu `REDIS_URL` được đặt trên service. Kết quả public theo thứ tự `/health`, `/ready`, `/ask` thiếu key và `/ask` có key là `200`, `200`, `401`, `200`. Xem [DEPLOYMENT.md](DEPLOYMENT.md).

Ví dụ [`render.yaml`](03-cloud-deployment/render/render.yaml) mô tả một Blueprint gồm web service Python và Redis, với lệnh build, lệnh start, gói tài nguyên và biến môi trường khai báo trong YAML. `generateValue` để Render sinh API key, còn `sync: false` để nhập secret trên dashboard. Cấu hình Railway của Part 6 dùng Dockerfile để đóng gói app, đồng thời quản lý Redis và tham chiếu kết nối trong project Railway. Cả hai dùng `/health` để kiểm tra tiến trình.

### Exercise 3.3 — Pipeline Cloud Run

1. [`cloudbuild.yaml`](03-cloud-deployment/production-cloud-run/cloudbuild.yaml) chạy `pytest`, rồi build Docker image và gắn tag theo commit cùng tag `latest`.
2. Pipeline push image lên registry và dùng `gcloud run deploy` để triển khai image mang tag của commit.
3. [`service.yaml`](03-cloud-deployment/production-cloud-run/service.yaml) mô tả cổng `8000`, giới hạn concurrency, autoscaling và các secret lấy từ Secret Manager.
4. Cấu hình service dùng `/ready` cho startup probe và `/health` cho liveness probe.

## Part 4 — API Security

### Exercise 4.1 — API key

App `develop/` bảo vệ `POST /ask` bằng `X-API-Key`. Kết quả `curl -i` trên localhost, trích dòng trạng thái và JSON:

```text
HTTP/1.1 401 Unauthorized
{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}

HTTP/1.1 200 OK
{"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

### Exercise 4.2 — JWT

Bản `production/` trả `401` và `WWW-Authenticate: Bearer` khi gọi `/ask` thiếu token. Đăng nhập bằng tài khoản mẫu `student` qua `POST /auth/token` trả `200` và JWT có hạn 60 phút. Client gửi `Authorization: Bearer <token>` cho các request sau. Server xác thực chữ ký và hạn dùng, rồi đọc `sub` và `role` để áp dụng quyền và giới hạn. Token thực tế đã được lược bỏ.

### Exercise 4.3 — Rate limiting

Limiter dùng cửa sổ trượt 60 giây. Nó lưu timestamp theo người dùng trong `deque`, loại các timestamp ngoài cửa sổ rồi kiểm tra số request còn lại. Role `user` có giới hạn 10 request/phút. Role `admin` dùng limiter riêng với giới hạn 100 request/phút.

Trong 20 lần gọi `POST /ask` liên tiếp bằng token `student`, lần 1–10 trả `200` và lần 11–20 trả `429`. Trích `curl -i` ở lần 11:

```text
HTTP/1.1 429 Too Many Requests
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
retry-after: 59
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
```

### Exercise 4.4 — Cost guard

App mẫu kiểm tra tổng chi phí đã ghi nhận trước khi gọi mock LLM, với ngân sách **1 USD/ngày mỗi người dùng** và **10 USD/ngày toàn app**. Hết ngân sách cá nhân trả `402`, hết ngân sách toàn app trả `503`. Sau khi gọi, app tính và ghi chi phí theo token đầu vào và đầu ra. Các bộ đếm của mẫu nằm trong bộ nhớ tiến trình.

Với thiết kế Redis theo bài tập, dùng khóa `budget:<user_id>:<YYYY-MM>` và hạn mức **10 USD/tháng mỗi người dùng**. So sánh số đã dùng cộng chi phí ước tính với hạn mức trước khi gọi LLM. Dùng một thao tác nguyên tử trong Redis để kiểm tra và giữ trước khoản ước tính, giúp nhiều instance không cùng phê duyệt vượt ngân sách. Sau khi gọi, đối soát với chi phí thực tế. Khóa tháng mới bắt đầu kỳ mới, và TTL dọn khóa cũ. Rate limit giới hạn tần suất request, còn cost guard giới hạn chi phí ngay cả khi từng request tốn lượng token khác nhau.

## Part 5 — Scaling & Reliability

### Exercises 5.1–5.2 — Health, readiness và graceful shutdown

- `GET /health` trả `200`, `status: ok` sau startup. Liveness cho biết tiến trình còn hoạt động. `GET /ready` trả `200`, `ready: true` và cho load balancer biết instance đã sẵn sàng nhận request. Theo mã mẫu develop, `/ready` trả `503` khi cờ readiness chưa bật.
- Gửi hai `POST /ask` đồng thời và gửi `SIGTERM` sau 0,5 giây khi cả hai còn chờ phản hồi. Cả hai trả `200`. Uvicorn ghi `Application shutdown complete.` và tiến trình thoát với mã `0` khi app được import trước khi khởi động server, tương đương thứ tự trong `python app.py`. Lần thử bằng `uvicorn app:app` trả đủ hai phản hồi nhưng tiến trình còn chạy sau thời gian chờ 10 giây. Thứ tự nạp app quan trọng vì mã mẫu đăng ký handler tín hiệu khi được import.

### Exercises 5.3–5.5 — Redis, load balancing và stateless

Nếu lưu hội thoại trong RAM, request tiếp theo có thể đến replica khác và mất lịch sử. Ở bản production, các replica dùng chung Redis và đọc cùng khóa `session:<session_id>`. Nginx nhận HTTP ở cổng `8080` rồi chuyển request đến một trong ba agent.

Từ `05-scaling-reliability/production/`, chạy `docker compose -p k5-day14-scaling up -d --build --scale agent=3 --wait`, sau đó chạy `python test_stateless.py`. `/health` qua Nginx báo `storage: redis` và `redis_connected: true`. Script gửi năm câu trong cùng một phiên, đi qua ba instance khác nhau rồi đọc được **10 tin nhắn** gồm năm câu hỏi và năm câu trả lời. Khi dừng riêng một replica, `GET /chat/{session_id}/history` vẫn trả `200` với đúng phiên và cả 10 tin nhắn theo thứ tự.

## Part 6 — Final Project

Kết quả chạy `python check_production_ready.py` trong `06-lab-complete/` với Docker:

```text
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 41/41 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
```

Bộ chấm đo image **297 MB** và `docker stop` hoàn tất trong **0,5 giây** với exit code `0`. Mục Public URL ở lần chạy này xác nhận cấu hình Railway và biến `PORT`. URL chạy thật thuộc CP6.

## AI log

- Yêu cầu: bắt đầu dự án theo checkpoint K5. AI hỗ trợ thiết lập `.venv`, đối chiếu mã mẫu, chạy smoke test trên localhost và ghi lại nhận xét cho Part 1.
- Kiểm chứng: các mã HTTP và mã thoát trong bản nháp được lấy từ lần chạy tại workspace. Phần chạy lại và xác nhận của học viên chưa được ghi nhận.
- CP2: AI hỗ trợ đọc Dockerfile, build hai image, đo dung lượng bằng Docker, chạy các yêu cầu HTTP và ghi bản nháp kết quả. Các số liệu và mã HTTP đến từ lần chạy tại workspace. Phần chạy lại và xác nhận của học viên chưa được ghi nhận.
- CP3: AI hỗ trợ chạy các app mẫu trên localhost, ghi lại mã HTTP từ `curl -i` và giải thích limiter cùng cost guard từ mã nguồn. Đã đối chiếu chuỗi 10 phản hồi `200` rồi 10 phản hồi `429`. Phần chạy lại và xác nhận của học viên chưa được ghi nhận.
- CP4: AI hỗ trợ kiểm tra health và shutdown, chạy stack ba replica và `test_stateless.py`, rồi xác minh lịch sử sau khi dừng một replica. Kết quả lấy từ các lệnh chạy tại workspace. Phần chạy lại và xác nhận của học viên chưa được ghi nhận.
- CP5: AI hỗ trợ triển khai endpoint FastAPI, xác thực, rate limit và ngân sách dùng Redis, JSON log, cấu hình Docker và Railway. Đã chạy bộ chấm gốc với Docker và dùng key tạm trong quá trình kiểm tra. Phần chạy lại và xác nhận của học viên chưa được ghi nhận.
- CP6: AI hỗ trợ so sánh Railway, Render và Cloud Run, triển khai agent lên Railway, cấu hình Redis nội bộ và chạy đủ bốn phép thử HTTPS. Các mã HTTP đến từ URL public. Key được tạo và lưu trong Railway.
- CP7: AI chạy benchmark và eval local, bổ sung kiến thức JWT và Kubernetes HPA từ hai câu baseline chưa đạt, rồi chạy lại quality gate 100%. Các số liệu trong `BENCHMARK_REPORT.md` lấy từ JSON do script tạo. Phần chạy lại và xác nhận của học viên chưa được ghi nhận.
- CP8: AI sửa đường dẫn thư viện Python trong Dockerfile của agent observability, chạy Locust với 1 và 3 replica, thu ảnh Grafana, Jaeger và Prometheus, rồi đối chiếu số liệu với CSV, kết quả Prometheus và log của hai trace. Phần chạy lại và xác nhận của học viên chưa được ghi nhận.
