"""Constants for the FCU integration."""
from homeassistant.const import CONF_NAME, CONF_IP_ADDRESS, CONF_USERNAME, CONF_PASSWORD
from homeassistant.const import Platform
from datetime import timedelta

DOMAIN = "fcu"
TOKEN_UPDATE_INTERVAL = 180  # Seconds (3 minutes)
SCAN_INTERVAL = timedelta(seconds=30)  # Update every 30 seconds
PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]

# Add sensor constants
DEVICE_STATUS_SENSOR = "device_status"
ERROR_INDEX_SENSOR = "error_index"

# Extra configuration parameters
CONF_T1D = "t1d"
CONF_T2D = "t2d"
CONF_T3D = "t3d"
CONF_T4D = "t4d"
CONF_SHUTDOWN_DELAY = "shutdown_delay"

DEFAULT_T1D = 0.3
DEFAULT_T2D = 0.3
DEFAULT_T3D = 0.3
DEFAULT_T4D = 0.3
DEFAULT_SHUTDOWN_DELAY = 30