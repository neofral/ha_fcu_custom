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
    climate = hass.data[DOMAIN][name]

    sensors = [
        FCUTemperatureSensor(
            name,
            climate,
            "Room Temperature",
            "_temperature",
            is_status=False
        ),
        FCUTemperatureSensor(
            name,
            climate,
            "Water Temperature",
            "_water_temp",
            is_status=False
        ),
        FCUTemperatureSensor(
            name,
            climate,
            "Device Status",
            "_device_status",
            is_status=True
        ),
        FCUTemperatureSensor(
            name,
            climate,
            "Error Index",
            "_error_index",
            is_status=True
        ),
    ]

    async_add_entities(sensors, True)

class FCUTemperatureSensor(SensorEntity):
    """Representation of an FCU Sensor."""

    def __init__(self, device_name, climate_entity, description, attr_name, is_status=False):
        """Initialize the sensor."""
        self._device_name = device_name
        self._attr_unique_id = f"{device_name}_{description.lower().replace(' ', '_')}"
        self._attr_name = f"{device_name} {description}"
        self._climate = climate_entity
        self._attr = attr_name
        self._is_status = is_status
        
        # Only set temperature attributes for temperature sensors
        if not is_status:
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif attr_name == "_error_index":
            # Set error index as a diagnostic sensor
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the sensor value."""
        if not self._climate:
            return None
            
        value = getattr(self._climate, self._attr, None)
        
        if self._attr == "_device_status" and value is not None:
            hvac_mode = self._climate.hvac_mode
            if value == 0:
                if hvac_mode == HVACMode.HEAT:
                    return "Heating"
                elif hvac_mode == HVACMode.COOL:
                    return "Cooling"
                else:
                    return "Working"
            else:
                return "Check Water Temperature"
        
        # Return raw value for error index
        if self._attr == "_error_index":
            return int(value) if value is not None else None
            
        return value

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._device_name)},
            "name": self._device_name,
            "manufacturer": "Eko Energis + Cotronika",
            "model": "FCU Controller v.0.0.3RD",
        }
