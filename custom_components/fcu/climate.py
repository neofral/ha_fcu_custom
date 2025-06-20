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
from homeassistant.core import callback  # Add this import
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import aiohttp
import asyncio
import logging
from datetime import timedelta, datetime
from homeassistant.core import CALLBACK_TYPE
from homeassistant.helpers.event import async_track_time_interval
from .const import DOMAIN

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

TIMEOUT = 15  # seconds  (increase from 10 to 15, or higher if needed)
CONTENT_TYPE_JSON = "application/json"
COMMON_HEADERS = {
    "X-Requested-With": "myApp",
}

RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds

# Add timeout constant
AVAILABILITY_TIMEOUT = timedelta(minutes=10)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up FCU climate based on config_entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    climate = FCUClimate(coordinator, entry.entry_id, data["name"], data["ip_address"])
    async_add_entities([climate])
    return True

class FCUClimate(CoordinatorEntity, ClimateEntity, RestoreEntity):
    """Representation of a fan coil unit as a climate entity."""

    def __init__(self, coordinator, entry_id, name, ip_address):
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_climate"
        self._name = name
        self._ip_address = ip_address
        self._entry_id = entry_id
        self._temperature = None
        self._water_temp = None
        self._error_index = None
        self._target_temperature = 22  # Default target temp
        self._cooling_temp = 22  # Initialize cooling temp
        self._heating_temp = 22  # Initialize heating temp
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
        self._last_update = None

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
            # Update successful timestamp
            self._last_update = datetime.now()
            
            # Parse temperatures with 1 decimal precision
            self._temperature = round(float(data.get("rt", 0)), 1)
            self._water_temp = round(float(data.get("wt", 0)), 1)
            self._error_index = data.get("error_index", None)
            
            # Update attributes and trigger sensor updates
            self._attributes.update({
                "room_temperature": self._temperature,
                "water_temperature": self._water_temp,
                "error_index": self._error_index,
            })
            self.async_write_ha_state()  # This will trigger sensor updates
            
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

            # --- Thermostat logic for hvac_action ---
            current_temp = self._temperature
            target_temp = self._target_temperature
            device_status_raw = data.get("device_status", "1")
            device_status = str(device_status_raw)
            _LOGGER.debug(
                "Device status for %s: raw=%r, str=%s, hvac_mode=%s, current_temp=%s, target_temp=%s",
                self._name, device_status_raw, device_status, self._hvac_mode, current_temp, target_temp
            )
            if self._hvac_mode == HVACMode.OFF:
                self._hvac_action = HVACAction.OFF
            elif self._hvac_mode == HVACMode.HEAT:
                if current_temp is not None and target_temp is not None and current_temp < target_temp:
                    self._hvac_action = HVACAction.HEATING
                else:
                    self._hvac_action = HVACAction.IDLE
            elif self._hvac_mode == HVACMode.COOL:
                if current_temp is not None and target_temp is not None and current_temp > target_temp:
                    self._hvac_action = HVACAction.COOLING
                else:
                    self._hvac_action = HVACAction.IDLE
            elif self._hvac_mode == HVACMode.FAN_ONLY:
                if device_status in ("0", 0):
                    self._hvac_action = HVACAction.FAN
                else:
                    self._hvac_action = HVACAction.IDLE
            else:
                self._hvac_action = HVACAction.IDLE
            _LOGGER.debug(
                "Set hvac_action for %s: %s (mode=%s, device_status=%s, current_temp=%s, target_temp=%s)",
                self._name, self._hvac_action, self._hvac_mode, device_status, current_temp, target_temp
            )

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
            "identifiers": {(DOMAIN, self._entry_id)},
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
        if self._temperature is not None:
            return self._temperature
        # Fallback to coordinator data if local value not set
        if self.coordinator.data and "rt" in self.coordinator.data:
            return round(float(self.coordinator.data["rt"]), 1)
        return None

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

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if self.coordinator.data and "rt" in self.coordinator.data:
            # Consider available if we have temperature data
            return True
        return False
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data:
            try:
                self._temperature = round(float(self.coordinator.data.get("rt", 0)), 1)
                self._water_temp = round(float(self.coordinator.data.get("wt", 0)), 1)
                self._error_index = self.coordinator.data.get("error_index", None)
                operation_mode = str(self.coordinator.data.get("operation_mode", "0"))
                self._hvac_mode = self._map_operation_mode(operation_mode)
                current_temp = self._temperature
                target_temp = self._target_temperature
                device_status_raw = self.coordinator.data.get("device_status", "1")
                device_status = str(device_status_raw)
                _LOGGER.debug(
                    "Coordinator update device_status for %s: raw=%r, str=%s, hvac_mode=%s, current_temp=%s, target_temp=%s",
                    self._name, device_status_raw, device_status, self._hvac_mode, current_temp, target_temp
                )
                if self._hvac_mode == HVACMode.OFF:
                    self._hvac_action = HVACAction.OFF
                elif self._hvac_mode == HVACMode.HEAT:
                    if current_temp is not None and target_temp is not None and current_temp < target_temp:
                        self._hvac_action = HVACAction.HEATING
                    else:
                        self._hvac_action = HVACAction.IDLE
                elif self._hvac_mode == HVACMode.COOL:
                    if current_temp is not None and target_temp is not None and current_temp > target_temp:
                        self._hvac_action = HVACAction.COOLING
                    else:
                        self._hvac_action = HVACAction.IDLE
                elif self._hvac_mode == HVACMode.FAN_ONLY:
                    if device_status in ("0", 0):
                        self._hvac_action = HVACAction.FAN
                    else:
                        self._hvac_action = HVACAction.IDLE
                else:
                    self._hvac_action = HVACAction.IDLE
                _LOGGER.debug(
                    "Coordinator set hvac_action for %s: %s (mode=%s, device_status=%s, current_temp=%s, target_temp=%s)",
                    self._name, self._hvac_action, self._hvac_mode, device_status, current_temp, target_temp
                )
                self.async_write_ha_state()
            except Exception as ex:
                _LOGGER.error("Error handling coordinator update: %s", ex)

    async def _async_update_from_data(self, data):
        """Update attrs from data."""
        if not data:
            return
        if "rt" in data:
            self._temperature = round(float(data["rt"]), 1)
        if "wt" in data:
            self._water_temp = round(float(data["wt"]), 1)
        if "operation_mode" in data:
            self._hvac_mode = self._map_operation_mode(str(data["operation_mode"]))
            current_temp = self._temperature
            target_temp = self._target_temperature
            device_status_raw = data.get("device_status", "1")
            device_status = str(device_status_raw)
            _LOGGER.debug(
                "Async update device_status for %s: raw=%r, str=%s, hvac_mode=%s, current_temp=%s, target_temp=%s",
                self._name, device_status_raw, device_status, self._hvac_mode, current_temp, target_temp
            )
            if self._hvac_mode == HVACMode.OFF:
                self._hvac_action = HVACAction.OFF
            elif self._hvac_mode == HVACMode.HEAT:
                if current_temp is not None and target_temp is not None and current_temp < target_temp:
                    self._hvac_action = HVACAction.HEATING
                else:
                    self._hvac_action = HVACAction.IDLE
            elif self._hvac_mode == HVACMode.COOL:
                if current_temp is not None and target_temp is not None and current_temp > target_temp:
                    self._hvac_action = HVACAction.COOLING
                else:
                    self._hvac_action = HVACAction.IDLE
            elif self._hvac_mode == HVACMode.FAN_ONLY:
                if device_status in ("0", 0):
                    self._hvac_action = HVACAction.FAN
                else:
                    self._hvac_action = HVACAction.IDLE
            else:
                self._hvac_action = HVACAction.IDLE
            _LOGGER.debug(
                "Async update set hvac_action for %s: %s (mode=%s, device_status=%s, current_temp=%s, target_temp=%s)",
                self._name, self._hvac_action, self._hvac_mode, device_status, current_temp, target_temp
            )
        # Update fan modes
        self._fan_mode_cooling = self._map_fan_speed(data.get("fan_state_current_cooling", "3"))
        self._fan_mode_heating = self._map_fan_speed(data.get("fan_state_current_heating", "3"))
        self._fan_mode_fan = self._map_fan_speed(data.get("fan_state_current_fan", "3"))

        # Update current fan mode based on hvac_mode
        if self._hvac_mode == HVACMode.COOL:
            self._fan_mode = self._fan_mode_cooling
        elif self._hvac_mode == HVACMode.HEAT:
            self._fan_mode = self._fan_mode_heating
        elif self._hvac_mode == HVACMode.FAN_ONLY:
            self._fan_mode = self._fan_mode_fan

        # Update attributes
        self._attributes.update({
            "fan_mode_cooling": self._fan_mode_cooling,
            "fan_mode_heating": self._fan_mode_heating,
            "fan_mode_fan": self._fan_mode_fan
        })

    async def _send_control_command(self, control_data):
        """Send control command to the device."""
        try:
            # First determine the temperature to send
            if "temperature" in control_data:
                temp = str(control_data["temperature"])
                # Update local temps
                if self._hvac_mode == HVACMode.COOL:
                    self._cooling_temp = float(temp)
                elif self._hvac_mode == HVACMode.HEAT:
                    self._heating_temp = float(temp)
                self._target_temperature = float(temp)
            else:
                # Use existing temperature based on mode
                if self._hvac_mode == HVACMode.COOL:
                    temp = str(self._cooling_temp)
                elif self._hvac_mode == HVACMode.HEAT:
                    temp = str(self._heating_temp)
                else:
                    temp = str(self._target_temperature if self._target_temperature is not None else 22)

            # Update mode if provided
            if "hvac_mode" in control_data:
                self._hvac_mode = control_data["hvac_mode"]

            # Update fan mode if provided
            if "fan_mode" in control_data:
                self._fan_mode = control_data["fan_mode"]

            # Build request with all required parameters
            device_params = {
                "required_temp": temp,
                "required_mode": self._reverse_map_hvac_mode(self._hvac_mode),
                "required_speed": self._reverse_map_fan_speed(self._fan_mode)
            }

            _LOGGER.debug("Sending control command: %s", device_params)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{self._ip_address}/wifi/setmodenoauth",
                    data=device_params,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=aiohttp.ClientTimeout(total=8)
                ) as response:
                    response_text = await response.text()
                    _LOGGER.debug("Response: %s", response_text)
                    if response.status == 200:
                        await self.coordinator.async_refresh()
                    else:
                        _LOGGER.error("Control failed: %s - %s", response.status, response_text)

        except Exception as err:
            _LOGGER.error("Failed to send control command: %s", str(err))

    def set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode not in HVAC_MODES:
            raise ValueError(f"Invalid hvac_mode: {hvac_mode}")
        self._hvac_mode = hvac_mode
        self.schedule_update_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        if hvac_mode not in HVAC_MODES:
            _LOGGER.error(f"Unsupported HVAC mode: {hvac_mode}")
            return
        await self._send_control_command({"hvac_mode": hvac_mode})

    def set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        self._target_temperature = float(temperature)
        self.schedule_update_ha_state()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        
        try:
            temp = float(temperature)
            if temp < self._attr_min_temp or temp > self._attr_max_temp:
                _LOGGER.error("Temperature %s out of range [%s, %s]", 
                            temp, self._attr_min_temp, self._attr_max_temp)
                return
                
            await self._send_control_command({
                "temperature": temp,
                "hvac_mode": self._hvac_mode,  # Include current mode
                "fan_mode": self._fan_mode      # Include current fan mode
            })
        except ValueError as ex:
            _LOGGER.error("Invalid temperature value: %s", ex)
        except Exception as ex:
            _LOGGER.error("Failed to set temperature: %s", ex)

    async def async_set_fan_mode(self, fan_mode):
        """Set new fan mode."""
        if fan_mode not in FAN_MODES:
            _LOGGER.error(f"Unsupported fan mode: {fan_mode}")
            return
            
        try:
            # Store the fan mode based on current HVAC mode
            if self._hvac_mode == HVACMode.COOL:
                self._fan_mode_cooling = fan_mode
            elif self._hvac_mode == HVACMode.HEAT:
                self._fan_mode_heating = fan_mode
            elif self._hvac_mode == HVACMode.FAN_ONLY:
                self._fan_mode_fan = fan_mode
                
            self._fan_mode = fan_mode
            
            await self._send_control_command({
                "fan_mode": fan_mode,
                "temperature": self._target_temperature,  # Include current temperature
                "hvac_mode": self._hvac_mode  # Include current mode
            })
        except Exception as ex:
            _LOGGER.error("Failed to set fan mode: %s", ex)