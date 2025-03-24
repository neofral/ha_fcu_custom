"""Initialize the ha_fcu_custom integration."""
import logging
import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ha_fcu_custom"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    hass.config_entries.async_setup_platforms(entry, ["climate"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an integration entry."""
    return await hass.config_entries.async_unload_platforms(entry, ["climate"])