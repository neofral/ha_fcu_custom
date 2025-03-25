"""FCU Sensors."""
import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

TOKEN_UPDATE_INTERVAL = timedelta(seconds=60)
STATUS_UPDATE_INTERVAL = timedelta(seconds=20)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up FCU sensors from a config entry."""
    name = entry.data["name"]
    ip_address = entry.data["ip_address"]

    token_coordinator = TokenUpdateCoordinator(hass, ip_address)
    status_coordinator = StatusUpdateCoordinator(hass, ip_address)

    await token_coordinator.async_config_entry_first_refresh()
    await status_coordinator.async_config_entry_first_refresh()

    async_add_entities([
        FCUTokenSensor(name, token_coordinator),
        FCUStatusSensor(name, status_coordinator),
    ])


class TokenUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch the authentication token."""

    def __init__(self, hass, ip_address):
        super().__init__(
            hass,
            _LOGGER,
            name="FCU Token Update",
            update_interval=TOKEN_UPDATE_INTERVAL,
        )
        self._ip_address = ip_address
        self._token = None

    async def _async_update_data(self):
        """Fetch the latest token."""
        try:
            _LOGGER.info("Updating token for device at %s", self._ip_address)
            session = async_get_clientsession(self.hass)
            async with session.post(
                f"http://{self._ip_address}/login.htm",
                headers={
                    "X-Requested-With": "myApp",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data="username=admin&password=d033e22ae348aeb5660fc2140aec35850c4da997",
            ) as response:
                response.raise_for_status()
                self._token = (await response.text()).strip()
            if not self._token:
                raise ValueError("Failed to retrieve access token")
            return self._token
        except Exception as e:
            raise UpdateFailed(f"Failed to update token: {e}")


class StatusUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch the device status."""

    def __init__(self, hass, ip_address):
        super().__init__(
            hass,
            _LOGGER,
            name="FCU Status Update",
            update_interval=STATUS_UPDATE_INTERVAL,
        )
        self._ip_address = ip_address

    async def _async_update_data(self):
        """Fetch the latest status."""
        try:
            _LOGGER.info("Updating status for device at %s", self._ip_address)
            session = async_get_clientsession(self.hass)
            async with session.get(
                f"http://{self._ip_address}/status",
                headers={"Authorization": f"Bearer {self.data}"},
            ) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            raise UpdateFailed(f"Failed to update status: {e}")


class FCUTokenSensor(Entity):
    """Sensor to display the authentication token."""

    def __init__(self, name, coordinator):
        self._name = f"{name} Token"
        self._coordinator = coordinator

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._coordinator.data

    @property
    def should_poll(self):
        return False

    async def async_update(self):
        await self._coordinator.async_request_refresh()


class FCUStatusSensor(Entity):
    """Sensor to display the device status."""

    def __init__(self, name, coordinator):
        self._name = f"{name} Status"
        self._coordinator = coordinator

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._coordinator.data

    @property
    def should_poll(self):
        return False

    async def async_update(self):
        await self._coordinator.async_request_refresh()
