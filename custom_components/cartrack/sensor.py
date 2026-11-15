"""Vehicle status sensors for CarTrack."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength, UnitOfSpeed
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
    """Set up one status sensor for each vehicle, including newly discovered ones."""
    coordinator: CarTrackCoordinator = entry.runtime_data
    known_ids: set[str] = set()

    @callback
    def add_new_vehicles() -> None:
        new_ids = set(coordinator.data["vehicles"]) - known_ids
        if new_ids:
            known_ids.update(new_ids)
            entities = []
            for vehicle_id in sorted(new_ids):
                entities.append(CarTrackVehicleSensor(coordinator, entry, vehicle_id))
                entities.extend(
                    CarTrackTelemetrySensor(coordinator, entry, vehicle_id, description)
                    for description in TELEMETRY_SENSORS
                )
            async_add_entities(entities)

    add_new_vehicles()
    entry.async_on_unload(coordinator.async_add_listener(add_new_vehicles))


class CarTrackVehicleSensor(CoordinatorEntity[CarTrackCoordinator], SensorEntity):
    """Summarize current vehicle state and expose available telemetry as attributes."""

    entity_description = SensorEntityDescription(key="vehicle_status")
    _attr_has_entity_name = True
    _attr_icon = "mdi:car-connected"

    def __init__(
        self, coordinator: CarTrackCoordinator, entry: ConfigEntry, vehicle_id: str
    ) -> None:
        """Initialize the summary sensor for one vehicle."""
        super().__init__(coordinator)
        vehicle = coordinator.data["vehicles"][vehicle_id]
        registration = vehicle.get("registration") or vehicle_id
        self._vehicle_id = vehicle_id
        self._attr_unique_id = f"{entry.entry_id}_{vehicle_id}_status"
        self._attr_name = "Status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{vehicle_id}")},
            name=registration,
            manufacturer="CarTrack",
        )

    @property
    def native_value(self) -> str | None:
        """Return a short human-readable vehicle status."""
        vehicle = self.coordinator.data["vehicles"].get(self._vehicle_id, {})
        ignition = vehicle.get("ignition")
        if ignition is False:
            return "Parked"
        if ignition is True:
            if vehicle.get("idling"):
                return "Idling"
            if vehicle.get("speed") is not None and vehicle["speed"] > 0:
                return "Driving"
            return "Ignition on"
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Expose the API telemetry without discarding nested vehicle details."""
        vehicle = self.coordinator.data["vehicles"].get(self._vehicle_id, {})
        attributes = {
            key: vehicle.get(key)
            for key in (
                "registration",
                "engine_type",
                "chassis_number",
                "event_ts",
                "ignition",
                "idling",
                "speed",
                "odometer",
                "bearing",
                "fuel",
                "electric",
                "location",
            )
            if vehicle.get(key) is not None
        }
        driver = vehicle.get("driver")
        if isinstance(driver, dict):
            driver_name = " ".join(
                part
                for part in (driver.get("first_name"), driver.get("last_name"))
                if part
            )
            if driver_name:
                attributes["driver_name"] = driver_name
        watch = self.coordinator.data["carwatch"].get(self._vehicle_id)
        if watch is not None:
            attributes["carwatch_active"] = watch.get("is_active")
        return attributes


class CarTrackTelemetrySensor(CoordinatorEntity[CarTrackCoordinator], SensorEntity):
    """Expose numeric telemetry for one vehicle."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CarTrackCoordinator,
        entry: ConfigEntry,
        vehicle_id: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize a telemetry sensor for one vehicle."""
        super().__init__(coordinator)
        vehicle = coordinator.data["vehicles"][vehicle_id]
        registration = vehicle.get("registration") or vehicle_id
        self._vehicle_id = vehicle_id
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{vehicle_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{vehicle_id}")},
            name=registration,
            manufacturer="CarTrack",
        )

    @property
    def native_value(self) -> int | float | None:
        """Return the latest numeric value reported by CarTrack."""
        value = (
            self.coordinator.data["vehicles"]
            .get(self._vehicle_id, {})
            .get(self.entity_description.key)
        )
        return (
            value
            if isinstance(value, (int, float)) and not isinstance(value, bool)
            else None
        )


TELEMETRY_SENSORS = (
    SensorEntityDescription(
        key="speed",
        name="Speed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="odometer",
        name="Odometer",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
)
