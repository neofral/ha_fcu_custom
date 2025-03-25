"""Support for FCU sensors."""
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from .const import DOMAIN, ROOM_TEMP_SENSOR, WATER_TEMP_SENSOR

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the FCU sensors."""
    name = config_entry.data["name"]
    ip_address = config_entry.data["ip_address"]

    sensors = [
        FCUTemperatureSensor(name, ip_address, "Room", ROOM_TEMP_SENSOR),
        FCUTemperatureSensor(name, ip_address, "Water", WATER_TEMP_SENSOR),
    ]
    async_add_entities(sensors, True)

class FCUTemperatureSensor(SensorEntity):
    """Representation of an FCU Temperature Sensor."""

    def __init__(self, name, ip_address, sensor_type, entity_id):
        """Initialize the sensor."""
        self._name = f"{name} {sensor_type} Temperature"
        self._ip_address = ip_address
        self._sensor_type = sensor_type
        self._state = None
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_unique_id = f"{name.lower()}_{entity_id}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    async def async_update(self):
        """Get the latest data from the sensor."""
        climate_entity = next(
            (
                entity
                for entity in self.hass.data[DOMAIN].values()
                if isinstance(entity, dict) and "climate" in entity
            ),
            None,
        )
        
        if climate_entity and "climate" in climate_entity:
            climate = climate_entity["climate"]
            if self._sensor_type == "Room":
                self._state = climate._temperature
            elif self._sensor_type == "Water":
                self._state = climate._water_temp
