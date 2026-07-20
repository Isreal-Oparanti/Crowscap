from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic

from fastapi import Depends, HTTPException, Request

from app.core.auth import CurrentUser, require_current_user
from app.core.config import get_settings


# NOTE: This rate limiter uses a module-level in-process dict. It works
# correctly in single-process deployments (one uvicorn worker). In multi-worker
# deployments (e.g. Gunicorn with 4 workers), each worker maintains its own
# bucket, so the effective per-user limit is limit / num_workers. For
# production scale, replace _BUCKETS with a Redis-backed sliding window counter.
class RateLimitExceeded(Exception):
    pass


_BUCKETS: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_LIMIT_MESSAGE = "You're moving fast - slow down a moment and try again shortly."


def check_rate_limit(
    *,
    scope: str,
    key: str,
    limit: int,
    window_seconds: int = 60,
    now: float | None = None,
) -> None:
    current = monotonic() if now is None else now
    bucket = _BUCKETS[(scope, key)]

    while bucket and current - bucket[0] >= window_seconds:
        bucket.popleft()

    if len(bucket) >= limit:
        raise RateLimitExceeded(_LIMIT_MESSAGE)

    bucket.append(current)


def rate_limit(scope: str, *, limit: int, window_seconds: int = 60):
    def dependency(
        request: Request,
        current_user: CurrentUser = Depends(require_current_user),
    ) -> None:
        if get_settings().app_env == "development":
            return

        client_host = request.client.host if request.client else "unknown"
        key = current_user.id or client_host
        try:
            check_rate_limit(
                scope=scope,
                key=key,
                limit=limit,
                window_seconds=window_seconds,
            )
        except RateLimitExceeded as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc

    return dependency


def reset_rate_limits() -> None:
    _BUCKETS.clear()
