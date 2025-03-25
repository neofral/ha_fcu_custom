from homeassistant import config_entries
import voluptuous as vol
from homeassistant.const import CONF_NAME, CONF_IP_ADDRESS
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

class FCUConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configuration flow for FCU integration."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            # Check if device already configured
            await self.async_set_unique_id(
                f"{user_input[CONF_IP_ADDRESS]}_{user_input[CONF_NAME]}"
            )
            self._abort_if_unique_id_configured()

            # Validate connection
            # TODO: Add actual device validation here
            try:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.error("Error setting up FCU integration: %s", ex)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_IP_ADDRESS): str,
            }),
            errors=errors,
        )