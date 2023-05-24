"""Diagnostics support for the Technische Alternative C.M.I. integration."""
from copy import deepcopy
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry, DeviceRegistry

from . import CMIDataUpdateCoordinator
from .const import CONF_DEVICES, CONF_SCAN_INTERVAL, DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return _async_get_diagnostics(hass, entry)


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device entry."""
    return _async_get_diagnostics(hass, entry, device)


@callback
def _async_get_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device: DeviceEntry | None = None,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: CMIDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    device_registry = dr.async_get(hass)

    data = {
        "host": entry.data[CONF_HOST],
        "update_interval": entry.data[CONF_SCAN_INTERVAL],
        "disabled_by": entry.disabled_by,
        "disabled_polling": entry.pref_disable_polling,
        "device_config": entry.data[CONF_DEVICES],
    }

    if device:
        device_id = next(iter(device.identifiers))[1]
        data |= _async_device_as_dict(hass, device_registry, coordinator, device_id)
    else:
        data.update(
            devices=[
                _async_device_as_dict(hass, device_registry, coordinator, device_id)
                for device_id in coordinator.data.keys()
            ]
        )

    return data


@callback
def _async_device_as_dict(
    hass: HomeAssistant,
    device_registry: DeviceRegistry,
    coordinator: CMIDataUpdateCoordinator,
    device_id: str,
) -> dict[str, Any]:
    """Represent a device as a dictionary."""

    device = device_registry.async_get_device(identifiers={(DOMAIN, device_id)})

    last_state = deepcopy(coordinator.data[device_id])
    remove_channel_from_dict(last_state)

    # Base device information, without sensitive information.
    data = {
        "name": device.name,
        "model": device.model if hasattr(device, "model") else None,
        "sw_version": device.sw_version,
        "configuration_url": device.configuration_url,
        "state": last_state,
    }

    return data


def remove_channel_from_dict(d: dict[str, Any]):
    if isinstance(d, list):
        for i in d:
            remove_channel_from_dict(i)
    elif isinstance(d, dict):
        for k, v in d.copy().items():
            if k == "channel":
                d.pop(k)
            else:
                remove_channel_from_dict(v)
