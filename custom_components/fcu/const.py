"""Constants for the FCU integration."""
from homeassistant.const import CONF_NAME, CONF_IP_ADDRESS

DOMAIN = "fcu"
TOKEN_UPDATE_INTERVAL = 180  # Seconds (3 minutes)

# Sensor names
ROOM_TEMP_SENSOR = "room_temperature"
WATER_TEMP_SENSOR = "water_temperature"

# Platforms
PLATFORMS = ["climate", "sensor"]