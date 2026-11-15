"""Config flow for CarTrack accounts."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CarTrackApi, CarTrackAuthError, CarTrackConnectionError
from .const import (
    API_REGION_DOMAINS,
    API_REGIONS,
    CONF_API_KEY,
    CONF_API_REGION,
    CONF_API_URL,
    CONF_USERNAME,
    DEFAULT_API_REGION,
    DOMAIN,
)


def _api_url_for_region(region: str) -> str:
    """Return the documented Fleet API URL for a country code."""
    domain = API_REGION_DOMAINS.get(region, "cartrack.com")
    return f"https://fleetapi-{region}.{domain}/rest"


class CarTrackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up an independent CarTrack account."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Collect credentials and verify them against CarTrack."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            api_url = _api_url_for_region(user_input[CONF_API_REGION])
            api = CarTrackApi(
                async_get_clientsession(self.hass),
                api_url,
                username,
                user_input[CONF_API_KEY],
            )
            try:
                await api.async_get_vehicles()
            except CarTrackAuthError:
                errors["base"] = "invalid_auth"
            except CarTrackConnectionError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{api_url}|{username.casefold()}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=username,
                    data={
                        CONF_USERNAME: username,
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_API_URL: api_url,
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_API_REGION, default=DEFAULT_API_REGION): (
                    selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=region, label=name)
                                for region, name in API_REGIONS
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
