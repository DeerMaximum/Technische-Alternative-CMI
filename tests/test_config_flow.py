"""Test the Technische Alternative C.M.I. config flow."""
from __future__ import annotations
import time
import json
from typing import Any
from unittest.mock import patch


from ta_cmi import ApiError, Device, InvalidCredentialsError, RateLimitError

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import data_entry_flow
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from custom_components.ta_cmi.config_flow import ConfigFlow
from custom_components.ta_cmi.const import (
    CONF_CHANNELS,
    CONF_CHANNELS_DEVICE_CLASS,
    CONF_CHANNELS_ID,
    CONF_CHANNELS_NAME,
    CONF_CHANNELS_TYPE,
    CONF_DEVICE_FETCH_MODE,
    CONF_DEVICES,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)

from . import sleep_mock

DUMMY_CONNECTION_DATA: dict[str, Any] = {
    CONF_HOST: "http://1.2.3.4",
    CONF_USERNAME: "username",
    CONF_PASSWORD: "password",
}

DUMMY_CONNECTION_DATA_ONLY_IP: dict[str, Any] = {
    CONF_HOST: "1.2.3.4",
    CONF_USERNAME: "username",
    CONF_PASSWORD: "password",
}

DUMMY_DEVICE_DATA_NO_CHANNEL_FETCH_ALL = {
    CONF_DEVICES: [2],
    "edit_channels": False,
    CONF_DEVICE_FETCH_MODE: True,
}

DUMMY_DEVICE_DATA_NO_CHANNEL_FETCH_DEFINED = {
    CONF_DEVICES: [2],
    "edit_channels": False,
    CONF_DEVICE_FETCH_MODE: False,
}

DUMMY_DEVICE_DATA_EDIT_CHANNEL = {
    CONF_DEVICES: [2],
    "edit_channels": True,
    CONF_DEVICE_FETCH_MODE: False,
}

DUMMY_CHANNEL_DATA_NO_OTHER_EDIT = {
    "node": "2",
    CONF_CHANNELS_ID: 1,
    CONF_CHANNELS_TYPE: "Input",
    CONF_CHANNELS_NAME: "Name",
    CONF_CHANNELS_DEVICE_CLASS: "",
    "edit_more_channels": False,
}

DUMMY_CHANNEL_DATA_OTHER_EDIT = {
    "node": "2",
    CONF_CHANNELS_ID: 1,
    CONF_CHANNELS_TYPE: "Input",
    CONF_CHANNELS_NAME: "Name",
    CONF_CHANNELS_DEVICE_CLASS: "",
    "edit_more_channels": True,
}

DUMMY_DEVICE_API_DATA: dict[str, Any] = {
    "Header": {"Version": 5, "Device": "88", "Timestamp": 1630764000},
    "Data": {
        "Inputs": [
            {"Number": 1, "AD": "A", "Value": {"Value": 92.2, "Unit": "1"}},
            {"Number": 2, "AD": "A", "Value": {"Value": 92.3, "Unit": "1"}},
        ],
        "Outputs": [{"Number": 1, "AD": "D", "Value": {"Value": 1, "Unit": "43"}}],
    },
    "Status": "OK",
    "Status code": 0,
}

DUMMY_DEVICE_API_DATA_UNKOWN_DEVICE: dict[str, Any] = {
    "Header": {"Version": 5, "Device": "44", "Timestamp": 1630764000},
    "Data": {
        "Inputs": [
            {"Number": 1, "AD": "A", "Value": {"Value": 92.2, "Unit": "1"}},
            {"Number": 2, "AD": "A", "Value": {"Value": 92.3, "Unit": "1"}},
        ],
        "Outputs": [{"Number": 1, "AD": "D", "Value": {"Value": 1, "Unit": "43"}}],
    },
    "Status": "OK",
    "Status code": 0,
}

DUMMY_DEVICE_API_DATA_NO_IO_SUPPORT: dict[str, Any] = {
    "Header": {"Version": 6, "Device": "8D", "Timestamp": 1630764000},
    "Data": {},
    "Status": "FAIL",
    "Status code": 2,
}


DUMMY_CONFIG_ENTRY: dict[str, Any] = {
    CONF_HOST: "http://localhost",
    CONF_USERNAME: "test",
    CONF_PASSWORD: "test",
    CONF_DEVICES: [
        {
            CONF_DEVICE_ID: "2",
            CONF_DEVICE_FETCH_MODE: "all",
            CONF_DEVICE_TYPE: "UVR16x2",
            CONF_CHANNELS: [],
        }
    ],
}

DUMMY_ENTRY_CHANGE: dict[str, Any] = {
    CONF_SCAN_INTERVAL: 15,
}

DUMMY_CONFIG_ENTRY_UPDATED: dict[str, Any] = {
    CONF_HOST: "http://localhost",
    CONF_USERNAME: "test",
    CONF_PASSWORD: "test",
    CONF_SCAN_INTERVAL: 15,
    CONF_DEVICES: [
        {
            CONF_DEVICE_ID: "2",
            CONF_DEVICE_FETCH_MODE: "all",
            CONF_DEVICE_TYPE: "UVR16x2",
            CONF_CHANNELS: [],
        }
    ],
}


