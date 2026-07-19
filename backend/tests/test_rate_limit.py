import pytest

from app.core.rate_limit import RateLimitExceeded, check_rate_limit, reset_rate_limits


def test_rate_limit_allows_requests_inside_limit() -> None:
    reset_rate_limits()

    check_rate_limit(scope="chat", key="user-1", limit=2, now=100.0)
    check_rate_limit(scope="chat", key="user-1", limit=2, now=101.0)


def test_rate_limit_blocks_requests_over_limit_until_window_expires() -> None:
    reset_rate_limits()

    check_rate_limit(scope="chat", key="user-1", limit=2, window_seconds=60, now=100.0)
    check_rate_limit(scope="chat", key="user-1", limit=2, window_seconds=60, now=101.0)

    with pytest.raises(RateLimitExceeded):
        check_rate_limit(scope="chat", key="user-1", limit=2, window_seconds=60, now=102.0)

    check_rate_limit(scope="chat", key="user-1", limit=2, window_seconds=60, now=161.0)


def test_rate_limit_is_scoped_by_user_and_endpoint() -> None:
    reset_rate_limits()

    check_rate_limit(scope="chat", key="user-1", limit=1, now=100.0)
    check_rate_limit(scope="chat", key="user-2", limit=1, now=100.0)
    check_rate_limit(scope="search", key="user-1", limit=1, now=100.0)

    with pytest.raises(RateLimitExceeded):
        check_rate_limit(scope="chat", key="user-1", limit=1, now=101.0)
