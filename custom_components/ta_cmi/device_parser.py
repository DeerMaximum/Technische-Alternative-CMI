"""Parser to parse device data."""
from __future__ import annotations
from typing import Any

from homeassistant.const import CONF_API_VERSION, STATE_OFF, STATE_ON
from ta_cmi import Channel, Device, ChannelType

from .const import (
    CONF_CHANNELS,
    CONF_CHANNELS_DEVICE_CLASS,
    CONF_CHANNELS_ID,
    CONF_CHANNELS_NAME,
    CONF_CHANNELS_TYPE,
    CONF_DEVICE_FETCH_MODE,
    DEVICE_TYPE,
    TYPE_ANALOG_LOG,
    TYPE_ANALOG_LOG_BINARY,
    TYPE_DIGITAL_LOG,
    TYPE_DIGITAL_LOG_BINARY,
    TYPE_INPUT,
    TYPE_INPUT_BINARY,
    TYPE_OUTPUT,
    TYPE_OUTPUT_BINARY,
    TYPE_DL_BUS,
    TYPE_DL_BUS_BINARY,
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
            TYPE_INPUT: {},
            TYPE_OUTPUT: {},
            TYPE_ANALOG_LOG: {},
            TYPE_DIGITAL_LOG: {},
            TYPE_DL_BUS: {},
            TYPE_INPUT_BINARY: {},
            TYPE_OUTPUT_BINARY: {},
            TYPE_ANALOG_LOG_BINARY: {},
            TYPE_DIGITAL_LOG_BINARY: {},
            TYPE_DL_BUS_BINARY: {},
            CONF_API_VERSION: self.device.api_version,
            DEVICE_TYPE: self.device.get_device_type(),
        }

        data = self._parse_channels(
            data,
            self.device.get_channels(ChannelType.INPUT),
            "input",
            TYPE_INPUT,
            TYPE_INPUT_BINARY,
        )
        data = self._parse_channels(
            data,
            self.device.get_channels(ChannelType.OUTPUT),
            "output",
            TYPE_OUTPUT,
            TYPE_OUTPUT_BINARY,
        )
        data = self._parse_channels(
            data,
            self.device.get_channels(ChannelType.ANALOG_LOGGING),
            "analog logging",
            TYPE_ANALOG_LOG,
            TYPE_ANALOG_LOG_BINARY,
        )
        data = self._parse_channels(
            data,
            self.device.get_channels(ChannelType.DIGITAL_LOGGING),
            "digital logging",
            TYPE_DIGITAL_LOG,
            TYPE_DIGITAL_LOG_BINARY,
        )
        data = self._parse_channels(
            data,
            self.device.get_channels(ChannelType.DL_BUS),
            "dl-bus",
            TYPE_DL_BUS,
            TYPE_DL_BUS_BINARY,
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
        self, channel_id: int, channel_type: str
    ) -> tuple[str | None, str | None]:
        """Get the channel customization."""
        name = None
        device_class = None

        for i in self.channel_options:
            if (
                channel_id == i[CONF_CHANNELS_ID]
                and i[CONF_CHANNELS_TYPE] == channel_type
            ):
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
    def _format_channel_type(channel_type: str) -> str:
        return channel_type.title().replace(" ", "-")

    def _parse_channels(
        self,
        base_data: dict[str, Any],
        target_channels: dict[int, Channel],
        channel_type: str,
        channel_type_sensor: str,
        channel_type_bin_sensor: str,
    ) -> dict[str, Any]:

        """Parse a channel type."""
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

            channel_platform = channel_type_sensor

            if self._is_channel_binary(channel):
                channel_platform = channel_type_bin_sensor

            base_data[channel_platform][channel_id] = {
                "channel": channel,
                "value": value,
                "mode": self._format_channel_type(channel_type),
                "unit": unit,
                "name": name,
                "device_class": device_class,
            }

        return base_data
