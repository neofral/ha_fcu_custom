"""FCU Climate Entity."""
import logging
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

_LOGGER = logging.getLogger(__name__)

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
        self._unique_id = f"{ip_address}_climate"
        self._available = True  # Assume the device is available initially

    @property
    def available(self):
        """Return True if the device is available."""
        return self._available

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

    @property
    def unique_id(self):
        """Return a unique ID for this entity."""
        return self._unique_id

    async def async_set_hvac_mode(self, hvac_mode):
        """Set the HVAC mode."""
        _LOGGER.info("Setting HVAC mode to %s for %s", hvac_mode, self._name)
        try:
            # Replace with actual logic to send the HVAC mode to the device
            self._hvac_mode = hvac_mode
            await self.async_update_ha_state()
        except Exception as e:
            _LOGGER.error("Failed to set HVAC mode: %s", e)
            raise

    async def async_set_temperature(self, **kwargs):
        """Set the target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            _LOGGER.error("No temperature provided to set_temperature")
            return
        _LOGGER.info("Setting target temperature to %s for %s", temperature, self._name)
        try:
            # Replace with actual logic to send the temperature to the device
            self._target_temperature = temperature
            await self.async_update_ha_state()
        except Exception as e:
            _LOGGER.error("Failed to set temperature: %s", e)
            raise

    async def async_set_fan_mode(self, fan_mode):
        """Set the fan mode."""
        _LOGGER.info("Setting fan mode to %s for %s", fan_mode, self._name)
        try:
            # Replace with actual logic to send the fan mode to the device
            self._fan_mode = fan_mode
            await self.async_update_ha_state()
        except Exception as e:
            _LOGGER.error("Failed to set fan mode: %s", e)
            raise

    def update(self):
        """Fetch the latest data from the device."""
        _LOGGER.info("Updating data for %s", self._name)
        try:
            response = requests.get(f"http://{self._ip_address}/status")
            response.raise_for_status()
            data = response.json()
            self._current_temperature = data["current_temperature"]
            self._target_temperature = data["target_temperature"]
            self._fan_mode = data["fan_mode"]
            self._hvac_mode = data["hvac_mode"]
            self._available = True
            pass
        except Exception as e:
            _LOGGER.error("Failed to update data: %s", e)
            self._available = False

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up FCU climate platform from a config entry."""
    data = hass.data["fcu"][entry.entry_id]
    name = data["name"]
    ip_address = data["ip_address"]

    _LOGGER.info("Creating FCUClimateEntity for name: %s, IP: %s", name, ip_address)

    # Create and add the climate entity
    async_add_entities([FCUClimateEntity(name, ip_address)])