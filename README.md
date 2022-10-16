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
## Installation

### Step 1:

<br>

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DeerMaximum&repository=Technische-Alternative-CMI&category=integration)

### Step 2 (**Don't forget**):

1. Click install.
2. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Technische Alternative".

{% endif %}

[taWebsite]: https://www.ta.co.at/
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/v/release/DeerMaximum/Technische-Alternative-CMI.svg?style=for-the-badge
[releases]: https://github.com/DeerMaximum/Technische-Alternative-CMI/releases
