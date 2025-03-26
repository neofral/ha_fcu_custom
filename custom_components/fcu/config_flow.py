"""Config flow for FCU integration."""
import voluptuous as vol
import aiohttp
import logging

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_IP_ADDRESS
from homeassistant.core import callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): str,
    vol.Required(CONF_IP_ADDRESS): str,
})

class FCUConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FCU integration."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Use name as unique ID
            await self.async_set_unique_id(user_input[CONF_NAME])
            self._abort_if_unique_id_configured()

            try:
                # Basic validation of IP address format
                if ":" in user_input[CONF_IP_ADDRESS]:
                    errors["base"] = "invalid_ip"
                else:
                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data=user_input
                    )
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return FCUOptionsFlow(config_entry)

class FCUOptionsFlow(config_entries.OptionsFlow):
    """Handle FCU options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__(config_entry)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({})
        )