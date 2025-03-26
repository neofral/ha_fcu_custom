"""Constants for the FCU integration."""
from homeassistant.const import CONF_NAME, CONF_IP_ADDRESS
from homeassistant.const import Platform

DOMAIN = "fcu"
TOKEN_UPDATE_INTERVAL = 180  # Seconds (3 minutes)
PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]