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
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import aiohttp
import asyncio
import logging
from datetime import timedelta, datetime
from homeassistant.core import CALLBACK_TYPE
from homeassistant.helpers.event import async_track_time_interval
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

def throttle(interval):
    """Decorator that prevents a function from being called more than once every interval."""
    def decorator(func):
        last_called = {}
        async def wrapper(*args, **kwargs):
            now = datetime.now()
            if func not in last_called or now - last_called[func] >= interval:
                last_called[func] = now
                return await func(*args, **kwargs)
        return wrapper
    return decorator

MIN_TIME_BETWEEN_LOGS = timedelta(seconds=60)

@throttle(MIN_TIME_BETWEEN_LOGS)
async def log_with_throttle(logger, level, msg, *args):
    """Log with throttling to avoid excessive messages."""
    logger.log(level, msg, *args)

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
    name = config_entry.data["name"]
    coordinator = hass.data[DOMAIN][name]
    
    climate_entity = FCUClimate(name, coordinator)
    async_add_entities([climate_entity], True)

class FCUClimate(CoordinatorEntity, ClimateEntity, RestoreEntity):
    """Representation of a fan coil unit as a climate entity."""

    def __init__(self, name, coordinator):
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._attr_unique_id = name
        self._name = name
        self._temperature = None
        self._water_temp = None
        self._device_status = None
        self._error_index = None
        self._target_temperature = None
        self._hvac_mode = HVACMode.OFF
        self._hvac_action = HVACAction.IDLE
        self._fan_mode = "auto"
        self._fan_modes = FAN_MODES
        self._attributes = {}
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_modes = HVAC_MODES
        self._attr_fan_modes = FAN_MODES
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
        )
        self._attr_min_temp = 16
        self._attr_max_temp = 30
        self._attr_precision = 0.5

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
            await self._fetch_device_state()
        except Exception as err:
            _LOGGER.error("Failed to update %s: %s", self._name, str(err))
            # Don't clear state on error to maintain last known state

    async def _fetch_device_state(self):
        """Fetch the current state of the device."""
        status_url = f"http://{self._ip_address}/wifi/shortstatus"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    status_url,
                    timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                ) as response:
                    text = await response.text()
                    _LOGGER.debug("Raw response from %s: %s", self._name, text)
                    
                    if response.status == 200:
                        try:
                            # Try to parse as JSON
                            data = text.replace("'", '"')  # Replace single quotes with double quotes
                            import json
                            try:
                                data = json.loads(data)
                            except json.JSONDecodeError:
                                # If JSON fails, try eval (response might be a Python dict string)
                                import ast
                                data = ast.literal_eval(text)
                            
                            if isinstance(data, dict):
                                self._parse_device_state(data)
                                return
                            else:
                                _LOGGER.error("Invalid data format for %s: %s", self._name, text)
                        except Exception as e:
                            _LOGGER.error("Failed to parse response for %s: %s. Response: %s", 
                                        self._name, str(e), text)
                    else:
                        _LOGGER.warning(
                            "Failed to fetch state for %s: %s", 
                            self._name, response.status
                        )

        except Exception as err:
            _LOGGER.error("Error fetching state for %s: %s", self._name, str(err))

    def _parse_device_state(self, data):
        """Parse the state data from the device."""
        try:
            # Parse temperatures with 1 decimal precision
            self._temperature = round(float(data.get("rt", 0)), 1)  # Room temperature
            self._water_temp = round(float(data.get("wt", 0)), 1)  # Water temperature
            self._device_status = data.get("device_status", None)  # Device status
            self._error_index = data.get("error_index", None)  # Error index
            
            # Update attributes for sensors
            self._attributes.update({
                "room_temperature": self._temperature,
                "water_temperature": self._water_temp,
                "device_status": self._device_status,
                "error_index": self._error_index,
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
            log_with_throttle(_LOGGER, logging.ERROR, 
                "Error parsing device state: %s. Data: %s", ex, data)
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
        return self.coordinator.data.get("rt")

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
        """Return device-specific state attributes."""
        return {
            "water_temperature": self.coordinator.data.get("wt"),
            "device_status": self.coordinator.data.get("device_status"),
            "error_index": self.coordinator.data.get("error_index"),
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
        self._target_temperature = temperature
        await self._send_control_command({"temperature": temperature})

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new HVAC mode."""
        if hvac_mode not in HVAC_MODES:
            _LOGGER.error(f"Unsupported HVAC mode: {hvac_mode}")
            return
        self._hvac_mode = hvac_mode
        await self._send_control_command({"hvac_mode": hvac_mode})

    async def async_set_fan_mode(self, fan_mode):
        """Set new fan mode."""
        if fan_mode not in self._fan_modes:
            _LOGGER.error(f"Unsupported fan mode: {fan_mode}")
            return
        self._fan_mode = fan_mode
        await self._send_control_command({"fan_mode": fan_mode})

    async def _send_control_command(self, control_data):
        """Send control command to the device."""
        # Handle temperature
        if "temperature" in control_data:
            temp = str(control_data["temperature"])
            if self._hvac_mode == HVACMode.COOL:
                self._cooling_temp = float(temp)
            elif self._hvac_mode == HVACMode.HEAT:
                self._heating_temp = float(temp)
            self._target_temperature = float(temp)
        else:
            if self._hvac_mode == HVACMode.COOL:
                temp = str(self._cooling_temp)
            elif self._hvac_mode == HVACMode.HEAT:
                temp = str(self._heating_temp)
            else:
                temp = str(self._target_temperature if self._target_temperature is not None else 22)

        # Handle fan speed
        if "fan_mode" in control_data:
            self._fan_mode_updating = True
            new_fan_mode = control_data["fan_mode"]
            fan_speed = self._reverse_map_fan_speed(new_fan_mode)
            self._fan_mode = new_fan_mode
        else:
            fan_speed = self._reverse_map_fan_speed(self._fan_mode)

        # Build control URL and form data
        control_url = f"http://{self._ip_address}/wifi/setmodenoauth"
        form_data = {
            "required_temp": temp,
            "required_mode": self._reverse_map_hvac_mode(self._hvac_mode),
            "required_speed": fan_speed
        }

        # Log the exact command for debugging
        _LOGGER.info("Sending command: curl -X POST %s -d \"%s\"", 
                    control_url, "&".join(f"{k}={v}" for k, v in form_data.items()))

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    control_url,
                    data=form_data,  # aiohttp will format this as form-urlencoded
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                ) as response:
                    response_text = await response.text()
                    _LOGGER.debug("Response: %s", response_text)
                    
                    if response.status == 200:
                        self._update_states_after_control(control_data)
                        return

                    _LOGGER.warning(
                        "Control failed for %s: %s %s", 
                        self._name, response.status, response_text
                    )

        except Exception as err:
            _LOGGER.error("Failed to control %s: %s", self._name, str(err))

    def _update_states_after_control(self, control_data):
        """Update internal states after successful control command."""
        # Update attributes
        self._attributes.update({
            "fan_mode_cooling": self._fan_mode_cooling,
            "fan_mode_heating": self._fan_mode_heating,
            "fan_mode_fan": self._fan_mode_fan
        })
        self.async_write_ha_state()