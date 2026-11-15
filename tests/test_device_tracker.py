"""Tests for CarTrack vehicle location trackers."""

from types import SimpleNamespace

from custom_components.cartrack.device_tracker import CarTrackVehicleTracker

ALTITUDE_METERS = 1568
VEHICLE_ID = "304913924"


def test_tracker_exposes_altitude_attribute() -> None:
    """The tracker exposes the vehicle altitude in meters when available."""
    tracker = object.__new__(CarTrackVehicleTracker)
    vars(tracker).update(
        {
            "_vehicle_id": VEHICLE_ID,
            "coordinator": SimpleNamespace(
                data={"vehicles": {VEHICLE_ID: {"altitude": ALTITUDE_METERS}}}
            ),
        }
    )

    assert tracker.extra_state_attributes == {"altitude": ALTITUDE_METERS}


def test_tracker_omits_missing_altitude_attribute() -> None:
    """The tracker omits altitude when CarTrack has no value."""
    tracker = object.__new__(CarTrackVehicleTracker)
    vars(tracker).update(
        {
            "_vehicle_id": VEHICLE_ID,
            "coordinator": SimpleNamespace(data={"vehicles": {VEHICLE_ID: {}}}),
        }
    )

    assert tracker.extra_state_attributes == {}
