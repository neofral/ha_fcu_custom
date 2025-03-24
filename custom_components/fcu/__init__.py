"""FCU integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

DOMAIN = "fcu"
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FCU from a config entry."""
    _LOGGER.info("Setting up FCU integration for device: %s", entry.data["name"])
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    hass.config_entries.async_setup_platforms(entry, ["climate"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading FCU integration for device: %s", entry.data["name"])
    hass.config_entries.async_unload_platforms(entry, ["climate"])
    hass.data[DOMAIN].pop(entry.entry_id)
    return True