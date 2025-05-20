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

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}

        if user_input is not None:
            ip_address = self.config_entry.data[CONF_IP_ADDRESS]
            
            # Format payload as key=value pairs joined by &
            payload = "&".join(f"{k}={v}" for k, v in user_input.items())
            url = f"http://{ip_address}/wifi/extraconfig"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        data=payload,  # Will be sent as form-urlencoded
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    ) as response:
                        if response.status != 200:
                            _LOGGER.error("Failed to update config: %s", await response.text())
                            errors["base"] = "update_failed"
                        else:
                            return self.async_create_entry(title="", data=user_input)
            except Exception as ex:
                _LOGGER.error("Error updating config: %s", str(ex))
                errors["base"] = "update_failed"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_T1D, default=DEFAULT_T1D): float,
                vol.Required(CONF_T2D, default=DEFAULT_T2D): float,
                vol.Required(CONF_T3D, default=DEFAULT_T3D): float,
                vol.Required(CONF_T4D, default=DEFAULT_T4D): float,
                vol.Required(CONF_SHUTDOWN_DELAY, default=DEFAULT_SHUTDOWN_DELAY): int,
            }),
            errors=errors,
        )