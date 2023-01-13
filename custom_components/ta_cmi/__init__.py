"""The Technische Alternative C.M.I. integration."""
from __future__ import annotations

from types import MappingProxyType

import asyncio
from typing import Any

from datetime import timedelta

from async_timeout import timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from ta_cmi import ApiError, Device, InvalidCredentialsError, RateLimitError

from .const import (
    _LOGGER,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_DEVICES,
    DEVICE_DELAY,
    DOMAIN,
    SCAN_INTERVAL,
    CONF_SCAN_INTERVAL,
)
from .device_parser import DeviceParser

PLATFORMS: list[str] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""
    host: str = entry.data[CONF_HOST]
    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]

    devices: dict[str, Any] = entry.data[CONF_DEVICES]

    update_interval: timedelta = SCAN_INTERVAL

    if entry.data.get(CONF_SCAN_INTERVAL, None) is not None:
        update_interval = timedelta(entry.data.get(CONF_SCAN_INTERVAL))

    coordinator = CMIDataUpdateCoordinator(
        hass, host, username, password, devices, update_interval
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    config = dict(entry.data)
    if entry.options:
        config.update(entry.options)
        entry.data = MappingProxyType(config)

    await hass.config_entries.async_reload(entry.entry_id)


class CMIDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching CMI data."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        username: str,
        password: str,
        devices: Any,
        update_interval: timedelta,
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

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data."""
        try:
            return_data: dict[str, Any] = {}
            for device in self.devices:
                _LOGGER.debug("Try to update device: %s", device.id)

                async with timeout(10):
                    await device.update()

                parser: DeviceParser = DeviceParser(device, self.devices_raw[device.id])

                return_data[device.id] = parser.parse()

                return_data[device.id][CONF_HOST] = self.host

                if len(self.devices) != 1:
                    _LOGGER.debug("Wait for 61 seconds to prevent rate limiting")
                    await asyncio.sleep(DEVICE_DELAY)

            return return_data
        except (InvalidCredentialsError, RateLimitError, ApiError) as err:
            raise UpdateFailed(err) from err
