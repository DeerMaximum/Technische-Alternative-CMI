"""Parser to parse device data."""
from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_API_VERSION, STATE_OFF, STATE_ON
from ta_cmi import Channel, ChannelType, Device

from .const import (
    CONF_CHANNELS,
    CONF_CHANNELS_DEVICE_CLASS,
    CONF_CHANNELS_ID,
    CONF_CHANNELS_NAME,
    CONF_CHANNELS_TYPE,
    CONF_DEVICE_FETCH_MODE,
    DEVICE_TYPE,
    DEVICE_TYPE_STRING_MAP,
    TYPE_BINARY,
    TYPE_SENSOR,
)


class DeviceParser:
    """Class to parse a devices."""

    def __init__(self, device: Device, device_raw: dict[str, Any]) -> None:
        """Initialize."""
        self.device = device
        self.device_raw = device_raw

        self.fetch_mode: str = device_raw[CONF_DEVICE_FETCH_MODE]
        self.channel_options: list = self._parse_channel_options()

    def parse(self) -> dict[str, Any]:
        """Parse the device."""
        data: dict[str, Any] = {
            TYPE_BINARY: {},
            TYPE_SENSOR: {},
            CONF_API_VERSION: self.device.api_version,
            DEVICE_TYPE: self.device.get_device_type(),
        }

        for channel_type in ChannelType:
            if not self.device.has_channel_type(channel_type):
                continue

            data = self._parse_channels(
                data, self.device.get_channels(channel_type), channel_type
            )

        return data

    def _parse_channel_options(self) -> list:
        """Parse the channel options."""
        options: list = []

        for channel in self.device_raw[CONF_CHANNELS]:
            options.append(
                {
                    CONF_CHANNELS_ID: channel[CONF_CHANNELS_ID],
                    CONF_CHANNELS_TYPE: channel[CONF_CHANNELS_TYPE],
                    CONF_CHANNELS_NAME: channel[CONF_CHANNELS_NAME],
                    CONF_CHANNELS_DEVICE_CLASS: channel[CONF_CHANNELS_DEVICE_CLASS],
                }
            )

        return options

    def _get_channel_customization(
        self, channel_id: int, channel_type: ChannelType
    ) -> tuple[str | None, str | None]:
        """Get the channel customization."""
        name = None
        device_class = None

        for i in self.channel_options:
            if channel_id == i[CONF_CHANNELS_ID] and i[
                CONF_CHANNELS_TYPE
            ] == DEVICE_TYPE_STRING_MAP.get(channel_type, ""):
                name = i[CONF_CHANNELS_NAME]
                if len(i[CONF_CHANNELS_DEVICE_CLASS]) != 0:
                    device_class = i[CONF_CHANNELS_DEVICE_CLASS]
                break

        return name, device_class

    @staticmethod
    def _format_input(target_channel: Channel) -> tuple[str, str]:
        """Format the unit and value."""
        unit: str = target_channel.get_unit()
        value: str = target_channel.value

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

    @staticmethod
    def _is_channel_binary(channel: Channel) -> bool:
        return channel.get_unit() == "On/Off" or channel.get_unit() == "No/Yes"

    @staticmethod
    def _format_channel_type(channel_type: ChannelType) -> str:
        type_string: str = DEVICE_TYPE_STRING_MAP.get(channel_type, "")
        return type_string.title().replace(" ", "-")

    def _parse_channels(
        self,
        base_data: dict[str, Any],
        target_channels: dict[int, Channel],
        channel_type: ChannelType,
    ) -> dict[str, Any]:
        """Parse a channel type."""

        # Dict structure
        # SENSOR_TYPE CHANNEL_TYPE CHANNEL_ID

        for channel_id in target_channels:
            name, device_class = self._get_channel_customization(
                channel_id, channel_type
            )

            if not (
                (name is not None and self.fetch_mode == "defined")
                or self.fetch_mode == "all"
            ):
                continue

            channel: Channel = target_channels[channel_id]

            value, unit = self._format_input(target_channel=channel)

            sensor_type: str = TYPE_SENSOR

            if self._is_channel_binary(channel):
                sensor_type: str = TYPE_BINARY

            if base_data[sensor_type].get(channel_type.name, None) is None:
                base_data[sensor_type][channel_type.name] = {}

            base_data[sensor_type][channel_type.name][channel_id] = {
                "channel": channel,
                "value": value,
                "mode": self._format_channel_type(channel_type),
                "unit": unit,
                "name": name,
                "device_class": device_class,
            }

        return base_data
