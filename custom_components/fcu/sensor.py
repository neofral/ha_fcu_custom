"""Support for FCU temperature sensors."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.components.climate import HVACMode  # Add this import
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the FCU temperature sensors."""
    climate_entity = hass.data[DOMAIN][config_entry.data["name"]]
    
    sensors = [
        # Regular temperature sensors
        FCUTemperatureSensor(
            f"{climate_entity.name} Water Temperature",
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
            SensorStateClass.MEASUREMENT,
            lambda: climate_entity._water_temp,
            climate_entity
        ),
        # Error index sensor without state class
        FCUTemperatureSensor(
            f"{climate_entity.name} Error Index",
            None,
            SensorDeviceClass.ENUM,
            None,  # No state class for enum
            lambda: climate_entity._error_index,
            climate_entity
        ),
    ]

    async_add_entities(sensors, True)

class FCUTemperatureSensor(SensorEntity):
    """Representation of an FCU Sensor."""

    def __init__(self, name, unit, device_class, state_class, measurement_fn, climate_entity):
        """Initialize the sensor."""
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        # Only set state_class if not an enum device class
        if device_class != SensorDeviceClass.ENUM:
            self._attr_state_class = state_class
        self._get_measurement = measurement_fn
        self._climate_entity = climate_entity

    @property
    def native_value(self):
        """Return the sensor value."""
        if not self._climate_entity:
            return None
            
        value = self._get_measurement()
        
        if self._attr == "_device_status" and value is not None:
            hvac_mode = self._climate_entity.hvac_mode
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
