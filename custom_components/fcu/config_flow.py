from homeassistant import config_entries
from .const import DOMAIN, CONF_NAME, CONF_IP_ADDRESS
import voluptuous as vol

class FCUConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # Dynamically add the device name and IP
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_IP_ADDRESS): str,
            }),
        )