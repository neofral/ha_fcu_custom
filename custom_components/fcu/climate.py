from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_FAN_ONLY, HVAC_MODE_OFF, SUPPORT_FAN_MODE)
from homeassistant.const import TEMP_CELSIUS

SUPPORT_FLAGS = SUPPORT_FAN_MODE

class CustomFCUClimate(ClimateEntity):
    """Representation of a custom FCU climate device."""

    def __init__(self, name, ip_address):
        self._name = name
        self._ip = ip_address
        self._hvac_mode = HVAC_MODE_COOL
        self._fan_mode = "Auto"
        self._temperature = 22
        
    @property
    def name(self):
        return self._name
    
    @property
    def temperature_unit(self):
        return TEMP_CELSIUS
    
    @property
    def hvac_modes(self):
        return [HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_FAN_ONLY, HVAC_MODE_OFF]
    
    @property
    def hvac_mode(self):
        return self._hvac_mode
    
    @property
    def fan_mode(self):
        return self._fan_mode
    
    @property
    def supported_features(self):
        return SUPPORT_FLAGS