"""Data coordinator for CarTrack account data."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CarTrackApi, CarTrackAuthError, CarTrackConnectionError
from .const import (
    DEFAULT_MOVING_UPDATE_INTERVAL_SECONDS,
    DOMAIN,
    UPDATE_INTERVAL_SECONDS,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def _records(payload: dict) -> list[dict]:
    """Extract a list of records from a documented API response envelope."""
    data = payload.get("data", [])
    if not isinstance(data, list):
        raise CarTrackConnectionError
    return [record for record in data if isinstance(record, dict)]


class CarTrackCoordinator(DataUpdateCoordinator[dict]):
    """Fetch vehicle status and CarWatch states for one account."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: CarTrackApi,
        moving_update_interval_seconds: int = DEFAULT_MOVING_UPDATE_INTERVAL_SECONDS,
    ) -> None:
        """Initialize the coordinator with parked and active polling intervals."""
        self.api = api
        self._parked_update_interval = timedelta(seconds=UPDATE_INTERVAL_SECONDS)
        self._moving_update_interval = timedelta(seconds=moving_update_interval_seconds)
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=self._parked_update_interval,
        )

    async def _async_update_data(self) -> dict:
        """Fetch all current vehicle and CarWatch data."""
        try:
            vehicle_payload = await self.api.async_get_vehicles()
            vehicles = {
                str(vehicle["vehicle_id"]): vehicle
                for vehicle in _records(vehicle_payload)
                if vehicle.get("vehicle_id") is not None
            }

            carwatch: dict[str, dict] = {}
            page = 1
            while True:
                payload = await self.api.async_get_carwatch(page)
                carwatch.update(
                    {
                        str(vehicle["vehicle_id"]): vehicle
                        for vehicle in _records(payload)
                        if vehicle.get("vehicle_id") is not None
                    }
                )
                meta = payload.get("meta", {})
                last_page = (
                    meta.get("last_page", page) if isinstance(meta, dict) else page
                )
                if not isinstance(last_page, int) or page >= last_page:
                    break
                page += 1

            self.update_interval = (
                self._parked_update_interval
                if all(
                    vehicle.get("ignition") is False for vehicle in vehicles.values()
                )
                else self._moving_update_interval
            )
        except CarTrackAuthError as err:
            raise ConfigEntryAuthFailed from err
        except CarTrackConnectionError as err:
            raise UpdateFailed from err
        else:
            return {"vehicles": vehicles, "carwatch": carwatch}
