"""Tests for CarTrack coordinator rate-limit handling."""

from datetime import timedelta

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.cartrack.api import CarTrackRateLimitError
from custom_components.cartrack.coordinator import CarTrackCoordinator


class RateLimitedApi:
    """Return a rate-limit error on the coordinator's first request."""

    async def async_get_vehicles(self) -> dict:
        """Raise the configured rate-limit response."""
        raise CarTrackRateLimitError(15)


@pytest.mark.asyncio
async def test_rate_limit_retry_delay_is_applied_to_coordinator() -> None:
    """The coordinator waits at least as long as CarTrack's retry header."""
    coordinator = object.__new__(CarTrackCoordinator)
    vars(coordinator).update(
        {
            "api": RateLimitedApi(),
            "_rate_limit_backoff_seconds": 1.5,
        }
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()  # noqa: SLF001

    retry_interval = coordinator.update_interval
    assert retry_interval is not None
    assert retry_interval >= timedelta(seconds=15)
