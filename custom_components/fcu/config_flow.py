from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME
import voluptuous as vol

from . import DOMAIN

class CustomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ha_fcu_custom."""

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
        
        data_schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_IP_ADDRESS): str
        })
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
