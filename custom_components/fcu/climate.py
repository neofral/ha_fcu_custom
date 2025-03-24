"""FCU Climate Entity."""
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_OFF,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_FAN_ONLY,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_FAN_MODE,
)
from homeassistant.const import TEMP_CELSIUS

class FCUClimateEntity(ClimateEntity):
    """Representation of an FCU climate entity."""

    def __init__(self, name, ip_address):
        self._name = name
        self._ip_address = ip_address
        self._current_temperature = None
        self._target_temperature = None
        self._fan_mode = FAN_AUTO
        self._hvac_mode = HVAC_MODE_OFF

    @property
    def name(self):
        return self._name

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def fan_mode(self):
        return self._fan_mode

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE

    @property
    def fan_modes(self):
        return [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]

    @property
    def hvac_modes(self):
        return [HVAC_MODE_OFF, HVAC_MODE_COOL, HVAC_MODE_HEAT, HVAC_MODE_FAN_ONLY]

    def update(self):
        """Fetch the latest data from the device."""
        # Replace with actual REST API logic using self._ip_address
        pass