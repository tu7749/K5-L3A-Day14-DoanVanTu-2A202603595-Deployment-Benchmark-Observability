"""FastAPI entry point for the Part 6 agent."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import logging
from time import perf_counter

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from redis.exceptions import RedisError

from utils.mock_llm import MOCK_RESPONSES, ask as llm_ask

from .auth import verify_api_key
from .config import settings
from .cost_guard import check_budget, record_cost
from .rate_limiter import check_rate_limit
from .redis_client import r, redis_healthy


MAX_OUTPUT_TOKENS = max(
    len(answer.split()) for answers in MOCK_RESPONSES.values() for answer in answers
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "lvl": record.levelname,
            "event": record.getMessage(),
        }
        for field_name in ("environment", "method", "path", "status", "ms"):
            if hasattr(record, field_name):
                entry[field_name] = getattr(record, field_name)
        return json.dumps(entry, ensure_ascii=False)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", extra={"environment": settings.environment})
    try:
        yield
    finally:
        r.close()
        logger.info("shutdown")


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@app.middleware("http")
async def log_request(request: Request, call_next):
    started = perf_counter()
    response = await call_next(request)
    logger.info(
        "request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": round((perf_counter() - started) * 1000, 2),
        },
    )
    return response


@app.exception_handler(RedisError)
async def redis_unavailable(request: Request, exc: RedisError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "Redis unavailable"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    return {"ready": True}


@app.post("/ask")
def ask(body: AskRequest, api_key: str = Depends(verify_api_key)):
    check_rate_limit(api_key)
    input_tokens = len(body.question.split())
    reservation = check_budget(input_tokens, MAX_OUTPUT_TOKENS)
    try:
        answer = llm_ask(body.question)
    except Exception:
        record_cost(reservation, 0, 0)
        raise
    record_cost(reservation, input_tokens, len(answer.split()))
    return {"question": body.question, "answer": answer}
