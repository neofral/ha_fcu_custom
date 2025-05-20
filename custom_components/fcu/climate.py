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
import asyncio  # Add this import
import logging
from datetime import timedelta
from homeassistant.core import CALLBACK_TYPE
from homeassistant.helpers.event import async_track_time_interval
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY]
FAN_MODES = ["low", "medium", "high", "auto"]

TIMEOUT = 10  # seconds
CONTENT_TYPE_JSON = "application/json"
COMMON_HEADERS = {
    "X-Requested-With": "myApp",
}

RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the fan coil unit climate entity."""
    # Clear any existing update jobs for this entry
    if config_entry.entry_id in hass.data.get(DOMAIN, {}):
        if f"{config_entry.data['name']}_cleanup" in hass.data[DOMAIN]:
            hass.data[DOMAIN][f"{config_entry.data['name']}_cleanup"]()
            
    name = config_entry.data["name"]
    ip_address = config_entry.data["ip_address"]
    use_auth = config_entry.data.get("use_auth", True)
    
    # Only get credentials if auth is enabled
    username = config_entry.data.get("username") if use_auth else None
    password = config_entry.data.get("password") if use_auth else None

    climate_entity = FCUClimate(name, ip_address, use_auth, username, password)
    async_add_entities([climate_entity], True)
    
    # Store climate entity in hass.data for sensors to access
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][name] = climate_entity

    # Set up periodic updates
    async def async_update(_now=None):
        """Update device state."""
        await climate_entity.async_update()

    remove_update_interval = async_track_time_interval(
        hass, async_update, SCAN_INTERVAL
    )

    # Store cleanup function
    hass.data[DOMAIN][f"{name}_cleanup"] = remove_update_interval

class FCUClimate(ClimateEntity, RestoreEntity):
    """Representation of a fan coil unit as a climate entity."""

    def __init__(self, name, ip_address, use_auth=True, username=None, password=None):
        """Initialize the climate entity."""
        self._attr_unique_id = name
        self._name = name
        self._ip_address = ip_address
        self._use_auth = use_auth
        # Only store credentials if auth is enabled
        self._username = username if use_auth else None
        self._password = password if use_auth else None
        self._token = None
        self._temperature = None
        self._water_temp = None
        self._temp2 = None
        self._target_temperature = None
        self._hvac_mode = HVACMode.OFF
        self._hvac_action = HVACAction.IDLE
        self._fan_mode = "auto"
        self._fan_modes = FAN_MODES  # Define supported fan modes
        self._attributes = {}
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_modes = HVAC_MODES
        self._attr_fan_modes = FAN_MODES
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE 
            | ClimateEntityFeature.FAN_MODE
        )
        self._fan_mode_cooling = "auto"
        self._fan_mode_heating = "auto"
        self._fan_mode_fan = "auto"
        self._cooling_temp = 21
        self._heating_temp = 23
        self._attr_min_temp = 16
        self._attr_max_temp = 30
        self._attr_precision = 0.1
        self._attr_target_temperature_step = 0.1
        self._target_temp_high = 0.3  # Cooling hysteresis
        self._target_temp_low = 0.3   # Heating hysteresis
        self._device_status = None
        self._error_index = None

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        
        # Restore previous state if available
        last_state = await self.async_get_last_state()
        if last_state is not None:
            if last_state.state:
                self._hvac_mode = last_state.state
            if last_state.attributes.get('fan_mode'):
                self._fan_mode = last_state.attributes['fan_mode']
            if last_state.attributes.get('temperature'):
                self._target_temperature = last_state.attributes['temperature']
            
            # Restore mode-specific temperatures and fan modes
            if last_state.attributes.get(f"{self._name}_fan_mode_cooling"):
                self._fan_mode_cooling = last_state.attributes[f"{self._name}_fan_mode_cooling"]
            if last_state.attributes.get(f"{self._name}_fan_mode_heating"):
                self._fan_mode_heating = last_state.attributes[f"{self._name}_fan_mode_heating"]
            if last_state.attributes.get(f"{self._name}_fan_mode_fan"):
                self._fan_mode_fan = last_state.attributes[f"{self._name}_fan_mode_fan"]
        
        # Force initial update
        await self.async_update()

    async def async_update(self):
        """Fetch new state data for the entity."""
        try:
            # Re-read use_auth from config entry
            entry = next((
                entry for entry in self.hass.config_entries.async_entries(DOMAIN)
                if entry.data.get("name") == self._name
            ), None)
            
            if entry:
                if entry.data.get("use_auth") != self._use_auth:
                    self._use_auth = entry.data["use_auth"]
                    self._username = entry.data.get("username") if self._use_auth else None
                    self._password = entry.data.get("password") if self._use_auth else None
                    self._token = None
            
            await self._fetch_token()
            await self._fetch_device_state()
        except Exception as err:
            _LOGGER.error("Failed to update %s: %s", self._name, str(err))
            # Don't clear state on error to maintain last known state

    async def _fetch_token(self):
        """Fetch a new token from the device."""
        if not self._use_auth:
            _LOGGER.debug("Skipping token fetch for %s (auth disabled)", self._name)
            self._token = "no_auth_token"
            return

        login_url = f"http://{self._ip_address}/login.htm"
        payload = {"username": self._username, "password": self._password}
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
        if self._use_auth and not self._token:
            _LOGGER.warning("No valid token available for %s, skipping state fetch", self._name)
            return

        # Use different endpoint based on auth mode
        status_url = f"http://{self._ip_address}/wifi/{'status' if self._use_auth else 'shortstatus'}"
        headers = COMMON_HEADERS.copy()
        
        if self._use_auth:
            headers.update({
                "Authorization": f"Bearer {self._token.strip()}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": CONTENT_TYPE_JSON,
            })

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
            # Parse temperatures with 1 decimal precision
            self._temperature = round(float(data.get("rt", 0)), 1)  # Room temperature
            self._water_temp = round(float(data.get("wt", 0)), 1)  # Water temperature
            self._device_status = round(float(data.get("device_status", 0)), 1)  # Device status
            self._error_index = round(float(data.get("error_index", 0)), 1)  # Error index
            
            # Store temperatures in attributes with same precision
            self._attributes.update({
                "water_temperature": self._water_temp,
                "room_temperature_2": self._temp2,
            })
            
            # Get operation mode
            operation_mode = str(data.get("operation_mode", "0"))
            prev_mode = self._hvac_mode  # Store previous mode
            self._hvac_mode = self._map_operation_mode(operation_mode)
            
            # Store mode-specific temperatures from device
            cooling_temp = data.get("required_temp_cooling")
            heating_temp = data.get("required_temp_heating")
            
            if cooling_temp is not None:
                self._cooling_temp = float(cooling_temp)
            if heating_temp is not None:
                self._heating_temp = float(heating_temp)
            
            # Set target temperature based on mode
            if self._hvac_mode == HVACMode.COOL:
                self._target_temperature = self._cooling_temp
            elif self._hvac_mode == HVACMode.HEAT:
                self._target_temperature = self._heating_temp

            # Only update fan modes if we haven't just changed them
            if not hasattr(self, '_fan_mode_updating'):
                self._fan_mode_cooling = self._map_fan_speed(data.get("fan_state_current_cooling", "3"))
                self._fan_mode_heating = self._map_fan_speed(data.get("fan_state_current_heating", "3"))
                self._fan_mode_fan = self._map_fan_speed(data.get("fan_state_current_fan", "3"))
                
                # Update current fan mode only if mode changed
                if prev_mode != self._hvac_mode:
                    if self._hvac_mode == HVACMode.COOL:
                        self._fan_mode = self._fan_mode_cooling
                    elif self._hvac_mode == HVACMode.HEAT:
                        self._fan_mode = self._fan_mode_heating
                    elif self._hvac_mode == HVACMode.FAN_ONLY:
                        self._fan_mode = self._fan_mode_fan

            # Store fan states in attributes
            self._attributes.update({
                "fan_mode_cooling": self._fan_mode_cooling,
                "fan_mode_heating": self._fan_mode_heating,
                "fan_mode_fan": self._fan_mode_fan
            })
            
            # Update HVAC action based on mode and device status
            if self._hvac_mode == HVACMode.OFF:
                self._hvac_action = HVACAction.OFF
            elif self._hvac_mode == HVACMode.HEAT:
                if self._device_status == 0:
                    self._hvac_action = HVACAction.HEATING
                else:
                    self._hvac_action = HVACAction.IDLE
            elif self._hvac_mode == HVACMode.COOL:
                if self._device_status == 0:
                    self._hvac_action = HVACAction.COOLING
                else:
                    self._hvac_action = HVACAction.IDLE
            else:
                self._hvac_action = HVACAction.FAN
            
            _LOGGER.debug("Parsed state - Mode: %s, Action: %s, Temp: %s, Target: %s, Fan: %s",
                    self._hvac_mode, self._hvac_action, self._temperature,
                    self._target_temperature, self._fan_mode)

        except Exception as ex:
            _LOGGER.error("Error parsing device state: %s. Data: %s", ex, data)
        finally:
            # Clear the fan mode updating flag
            if hasattr(self, '_fan_mode_updating'):
                delattr(self, '_fan_mode_updating')

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
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": self._name,
            "manufacturer": "Eko Energis + Cotronika",
            "model": "FCU Controller v.0.0.3RD",
            "configuration_url": f"http://{self._ip_address}"
        }

    @property
    def unique_id(self):
        """Return unique ID for this device."""
        return self._attr_unique_id

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
    def target_temperature_high(self):
        """Return the upper bound temperature we try to reach."""
        if self._hvac_mode == HVACMode.COOL and self._target_temperature is not None:
            return self._target_temperature + self._target_temp_high
        return None

    @property
    def target_temperature_low(self):
        """Return the lower bound temperature we try to reach."""
        if self._hvac_mode == HVACMode.HEAT and self._target_temperature is not None:
            return self._target_temperature - self._target_temp_low
        return None

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
        """Return device specific state attributes."""
        return {
            f"{self._name}_water_temperature": self._water_temp,
            f"{self._name}_fan_mode_cooling": self._fan_mode_cooling,
            f"{self._name}_fan_mode_heating": self._fan_mode_heating,
            f"{self._name}_fan_mode_fan": self._fan_mode_fan,
        }

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._attr_min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._attr_max_temp

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
        if self._use_auth and not self._token:
            await self._fetch_token()
            if not self._token:
                _LOGGER.error("No valid token available for %s, cannot set control", self._name)
                return

        # Use different endpoint based on auth mode
        control_url = f"http://{self._ip_address}/wifi/{'setmode' if self._use_auth else 'setmodenoauth'}"
        headers = COMMON_HEADERS.copy()
        
        if self._use_auth:
            headers.update({
                "Authorization": f"Bearer {self._token.strip()}",
                "Content-Type": "application/x-www-form-urlencoded",
            })

        # Get current mode and build basic payload
        current_mode = control_data.get("hvac_mode", self._hvac_mode)
        device_data = {}

        # Handle temperature
        if "temperature" in control_data:
            temp = str(control_data["temperature"])
            # Store temperature for the current mode
            if current_mode == HVACMode.COOL:
                self._cooling_temp = float(temp)
            elif current_mode == HVACMode.HEAT:
                self._heating_temp = float(temp)
            self._target_temperature = float(temp)
        else:
            # Use stored temperature for the mode
            if current_mode == HVACMode.COOL:
                temp = str(self._cooling_temp)
            elif current_mode == HVACMode.HEAT:
                temp = str(self._heating_temp)
            else:
                temp = str(self._target_temperature if self._target_temperature is not None else 22)

        # Add required parameters
        device_data["required_mode"] = self._reverse_map_hvac_mode(current_mode)
        device_data["required_temp"] = temp

        # Update target temperature based on new mode
        if "hvac_mode" in control_data:
            if current_mode == HVACMode.COOL:
                self._target_temperature = self._cooling_temp
            elif current_mode == HVACMode.HEAT:
                self._target_temperature = self._heating_temp

        # Handle fan speed changes
        if "fan_mode" in control_data:
            # Set flag to prevent immediate fan mode override
            self._fan_mode_updating = True
            new_fan_mode = control_data["fan_mode"]
            fan_speed = self._reverse_map_fan_speed(new_fan_mode)
            device_data["required_speed"] = fan_speed
            
            # Update mode-specific fan state and current fan mode
            if current_mode == HVACMode.COOL:
                self._fan_mode_cooling = new_fan_mode
                device_data["fan_state_current_cooling"] = fan_speed
            elif current_mode == HVACMode.HEAT:
                self._fan_mode_heating = new_fan_mode
                device_data["fan_state_current_heating"] = fan_speed
            elif current_mode == HVACMode.FAN_ONLY:
                self._fan_mode_fan = new_fan_mode
                device_data["fan_state_current_fan"] = fan_speed

            # Update current fan mode immediately
            self._fan_mode = new_fan_mode
            self.async_write_ha_state()
        else:
            # Use current fan mode if not changing
            device_data["required_speed"] = self._reverse_map_fan_speed(self._fan_mode)

        # Build payload string with leading &
        payload = "&" + "&".join(f"{k}={v}" for k, v in device_data.items())
        
        _LOGGER.debug("Sending control payload: %s for mode: %s", payload, current_mode)

        for attempt in range(RETRY_ATTEMPTS):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        control_url,
                        headers=headers,
                        data=payload,
                        timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                        allow_redirects=False,
                        ssl=False
                    ) as response:
                        response_text = await response.text()
                        _LOGGER.debug("Control response [%d]: %s", response.status, response_text)
                        
                        if self._use_auth and response.status == 401:  # Unauthorized
                            await self._fetch_token()
                            continue
                        
                        if response.status != 200:
                            raise aiohttp.ClientError(f"Invalid response status: {response.status}")

                        # Success - update states and return
                        self._update_states_after_control(control_data)
                        return

            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                _LOGGER.warning("Attempt %d failed for %s: %s", attempt + 1, self._name, str(err))
                if attempt < RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    _LOGGER.error("Failed to send control command after %d attempts", RETRY_ATTEMPTS)
                    raise

    def _update_states_after_control(self, control_data):
        """Update internal states after successful control command."""
        # Update attributes
        self._attributes.update({
            "fan_mode_cooling": self._fan_mode_cooling,
            "fan_mode_heating": self._fan_mode_heating,
            "fan_mode_fan": self._fan_mode_fan
        })
        self.async_write_ha_state()