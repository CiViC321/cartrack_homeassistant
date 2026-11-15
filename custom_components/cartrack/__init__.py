"""CarTrack Home Assistant integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CarTrackApi
from .const import (
    CONF_API_KEY,
    CONF_API_URL,
    CONF_USERNAME,
)
from .coordinator import CarTrackCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

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
    coordinator = CarTrackCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a CarTrack account."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
