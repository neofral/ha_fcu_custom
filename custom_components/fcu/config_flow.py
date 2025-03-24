"""Config flow for FCU integration."""
import logging
import voluptuous as vol
import ipaddress
from homeassistant import config_entries
from homeassistant.exceptions import ConfigEntryNotReady

_LOGGER = logging.getLogger(__name__)

DOMAIN = "fcu"

class FCUConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FCU."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            ip_address = user_input["ip_address"]
            name = user_input["name"]
            # Validate IP and Name
            try:
                ipaddress.ip_address(ip_address)
                await self.async_set_unique_id(ip_address)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=name, data=user_input)
            except ValueError:
                errors["ip_address"] = "invalid_ip"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("ip_address"): str,
            }),
            errors=errors,
        )