"""The Technische Alternative C.M.I. integration."""
from __future__ import annotations

import asyncio
from typing import Any

from async_timeout import timeout
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
from ta_cmi import ApiError, Channel, Device, InvalidCredentialsError, RateLimitError

from .const import (
    _LOGGER,
    CONF_CHANNELS,
    CONF_CHANNELS_DEVICE_CLASS,
    CONF_CHANNELS_ID,
    CONF_CHANNELS_NAME,
    CONF_CHANNELS_TYPE,
    CONF_DEVICE_FETCH_MODE,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_DEVICES,
    DEVICE_DELAY,
    DOMAIN,
    SCAN_INTERVAL,
    TYPE_ANALOG_LOG,
    TYPE_ANALOG_LOG_BINARY,
    TYPE_DIGITAL_LOG,
    TYPE_DIGITAL_LOG_BINARY,
    TYPE_INPUT,
    TYPE_INPUT_BINARY,
    TYPE_OUTPUT,
    TYPE_OUTPUT_BINARY,
)
from .device_parser import DeviceParser

PLATFORMS: list[str] = [Platform.SENSOR, Platform.BINARY_SENSOR]


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

                parser: DeviceParser = DeviceParser(device, self.devices_raw[device.id])

                return_data[device.id] = parser.parse()

                return_data[device.id][CONF_HOST] = self.host

                if len(self.devices) != 1:
                    await asyncio.sleep(DEVICE_DELAY)

            return return_data
        except (InvalidCredentialsError, RateLimitError, ApiError) as err:
            raise UpdateFailed(err) from err
