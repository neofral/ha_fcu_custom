"""Fan Coil Unit integration."""
import asyncio
import logging
import json
import ast
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady
import aiohttp

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the FCU component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_fetch_data(ip_address):
    """Fetch data from device."""
    _LOGGER.debug("Fetching data from %s", ip_address)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://{ip_address}/wifi/shortstatus",
                timeout=aiohttp.ClientTimeout(total=8)
            ) as response:
                text = await response.text()
                _LOGGER.debug("Raw response: %s", text)
                if response.status != 200:
                    raise UpdateFailed(f"Error {response.status}")
                data = text.replace("'", '"')
                try:
                    parsed_data = json.loads(data)
                    # Ensure these values are properly parsed
                    parsed_data["device_status"] = str(parsed_data.get("device_status", "0"))
                    parsed_data["error_index"] = str(parsed_data.get("error_index", "0"))
                    _LOGGER.debug("Parsed data: %s", parsed_data)
                    return parsed_data
                except json.JSONDecodeError:
                    parsed_data = ast.literal_eval(text)
                    parsed_data["device_status"] = str(parsed_data.get("device_status", "0"))
                    parsed_data["error_index"] = str(parsed_data.get("error_index", "0"))
                    return parsed_data
    except Exception as ex:
        _LOGGER.error("Error fetching data: %s", str(ex))
        raise

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FCU from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=entry.data["name"],
        update_method=lambda: async_fetch_data(entry.data["ip_address"]),
        update_interval=timedelta(seconds=30),  # Update every 30 seconds
    )

    try:
        # Do initial refresh
        await coordinator.async_refresh()
    except Exception as ex:
        _LOGGER.error("Failed to fetch initial data: %s", ex)
        raise ConfigEntryNotReady from ex

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "name": entry.data["name"],
        "ip_address": entry.data["ip_address"],
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)