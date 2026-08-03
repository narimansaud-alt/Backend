from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from random import random


class RetryAction(StrEnum):
    RETRY = "retry"
    PAUSE = "pause"
    FAIL = "fail"


@dataclass(frozen=True)
class RetryDecision:
    action: RetryAction
    delay_seconds: float | None
    code: str


def retry_decision(
    *,
    status_code: int | None,
    attempt: int,
    max_attempts: int,
    retry_after: float | None = None,
) -> RetryDecision:
    if status_code in {401, 403}:
        return RetryDecision(RetryAction.PAUSE, None, "TOKEN_INVALID" if status_code == 401 else "TOKEN_SCOPE_MISSING")
    retryable = status_code is None or status_code == 429 or status_code >= 500
    if not retryable or attempt >= max_attempts:
        return RetryDecision(RetryAction.FAIL, None, "MARKETPLACE_UNAVAILABLE" if retryable else "REQUEST_REJECTED")
    base = retry_after if retry_after is not None else min(300.0, 2 ** max(attempt, 0))
    return RetryDecision(
        RetryAction.RETRY,
        base + random() * min(base * 0.2, 5.0),
        "RATE_LIMITED" if status_code == 429 else "MARKETPLACE_UNAVAILABLE",
    )


def split_period(date_from: date, date_to: date, max_days: int) -> list[tuple[date, date]]:
    if date_to < date_from:
        raise ValueError("date_to must not be earlier than date_from")
    if max_days < 1:
        raise ValueError("max_days must be positive")
    result: list[tuple[date, date]] = []
    current = date_from
    while current <= date_to:
        end = min(date_to, current + timedelta(days=max_days - 1))
        result.append((current, end))
        current = end + timedelta(days=1)
    return result
