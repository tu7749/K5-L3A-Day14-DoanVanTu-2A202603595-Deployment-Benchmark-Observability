"""Apply a rolling, shared 60-second limit to each authenticated API key."""

from hashlib import sha256
from uuid import uuid4

from fastapi import HTTPException

from .config import settings
from .redis_client import r


_CHECK_WINDOW = r.register_script("""
local now = redis.call('TIME')
local current = tonumber(now[1]) * 1000 + math.floor(tonumber(now[2]) / 1000)
local window = 60000

redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', current - window)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    return math.ceil((tonumber(oldest[2]) + window - current) / 1000)
end

redis.call('ZADD', KEYS[1], current, ARGV[2])
redis.call('PEXPIRE', KEYS[1], window)
return 0
""")


def check_rate_limit(key: str) -> None:
    key_digest = sha256(key.encode()).hexdigest()
    retry_after = _CHECK_WINDOW(
        keys=[f"agent:rate:{key_digest}"],
        args=[settings.rate_limit_per_minute, uuid4().hex],
    )
    if retry_after:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
