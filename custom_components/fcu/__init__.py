"""Fan Coil Unit integration."""
import asyncio
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import aiohttp
import logging

from .const import DOMAIN, PLATFORMS, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the FCU component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FCU from a config entry."""
    ip_address = entry.data["ip_address"]

    async def async_fetch_data():
        """Fetch data from the device."""
        url = f"http://{ip_address}/wifi/shortstatus"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        return await response.json(content_type=None)
                    raise UpdateFailed(f"Invalid response from device: {response.status}")
        except Exception as ex:
            raise UpdateFailed(f"Error fetching data: {ex}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"FCU {entry.data['name']}",
        update_method=async_fetch_data,
        update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.data["name"]] = coordinator

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        entry.async_on_unload(entry.add_update_listener(update_listener))
        return True
    except Exception as ex:
        _LOGGER.error("Error setting up FCU integration: %s", ex)
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)