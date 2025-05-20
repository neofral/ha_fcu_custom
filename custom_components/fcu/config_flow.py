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
                                CONF_T1D: float(data.get('t1d', 0.3)),
                                CONF_T2D: float(data.get('t2d', 0.3)),
                                CONF_T3D: float(data.get('t3d', 0.3)),
                                CONF_T4D: float(data.get('t4d', 0.3)),
                                CONF_SHUTDOWN_DELAY: int(data.get('shutdown_delay', 30))
                            }
                        except Exception as ex:
                            _LOGGER.error("Error parsing response: %s. Response: %s", ex, text)
        except Exception as ex:
            _LOGGER.error("Error fetching current values: %s", ex)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}

        # Fetch current values first time
        if not self.current_values:
            await self._fetch_current_values()

        if user_input is not None:
            ip_address = self._ip_address  # Use stored IP address
            # Format payload like setmodenoauth
            payload = "&".join([
                f"{k}={v}" for k, v in user_input.items()
            ])
            _LOGGER.debug("Sending payload: %s", payload)

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"http://{ip_address}/wifi/extraconfig",
                        data=payload,  # Will be sent as form-urlencoded automatically
                    ) as response:
                        response_text = await response.text()
                        _LOGGER.debug("Response: %s", response_text)
                        if response.status == 200:
                            await self._fetch_current_values()  # Refresh values
                            return self.async_create_entry(title="", data=self.current_values)
                        errors["base"] = "update_failed"
            except Exception as ex:
                _LOGGER.error("Error updating config: %s", ex)
                errors["base"] = "update_failed"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_T1D, default=self.current_values.get(CONF_T1D, 0.3)): float,
                vol.Required(CONF_T2D, default=self.current_values.get(CONF_T2D, 0.3)): float,
                vol.Required(CONF_T3D, default=self.current_values.get(CONF_T3D, 0.3)): float,
                vol.Required(CONF_T4D, default=self.current_values.get(CONF_T4D, 0.4)): float,
                vol.Required(CONF_SHUTDOWN_DELAY, default=self.current_values.get(CONF_SHUTDOWN_DELAY, 30)): int,
            }),
            errors=errors,
        )