async def test_show_set_form(hass: HomeAssistant) -> None:
    """Test that the setup form is served."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"


async def test_step_user_connection_error(hass: HomeAssistant) -> None:
    """Test starting a flow by user but no connection found."""
    with patch(
        "ta_cmi.baseApi.BaseAPI._make_request_no_json",
        side_effect=ApiError("Could not connect to C.M.I."),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=DUMMY_CONNECTION_DATA
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "cannot_connect"}


async def test_step_user_invalid_auth(hass: HomeAssistant) -> None:
    """Test starting a flow by user but with invalid credentials."""
    with patch(
        "ta_cmi.baseApi.BaseAPI._make_request_no_json",
        side_effect=InvalidCredentialsError("Invalid API key"),
    ):

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=DUMMY_CONNECTION_DATA
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "invalid_auth"}


async def test_step_user_unexpected_exception(hass: HomeAssistant) -> None:
    """Test starting a flow by user but with an unexpected exception."""
    with patch(
        "ta_cmi.baseApi.BaseAPI._make_request_no_json",
        side_effect=Exception("DUMMY"),
    ):

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=DUMMY_CONNECTION_DATA
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "unknown"}


async def test_step_user(hass: HomeAssistant) -> None:
    """Test starting a flow by user with valid values."""
    with patch(
        "ta_cmi.baseApi.BaseAPI._make_request_no_json",
        return_value="2;",
    ), patch(
        "ta_cmi.baseApi.BaseAPI._make_request", return_value=DUMMY_DEVICE_API_DATA
    ), patch(
        "asyncio.sleep", wraps=sleep_mock
    ) as sleep_m:

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=DUMMY_CONNECTION_DATA
        )

        sleep_m.assert_called_once()

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "devices"
        assert result["errors"] == {}


async def test_step_user_only_ip(hass: HomeAssistant) -> None:
    """Test starting a flow by user with valid values but the host is only an ip."""
    with patch(
        "ta_cmi.baseApi.BaseAPI._make_request_no_json",
        return_value="2;",
    ), patch(
        "ta_cmi.baseApi.BaseAPI._make_request", return_value=DUMMY_DEVICE_API_DATA
    ), patch(
        "asyncio.sleep", wraps=sleep_mock
    ) as sleep_m:

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=DUMMY_CONNECTION_DATA_ONLY_IP
        )

        sleep_m.assert_called_once()

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "devices"
        assert result["errors"] == {}


async def test_step_user_unkown_device(hass: HomeAssistant) -> None:
    """Test to start a flow by a user with unknown device."""

    with patch(
        "ta_cmi.baseApi.BaseAPI._make_request_no_json",
        return_value="2;3;",
    ), patch(
        "ta_cmi.baseApi.BaseAPI._make_request",
        return_value=DUMMY_DEVICE_API_DATA_UNKOWN_DEVICE,
    ), patch(
        "asyncio.sleep", wraps=sleep_mock
    ):

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=DUMMY_CONNECTION_DATA
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "devices"
        assert result["errors"] == {"base": "invalid_device"}


async def test_step_devices_without_edit_fetch_all(hass: HomeAssistant) -> None:
    """Test the device step without edit channels and fetchmode all."""

    with patch("asyncio.sleep", wraps=sleep_mock):

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "devices"},
            data=DUMMY_DEVICE_DATA_NO_CHANNEL_FETCH_ALL,
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == "C.M.I"


async def test_step_devices_without_edit_fetch_defined(hass: HomeAssistant) -> None:
    """Test the device step without edit channels and fetchmode defined."""

    dummy_device: Device = Device("2", "http://dummy", "", "")
    DATA_OVERRIDE = {"allDevices": [dummy_device]}

    with patch("asyncio.sleep", wraps=sleep_mock), patch.object(
        ConfigFlow, "override_data", DATA_OVERRIDE
    ):

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "devices"},
            data=DUMMY_DEVICE_DATA_NO_CHANNEL_FETCH_DEFINED,
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == "C.M.I"


async def test_step_device_with_device_without_io_support(hass: HomeAssistant) -> None:
    """Test the device step with a device that dont support inputs and outputs."""
    dummy_device: Device = Device("2", "http://dummy", "", "")
    DATA_OVERRIDE = {"allDevices": [dummy_device]}

    with patch("asyncio.sleep", wraps=sleep_mock) as sleep_m, patch(
        "ta_cmi.baseApi.BaseAPI._make_request_no_json",
        side_effect=[
            json.dumps(DUMMY_DEVICE_API_DATA_NO_IO_SUPPORT),
            json.dumps(DUMMY_DEVICE_API_DATA),
            json.dumps(DUMMY_DEVICE_API_DATA),
            json.dumps(DUMMY_DEVICE_API_DATA),
        ],
    ) as request_m, patch.object(ConfigFlow, "override_data", DATA_OVERRIDE), patch(
        "ta_cmi.device.Device.set_device_type",
        side_effect=Device.set_device_type,
        autospec=True,
    ) as type_m:

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "devices"},
        )

        args, _ = type_m.call_args
        assert "DUMMY-NO-IO" in args

        assert sleep_m.call_count == 2
        assert request_m.call_count == 3

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "devices"
        assert result["errors"] == {}


async def test_step_devices_with_multiple_devices(hass: HomeAssistant) -> None:
    """Test the device step with multiple devices."""

    dummy_device: Device = Device("2", "http://dummy", "", "")
    dummy_Device2: Device = Device("3", "http://dummy", "", "")

    DATA_OVERRIDE = {"allDevices": [dummy_device, dummy_Device2]}

    with patch.object(ConfigFlow, "override_data", DATA_OVERRIDE), patch(
        "ta_cmi.baseApi.BaseAPI._make_request",
        return_value=DUMMY_DEVICE_API_DATA_UNKOWN_DEVICE,
    ), patch("asyncio.sleep", wraps=sleep_mock):

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "devices"}
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "devices"
        assert result["errors"] == {"base": "invalid_device"}


async def test_step_devices_with_edit(hass: HomeAssistant) -> None:
    """Test the device step with edit channels."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "devices"},
        data=DUMMY_DEVICE_DATA_EDIT_CHANNEL,
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "channel"
    assert result["errors"] == {}


