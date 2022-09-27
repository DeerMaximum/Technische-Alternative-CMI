# Home Assistant integration to read Values from C.M.I
[![GitHub Release][releases-shield]][releases]
[![hacs][hacsbadge]][hacs]

This integration monitors the inputs and outputs of the devices connected to a C.M.I. from [Technische Alternative](https://www.ta.co.at/). It creates a separate (binary) sensor for each input and output which displays the current values.

Currently supported devices:

- UVR1611
- UVR16x2 (Tested)
- RSM610
- CAN-I/O45
- CAN-EZ2
- CAN-MTx2
- CAN-BC2
- UVR65
- CAN-EZ3
- UVR610
- UVR67

{% if not installed %}

## Prerequisites

To use the integration in your installation, you need to specify the credentials of a user with `expert` rights.

## Installation

1. Click install.
2. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "QR-Code".

{% endif %}

[taWebsite]: https://www.ta.co.at/
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/v/release/DeerMaximum/Technische-Alternative-CMI.svg?style=for-the-badge
[releases]: https://github.com/DeerMaximum/Technische-Alternative-CMI/releases