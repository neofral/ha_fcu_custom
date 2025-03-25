from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, CONF_NAME, CONF_IP_ADDRESS
import voluptuous as vol

class FCUConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configuration flow for the Fan Coil Unit Integration."""

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step where users provide device details."""
        if user_input is not None:
            # Create the configuration entry with user-provided device name and IP
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        # Show the form for entering device details
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_IP_ADDRESS): str,
            }),
        )