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
        self.config_entry = config_entry
        self.current_values = {}

    async def _fetch_current_values(self):
        """Fetch current values from device."""
        ip_address = self.config_entry.data[CONF_IP_ADDRESS]
        url = f"http://{ip_address}/wifi/extraconfig"
        
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
            # Only send changed values to device
            changed_values = {
                k: v for k, v in user_input.items() 
                if k in self.current_values and v != self.current_values[k]
            }
            
            if changed_values:
                ip_address = self.config_entry.data[CONF_IP_ADDRESS]
                payload = "&".join(f"{k}={v}" for k, v in changed_values.items())

                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"http://{ip_address}/wifi/extraconfig",
                            data=payload,
                            headers={"Content-Type": "application/x-www-form-urlencoded"},
                        ) as response:
                            if response.status != 200:
                                _LOGGER.error("Failed to update config: %s", await response.text())
                                errors["base"] = "update_failed"
                            else:
                                self.current_values.update(changed_values)
                                return self.async_create_entry(title="", data=self.current_values)
                except Exception as ex:
                    _LOGGER.error("Error updating config: %s", ex)
                    errors["base"] = "update_failed"
            else:
                return self.async_create_entry(title="", data=self.current_values)

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