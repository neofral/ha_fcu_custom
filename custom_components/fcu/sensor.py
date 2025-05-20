"""Support for FCU sensors."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the FCU sensors."""
    coordinator = hass.data[DOMAIN][config_entry.data["name"]]

    sensors = [
        FCUSensor(coordinator, "Room Temperature", "rt", UnitOfTemperature.CELSIUS),
        FCUSensor(coordinator, "Water Temperature", "wt", UnitOfTemperature.CELSIUS),
        FCUSensor(coordinator, "Device Status", "device_status", None),
        FCUSensor(coordinator, "Error Index", "error_index", None),
    ]
    async_add_entities(sensors, True)

class FCUSensor(CoordinatorEntity, SensorEntity):
    """Representation of an FCU sensor."""

    def __init__(self, coordinator, name, key, unit):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = name
        self._key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{coordinator.name}_{key}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key)

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._climate_entity.unique_id)},
            "name": self._climate_entity.name,
            "manufacturer": "Eko Energis + Cotronika",
            "model": "FCU Controller v.0.0.3RD",
        }

    @property
    def available(self):
        """Return True if the sensor is available."""
        return self._climate_entity.available
