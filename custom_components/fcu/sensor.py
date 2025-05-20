"""Support for FCU sensors."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import UnitOfTemperature, CONF_NAME
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up FCU sensors based on config_entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    device_info = {
        "identifiers": {(DOMAIN, entry.entry_id)},  # Match climate entity identifier
        "name": data["name"],
        "manufacturer": "Eko Energis + Cotronika",
        "model": "FCU Controller v.0.0.3RD",
    }
    
    entities = [
        FCUSensor(
            coordinator,
            device_info,
            entry.entry_id,
            "Room Temperature",
            "rt",
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
            round_to=1
        ),
        FCUSensor(
            coordinator,
            device_info,
            entry.entry_id,
            "Water Temperature",
            "wt",
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
            round_to=1
        ),
        FCUSensor(
            coordinator,
            device_info,
            entry.entry_id,
            "Error Index",
            "error_index",
            None,
            SensorDeviceClass.ENUM,
            states={
                "0": "OK",
                "1": "Error",
                "2": "Water Temp Low Heating",
                "4": "Water Temp High Cooling"
            }
        ),
    ]
    
    async_add_entities(entities)

class FCUSensor(CoordinatorEntity, SensorEntity):
    """FCU Sensor."""
    
    def __init__(self, coordinator, device_info, entry_id, name, key, unit, device_class, states=None, round_to=None):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_device_info = device_info
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_name = name
        self._attr_has_entity_name = True
        self._key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._states = states
        self._attr_should_poll = False  # Let coordinator handle updates
        self._round_to = round_to

    @property
    def native_value(self):
        """Return sensor value."""
        if not self.coordinator.data:
            return None
        value = self.coordinator.data.get(self._key)
        if value is None:
            return None
        if self._states and str(value) in self._states:
            return self._states[str(value)]
        if self._round_to is not None:
            try:
                return round(float(value), self._round_to)
            except (ValueError, TypeError):
                return value
        return value
