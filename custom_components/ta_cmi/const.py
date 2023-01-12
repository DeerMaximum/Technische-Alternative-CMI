"""Constants for the Technische Alternative C.M.I. integration."""
from __future__ import annotations

from datetime import timedelta
from logging import Logger, getLogger

from ta_cmi import ChannelType
from homeassistant.components.sensor import SensorDeviceClass

_LOGGER: Logger = getLogger(__package__)

SCAN_INTERVAL: timedelta = timedelta(minutes=10)
DEVICE_DELAY: int = 61

DOMAIN: str = "ta_cmi"

DEVICE_TYPE: str = "device_type"

CONF_SCAN_INTERVAL = "scasn_interval"

CONF_DEVICES: str = "devices"
CONF_DEVICE_ID: str = "id"
CONF_DEVICE_FETCH_MODE: str = "fetchmode"
CONF_DEVICE_TYPE: str = "type"

CONF_CHANNELS: str = "channels"
CONF_CHANNELS_TYPE: str = "type"
CONF_CHANNELS_ID: str = "id"
CONF_CHANNELS_NAME: str = "name"
CONF_CHANNELS_DEVICE_CLASS: str = "device_class"


DEFAULT_DEVICE_CLASS_MAP: dict[str, SensorDeviceClass] = {
    "°C": SensorDeviceClass.TEMPERATURE,
    "K": SensorDeviceClass.TEMPERATURE,
    "A": SensorDeviceClass.CURRENT,
    "kWh": SensorDeviceClass.ENERGY,
    "m³": SensorDeviceClass.GAS,
    "%": SensorDeviceClass.HUMIDITY,
    "lx": SensorDeviceClass.ILLUMINANCE,
    "W": SensorDeviceClass.POWER,
    "mbar": SensorDeviceClass.PRESSURE,
    "V": SensorDeviceClass.VOLTAGE,
}

TYPE_BINARY = "binary"
TYPE_SENSOR = "sensor"

DEVICE_TYPE_STRING_MAP: dict[ChannelType, str] = {
    ChannelType.INPUT: "input",
    ChannelType.OUTPUT: "output",
    ChannelType.DL_BUS: "dl-bus",
    ChannelType.SYSTEM_VALUES_GENERAL: "system general",
    ChannelType.SYSTEM_VALUES_DATE: "system date",
    ChannelType.SYSTEM_VALUES_TIME: "system time",
    ChannelType.SYSTEM_VALUES_SUN: "system sun",
    ChannelType.SYSTEM_VALUES_E_POWER: "electrical power",
    ChannelType.NETWORK_ANALOG: "network analog",
    ChannelType.NETWORK_DIGITAL: "network digital",
    ChannelType.MBUS: "mbus",
    ChannelType.MODBUS: "modbus",
    ChannelType.KNX: "knx",
    ChannelType.ANALOG_LOGGING: "analog logging",
    ChannelType.DIGITAL_LOGGING: "digital logging",
}
