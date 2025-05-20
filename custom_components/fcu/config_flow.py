"""Config flow for FCU integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_IP_ADDRESS
import aiohttp
import logging

from .const import (
    DOMAIN, CONF_T1D, CONF_T2D, CONF_T3D, CONF_T4D, CONF_SHUTDOWN_DELAY,
    DEFAULT_T1D, DEFAULT_T2D, DEFAULT_T3D, DEFAULT_T4D, DEFAULT_SHUTDOWN_DELAY
)

_LOGGER = logging.getLogger(__name__)

class FCUConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FCU."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_NAME])
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_IP_ADDRESS): str,
            }),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return FCUOptionsFlowHandler(config_entry)

class FCUOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle FCU options."""
    
    def __init__(self, config_entry):
        """Initialize options flow."""
        super().__init__()
        # Don't store config_entry directly
        self._entry_id = config_entry.entry_id
        self._ip_address = config_entry.data[CONF_IP_ADDRESS]
        self.current_values = {}

    async def _fetch_current_values(self):
        """Fetch current values from device."""
        url = f"http://{self._ip_address}/wifi/extraconfig"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url) as response:
                    if response.status == 200:
                        text = await response.text()
                        # Parse response text
                        try:
                            import json
                            data = text.replace("'", '"')  # Replace single quotes with double quotes
                            data = json.loads(data)
                            # Store current values
                            self.current_values = {
                                CONF_T1D: float(data.get('t1d', 0.0)),
                                CONF_T2D: float(data.get('t2d', 0.0)),
                                CONF_T3D: float(data.get('t3d', 0.0)),
                                CONF_T4D: float(data.get('t4d', 0.0)),
                                CONF_SHUTDOWN_DELAY: int(data.get('shutdown_delay', 30000))
                            }
                        except Exception as ex:
                            _LOGGER.error("Error parsing response: %s. Response: %s", ex, text)
        except Exception as ex:
            _LOGGER.error("Error fetching current values: %s", ex)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}

        if not self.current_values:
            await self._fetch_current_values()
            _LOGGER.debug("Fetched values: %s", self.current_values)

        if user_input is not None:
            try:
                # Convert and validate values
                device_vars = {
                    't1d': "{:.1f}".format(float(user_input[CONF_T1D])),
                    't2d': "{:.1f}".format(float(user_input[CONF_T2D])),
                    't3d': "{:.1f}".format(float(user_input[CONF_T3D])),
                    't4d': "{:.1f}".format(float(user_input[CONF_T4D])),
                    'shutdown_delay': str(int(user_input[CONF_SHUTDOWN_DELAY]))
                }
                _LOGGER.debug("Submitting values: %s", device_vars)
                
                payload = "&".join(f"{k}={v}" for k, v in device_vars.items())
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"http://{self._ip_address}/wifi/extraconfig",
                        data=payload,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    ) as response:
                        response_text = await response.text()
                        _LOGGER.debug("Response: %s", response_text)
                        if response.status == 200:
                            await self._fetch_current_values()  # Refresh values
                            return self.async_create_entry(title="", data=self.current_values)
                        errors["base"] = "update_failed"
            except ValueError as ex:
                _LOGGER.error("Value error: %s", ex)
                errors["base"] = "invalid_value"
                
        # Schema with value validation
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_T1D, 
                    default=self.current_values.get(CONF_T1D, 0.0)
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=10.0)),
                vol.Required(
                    CONF_T2D,
                    default=self.current_values.get(CONF_T2D, 0.0)
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=10.0)),
                vol.Required(
                    CONF_T3D,
                    default=self.current_values.get(CONF_T3D, 0.0)
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=10.0)),
                vol.Required(
                    CONF_T4D,
                    default=self.current_values.get(CONF_T4D, 0.0)
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=10.0)),
                vol.Required(
                    CONF_SHUTDOWN_DELAY,
                    default=self.current_values.get(CONF_SHUTDOWN_DELAY, 30000)
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=60000)),
            }),
            errors=errors,
        )