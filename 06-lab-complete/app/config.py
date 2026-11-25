"""Settings read from the process environment."""

from dataclasses import dataclass
from decimal import Decimal
import os


@dataclass(frozen=True)
class Settings:
    port: int
    environment: str
    agent_api_key: str
    redis_url: str
    rate_limit_per_minute: int
    daily_budget_usd: Decimal


settings = Settings(
    port=int(os.getenv("PORT", "8000")),
    environment=os.getenv("ENVIRONMENT", "development"),
    agent_api_key=os.getenv("AGENT_API_KEY", ""),
    redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
    rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "10")),
    daily_budget_usd=Decimal(os.getenv("DAILY_BUDGET_USD", "1.00")),
)

if settings.rate_limit_per_minute < 1:
    raise ValueError("RATE_LIMIT_PER_MINUTE must be positive")

if not settings.daily_budget_usd.is_finite() or settings.daily_budget_usd < 0:
    raise ValueError("DAILY_BUDGET_USD must be a finite, nonnegative amount")
