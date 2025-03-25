from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import TEMP_CELSIUS
import aiohttp
import logging
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the fan coil unit climate entity."""
    name = config_entry.data["name"]
    ip_address = config_entry.data["ip_address"]

    # Add the climate entity with unique initialization
    async_add_entities([FCUClimate(name, ip_address)], True)

class FCUClimate(ClimateEntity):
    """Representation of a fan coil unit as a climate entity."""

    def __init__(self, name, ip_address):
        self._name = name
        self._ip_address = ip_address
        self._temperature = None
        self._hvac_mode = HVACMode.OFF
        self._fan_mode = "auto"
        self._fan_modes = ["low", "medium", "high", "auto"]  # Define supported fan modes
        self._token = None
        self._attributes = {}

    async def async_update(self):
        """Fetch new state data for the entity."""
        await self._fetch_token()
        await self._fetch_device_state()

    async def _fetch_token(self):
        """Fetch a new token from the device."""
        login_url = f"http://{self._ip_address}/login.htm"
        payload = {"username": "admin", "password": "hashed_password"}  # Replace with actual credentials
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(login_url, data=payload, headers=headers) as response:
                    if response.status == 200:
                        self._token = await response.text()  # Assuming token is returned as plain text
                        _LOGGER.debug(f"Token fetched for {self._name}: {self._token}")
                    else:
                        _LOGGER.error(f"Failed to fetch token for {self._name}: {response.status}")
            except Exception as e:
                _LOGGER.error(f"Error fetching token for {self._name}: {e}")

    async def _fetch_device_state(self):
        """Fetch the current state of the device."""
        if not self._token:
            _LOGGER.error(f"No valid token available for {self._name}")
            return

        status_url = f"http://{self._ip_address}/wifi/status"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "X-Requested-With": "myApp",
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(status_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._parse_device_state(data)
                        _LOGGER.debug(f"State fetched for {self._name}: {data}")
                    else:
                        _LOGGER.error(f"Failed to fetch state for {self._name}: {response.status}")
            except Exception as e:
                _LOGGER.error(f"Error fetching state for {self._name}: {e}")

    def _parse_device_state(self, data):
        """Parse the state data from the device."""
        self._temperature = data.get("rt", None)  # Room temperature
        operation_mode = data.get("operation_mode", "0")
        self._hvac_mode = self._map_operation_mode(operation_mode)
        self._fan_mode = self._map_fan_speed(data.get("fan_state_current_cooling", "0"))
        self._attributes = data  # Store all attributes for additional sensors/entities

    def _map_operation_mode(self, mode):
        """Map device operation mode to HVACMode."""
        return {
            "0": HVACMode.OFF,
            "1": HVACMode.HEAT,
            "2": HVACMode.COOL,
            "3": HVACMode.FAN_ONLY,
        }.get(mode, HVACMode.OFF)

    def _map_fan_speed(self, speed):
        """Map device fan speed to readable strings."""
        return {
            "0": "low",
            "1": "medium",
            "2": "high",
            "3": "auto",
        }.get(speed, "auto")

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for the climate entity."""
        return f"{self._name.lower().replace(' ', '_')}_climate"

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def target_temperature(self):
        """Return the target temperature."""
        return self._temperature

    @property
    def hvac_mode(self):
        """Return the current HVAC mode."""
        return self._hvac_mode

    @property
    def fan_mode(self):
        """Return the fan mode."""
        return self._fan_mode

    @property
    def fan_modes(self):
        """Return the list of supported fan modes."""
        return self._fan_modes

    @property
    def supported_features(self):
        """Return the features supported by this climate entity."""
        return SUPPORT_TARGET_TEMPERATURE

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return self._attributes