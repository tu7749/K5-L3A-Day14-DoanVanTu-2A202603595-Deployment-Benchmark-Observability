# Deployment Information

## Public URL

[https://day14-api-production.up.railway.app](https://day14-api-production.up.railway.app)

## Platform

Railway, project `day14-agent`, service `day14-api`, môi trường `production`. Nguồn deploy là `06-lab-complete/`, sử dụng Dockerfile và cấu hình health check `/health` trong `railway.toml`. Redis chạy trong cùng môi trường Railway và được truy cập qua mạng nội bộ.

## Environment Variables

| Biến | Cấu hình đã đặt |
| --- | --- |
| `AGENT_API_KEY` | Key ngẫu nhiên của agent, lưu trong biến môi trường Railway |
| `REDIS_URL` | Tham chiếu đến URL Redis nội bộ của service Redis |
| `ENVIRONMENT` | `production` |
| `PORT` | `8000`, trùng cổng đích của domain Railway |

## Test Commands

Nạp `AGENT_API_KEY` từ mục Variables của service `day14-api` trước khi chạy lệnh xác thực.

```bash
BASE=https://day14-api-production.up.railway.app
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ask" \
  -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ask" \
  -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" \
  -d '{"question":"Hello"}'
```

Kết quả xác minh trên URL public ngày 25/11/2026 (GMT+7):

| Request | HTTP |
| --- | ---: |
| `GET /health` | `200` |
| `GET /ready` | `200` |
| `POST /ask` thiếu key | `401` |
| `POST /ask` có key hợp lệ | `200` |

## Screenshots

- [Dashboard Railway](screenshots/dashboard.png) hiển thị agent và Redis online.
- [Bản triển khai đang chạy](screenshots/running.png) hiển thị trạng thái Active và log HTTP của agent.
- [Kết quả kiểm tra HTTPS](screenshots/test.png) hiển thị đủ bốn mã HTTP CP6.
