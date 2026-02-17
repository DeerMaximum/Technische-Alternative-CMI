# Home Assistant integration to read Values from C.M.I
[![GitHub Release][releases-shield]][releases]
[![hacs][hacsbadge]][hacs]

This integration monitors the inputs and outputs of the devices connected to a C.M.I. from [Technische Alternative](https://www.ta.co.at/). It creates a separate (binary) sensor for each input and output which displays the current values.

The data is fetched every 10 minutes.

Currently supported devices:

- UVR1611
- UVR16x2
- RSM610
- CAN-I/O45
- CAN-EZ2
- CAN-MTx2
- CAN-BC2
- UVR65
- CAN-EZ3
- UVR610
- UVR67

> **Note**
> The loading time of the integration is extended by one minute per configured node on the C.M.I. to avoid triggering the rate limit.
> The same applies to the setup process

## Requirements

* Credentials for an expert user on the C.M.I.

{% if not installed %}
## Installation

### Step 1:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DeerMaximum&repository=Technische-Alternative-CMI&category=integration)

### Step 2 (**Don't forget**):

1. Click install.
2. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Technische Alternative".
3. Start the config flow.

{% endif %}

### Step 3:

> **Note**
> When saving the configuration, there may be a wait time due to the rate limit.
> 
#### C.M.I. configuration

In the first step of the config flow, set up the connection to C.M.I.. To do this, enter the address, user name and password.

#### Device selection

In the 2nd step, select the devices from which the data is to be read.
For this purpose, a list of all devices and details about them are retrieved at the start of the step.
This can take several minutes due to a rate limit of one request per minute.
Once the data has been retrieved, select the supported devices from the list.
If an error occurs during this query, the devices may be missing from the list. 
Depending on the type of error, you should try again after a few minutes.

If to configure the channels individually, continue with the next step, otherwise the setup is finished.

#### Channel configuration

In this step, individual channels can be customized, including the following properties:

* Name of the sensor (can also be changed to HA afterward)
* Device class

To customize a channel, select the device,
on which the channel is located, enter the channel number and finally select the channel type.

## Common errors

### "Unknown error occurred" on setup after ~60s

This error occurs if the setup is done on a Home Assistant instance that is accessed through a reverse proxy or the Home Assistant Cloud. 
In this case please connect **directly** to your instance and set up the integration.

## Supported data types

| Device type | Inputs | Outputs | DL-inputs | System-values: General | System-values: Date | System-values: Time | System-values: Sun | System-values: Electrical power | Analog network inputs | Digital network inputs | M-Bus | Modbus | KNX | Analog logging | Digital logging |
|-------------|:------:|:-------:|:---------:|:----------------------:|:-------------------:|:-------------------:|:------------------:|:-------------------------------:|:---------------------:|:----------------------:|:-----:|:------:|:---:|:--------------:|:---------------:|
| UVR1611     |   ✔    |    ✔    |     ❌     |           ❌            |          ❌          |          ❌          |         ❌          |                ❌                |           ✔           |           ✔            |   ❌   |   ❌    |  ❌  |       ❌        |        ❌        |
| UVR16x2     |   ✔    |    ✔    |     ✔     |           ✔            |          ✔          |          ✔          |         ✔          |                ❌                |           ❌           |           ❌            |   ❌   |   ❌    |  ❌  |       ✔        |        ✔        |
| RSM610      |   ✔    |    ✔    |     ✔     |           ❌            |          ❌          |          ❌          |         ❌          |                ❌                |           ❌           |           ❌            |   ✔   |   ❌    |  ❌  |       ❌        |        ❌        |
| CAN-I/O45   |   ✔    |    ✔    |     ✔     |           ❌            |          ❌          |          ❌          |         ❌          |                ❌                |           ❌           |           ❌            |   ❌   |   ❌    |  ❌  |       ❌        |        ❌        |
| CAN-EZ2     |   ✔    |    ✔    |     ❌     |           ❌            |          ❌          |          ❌          |         ❌          |                ✔                |           ❌           |           ❌            |   ❌   |   ❌    |  ❌  |       ❌        |        ❌        |
| CAN-MTx2    |   ✔    |    ✔    |     ❌     |           ❌            |          ❌          |          ❌          |         ❌          |                ❌                |           ❌           |           ❌            |   ❌   |   ❌    |  ❌  |       ❌        |        ❌        |
| CAN-BC2     |   ❌    |    ❌    |     ✔     |           ✔            |          ✔          |          ✔          |         ✔          |                ❌                |           ❌           |           ❌            |   ✔   |   ✔    |  ✔  |       ✔        |        ✔        |
| UVR65       |   ✔    |    ✔    |     ❌     |           ❌            |          ❌          |          ❌          |         ❌          |                ❌                |           ❌           |           ❌            |   ❌   |   ❌    |  ❌  |       ❌        |        ❌        |
| CAN-EZ3     |   ❌    |    ❌    |     ✔     |           ✔            |          ✔          |          ✔          |         ✔          |                ✔                |           ❌           |           ❌            |   ❌   |   ✔    |  ❌  |       ✔        |        ✔        |
| UVR610      |   ✔    |    ✔    |     ✔     |           ❌            |          ❌          |          ❌          |         ❌          |                ❌                |           ❌           |           ❌            |   ✔   |   ❌    |  ❌  |       ✔        |        ✔        |
| UVR67       |   ✔    |    ✔    |     ❌     |           ❌            |          ❌          |          ❌          |         ❌          |                ❌                |           ❌           |           ❌            |   ❌   |   ❌    |  ❌  |       ❌        |        ❌        |


> **Note**
> The supported data types may differ from the official API. If a device type supports other data types than listed here, please create an issue.

[taWebsite]: https://www.ta.co.at/
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/v/release/DeerMaximum/Technische-Alternative-CMI.svg?style=for-the-badge
[releases]: https://github.com/DeerMaximum/Technische-Alternative-CMI/releases
