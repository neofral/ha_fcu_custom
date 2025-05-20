"""Support for FCU sensors."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the FCU temperature sensors."""
    coordinator = hass.data[DOMAIN][config_entry.data["name"]]

    sensors = [
        FCUTemperatureSensor(
            coordinator,
            f"{config_entry.data['name']} Room Temperature",
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
            SensorStateClass.MEASUREMENT,
            "rt",  # Key for room temperature
        ),
        FCUTemperatureSensor(
            coordinator,
            f"{config_entry.data['name']} Water Temperature",
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
            SensorStateClass.MEASUREMENT,
            "wt",  # Key for water temperature
        ),
        FCUTemperatureSensor(
            coordinator,
            f"{config_entry.data['name']} Device Status",
            None,
            SensorDeviceClass.ENUM,
            None,
            "device_status",  # Key for device status
        ),
        FCUTemperatureSensor(
            coordinator,
            f"{config_entry.data['name']} Error Index",
            None,
            SensorDeviceClass.ENUM,
            None,
            "error_index",  # Key for error index
        ),
    ]
    async_add_entities(sensors, True)

class FCUTemperatureSensor(SensorEntity):
    """Representation of a Temperature Sensor."""
    def __init__(self, coordinator, name, unit, device_class, state_class, key):
        """Initialize the sensor."""
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.name}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._coordinator = coordinator
        self._key = key

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._coordinator.name)},
            "name": self._coordinator.name,
            "manufacturer": "Eko Energis + Cotronika",
            "model": "FCU Controller v.0.0.3RD",
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._coordinator.data.get(self._key)

    async def async_update(self):
        """Update the sensor."""
        await self._coordinator.async_request_refresh()

    @property
    def available(self):
        """Return True if the sensor is available."""
        return self._coordinator.last_update_success
