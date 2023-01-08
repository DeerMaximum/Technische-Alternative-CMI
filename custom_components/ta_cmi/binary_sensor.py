"""C.M.I binary sensor platform."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_NAME,
    ATTR_SW_VERSION,
    CONF_API_VERSION,
    CONF_HOST,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ta_cmi import ChannelType

from . import CMIDataUpdateCoordinator
from .const import (
    DEVICE_TYPE,
    TYPE_BINARY,
    DOMAIN,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entries."""
    coordinator: CMIDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[DeviceChannelBinary] = []

    device_registry = dr.async_get(hass)

    for ent in coordinator.data:

        for channel_type in ChannelType:
            if coordinator.data[ent][TYPE_BINARY].get(channel_type.name, None) is None:
                continue

            available_channels = coordinator.data[ent][TYPE_BINARY][channel_type.name]
            for ch_id in available_channels:
                channel: DeviceChannelBinary = DeviceChannelBinary(
                    coordinator, ent, ch_id, channel_type.name
                )

                entities.append(channel)

        device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers={(DOMAIN, ent)},
            manufacturer="Technische Alternative",
            name=coordinator.data[ent][DEVICE_TYPE],
            model=coordinator.data[ent][DEVICE_TYPE],
            sw_version=coordinator.data[ent][CONF_API_VERSION],
            configuration_url=coordinator.data[ent][CONF_HOST],
        )

    async_add_entities(entities)


class DeviceChannelBinary(CoordinatorEntity, BinarySensorEntity):
    """Representation of an C.M.I channel."""

    def __init__(
        self,
        coordinator: CMIDataUpdateCoordinator,
        node_id: str,
        channel_id: str,
        input_type: ChannelType,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._id = channel_id
        self._node_id = node_id
        self._input_type = input_type
        self._coordinator = coordinator

        channel_raw: dict[str, Any] = self._coordinator.data[self._node_id][
            TYPE_BINARY
        ][self._input_type][self._id]

        name: str = channel_raw["name"]
        mode: str = channel_raw["mode"]

        self._attr_name: str = name or f"Node: {self._node_id} - {mode} {self._id}"
        self._attr_unique_id: str = f"ta-cmi-{self._node_id}-{mode}{self._id}"

    @property
    def is_on(self) -> bool:
        """Return the state of the sensor."""
        channel_raw: dict[str, Any] = self._coordinator.data[self._node_id][
            TYPE_BINARY
        ][self._input_type][self._id]

        value: str = channel_raw["value"]

        return value in ("on", "yes")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""

        device_api_type: str = self._coordinator.data[self._node_id][CONF_API_VERSION]
        device_name: str = self._coordinator.data[self._node_id][DEVICE_TYPE]

        return {
            ATTR_NAME: device_name,
            ATTR_IDENTIFIERS: {(DOMAIN, self._node_id)},
            ATTR_MANUFACTURER: "Technische Alternative",
            ATTR_MODEL: device_name,
            ATTR_SW_VERSION: device_api_type,
        }

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the device class of this entity, if any."""
        channel_raw: dict[str, Any] = self._coordinator.data[self._node_id][
            TYPE_BINARY
        ][self._input_type][self._id]

        return channel_raw.get("device_class", None)
