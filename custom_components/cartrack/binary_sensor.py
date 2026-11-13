"""Ignition and idling binary sensors for CarTrack vehicles."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    """Set up ignition and idling sensors for each vehicle."""
    coordinator: CarTrackCoordinator = entry.runtime_data
    known_ids: set[str] = set()

    @callback
    def add_new_vehicles() -> None:
        new_ids = set(coordinator.data["vehicles"]) - known_ids
        if new_ids:
            known_ids.update(new_ids)
            async_add_entities(
                CarTrackVehicleBinarySensor(coordinator, entry, vehicle_id, key, name)
                for vehicle_id in sorted(new_ids)
                for key, name in (("ignition", "Ignition"), ("idling", "Idling"))
            )

    add_new_vehicles()
    entry.async_on_unload(coordinator.async_add_listener(add_new_vehicles))


class CarTrackVehicleBinarySensor(
    CoordinatorEntity[CarTrackCoordinator], BinarySensorEntity
):
    """Represent one boolean vehicle state reported by CarTrack."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CarTrackCoordinator,
        entry: ConfigEntry,
        vehicle_id: str,
        key: str,
        name: str,
    ) -> None:
        """Initialize a binary sensor for one vehicle property."""
        super().__init__(coordinator)
        vehicle = coordinator.data["vehicles"][vehicle_id]
        registration = vehicle.get("registration") or vehicle_id
        self._vehicle_id = vehicle_id
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{vehicle_id}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{vehicle_id}")},
            name=registration,
            manufacturer="CarTrack",
        )

    @property
    def is_on(self) -> bool | None:
        """Return the latest boolean state, or unknown if it is unavailable."""
        value = (
            self.coordinator.data["vehicles"].get(self._vehicle_id, {}).get(self._key)
        )
        return value if isinstance(value, bool) else None
