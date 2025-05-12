"""Config flow for FCU integration."""
import voluptuous as vol
import aiohttp
import logging
import hashlib

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_IP_ADDRESS, CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): str,
    vol.Required(CONF_IP_ADDRESS): str,
    vol.Required("use_auth", default=True): bool,
    vol.Optional(CONF_USERNAME, default="admin"): str,
    vol.Optional(CONF_PASSWORD): str,
})

def hash_password(password: str) -> str:
    """Hash password using SHA1."""
    return hashlib.sha1(password.encode()).hexdigest()

class FCUConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FCU integration."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_NAME])
            self._abort_if_unique_id_configured()

            try:
                if ":" in user_input[CONF_IP_ADDRESS]:
                    errors["base"] = "invalid_ip"
                else:
                    # Only hash password if auth is enabled
                    if user_input.get("use_auth", True):
                        if CONF_PASSWORD in user_input:
                            user_input[CONF_PASSWORD] = hash_password(user_input[CONF_PASSWORD])
                    else:
                        # Remove credentials if auth is disabled
                        user_input.pop(CONF_USERNAME, None)
                        user_input.pop(CONF_PASSWORD, None)
                    
                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data=user_input
                    )
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Adjust schema based on auth selection
        schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_IP_ADDRESS): str,
            vol.Required("use_auth", default=True): bool,
        })

        if user_input is None or user_input.get("use_auth", True):
            schema = schema.extend({
                vol.Required(CONF_USERNAME, default="admin"): str,
                vol.Required(CONF_PASSWORD): str,
            })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
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
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            # Handle auth mode changes
            if "use_auth" in user_input:
                update_data = {}
                if not user_input["use_auth"]:
                    # Remove auth credentials when disabling auth
                    update_data = {
                        CONF_USERNAME: None,
                        CONF_PASSWORD: None,
                    }
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, **update_data}
                )
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema({
            vol.Required(
                "use_auth",
                default=self.config_entry.options.get(
                    "use_auth", 
                    self.config_entry.data.get("use_auth", True)
                )
            ): bool,
            vol.Optional(
                "target_temp_high",
                default=self.config_entry.options.get("target_temp_high", 0.3)
            ): vol.Coerce(float),
            vol.Optional(
                "target_temp_low",
                default=self.config_entry.options.get("target_temp_low", 0.3)
            ): vol.Coerce(float),
        })

        return self.async_show_form(
            step_id="init", 
            data_schema=options_schema
        )