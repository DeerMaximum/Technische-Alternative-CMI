"""The Technische Alternative C.M.I. integration."""
from __future__ import annotations

import asyncio
from typing import Any

from async_timeout import timeout
from ta_cmi import ApiError, Channel, Device, InvalidCredentialsError, RateLimitError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    STATE_OFF,
    STATE_ON,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    _LOGGER,
    CONF_CHANNELS,
    CONF_CHANNELS_DEVICE_CLASS,
    CONF_CHANNELS_ID,
    CONF_CHANNELS_NAME,
    CONF_CHANNELS_TYPE,
    CONF_DEVICE_FETCH_MODE,
    CONF_DEVICE_ID,
    CONF_DEVICES,
    CONF_DEVICE_TYPE,
    DEVICE_DELAY,
    DOMAIN,
    SCAN_INTERVAL,
    TYPE_INPUT,
    TYPE_OUTPUT,
    TYPE_INPUT_BINARY,
    TYPE_OUTPUT_BINARY,
    TYPE_ANALOG_LOG,
    TYPE_DIGITAL_LOG,
    TYPE_ANALOG_LOG_BINARY,
    TYPE_DIGITAL_LOG_BINARY,
)

PLATFORMS: list[str] = [Platform.SENSOR, Platform.BINARY_SENSOR]

API_VERSION: str = "api_version"
DEVICE_TYPE: str = "device_type"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""
    host: str = entry.data[CONF_HOST]
    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]

    devices: dict[str, Any] = entry.data[CONF_DEVICES]

    coordinator = CMIDataUpdateCoordinator(hass, host, username, password, devices)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


class CMIDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching CMI data."""

    def __init__(
            self,
            hass: HomeAssistant,
            host: str,
            username: str,
            password: str,
            devices: Any,
    ) -> None:
        """Initialize."""
        self.devices_raw: dict[str, Any] = {}

        self.devices: list[Device] = []
        self.host = host

        for dev_raw in devices:
            device_id: str = dev_raw[CONF_DEVICE_ID]
            device: Device = Device(
                device_id, host, username, password, async_get_clientsession(hass)
            )

            if CONF_DEVICE_TYPE in dev_raw:
                device.set_device_type(dev_raw[CONF_DEVICE_TYPE])

            self.devices.append(device)
            self.devices_raw[device_id] = dev_raw

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data."""
        try:
            return_data: dict[str, Any] = {}
            for device in self.devices:
                async with timeout(10):
                    await device.update()

                return_data[device.id] = _parse_data(
                    device, self.devices_raw[device.id]
                )

                return_data[device.id][CONF_HOST] = self.host

                if len(self.devices) != 1:
                    await asyncio.sleep(DEVICE_DELAY)

            return return_data
        except (InvalidCredentialsError, RateLimitError, ApiError) as err:
            raise UpdateFailed(err) from err


def _parse_data(device: Device, device_raw: dict[str, Any]) -> dict[str, Any]:
    """Parse data."""
    data: dict[str, Any] = {
        TYPE_INPUT: {},
        TYPE_OUTPUT: {},
        TYPE_ANALOG_LOG: {},
        TYPE_DIGITAL_LOG: {},
        TYPE_INPUT_BINARY: {},
        TYPE_OUTPUT_BINARY: {},
        TYPE_ANALOG_LOG_BINARY: {},
        TYPE_DIGITAL_LOG_BINARY: {},
        API_VERSION: device.apiVersion,
        DEVICE_TYPE: device.getDeviceType(),
    }

    fetchmode: str = device_raw[CONF_DEVICE_FETCH_MODE]
    channel_options: list = []

    for channel in device_raw[CONF_CHANNELS]:
        channel_options.append(
            {
                CONF_CHANNELS_ID: channel[CONF_CHANNELS_ID],
                CONF_CHANNELS_TYPE: channel[CONF_CHANNELS_TYPE],
                CONF_CHANNELS_NAME: channel[CONF_CHANNELS_NAME],
                CONF_CHANNELS_DEVICE_CLASS: channel[CONF_CHANNELS_DEVICE_CLASS],
            }
        )

    data = _parse_channel(data, device.inputs, "input", "Input", channel_options, fetchmode, TYPE_INPUT,
                          TYPE_INPUT_BINARY)
    data = _parse_channel(data, device.outputs, "output", "Output", channel_options, fetchmode, TYPE_OUTPUT,
                          TYPE_OUTPUT_BINARY)
    data = _parse_channel(data, device.analog_logging, "analog logging", "Analog-Logging", channel_options,
                          fetchmode, TYPE_ANALOG_LOG, TYPE_ANALOG_LOG_BINARY)
    data = _parse_channel(data, device.digital_logging, "digital logging", "Digital-Logging", channel_options,
                          fetchmode, TYPE_DIGITAL_LOG, TYPE_DIGITAL_LOG_BINARY)

    return data


def _parse_channel(base_data: dict[str, Any], target_channels: dict[int, Channel], channel_type: str,
                   channel_type_full: str,
                   all_channel_options: list, fetchmode: str, channel_sensor: str, channel_bin_sensor: str):
    for channel_id in target_channels:
        name = None
        device_class = None

        for i in all_channel_options:
            if (
                    channel_id == i[CONF_CHANNELS_ID]
                    and i[CONF_CHANNELS_TYPE] == channel_type
            ):
                name = i[CONF_CHANNELS_NAME]
                if len(i[CONF_CHANNELS_DEVICE_CLASS]) != 0:
                    device_class = i[CONF_CHANNELS_DEVICE_CLASS]
                break

        if (name is not None and fetchmode == "defined") or fetchmode == "all":
            channel: Channel = target_channels[channel_id]

            value, unit = format_input(channel)

            channel_platform = channel_sensor

            if (
                    channel.getUnit() == "On/Off"
                    or channel.getUnit() == "No/Yes"
            ):
                channel_platform = channel_bin_sensor

            base_data[channel_platform][channel_id] = {
                "channel": channel,
                "value": value,
                "mode": channel_type_full,
                "unit": unit,
                "name": name,
                "device_class": device_class,
            }

    return base_data


def format_input(channel: Channel) -> tuple[str, str]:
    """Format the unit and value."""
    unit: str = channel.getUnit()
    value: str = channel.value

    if unit == "On/Off":
        unit = ""
        if bool(value):
            value = STATE_ON
        else:
            value = STATE_OFF

    if unit == "No/Yes":
        unit = ""
        if bool(value):
            value = "yes"
        else:
            value = "no"

    return value, unit
