"""Shared Redis connection pool for each worker."""

from redis import Redis
from redis.exceptions import RedisError

from .config import settings


r = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def redis_healthy() -> bool:
    try:
        return bool(r.ping())
    except RedisError:
        return False
