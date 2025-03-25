"""FCU Climate Entity."""
import logging
import aiohttp
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
        await self.async_write_ha_state()

    @property
    def name(self):
        return self._name
elf):
    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS
e(self):
    @property
    def current_temperature(self):
        return self._current_temperature
(self):
    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def fan_mode(self):
        return self._fan_mode

    @property
    def hvac_mode(self):
        return self._hvac_mode
(self):
    @propertyE | ClimateEntityFeature.FAN_MODE
    def supported_features(self):
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

    @property, FAN_HIGH, FAN_AUTO]
    def fan_modes(self):
        return [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]

    @propertye.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY]
    def hvac_modes(self):
        return [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY]

    @propertyhis entity."""
    def unique_id(self):
        """Return a unique ID for this entity."""
        return self._unique_idode(self, hvac_mode):

    async def async_set_hvac_mode(self, hvac_mode):s", hvac_mode, self._name)
        """Set the HVAC mode."""
        _LOGGER.info("Setting HVAC mode to %s for %s", hvac_mode, self._name)de={hvac_mode}&required_speed={self._fan_mode}"
        try:
            payload = f"&required_temp={self._target_temperature}&required_mode={hvac_mode}&required_speed={self._fan_mode}"
            response = requests.post(
                f"http://{self._ip_address}/wifi/setmode",
                headers={,
                    "Authorization": f"Bearer {self._token}",
                    "X-Requested-With": "myApp",
                    "Content-Type": "application/x-www-form-urlencoded",
                },ent-Type": "application/x-www-form-urlencoded",
                data=payload,s()
            )
            response.raise_for_status()
            self._hvac_mode = hvac_mode()
            await self.async_write_ha_state()s", e)
        except Exception as e:
            _LOGGER.error("Failed to set HVAC mode: %s", e)
            raiseER.error("Failed to set HVAC mode: %s", e)nc_set_temperature(self, **kwargs):

    async def async_set_temperature(self, **kwargs):
        """Set the target temperature."""rgs):
        temperature = kwargs.get("temperature") set_temperature")
        if temperature is None:
            _LOGGER.error("No temperature provided to set_temperature")
            return
        _LOGGER.info("Setting target temperature to %s for %s", temperature, self._name)
        try:
            payload = f"&required_temp={temperature}&required_mode={self._hvac_mode}&required_speed={self._fan_mode}"
            response = requests.post(red_mode={self._hvac_mode}&required_speed={self._fan_mode}"
                f"http://{self._ip_address}/wifi/setmode",}",
                headers={
                    "Authorization": f"Bearer {self._token}",,rlencoded",
                    "X-Requested-With": "myApp",
                    "Content-Type": "application/x-www-form-urlencoded",
                },quested-With": "myApp",
                data=payload,ent-Type": "application/x-www-form-urlencoded",r_status()
            )
            response.raise_for_status()
            self._target_temperature = temperature
            await self.async_write_ha_state())rature: %s", e)
        except Exception as e:
            _LOGGER.error("Failed to set temperature: %s", e)
            raiseception as e:nc_set_fan_mode(self, fan_mode):
ure: %s", e)
    async def async_set_fan_mode(self, fan_mode):
        """Set the fan mode."""
        _LOGGER.info("Setting fan mode to %s for %s", fan_mode, self._name)uired_speed={fan_mode}"
        try:
            payload = f"&required_temp={self._target_temperature}&required_mode={self._hvac_mode}&required_speed={fan_mode}"
            response = requests.post(
                f"http://{self._ip_address}/wifi/setmode",rature}&required_mode={self._hvac_mode}&required_speed={fan_mode}"}",
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "X-Requested-With": "myApp",
                    "Content-Type": "application/x-www-form-urlencoded",
                },orization": f"Bearer {self._token}",
                data=payload,quested-With": "myApp",r_status()
            ) "application/x-www-form-urlencoded",
            response.raise_for_status()
            self._fan_mode = fan_mode
            await self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Failed to set fan mode: %s", e)
            raise self.async_write_ha_state()lf):
ion as e:latest data from the device."""
    def update(self):s", e)ame)
        """Fetch the latest data from the device."""
        _LOGGER.info("Updating data for %s", self._name)
        try:
            # Update the token before making the request
            self._update_token()ata for %s", self._name)get(
            # Fetch the latest status from the device
            response = requests.get(estelf._token}"},  # Use the token
                f"http://{self._ip_address}/status",
                headers={"Authorization": f"Bearer {self._token}"},  # Use the token
            )
            response.raise_for_status() data["current_temperature"]
            data = response.json()address}/status",data["target_temperature"]
            self._current_temperature = data["current_temperature"]}"},  # Use the token
            self._target_temperature = data["target_temperature"]
            self._fan_mode = data["fan_mode"]
            self._hvac_mode = data["hvac_mode"])
            self._available = Trueurrent_temperature"]a: %s", e)
        except Exception as e:re = data["target_temperature"]e
            _LOGGER.error("Failed to update data: %s", e)
            self._available = False
 token."""
    def _update_token(self):e:
        """Update the authentication token."""ta: %s", e)s", self._name)
        try:
            _LOGGER.info("Updating token for %s", self._name)
            # Send a POST request to fetch the token
            response = requests.post(
                f"http://{self._ip_address}/login.htm",
                headers={_name)form-urlencoded",
                    "X-Requested-With": "myApp",s session:
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data="username=admin&password=d033e22ae348aeb5660fc2140aec35850c4da997",
            )
            response.raise_for_status() "application/x-www-form-urlencoded",.strip()  # Assuming the token is returned as plain text
            # Extract the token from the response (adjust this based on the actual response format)
            self._token = response.text.strip()  # Assuming the token is returned as plain text
            if not self._token:
                raise ValueError("Failed to retrieve access token")
        except Exception as e:
            _LOGGER.error("Failed to update token: %s", e)
            self._available = Falseve access token")
try, async_add_entities: AddEntitiesCallback
async def async_setup_entry(ailed to update token: %s", e)
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up FCU climate platform from a config entry."""
    data = hass.data["fcu"][entry.entry_id]ities: AddEntitiesCallback
    name = data["name"]
    ip_address = data["ip_address"]from a config entry."""tity
    _LOGGER.info("Creating FCUClimateEntity for name: %s, IP: %s", name, ip_address)ntry_id]ntity(name, ip_address)])    name = data["name"]    ip_address = data["ip_address"]    _LOGGER.info("Creating FCUClimateEntity for name: %s, IP: %s", name, ip_address)    # Create and add the climate entity    async_add_entities([FCUClimateEntity(name, ip_address)])    # Create and add the climate entity    async_add_entities([FCUClimateEntity(name, ip_address)])