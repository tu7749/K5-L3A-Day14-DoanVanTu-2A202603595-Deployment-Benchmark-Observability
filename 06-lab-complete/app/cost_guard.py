"""Reserve and settle the agent's daily UTC budget in Redis."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from fastapi import HTTPException

from .config import settings
from .redis_client import r


# Mock billing rates in billionths of a US dollar per token.
INPUT_TOKEN_COST = 150
OUTPUT_TOKEN_COST = 600
NANO_USD_PER_DOLLAR = 1_000_000_000

_RESERVE = r.register_script("""
local used = tonumber(redis.call('GET', KEYS[1]) or '0')
if used + tonumber(ARGV[1]) > tonumber(ARGV[2]) then
    return 0
end

redis.call('INCRBY', KEYS[1], ARGV[1])
redis.call('EXPIREAT', KEYS[1], ARGV[3])
return 1
""")

_REFUND = r.register_script("""
if redis.call('EXISTS', KEYS[1]) == 1 then
    redis.call('DECRBY', KEYS[1], ARGV[1])
end
""")


@dataclass(frozen=True)
class BudgetReservation:
    key: str
    amount: int


def _cost(input_tokens: int, output_tokens: int) -> int:
    return input_tokens * INPUT_TOKEN_COST + output_tokens * OUTPUT_TOKEN_COST


def check_budget(input_tokens: int, max_output_tokens: int) -> BudgetReservation:
    """Reserve the maximum mock cost before starting a call."""
    today = datetime.now(timezone.utc).date()
    period_end = datetime.combine(today + timedelta(days=1), time.min, timezone.utc)
    key = f"agent:budget:{today.isoformat()}"
    amount = _cost(input_tokens, max_output_tokens)
    limit = int(settings.daily_budget_usd * NANO_USD_PER_DOLLAR)
    if not _RESERVE(keys=[key], args=[amount, limit, int(period_end.timestamp())]):
        raise HTTPException(status_code=402, detail="Daily cost budget exceeded")
    return BudgetReservation(key, amount)


def record_cost(
    reservation: BudgetReservation, input_tokens: int, output_tokens: int
) -> None:
    """Keep the actual charge and refund the unused portion of the reservation."""
    unused = reservation.amount - _cost(input_tokens, output_tokens)
    if unused:
        _REFUND(keys=[reservation.key], args=[unused])
