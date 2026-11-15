"""Vehicle location trackers for CarTrack."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.device_tracker.const import SourceType
from homeassistant.components.device_tracker.entity import TrackerEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CarTrackCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one location tracker per vehicle."""
    coordinator: CarTrackCoordinator = entry.runtime_data
    known_ids: set[str] = set()

    @callback
    def add_new_vehicles() -> None:
        new_ids = set(coordinator.data["vehicles"]) - known_ids
        if new_ids:
            known_ids.update(new_ids)
            async_add_entities(
                CarTrackVehicleTracker(coordinator, entry, vehicle_id)
                for vehicle_id in sorted(new_ids)
            )

    add_new_vehicles()
    entry.async_on_unload(coordinator.async_add_listener(add_new_vehicles))


class CarTrackVehicleTracker(CoordinatorEntity[CarTrackCoordinator], TrackerEntity):
    """Expose the latest CarTrack coordinates as a Home Assistant tracker."""

    _attr_device_info: DeviceInfo
    _attr_has_entity_name = True
    _attr_source_type = SourceType.GPS
    _attr_name = "Location"

    def __init__(
        self, coordinator: CarTrackCoordinator, entry: ConfigEntry, vehicle_id: str
    ) -> None:
        """Initialize the tracker for one vehicle."""
        super().__init__(coordinator)
        vehicle = coordinator.data["vehicles"][vehicle_id]
        registration = vehicle.get("registration") or vehicle_id
        self._vehicle_id = vehicle_id
        self._attr_unique_id = f"{entry.entry_id}_{vehicle_id}_location"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{vehicle_id}")},
            name=registration,
            manufacturer="CarTrack",
        )

    @property
    def latitude(self) -> float | None:
        """Return the latest vehicle latitude."""
        return self._coordinate("latitude", "lat")

    @property
    def longitude(self) -> float | None:
        """Return the latest vehicle longitude."""
        return self._coordinate("longitude", "lon", "lng")

    def _coordinate(self, *keys: str) -> float | None:
        vehicle = self.coordinator.data["vehicles"].get(self._vehicle_id, {})
        location = vehicle.get("location")
        if not isinstance(location, dict):
            return None
        for key in keys:
            value = location.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value)
                except ValueError:
                    continue
        return None
