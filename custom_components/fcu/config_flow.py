"""Config flow for FCU integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_IP_ADDRESS
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import aiohttp
import asyncio
import logging

from .const import (
    DOMAIN, CONF_T1D, CONF_T2D, CONF_T3D, CONF_T4D, CONF_SHUTDOWN_DELAY,
    DEFAULT_T1D, DEFAULT_T2D, DEFAULT_T3D, DEFAULT_T4D, DEFAULT_SHUTDOWN_DELAY
)

_LOGGER = logging.getLogger(__name__)

class FCUConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FCU."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
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
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow."""
        return FCUOptionsFlow(config_entry)

class FCUOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry
        self._ip_address = config_entry.data[CONF_IP_ADDRESS]

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        if user_input is not None:
            # Format the data for form-urlencoded request
            params = {
                't1d': "{:.1f}".format(float(user_input[CONF_T1D])),
                't2d': "{:.1f}".format(float(user_input[CONF_T2D])),
                't3d': "{:.1f}".format(float(user_input[CONF_T3D])),
                't4d': "{:.1f}".format(float(user_input[CONF_T4D])),
                'shutdown_delay': str(int(user_input[CONF_SHUTDOWN_DELAY]))
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"http://{self._ip_address}/wifi/extraconfig",
                        data=params,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            _LOGGER.debug(
                                "Config update success: %s with data: %s",
                                self._ip_address,
                                "&".join(f"{k}={v}" for k, v in params.items())
                            )
                            return self.async_create_entry(title="", data=user_input)
                        _LOGGER.error("Failed to update config: %s", response.status)
            except Exception as ex:
                _LOGGER.error("Error updating config: %s", ex)

        schema = vol.Schema({
            vol.Required(
                CONF_T1D,
                default=self.config_entry.options.get(CONF_T1D, DEFAULT_T1D)
            ): vol.All(vol.Coerce(float), vol.Range(min=-10.0, max=10.0)),
            vol.Required(
                CONF_T2D,
                default=self.config_entry.options.get(CONF_T2D, DEFAULT_T2D)
            ): vol.All(vol.Coerce(float), vol.Range(min=-10.0, max=10.0)),
            vol.Required(
                CONF_T3D,
                default=self.config_entry.options.get(CONF_T3D, DEFAULT_T3D)
            ): vol.All(vol.Coerce(float), vol.Range(min=-10.0, max=10.0)),
            vol.Required(
                CONF_T4D,
                default=self.config_entry.options.get(CONF_T4D, DEFAULT_T4D)
            ): vol.All(vol.Coerce(float), vol.Range(min=-10.0, max=10.0)),
            vol.Required(
                CONF_SHUTDOWN_DELAY,
                default=self.config_entry.options.get(CONF_SHUTDOWN_DELAY, DEFAULT_SHUTDOWN_DELAY)
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=60000)),
        })

        return self.async_show_form(step_id="init", data_schema=schema)