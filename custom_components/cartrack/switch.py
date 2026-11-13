"""CarWatch switches for CarTrack vehicles."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CarTrackCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up one CarWatch switch for each vehicle, including new vehicles."""
    coordinator: CarTrackCoordinator = entry.runtime_data
    known_ids: set[str] = set()

    @callback
    def add_new_vehicles() -> None:
        new_ids = set(coordinator.data["vehicles"]) - known_ids
        if new_ids:
            known_ids.update(new_ids)
            async_add_entities(
                CarTrackCarWatchSwitch(coordinator, entry, vehicle_id)
                for vehicle_id in sorted(new_ids)
            )

    add_new_vehicles()
    entry.async_on_unload(coordinator.async_add_listener(add_new_vehicles))


class CarTrackCarWatchSwitch(CoordinatorEntity[CarTrackCoordinator], SwitchEntity):
    """Activate or deactivate CarWatch for a single vehicle."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:shield-car"

    def __init__(
        self, coordinator: CarTrackCoordinator, entry: ConfigEntry, vehicle_id: str
    ) -> None:
        super().__init__(coordinator)
        vehicle = coordinator.data["vehicles"][vehicle_id]
        registration = vehicle.get("registration") or vehicle_id
        self._vehicle_id = vehicle_id
        self._attr_unique_id = f"{entry.entry_id}_{vehicle_id}_carwatch"
        self._attr_name = "CarWatch"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{vehicle_id}")},
            name=registration,
            manufacturer="CarTrack",
        )

    @property
    def is_on(self) -> bool | None:
        """Return CarWatch status, or unknown until CarTrack reports it."""
        watch = self.coordinator.data["carwatch"].get(self._vehicle_id)
        return watch.get("is_active") if watch is not None else None

    async def async_turn_on(self, **kwargs) -> None:
        """Activate CarWatch for this vehicle."""
        await self._set_carwatch(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Deactivate CarWatch for this vehicle."""
        await self._set_carwatch(False)

    async def _set_carwatch(self, activate: bool) -> None:
        await self.coordinator.api.async_set_carwatch(
            int(self._vehicle_id), activate
        )
        await self.coordinator.async_request_refresh()