"""Constants for the FCU integration."""
from homeassistant.const import CONF_NAME, CONF_IP_ADDRESS, CONF_USERNAME, CONF_PASSWORD
from homeassistant.const import Platform
from datetime import timedelta

DOMAIN = "fcu"
TOKEN_UPDATE_INTERVAL = 180  # Seconds (3 minutes)
SCAN_INTERVAL = timedelta(seconds=30)  # Update interval for the climate entity
PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]

# Add sensor constants
DEVICE_STATUS_SENSOR = "device_status"
ERROR_INDEX_SENSOR = "error_index"