"""Support for FCU sensors."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the FCU sensors."""
    climate_entity = hass.data[DOMAIN][config_entry.data["name"]]

    sensors = [
        FCUSensor(
            climate_entity,
            f"{climate_entity.name} Room Temperature",
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
            SensorStateClass.MEASUREMENT,
            "room_temperature",
        ),
        FCUSensor(
            climate_entity,
            f"{climate_entity.name} Water Temperature",
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
            SensorStateClass.MEASUREMENT,
            "water_temperature",
        ),
        FCUSensor(
            climate_entity,
            f"{climate_entity.name} Device Status",
            None,
            None,
            None,
            "device_status",
        ),
        FCUSensor(
            climate_entity,
            f"{climate_entity.name} Error Index",
            None,
            None,
            None,
            "error_index",
        ),
    ]
    async_add_entities(sensors, True)

class FCUSensor(SensorEntity):
    """Representation of an FCU sensor."""
    def __init__(self, climate_entity, name, unit, device_class, state_class, attribute):
        """Initialize the sensor."""
        self._climate_entity = climate_entity
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attribute = attribute
        self._attr_unique_id = f"{climate_entity.unique_id}_{attribute}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._climate_entity.extra_state_attributes.get(self._attribute)

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
