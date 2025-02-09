"""The Technische Alternative C.M.I. integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import time
from typing import Any

from async_timeout import timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from ta_cmi import CMIAPI, ApiError, Device, InvalidCredentialsError, RateLimitError

from .const import (
    _LOGGER,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_DEVICES,
    CONF_SCAN_INTERVAL,
    DEVICE_DELAY,
    DOMAIN,
    SCAN_INTERVAL,
)
from .device_parser import DeviceParser

PLATFORMS: list[str] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def custom_sleep(delay: int) -> None:
    """Custom sleep function to prevent Home Assistant from canceling."""
    start = time.time()
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        elapsed = time.time() - start
        _LOGGER.debug(
            "Sleep cancelled after %s. Sleep remaining time: %s",
            elapsed,
            delay - elapsed,
        )
        await asyncio.sleep(delay - elapsed)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""
    host: str = entry.data[CONF_HOST]
    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]

    devices: dict[str, Any] = entry.data[CONF_DEVICES]

    update_interval: timedelta = SCAN_INTERVAL

    if entry.data.get(CONF_SCAN_INTERVAL, None) is not None:
        update_interval = timedelta(minutes=entry.data.get(CONF_SCAN_INTERVAL))

    coordinator = CMIDataUpdateCoordinator(
        hass, host, username, password, devices, update_interval
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    hass.config_entries.async_update_entry(entry, data=entry.options)
    await hass.config_entries.async_reload(entry.entry_id)


class CMIDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching CMI data."""

    _coe_sleep_function = asyncio.sleep

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

        cmi_api = CMIAPI(host, username, password, async_get_clientsession(hass))

        for dev_raw in devices:
            device_id: str = dev_raw[CONF_DEVICE_ID]
            device: Device = Device(
                device_id, cmi_api, CMIDataUpdateCoordinator._coe_sleep_function
            )

            if CONF_DEVICE_TYPE in dev_raw:
                device.set_device_type(dev_raw[CONF_DEVICE_TYPE])

            self.devices.append(device)
            self.devices_raw[device_id] = dev_raw

        _LOGGER.debug("Used update interval: %s", update_interval)

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data."""
        try:
            return_data: dict[str, Any] = {}
            for device in self.devices:
                _LOGGER.debug("Try to update device: %s", device.id)

                async with timeout((DEVICE_DELAY * 2) + 5):
                    await device.update()

                parser: DeviceParser = DeviceParser(device, self.devices_raw[device.id])

                return_data[device.id] = parser.parse()

                return_data[device.id][CONF_HOST] = self.host

                if len(self.devices) != 1:
                    _LOGGER.debug(
                        f"Sleep mode for {DEVICE_DELAY} seconds to prevent rate limiting"
                    )
                    await custom_sleep(DEVICE_DELAY)

            return return_data
        except (InvalidCredentialsError, RateLimitError, ApiError) as err:
            _LOGGER.warning("Update failed with error: %s", str(err))
            _LOGGER.debug(
                "Waiting %s seconds to prevent retrying with an rate limit error",
                DEVICE_DELAY,
            )
            await custom_sleep(DEVICE_DELAY)
            raise UpdateFailed(err) from err
