"""Tests for the CarTrack API client."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

_API_PATH = Path(__file__).parents[1] / "custom_components" / "cartrack" / "api.py"
_API_SPEC = importlib.util.spec_from_file_location("cartrack_api", _API_PATH)
assert _API_SPEC is not None
assert _API_SPEC.loader is not None
_API_MODULE = importlib.util.module_from_spec(_API_SPEC)
_API_SPEC.loader.exec_module(_API_MODULE)
CarTrackApi = _API_MODULE.CarTrackApi
CarTrackAuthError = _API_MODULE.CarTrackAuthError

BASE_URL = "https://fleetapi-au.cartrack.com/rest"
EXPECTED_RETRY_AFTER_SECONDS = 15

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Self


class FakeResponse:
    """Minimal async response used to test the API client contract."""

    def __init__(
        self,
        payload: dict,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Store the payload and HTTP status returned by the fake response."""
        self.payload = payload
        self.status = status
        self.headers = headers or {}

    async def __aenter__(self) -> Self:
        """Enter the fake asynchronous response context."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the fake asynchronous response context."""

    async def json(self, **_kwargs: Any) -> dict:
        """Return the configured response payload."""
        return self.payload

    def raise_for_status(self) -> None:
        """Match the response method without raising an HTTP error."""


class FakeSession:
    """Capture API requests and return a configured response."""

    def __init__(
        self,
        payload: dict,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Store the response configuration and initialize request capture."""
        self.payload = payload
        self.status = status
        self.headers = headers or {}
        self.requests = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        """Capture request arguments and return the configured response."""
        self.requests.append({"method": method, "url": url, **kwargs})
        return FakeResponse(self.payload, self.status, self.headers)


@pytest.mark.asyncio
async def test_get_vehicles_uses_documented_endpoint() -> None:
    """Vehicle status is read from the documented API path."""
    response = {"data": [{"vehicle_id": 123, "registration": "ABC123"}]}
    session = FakeSession(response)
    api = CarTrackApi(session, BASE_URL, "account", "api-key")

    assert await api.async_get_vehicles() == response
    request = session.requests[0]
    assert request["method"] == "GET"
    assert request["url"] == f"{BASE_URL}/vehicles/status"
    assert request["params"] == {"odometer_in_km": "true"}
    assert request["headers"]["Authorization"] == "Basic YWNjb3VudDphcGkta2V5"


@pytest.mark.asyncio
async def test_set_carwatch_posts_vehicle_and_requested_state() -> None:
    """CarWatch changes use the documented POST body."""
    session = FakeSession({"data": [{"message": "Successfully activated"}]})
    api = CarTrackApi(session, BASE_URL, "account", "api-key")

    await api.async_set_carwatch(123, activate=True)

    request = session.requests[0]
    assert request["method"] == "POST"
    assert request["url"] == f"{BASE_URL}/carwatch"
    assert request["json"] == {"vehicle_id": 123, "activate": True}


@pytest.mark.asyncio
async def test_unauthorized_response_is_reported_as_auth_error() -> None:
    """Invalid account credentials are distinguishable from connection errors."""
    session = FakeSession({}, status=401)
    api = CarTrackApi(session, BASE_URL, "account", "bad-key")

    with pytest.raises(CarTrackAuthError):
        await api.async_get_vehicles()


@pytest.mark.asyncio
async def test_rate_limit_stats_count_requests_per_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The monitor reports account requests and the endpoint-specific ceiling."""
    now = 100.0
    monkeypatch.setattr(_API_MODULE, "monotonic", lambda: now)
    api = CarTrackApi(FakeSession({}), BASE_URL, "account", "api-key")

    await api.async_get_vehicles()
    await api.async_get_vehicles()
    await api.async_get_carwatch(1)

    assert api.rate_limit_stats == {
        "window_seconds": 60,
        "default_limit_per_minute": 1000,
        "requests_last_minute": 3,
        "requests_by_endpoint": {
            "GET /vehicles/status": 2,
            "GET /carwatch/status": 1,
        },
        "limits_per_minute": {
            "GET /vehicles/status": 60,
            "GET /carwatch/status": 1000,
        },
    }


@pytest.mark.asyncio
async def test_rate_limit_stats_expire_requests_after_one_minute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Requests older than the rolling 60-second window are excluded."""
    now = 100.0
    monkeypatch.setattr(_API_MODULE, "monotonic", lambda: now)
    api = CarTrackApi(FakeSession({}), BASE_URL, "account", "api-key")

    await api.async_get_vehicles()
    now += 60

    assert api.rate_limit_stats == {
        "window_seconds": 60,
        "default_limit_per_minute": 1000,
        "requests_last_minute": 0,
        "requests_by_endpoint": {},
        "limits_per_minute": {},
    }


@pytest.mark.asyncio
async def test_rate_limit_error_uses_server_retry_headers() -> None:
    """A 429 response preserves CarTrack's recommended retry delay."""
    session = FakeSession(
        {},
        status=429,
        headers={
            "Retry-After": "15",
            "X-RateLimit-Retry-After-Seconds": str(EXPECTED_RETRY_AFTER_SECONDS),
        },
    )
    api = CarTrackApi(session, BASE_URL, "account", "api-key")

    with pytest.raises(_API_MODULE.CarTrackRateLimitError) as error:
        await api.async_get_vehicles()

    assert error.value.retry_after == EXPECTED_RETRY_AFTER_SECONDS
