"""Asynchronous client for the CarTrack Fleet API."""

from __future__ import annotations

import base64

import aiohttp


class CarTrackApiError(Exception):
    """Base exception for CarTrack API errors."""


class CarTrackAuthError(CarTrackApiError):
    """The API rejected the supplied credentials."""


class CarTrackConnectionError(CarTrackApiError):
    """The API could not be reached or returned an invalid response."""


class CarTrackApi:
    """Make authenticated requests to one CarTrack account."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        username: str,
        api_key: str,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        credentials = base64.b64encode(f"{username}:{api_key}".encode()).decode()
        self._headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {credentials}",
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

    async def async_set_carwatch(self, vehicle_id: int, activate: bool) -> dict:
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
        try:
            async with self._session.request(
                method,
                f"{self._base_url}/{path}",
                headers=self._headers,
                params=params,
                json=json_body,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status in (401, 403):
                    raise CarTrackAuthError
                response.raise_for_status()
                payload = await response.json(content_type=None)
                if not isinstance(payload, dict):
                    raise CarTrackConnectionError("Unexpected API response")
                return payload
        except CarTrackApiError:
            raise
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise CarTrackConnectionError from err