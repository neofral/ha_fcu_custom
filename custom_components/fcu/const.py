"""Constants for the FCU integration."""
from homeassistant.const import CONF_NAME, CONF_IP_ADDRESS, CONF_USERNAME, CONF_PASSWORD
from homeassistant.const import Platform
from datetime import timedelta

DOMAIN = "fcu"
TOKEN_UPDATE_INTERVAL = 180  # Seconds (3 minutes)
<<<<<<< HEAD
SCAN_INTERVAL = timedelta(seconds=30)  # Update every 30 seconds
=======
SCAN_INTERVAL = timedelta(seconds=30)  # Update interval for the climate entity
>>>>>>> d50f2c95bd5a4445f837654d93ba8c88fbed760c
PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]

# Add sensor constants
DEVICE_STATUS_SENSOR = "device_status"
ERROR_INDEX_SENSOR = "error_index"