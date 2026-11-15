"""Tests for CarTrack vehicle telemetry sensors."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfElectricPotential, UnitOfTime

from custom_components.cartrack.sensor import (
    TELEMETRY_SENSORS,
    _coerce_numeric_value,
)

EXPECTED_BATTERY_VOLTAGE = 12.08


def test_battery_voltage_sensor_uses_cartrack_vext() -> None:
    """The external battery voltage is exposed as a voltage measurement."""
    battery_voltage = next(
        description for description in TELEMETRY_SENSORS if description.key == "vext"
    )

    assert battery_voltage.name == "Battery voltage"
    assert battery_voltage.device_class == SensorDeviceClass.VOLTAGE
    assert battery_voltage.native_unit_of_measurement == UnitOfElectricPotential.VOLT
    assert battery_voltage.state_class == SensorStateClass.MEASUREMENT


def test_tcu_battery_sensor_uses_percentage() -> None:
    """The TCU battery telemetry is exposed as a percentage measurement."""
    tcu_battery = next(
        description
        for description in TELEMETRY_SENSORS
        if description.key == "tcu_percentage"
    )

    assert tcu_battery.device_class == SensorDeviceClass.BATTERY
    assert tcu_battery.native_unit_of_measurement == PERCENTAGE
    assert tcu_battery.state_class == SensorStateClass.MEASUREMENT


def test_rpm_sensor_uses_revolutions_per_minute() -> None:
    """The engine RPM telemetry is exposed in rpm."""
    rpm = next(
        description for description in TELEMETRY_SENSORS if description.key == "rpm"
    )

    assert rpm.name == "Engine RPM"
    assert rpm.native_unit_of_measurement == "rpm"
    assert rpm.state_class == SensorStateClass.MEASUREMENT


def test_clock_sensor_uses_cumulative_minutes() -> None:
    """The engine clock is exposed as cumulative engine-on time in minutes."""
    clock = next(
        description for description in TELEMETRY_SENSORS if description.key == "clock"
    )

    assert clock.name == "Engine runtime"
    assert clock.device_class == SensorDeviceClass.DURATION
    assert clock.native_unit_of_measurement == UnitOfTime.MINUTES
    assert clock.state_class == SensorStateClass.TOTAL_INCREASING


def test_telemetry_value_parses_numeric_string() -> None:
    """CarTrack may serialize numeric telemetry such as vext as a string."""
    assert _coerce_numeric_value("12.080") == EXPECTED_BATTERY_VOLTAGE


def test_telemetry_value_ignores_invalid_numeric_string() -> None:
    """Malformed telemetry should remain unavailable rather than raise."""
    assert _coerce_numeric_value("not-a-number") is None
