"""FCU Climate Entity."""
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
    ClimateEntityFeature,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

class FCUClimateEntity(ClimateEntity):
    """Representation of an FCU climate entity."""

    def __init__(self, name, ip_address):
        self._name = name
        self._ip_address = ip_address
        self._current_temperature = None
        self._target_temperature = None
        self._fan_mode = FAN_AUTO
        self._hvac_mode = HVACMode.OFF
        self._attr_should_poll = False

    async def async_added_to_hass(self):
        """Run when entity is added to hass."""
        _LOGGER.info("FCUClimateEntity added to Home Assistant: %s", self._name)
        # Initialize or fetch data here
        await self.async_update_ha_state()

    @property
    def name(self):
        return self._name

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

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
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

    @property
    def fan_modes(self):
        return [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]

    @property
    def hvac_modes(self):
        return [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY]

    def update(self):
        """Fetch the latest data from the device."""
        # Replace with actual REST API logic using self._ip_address
        pass

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up FCU climate platform from a config entry."""
    data = hass.data["fcu"][entry.entry_id]
    name = data["name"]
    ip_address = data["ip_address"]

    # Create and add the climate entity
    async_add_entities([FCUClimateEntity(name, ip_address)])