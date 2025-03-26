"""Support for FCU temperature sensors."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the FCU temperature sensors."""
    name = config_entry.data["name"]
    climate = hass.data[DOMAIN][name]  # Get climate entity by name

    sensors = [
        FCUTemperatureSensor(
            name,
            climate,
            "Room Temperature",
            "_temperature"
        ),
        FCUTemperatureSensor(
            name,
            climate,
            "Water Temperature",
            "_water_temp"
        ),
    ]

    async_add_entities(sensors, True)

class FCUTemperatureSensor(SensorEntity):
    """Representation of an FCU Temperature Sensor."""

    def __init__(self, device_name, climate_entity, description, attr_name):
        """Initialize the sensor."""
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._device_name = device_name
        self._attr_unique_id = f"{device_name}_{description.lower().replace(' ', '_')}"
        self._attr_name = f"{device_name} {description}"
        self._climate = climate_entity
        self._attr = attr_name

    @property
    def native_value(self):
        """Return the temperature value."""
        if self._climate:
            return getattr(self._climate, self._attr, None)
        return None

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._device_name)},
            "name": self._device_name,
            "manufacturer": "Eko Energis + Cotronika",
            "model": "FCU Controller v.0.0.3RD",
        }
