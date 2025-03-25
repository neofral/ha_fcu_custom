"""FCU Climate Entity."""
import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (Entity
    HVACMode,stant.components.climate.const import (
    FAN_LOW,,
    FAN_MEDIUM,
    FAN_HIGH,M,
    FAN_AUTO,
    ClimateEntityFeature,
)   ClimateEntityFeature,
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntrydEntitiesCallback
from homeassistant.core import HomeAssistantfigEntry
from homeassistant.core import HomeAssistant
_LOGGER = logging.getLogger(__name__)
_LOGGER = logging.getLogger(__name__)
class FCUClimateEntity(ClimateEntity):
    """Representation of an FCU climate entity."""
    """Representation of an FCU climate entity."""
    def __init__(self, name, ip_address):
        self._name = nameme, ip_address):
        self._ip_address = ip_address
        self._current_temperature = None
        self._target_temperature = Nonee
        self._fan_mode = FAN_AUTO= None
        self._hvac_mode = HVACMode.OFF
        self._attr_should_poll = False
        self._unique_id = f"{ip_address}_climate"
        self._available = True  # Assume the device is available initially
        self._available = True  # Assume the device is available initially
    @property
    def available(self):
        """Return True if the device is available."""
        return self._availabledevice is available."""
        return self._available
    async def async_added_to_hass(self):
        """Run when entity is added to hass."""
        _LOGGER.info("FCUClimateEntity added to Home Assistant: %s", self._name)
        # Initialize or fetch data hereadded to Home Assistant: %s", self._name)
        await self.async_write_ha_state()
        await self.async_update_ha_state()
    @property
    def name(self):
        return self._name
        return self._name
    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS
        return UnitOfTemperature.CELSIUS
    @property
    def current_temperature(self):
        return self._current_temperature
        return self._current_temperature
    @property
    def target_temperature(self):
        return self._target_temperature
        return self._target_temperature
    @property
    def fan_mode(self):
        return self._fan_mode
        return self._fan_mode
    @property
    def hvac_mode(self):
        return self._hvac_mode
        return self._hvac_mode
    @property
    def supported_features(self):
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
    @property
    def fan_modes(self):
        return [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]
        return [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]
    @property
    def hvac_modes(self):
        return [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY]
        return [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY]
    @property
    def unique_id(self):
        """Return a unique ID for this entity."""
        return self._unique_idfor this entity."""
        return self._unique_id
    async def async_set_hvac_mode(self, hvac_mode):
        """Set the HVAC mode."""e(self, hvac_mode):
        _LOGGER.info("Setting HVAC mode to %s for %s", hvac_mode, self._name)
        try:GER.info("Setting HVAC mode to %s for %s", hvac_mode, self._name)
            payload = f"&required_temp={self._target_temperature}&required_mode={hvac_mode}&required_speed={self._fan_mode}"
            response = requests.post(p={self._target_temperature}&required_mode={hvac_mode}&required_speed={self._fan_mode}"
                f"http://{self._ip_address}/wifi/setmode",
                headers={{self._ip_address}/wifi/setmode",
                    "Authorization": f"Bearer {self._token}",
                    "X-Requested-With": "myApp",elf._token}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },  "Content-Type": "application/x-www-form-urlencoded",
                data=payload,
            )   data=payload,
            response.raise_for_status()
            self._hvac_mode = hvac_mode
            await self.async_write_ha_state()
        except Exception as e:pdate_ha_state()
            _LOGGER.error("Failed to set HVAC mode: %s", e)
            raiseER.error("Failed to set HVAC mode: %s", e)
            raise
    async def async_set_temperature(self, **kwargs):
        """Set the target temperature.""" **kwargs):
        temperature = kwargs.get("temperature")
        if temperature is None:t("temperature")
            _LOGGER.error("No temperature provided to set_temperature")
            returnR.error("No temperature provided to set_temperature")
        _LOGGER.info("Setting target temperature to %s for %s", temperature, self._name)
        try:GER.info("Setting target temperature to %s for %s", temperature, self._name)
            payload = f"&required_temp={temperature}&required_mode={self._hvac_mode}&required_speed={self._fan_mode}"
            response = requests.post(p={temperature}&required_mode={self._hvac_mode}&required_speed={self._fan_mode}"
                f"http://{self._ip_address}/wifi/setmode",
                headers={{self._ip_address}/wifi/setmode",
                    "Authorization": f"Bearer {self._token}",
                    "X-Requested-With": "myApp",elf._token}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },  "Content-Type": "application/x-www-form-urlencoded",
                data=payload,
            )   data=payload,
            response.raise_for_status()
            self._target_temperature = temperature
            await self.async_write_ha_state()ture
        except Exception as e:pdate_ha_state()
            _LOGGER.error("Failed to set temperature: %s", e)
            raiseER.error("Failed to set temperature: %s", e)
            raise
    async def async_set_fan_mode(self, fan_mode):
        """Set the fan mode."""e(self, fan_mode):
        _LOGGER.info("Setting fan mode to %s for %s", fan_mode, self._name)
        try:GER.info("Setting fan mode to %s for %s", fan_mode, self._name)
            payload = f"&required_temp={self._target_temperature}&required_mode={self._hvac_mode}&required_speed={fan_mode}"
            response = requests.post(p={self._target_temperature}&required_mode={self._hvac_mode}&required_speed={fan_mode}"
                f"http://{self._ip_address}/wifi/setmode",
                headers={{self._ip_address}/wifi/setmode",
                    "Authorization": f"Bearer {self._token}",
                    "X-Requested-With": "myApp",elf._token}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },  "Content-Type": "application/x-www-form-urlencoded",
                data=payload,
            )   data=payload,
            response.raise_for_status()
            self._fan_mode = fan_mode()
            await self.async_write_ha_state()
        except Exception as e:pdate_ha_state()
            _LOGGER.error("Failed to set fan mode: %s", e)
            raiseER.error("Failed to set fan mode: %s", e)
            raise
    def update(self):
        """Fetch the latest data from the device."""
        _LOGGER.info("Updating data for %s", self._name)
        try:GER.info("Updating data for %s", self._name)
            # Update the token before making the request
            self._update_token()efore making the request
            self._update_token()
            # Fetch the latest status from the device
            response = requests.get(s from the device
                f"http://{self._ip_address}/status",
                headers={"Authorization": f"Bearer {self._token}"},  # Use the token
            )   headers={"Authorization": f"Bearer {self._token}"},  # Use the token
            response.raise_for_status()
            data = response.json()tus()
            self._current_temperature = data["current_temperature"]
            self._target_temperature = data["target_temperature"]"]
            self._fan_mode = data["fan_mode"]target_temperature"]
            self._hvac_mode = data["hvac_mode"]
            self._available = True["hvac_mode"]
        except Exception as e:True
            _LOGGER.error("Failed to update data: %s", e)
            self._available = Falseo update data: %s", e)
            self._available = False
    def _update_token(self):
        """Update the authentication token."""
        try:pdate the authentication token."""
            _LOGGER.info("Updating token for %s", self._name)
            # Send a POST request to fetch the tokenlf._name)
            response = requests.post(fetch the token
                f"http://{self._ip_address}/login.htm",
                headers={{self._ip_address}/login.htm",
                    "X-Requested-With": "myApp",
                    "Content-Type": "application/x-www-form-urlencoded",
                },  "Content-Type": "application/x-www-form-urlencoded",
                data="username=admin&password=d033e22ae348aeb5660fc2140aec35850c4da997",
            )   data="username=admin&password=d033e22ae348aeb5660fc2140aec35850c4da997",
            response.raise_for_status()
            # Extract the token from the response (adjust this based on the actual response format)
            self._token = response.text.strip()  # Assuming the token is returned as plain textmat)
            if not self._token:nse.text.strip()  # Assuming the token is returned as plain text
                raise ValueError("Failed to retrieve access token")
        except Exception as e:or("Failed to retrieve access token")
            _LOGGER.error("Failed to update token: %s", e)
            self._available = Falseo update token: %s", e)
            self._available = False
async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):  hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
    """Set up FCU climate platform from a config entry."""
    data = hass.data["fcu"][entry.entry_id]onfig entry."""
    name = data["name"]cu"][entry.entry_id]
    ip_address = data["ip_address"]
    ip_address = data["ip_address"]
    _LOGGER.info("Creating FCUClimateEntity for name: %s, IP: %s", name, ip_address)
    _LOGGER.info("Creating FCUClimateEntity for name: %s, IP: %s", name, ip_address)
    # Create and add the climate entity
    async_add_entities([FCUClimateEntity(name, ip_address)])
    async_add_entities([FCUClimateEntity(name, ip_address)])