async def test_step_finish_dynamic_wait(hass: HomeAssistant) -> None:
    """Test the finish step with dynamic waiting."""

    with patch("asyncio.sleep", wraps=sleep_mock) as mock, patch.object(
        ConfigFlow, "init_start_time", time.time()
    ):

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "devices"},
            data=DUMMY_DEVICE_DATA_NO_CHANNEL_FETCH_DEFINED,
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == "C.M.I"

        assert mock.call_count == 2


async def test_step_device_communication_error(hass: HomeAssistant) -> None:
    """Test the channel step with an communication error."""

    with patch(
        "ta_cmi.baseApi.BaseAPI._make_request",
        side_effect=ApiError("Could not connect to C.M.I"),
    ), patch("asyncio.sleep", wraps=sleep_mock):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "devices"},
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "devices"
    assert result["errors"] == {"base": "device_error"}


async def test_step_device_unkown_error(hass: HomeAssistant) -> None:
    """Test the channel step with an unexpected error."""

    with patch(
        "ta_cmi.baseApi.BaseAPI._make_request",
        side_effect=ApiError("Unknown error"),
    ), patch("asyncio.sleep", wraps=sleep_mock):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "devices"},
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "devices"
    assert result["errors"] == {"base": "unknown"}


async def test_step_device_rate_limit_error(hass: HomeAssistant) -> None:
    """Test the channel step with a rate limit error."""

    with patch(
        "ta_cmi.baseApi.BaseAPI._make_request",
        side_effect=RateLimitError("RateLimit"),
    ), patch("asyncio.sleep", wraps=sleep_mock):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "devices"},
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "devices"
    assert result["errors"] == {"base": "rate_limit"}


async def test_step_channels_edit_only_one(hass: HomeAssistant) -> None:
    """Test the channel step without edit other channels."""

    dummy_device: Device = Device("2", "", "", "")

    DATA_OVERRIDE = {"allDevices": [dummy_device]}

    CONFIG_OVERRIDE = {
        CONF_DEVICES: [
            {CONF_CHANNELS_ID: "2", CONF_DEVICE_FETCH_MODE: "all", CONF_CHANNELS: []}
        ]
    }

    with patch.object(ConfigFlow, "override_data", DATA_OVERRIDE), patch.object(
        ConfigFlow, "override_config", CONFIG_OVERRIDE
    ), patch("asyncio.sleep", wraps=sleep_mock):

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "channel"},
            data=DUMMY_CHANNEL_DATA_NO_OTHER_EDIT,
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == "C.M.I"


async def test_step_channels_edit_more(hass: HomeAssistant) -> None:
    """Test the channel step with edit other channels."""

    dummy_device: Device = Device("2", "", "", "")

    DATA_OVERRIDE = {"allDevices": [dummy_device], CONF_DEVICES: ["2"]}

    CONFIG_OVERRIDE = {
        CONF_DEVICES: [
            {CONF_CHANNELS_ID: "2", CONF_DEVICE_FETCH_MODE: "all", CONF_CHANNELS: []}
        ]
    }

    with patch.object(ConfigFlow, "override_data", DATA_OVERRIDE), patch.object(
        ConfigFlow, "override_config", CONFIG_OVERRIDE
    ), patch("asyncio.sleep", wraps=sleep_mock):

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "channel"}, data=DUMMY_CHANNEL_DATA_OTHER_EDIT
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "channel"
        assert result["errors"] == {}


async def test_options_flow_init(hass: HomeAssistant) -> None:
    """Test config flow options."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="C.M.I",
        data=DUMMY_CONFIG_ENTRY,
    )
    config_entry.add_to_hass(hass)

    with patch("custom_components.ta_cmi.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_init(config_entry.entry_id)

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "init"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input=DUMMY_ENTRY_CHANGE,
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert dict(config_entry.options) == DUMMY_CONFIG_ENTRY_UPDATED
