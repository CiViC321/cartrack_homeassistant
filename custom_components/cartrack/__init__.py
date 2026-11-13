"""CarTrack Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CarTrackApi
from .const import (
    CONF_API_KEY,
    CONF_API_URL,
    CONF_LEGACY_MOVING_UPDATE_INTERVAL_MINUTES,
    CONF_MOVING_UPDATE_INTERVAL_SECONDS,
    CONF_USERNAME,
    DEFAULT_MOVING_UPDATE_INTERVAL_SECONDS,
)
from .coordinator import CarTrackCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a CarTrack account from a config entry."""
    api = CarTrackApi(
        async_get_clientsession(hass),
        entry.data[CONF_API_URL],
        entry.data[CONF_USERNAME],
        entry.data[CONF_API_KEY],
    )
    coordinator = CarTrackCoordinator(
        hass,
        api,
        moving_update_interval_seconds=entry.options.get(
            CONF_MOVING_UPDATE_INTERVAL_SECONDS,
            entry.options.get(
                CONF_LEGACY_MOVING_UPDATE_INTERVAL_MINUTES,
                DEFAULT_MOVING_UPDATE_INTERVAL_SECONDS,
            ),
        ),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a CarTrack account."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload an account after its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
