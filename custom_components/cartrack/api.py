"""Asynchronous client for the CarTrack Fleet API."""

from __future__ import annotations

import base64
import math
import time
from collections import deque
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from time import monotonic
from typing import TYPE_CHECKING

import aiohttp

if TYPE_CHECKING:
    from collections.abc import Mapping

RATE_LIMIT_WINDOW_SECONDS = 60
DEFAULT_RATE_LIMIT_PER_MINUTE = 1000
ENDPOINT_RATE_LIMITS_PER_MINUTE = {"GET /vehicles/status": 60}
HTTP_TOO_MANY_REQUESTS = 429


class CarTrackApiError(Exception):
    """Base exception for CarTrack API errors."""


class CarTrackAuthError(CarTrackApiError):
    """The API rejected the supplied credentials."""


class CarTrackConnectionError(CarTrackApiError):
    """The API could not be reached or returned an invalid response."""


class CarTrackRateLimitError(CarTrackApiError):
    """The API rejected a request because its rate limit was exceeded."""

    def __init__(self, retry_after: float | None) -> None:
        """Store the server's recommended retry delay, if it provided one."""
        super().__init__("CarTrack API rate limit exceeded")
        self.retry_after = retry_after


def _finite_number(value: str | None) -> float | None:
    """Parse a finite number from a header value."""
    if value is None:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _delay_from_seconds(value: str | None) -> float | None:
    """Parse a seconds value and clamp negative delays to zero."""
    seconds = _finite_number(value)
    return max(0.0, seconds) if seconds is not None else None


def _delay_from_retry_after(value: str | None) -> float | None:
    """Parse Retry-After as either seconds or an HTTP date."""
    delay = _delay_from_seconds(value)
    if delay is not None or value is None:
        return delay
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=UTC)
    delay = (retry_at - datetime.now(UTC)).total_seconds()
    return max(0.0, delay) if math.isfinite(delay) else None


def _delay_from_retry_at(value: str | None) -> float | None:
    """Parse the documented Unix timestamp retry header."""
    retry_at = _finite_number(value)
    if retry_at is None:
        return None
    return max(0.0, retry_at - time.time())


def _retry_after_seconds(headers: Mapping[str, str]) -> float | None:
    """Parse documented rate-limit retry headers into a non-negative delay."""
    normalized_headers = {name.casefold(): value for name, value in headers.items()}
    delays = [
        _delay_from_retry_after(normalized_headers.get("retry-after")),
        _delay_from_seconds(
            normalized_headers.get("x-ratelimit-retry-after-seconds")
        ),
        _delay_from_retry_at(normalized_headers.get("x-ratelimit-retry-at")),
    ]
    valid_delays = [delay for delay in delays if delay is not None]
    return max(valid_delays) if valid_delays else None


class CarTrackApi:
    """Make authenticated requests to one CarTrack account."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        username: str,
        api_key: str,
    ) -> None:
        """Initialize an API client for one account."""
        self._session = session
        self._base_url = base_url.rstrip("/")
        credentials = base64.b64encode(f"{username}:{api_key}".encode()).decode()
        self._headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {credentials}",
        }
        self._request_times: deque[tuple[float, str]] = deque()

    @property
    def rate_limit_stats(self) -> dict:
        """Return request counts and limits for the trailing minute."""
        self._prune_request_times(monotonic())
        requests_by_endpoint: dict[str, int] = {}
        for _, endpoint in self._request_times:
            requests_by_endpoint[endpoint] = requests_by_endpoint.get(endpoint, 0) + 1
        return {
            "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
            "default_limit_per_minute": DEFAULT_RATE_LIMIT_PER_MINUTE,
            "requests_last_minute": len(self._request_times),
            "requests_by_endpoint": requests_by_endpoint,
            "limits_per_minute": {
                endpoint: ENDPOINT_RATE_LIMITS_PER_MINUTE.get(
                    endpoint, DEFAULT_RATE_LIMIT_PER_MINUTE
                )
                for endpoint in requests_by_endpoint
            },
        }

    async def async_get_vehicles(self) -> dict:
        """Return current vehicle status records."""
        return await self._request(
            "GET", "vehicles/status", params={"odometer_in_km": "true"}
        )

    async def async_get_carwatch(self, page: int) -> dict:
        """Return a page of CarWatch states."""
        return await self._request(
            "GET", "carwatch/status", params={"page": page, "limit": 1000}
        )

    async def async_set_carwatch(self, vehicle_id: int, *, activate: bool) -> dict:
        """Change CarWatch state for a vehicle."""
        return await self._request(
            "POST",
            "carwatch",
            json_body={"vehicle_id": vehicle_id, "activate": activate},
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> dict:
        """Send one request and translate transport errors for Home Assistant."""
        now = monotonic()
        self._prune_request_times(now)
        self._request_times.append((now, f"{method} /{path}"))
        try:
            async with self._session.request(
                method,
                f"{self._base_url}/{path}",
                headers=self._headers,
                params=params,
                json=json_body,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == HTTP_TOO_MANY_REQUESTS:
                    raise CarTrackRateLimitError(
                        _retry_after_seconds(response.headers)
                    )
                if response.status in (401, 403):
                    raise CarTrackAuthError
                response.raise_for_status()
                payload = await response.json(content_type=None)
                if not isinstance(payload, dict):
                    raise CarTrackConnectionError
                return payload
        except CarTrackApiError:
            raise
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise CarTrackConnectionError from err

    def _prune_request_times(self, now: float) -> None:
        """Discard requests outside the trailing-minute monitoring window."""
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS
        while self._request_times and self._request_times[0][0] <= cutoff:
            self._request_times.popleft()
