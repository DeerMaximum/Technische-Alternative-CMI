"""Constants for the Technische Alternative C.M.I. integration."""
from __future__ import annotations

from datetime import timedelta
from logging import Logger, getLogger

_LOGGER: Logger = getLogger(__package__)

SCAN_INTERVAL: timedelta = timedelta(minutes=10)
DEVICE_DELAY: int = 61

DOMAIN: str = "ta_cmi"

DEVICE_TYPE: str = "device_type"

CONF_FETCH_CAN_LOGGING: str = "fetch_can_logging"

CONF_DEVICES: str = "devices"
CONF_DEVICE_ID: str = "id"
CONF_DEVICE_FETCH_MODE: str = "fetchmode"
CONF_DEVICE_TYPE: str = "type"

CONF_CHANNELS: str = "channels"
CONF_CHANNELS_TYPE: str = "type"
CONF_CHANNELS_ID: str = "id"
CONF_CHANNELS_NAME: str = "name"
CONF_CHANNELS_DEVICE_CLASS: str = "device_class"

TYPE_INPUT = "I"
TYPE_OUTPUT = "O"
TYPE_INPUT_BINARY = "IB"
TYPE_OUTPUT_BINARY = "OB"
TYPE_ANALOG_LOG = "AL"
TYPE_DIGITAL_LOG = "DL"
TYPE_ANALOG_LOG_BINARY = "ALB"
TYPE_DIGITAL_LOG_BINARY = "DLB"

DEFAULT_DEVICE_CLASS_MAP: dict[str, str] = {
    "°C": "temperature",
    "K": "temperature",
    "A": "current",
    "kWh": "energy",
    "m³": "gas",
    "%": "humidity",
    "lx": "illuminance",
    "W": "power",
    "mbar": "pressure",
    "V": "voltage",
}
