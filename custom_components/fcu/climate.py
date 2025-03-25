from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import (
    UnitOfTemperature,
    ATTR_TEMPERATURE,
)
import aiohttp
import logging
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY]
FAN_MODES = ["low", "medium", "high", "auto"]

TIMEOUT = 10  # seconds
CONTENT_TYPE_JSON = "application/json"
COMMON_HEADERS = {
    "X-Requested-With": "myApp",
}

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
        self._target_temperature = None
        self._hvac_mode = HVACMode.OFF
        self._hvac_action = HVACAction.IDLE
        self._fan_mode = "auto"
        self._fan_modes = FAN_MODES  # Define supported fan modes
        self._token = None
        self._attributes = {}
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_modes = HVAC_MODES
        self._attr_fan_modes = FAN_MODES
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE 
            | ClimateEntityFeature.FAN_MODE
        )

    async def async_update(self):
        """Fetch new state data for the entity."""
        await self._fetch_token()
        await self._fetch_device_state()

    async def _fetch_token(self):
        """Fetch a new token from the device."""
        login_url = f"http://{self._ip_address}/login.htm"
        payload = {"username": "admin", "password": "d033e22ae348aeb5660fc2140aec35850c4da997"}
        headers = {
            "x-requested-with": "myApp",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    login_url,
                    data=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                    allow_redirects=False,
                ) as response:
                    if response.status != 200:
                        raise aiohttp.ClientError(f"Invalid response status: {response.status}")
                    
                    content_type = response.headers.get("content-type", "").lower()
                    if "text/plain" not in content_type:
                        raise aiohttp.ClientError(f"Invalid content type: {content_type}")

                    token = (await response.text()).strip()
                    if not token or '\n' in token or '\r' in token:
                        raise aiohttp.ClientError("Invalid token format")
                    
                    self._token = token
                    _LOGGER.debug("Token fetched successfully for %s", self._name)

        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("Failed to fetch token for %s: %s", self._name, str(err))
            self._token = None

    async def _fetch_device_state(self):
        """Fetch the current state of the device."""
        if not self._token:
            _LOGGER.warning("No valid token available for %s, skipping state fetch", self._name)
            return

        status_url = f"http://{self._ip_address}/wifi/status"
        headers = {
            "X-Requested-With": "myApp",
            "Authorization": f"Bearer {self._token.strip()}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": CONTENT_TYPE_JSON,
            **COMMON_HEADERS
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    status_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                    allow_redirects=False,
                ) as response:
                    if response.status != 200:
                        raise aiohttp.ClientError(f"Invalid response status: {response.status}")
                    
                    content_type = response.headers.get("content-type", "").lower()
                    if CONTENT_TYPE_JSON not in content_type:
                        raise aiohttp.ClientError(f"Invalid content type: {content_type}")

                    data = await response.json()
                    if not isinstance(data, dict):
                        raise aiohttp.ClientError("Invalid response format")

                    self._parse_device_state(data)
                    _LOGGER.debug("State fetched for %s: %s", self._name, data)

        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            _LOGGER.error("Failed to fetch state for %s: %s", self._name, str(err))

    def _parse_device_state(self, data):
        """Parse the state data from the device."""
        try:
            # Parse temperatures
            self._temperature = float(data.get("rt", 0))  # Room temperature
            self._water_temp = float(data.get("wt", 0))  # Water temperature
            self._temp2 = float(data.get("t3", 0))  # Room temperature 2
            
            # Get operation mode and set target temp based on mode
            operation_mode = str(data.get("operation_mode", "0"))
            self._hvac_mode = self._map_operation_mode(operation_mode)
            
            # Set target temperature based on mode
            if self._hvac_mode == HVACMode.COOL:
                self._target_temperature = float(data.get("required_temp_cooling", 0))
                self._fan_mode = self._map_fan_speed(data.get("fan_state_current_cooling", "0"))
            elif self._hvac_mode == HVACMode.HEAT:
                self._target_temperature = float(data.get("required_temp_heating", 0))
                self._fan_mode = self._map_fan_speed(data.get("fan_state_current_heating", "0"))
            elif self._hvac_mode == HVACMode.FAN_ONLY:
                self._fan_mode = self._map_fan_speed(data.get("fan_state_current_fan", "0"))
            
            self._attributes.update({
                "water_temperature": self._water_temp,
                "room_temperature_2": self._temp2,
            })
            
            # Update HVAC action
            if self._hvac_mode == HVACMode.OFF:
                self._hvac_action = HVACAction.OFF
            elif self._hvac_mode == HVACMode.HEAT:
                self._hvac_action = HVACAction.HEATING if self._temperature < self._target_temperature else HVACAction.IDLE
            elif self._hvac_mode == HVACMode.COOL:
                self._hvac_action = HVACAction.COOLING if self._temperature > self._target_temperature else HVACAction.IDLE
            else:
                self._hvac_action = HVACAction.FAN
            
            _LOGGER.debug("Parsed state - Mode: %s, Action: %s, Temp: %s, Target: %s, Fan: %s",
                         self._hvac_mode, self._hvac_action, self._temperature,
                         self._target_temperature, self._fan_mode)
                         
        except Exception as ex:
            _LOGGER.error("Error parsing device state: %s. Data: %s", ex, data)

    def _map_operation_mode(self, mode):
        """Map device operation mode to HVACMode."""
        return {
            "0": HVACMode.OFF,
            "1": HVACMode.COOL,
            "2": HVACMode.HEAT,
            "3": HVACMode.FAN_ONLY,
        }.get(str(mode), HVACMode.OFF)

    def _map_fan_speed(self, speed):
        """Map device fan speed to readable strings."""
        return {
            "0": "low",
            "1": "medium",
            "2": "high",
            "3": "auto",
        }.get(speed, "auto")

    def _reverse_map_hvac_mode(self, hvac_mode):
        """Map HVACMode to device operation mode."""
        mode_map = {
            HVACMode.OFF: "0",
            HVACMode.HEAT: "2",
            HVACMode.COOL: "1",
            HVACMode.FAN_ONLY: "3",
        }
        device_mode = mode_map.get(hvac_mode, "0")
        _LOGGER.debug("Reverse mapping HVAC mode %s to %s", hvac_mode, device_mode)
        return device_mode

    def _reverse_map_fan_speed(self, fan_speed):
        """Map fan speed to device fan speed."""
        return {
            "low": "0",
            "medium": "1",
            "high": "2",
            "auto": "3",
        }.get(fan_speed, "3")

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
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._temperature

    @property
    def target_temperature(self):
        """Return the target temperature."""
        return self._target_temperature

    @property
    def hvac_mode(self):
        """Return the current HVAC mode."""
        return self._hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available HVAC modes."""
        return HVAC_MODES

    @property
    def hvac_action(self):
        """Return current HVAC action."""
        return self._hvac_action

    @property
    def fan_mode(self):
        """Return the fan mode."""
        return self._fan_mode

    @property
    def fan_modes(self):
        """Return the list of supported fan modes."""
        return self._fan_modes

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return self._attr_supported_features

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return self._attributes

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        
        # Optimistically update the target temperature
        self._target_temperature = temperature
        self.async_write_ha_state()
        
        await self._set_control({"temperature": temperature})

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new HVAC mode."""
        if hvac_mode not in HVAC_MODES:
            _LOGGER.error(f"Unsupported HVAC mode: {hvac_mode}")
            return

        # Optimistically update the HVAC mode
        self._hvac_mode = hvac_mode
        self.async_write_ha_state()

        await self._set_control({"hvac_mode": hvac_mode})

    async def async_set_fan_mode(self, fan_mode):
        """Set new fan mode."""
        if fan_mode not in self._fan_modes:
            _LOGGER.error(f"Unsupported fan mode: {fan_mode}")
            return

        # Optimistically update the fan mode
        self._fan_mode = fan_mode
        self.async_write_ha_state()

        await self._set_control({"fan_mode": fan_mode})

    async def _set_control(self, control_data):
        """Send control command to the device."""
        if not self._token:
            _LOGGER.warning("No valid token available for %s, cannot set control", self._name)
            return

        control_url = f"http://{self._ip_address}/wifi/setmode"
        headers = {
            "Authorization": f"Bearer {self._token.strip()}",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "myApp"
        }

        # Build payload string
        payload_parts = []
        if "temperature" in control_data:
            payload_parts.append(f"required_temp={control_data['temperature']}")
        if "hvac_mode" in control_data:
            payload_parts.append(f"required_mode={self._reverse_map_hvac_mode(control_data['hvac_mode'])}")
        if "fan_mode" in control_data:
            payload_parts.append(f"required_speed={self._reverse_map_fan_speed(control_data['fan_mode'])}")

        payload = "&".join(payload_parts)
        if payload:
            payload = "&" + payload  # Add leading & as per your example

        _LOGGER.debug("Sending control payload: %s", payload)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    control_url,
                    headers=headers,
                    data=payload,
                    timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                    allow_redirects=False,
                ) as response:
                    response_text = await response.text()
                    _LOGGER.debug("Control response [%d]: %s", response.status, response_text)
                    
                    if response.status != 200:
                        raise aiohttp.ClientError(f"Invalid response status: {response.status}")

        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("Failed to send control command to %s: %s", self._name, str(err))
            raise