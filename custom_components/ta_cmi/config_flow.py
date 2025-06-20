"""Config flow for Technische Alternative C.M.I. integration."""
from __future__ import annotations

import time
from copy import deepcopy
from datetime import timedelta
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiohttp import ClientSession
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from ta_cmi import CMI, ApiError, Device, InvalidCredentialsError, RateLimitError

from . import custom_sleep
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
    CONF_SCAN_INTERVAL,
    DEVICE_DELAY,
    DEVICE_TYPE_STRING_MAP,
    DOMAIN,
    NEW_UID,
    SCAN_INTERVAL,
)


async def validate_login(data: dict[str, Any], session: ClientSession) -> Any:
    """Validate the user input allows us to connect."""
    try:
        cmi: CMI = CMI(
            data[CONF_HOST],
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
            session,
            rate_limit_wait_time=DEVICE_DELAY,
        )
        return await cmi.get_devices()
    except InvalidCredentialsError as err:
        raise InvalidAuth from err
    except ApiError as err:
        raise CannotConnect from err


async def fetch_device(device: Device, retry=False) -> None:
    """Fetch the device data to display."""
    try:
        if retry:
            _LOGGER.debug(
                f"Sleep mode for {DEVICE_DELAY} seconds to prevent rate limiting"
            )
            await custom_sleep(DEVICE_DELAY)
            device.set_device_type("DUMMY-NO-IO")

        _LOGGER.debug("Try to fetch device type: %s", device.id)
        await device.fetch_type()
        _LOGGER.debug(f"Sleep mode for {DEVICE_DELAY} seconds to prevent rate limiting")
        await custom_sleep(DEVICE_DELAY)

        _LOGGER.debug("Try to fetch available device channels: %s", device.id)
        await device.update()

    except ApiError as err:
        if "CAN-request/parameter" in str(err) and not retry:
            return await fetch_device(device, True)
        raise


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Technische Alternative C.M.I.."""

    VERSION = 1
    override_data: dict[str, Any] = {}
    override_config: dict[str, Any] = {}
    init_start_time: float = 0

    def __init__(self) -> None:
        """Initialize."""
        super().__init__()
        self.data: dict[str, Any] = ConfigFlow.override_data
        self.config: dict[str, Any] = ConfigFlow.override_config

        self.start_time: float = ConfigFlow.init_start_time

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, Any] = {}

        if user_input is not None:
            if not user_input[CONF_HOST].startswith("http://"):
                user_input[CONF_HOST] = "http://" + user_input[CONF_HOST]

            self.data["allDevices"] = {}

            try:
                self.data["allDevices"] = await validate_login(
                    user_input, async_get_clientsession(self.hass)
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", err)
                errors["base"] = "unknown"
            else:
                self.config[CONF_HOST] = user_input[CONF_HOST]
                self.config[CONF_USERNAME] = user_input[CONF_USERNAME]
                self.config[CONF_PASSWORD] = user_input[CONF_PASSWORD]
                self.config[CONF_DEVICES] = []
                return await self.async_step_devices()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): cv.string,
                    vol.Required(CONF_USERNAME): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            ),
            errors=errors,
        )

    async def async_step_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step for setup devices."""
        errors: dict[str, Any] = {}

        if user_input is not None:
            self.data[CONF_DEVICES] = user_input[CONF_DEVICES]

            self.config[CONF_DEVICES] = []

            for dev_id in self.data[CONF_DEVICES]:
                device_type: str = ""

                for dev in self.data["allDevices"]:
                    if dev.id == str(dev_id):
                        device_type = dev.get_device_type()

                fetchmode: str = ""
                if user_input[CONF_DEVICE_FETCH_MODE]:
                    fetchmode = "all"
                else:
                    fetchmode = "defined"

                device: dict[str, Any] = {
                    CONF_DEVICE_ID: dev_id,
                    CONF_DEVICE_FETCH_MODE: fetchmode,
                    CONF_DEVICE_TYPE: device_type,
                    CONF_CHANNELS: [],
                }
                self.config[CONF_DEVICES].append(device)
                self.config[NEW_UID] = True

            if not user_input["edit_channels"]:
                return await self.async_step_finish()

            return await self.async_step_channel()

        devices_list: dict[int, str] = {}

        for dev in self.data["allDevices"]:
            if len(self.data["allDevices"]) > 1:
                _LOGGER.debug(
                    f"Sleep mode for {DEVICE_DELAY} seconds to prevent rate limiting"
                )
                await custom_sleep(DEVICE_DELAY)

            try:
                await fetch_device(dev)

            except ApiError as err:
                if "Device not supported" in str(err):
                    errors["base"] = "invalid_device"
                    _LOGGER.warning("Invalid device: %s", dev.id)
                elif "Unknown" not in str(err):
                    errors["base"] = "device_error"
                    _LOGGER.warning(
                        "Error while communicating with a device (%s): %s", dev.id, err
                    )
                else:
                    errors["base"] = "unknown"
                    _LOGGER.exception("Unexpected exception: %s", err)
                    break
            except RateLimitError:
                errors["base"] = "rate_limit"
                break
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", err)
                errors["base"] = "unknown"
                break
            else:
                devices_list[dev.id] = str(dev)

        self.start_time = time.time()
        return self.async_show_form(
            step_id="devices",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICES): cv.multi_select(devices_list),
                    vol.Optional("edit_channels", default=False): cv.boolean,
                    vol.Optional(CONF_DEVICE_FETCH_MODE, default=True): cv.boolean,
                }
            ),
            errors=errors,
        )

    def _generate_channel_types(self) -> list[str]:
        """Generate a list of available channel types"""
        return [x.title() for x in DEVICE_TYPE_STRING_MAP.values()]

    async def async_step_channel(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step for setup channels."""

        errors: dict[str, Any] = {}

        if user_input is not None:
            for dev in self.config[CONF_DEVICES]:
                if dev[CONF_DEVICE_ID] == user_input["node"]:
                    channel: dict[str, Any] = {
                        CONF_CHANNELS_TYPE: user_input[CONF_CHANNELS_TYPE].lower(),
                        CONF_CHANNELS_ID: user_input[CONF_CHANNELS_ID],
                        CONF_CHANNELS_NAME: user_input[CONF_CHANNELS_NAME],
                    }

                    channel[CONF_CHANNELS_DEVICE_CLASS] = user_input[
                        CONF_CHANNELS_DEVICE_CLASS
                    ]

                    dev[CONF_CHANNELS].append(channel)
                    break

            if not user_input["edit_more_channels"]:
                return await self.async_step_finish()
            return await self.async_step_channel()

        devices_list: dict[int, str] = {}
        for dev in self.data["allDevices"]:
            for dev_id in self.data[CONF_DEVICES]:
                if dev_id == dev.id:
                    devices_list[dev.id] = str(dev)
                    break

        return self.async_show_form(
            step_id="channel",
            data_schema=vol.Schema(
                {
                    vol.Required("node"): vol.In(devices_list),
                    vol.Required(CONF_CHANNELS_ID): cv.positive_int,
                    vol.Required(CONF_CHANNELS_TYPE): vol.In(
                        self._generate_channel_types()
                    ),
                    vol.Required(CONF_CHANNELS_NAME): cv.string,
                    vol.Optional(CONF_CHANNELS_DEVICE_CLASS, default=""): cv.string,
                    vol.Optional("edit_more_channels", default=True): cv.boolean,
                }
            ),
            errors=errors,
        )

    async def async_step_finish(self) -> ConfigFlowResult:
        """Step for save the config."""
        # Wait to prevent rate limiting from being triggered.
        end_time = time.time()
        time_lapsed = end_time - self.start_time
        if time_lapsed <= DEVICE_DELAY:
            await custom_sleep(int(DEVICE_DELAY - time_lapsed))
        return self.async_create_entry(title="C.M.I", data=self.config)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


def get_schema(config: dict[str, Any], device_count: int) -> vol.Schema:
    """Generate the schema."""

    default_interval: timedelta = SCAN_INTERVAL

    if config.get(CONF_SCAN_INTERVAL, None) is not None:
        default_interval = timedelta(minutes=config.get(CONF_SCAN_INTERVAL))

    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=config[CONF_HOST]): cv.string,
            vol.Required(
                CONF_SCAN_INTERVAL, default=default_interval.seconds / 60
            ): vol.All(int, vol.Range(min=device_count + 1, max=60)),
        }
    )


class OptionsFlowHandler(OptionsFlow):
    """Handle a option flow for Technische Alternative C.M.I.."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.data = dict(config_entry.data)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle options flow."""

        errors: dict[str, Any] = {}

        if user_input is not None and not errors:
            self.data[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]

            if user_input[CONF_HOST] != self.data[CONF_HOST]:
                if not user_input[CONF_HOST].startswith("http://"):
                    user_input[CONF_HOST] = "http://" + user_input[CONF_HOST]

                try:
                    tmp = deepcopy(self.data)
                    tmp[CONF_HOST] = user_input[CONF_HOST]
                    await validate_login(tmp, async_get_clientsession(self.hass))
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except Exception as err:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception: %s", err)
                    errors["base"] = "unknown"
                else:
                    self.data[CONF_HOST] = user_input[CONF_HOST]
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=self.data
                    )
                    return self.async_create_entry(title="", data={})
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=self.data
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=get_schema(self.data, len(self.data.get(CONF_DEVICES, {}))),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
