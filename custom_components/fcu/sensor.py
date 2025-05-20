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
    climate_entity = hass.data[DOMAIN][config_entry.data["name"]]
    
    sensors = [
        FCUTemperatureSensor(
            f"{climate_entity.name} Room Temperature",
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
            SensorStateClass.MEASUREMENT,
            lambda: climate_entity._temperature,
            climate_entity,
        ),
        FCUTemperatureSensor(
            f"{climate_entity.name} Water Temperature",
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
            SensorStateClass.MEASUREMENT,
            lambda: climate_entity._water_temp,
            climate_entity,
        ),
        FCUTemperatureSensor(
            f"{climate_entity.name} Device Status",
            None,
            SensorDeviceClass.ENUM,
            None,
            lambda: climate_entity._device_status,
            climate_entity,
        ),
        FCUTemperatureSensor(
            f"{climate_entity.name} Error Index",
            None,
            SensorDeviceClass.ENUM,
            None,
            lambda: climate_entity._error_index,
            climate_entity,
        ),
    ]
    async_add_entities(sensors, True)

class FCUTemperatureSensor(SensorEntity):
    """Representation of a Temperature Sensor."""
    def __init__(self, name, unit, device_class, state_class, measurement_fn, climate_entity):
        """Initialize the sensor."""
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._get_measurement = measurement_fn
        self._climate_entity = climate_entity

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._climate_entity._name)},
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._get_measurement()
