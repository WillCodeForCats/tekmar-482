# Tekmar Gateway 482 (tekmar-482)

[![hacs_badge](https://img.shields.io/badge/HACS%20%7C%20Marketplace-Default-41BDF5.svg?style=for-the-badge)](https://contributors.home-assistant.io/marketplace/)

A Home Assistant Integration for the Tekmar Gateway 482

Integrates your Tekmar communicating thermostats, setpoints, and snowmelt controls with Home Assistant.

## Features

- Suports the Tekmar Gateway 482.
- Works with tN4 and tN2 devices.
- View the status of devices.
- Control devices and setpoint groups.
- View and update device setpoints.

### Packet Server

This integration connects to the gateway through one of the following packet servers:

- [Tekmar Packet Server App](https://github.com/WillCodeForCats/tekmar-packetserv) for Home Assistant.
- [tekmar-482-dashboard](https://github.com/jameshilliard/tekmar-482-dashboard), an experimental dashboard with a compatible packet server.
  With custom 482 firmware, it also offers features unavailable in the original Tekmar firmware, such as bidirectional tN4 frame tracing.

<!-- ha-marketplace:exclude-start -->

## Installation

Install with Marketplace (Home Assistant 2026.11 and later): Go to **Settings** → **Marketplace** and search for "Tekmar Gateway 482".

Install with [HACS](https://hacs.xyz) (before Home Assistant 2026.11): Search for "Tekmar Gateway 482" in the default repository.

Either way, you can also use this link to open the integration's page directly:

[![Open your Home Assistant instance and open a repository in the Marketplace or the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=WillCodeForCats&repository=tekmar-482&category=integration)

OR

Download the [latest release](https://github.com/WillCodeForCats/tekmar-482/releases) and copy the `tekmar_482` folder into to your Home Assistant `config/custom_components` folder.

After rebooting Home Assistant, this integration can be configured through the integration setup UI.
<!-- ha-marketplace:exclude-end -->

## Configuration

[WillCodeForCats/tekmar-482/wiki/Configuration](https://github.com/WillCodeForCats/tekmar-482/wiki/Configuration)

### Documentation

[WillCodeForCats/tekmar-482/wiki](https://github.com/WillCodeForCats/tekmar-482/wiki)

### Required Versions

- Home Assistant 2025.12.0 or newer

## Compatible Equipment

For a list of compatible equipment see the wiki.

[WillCodeForCats/tekmar-482/wiki/Compatible-Equipment](https://github.com/WillCodeForCats/tekmar-482/wiki/Compatible-Equipment)

## Credits

Implemented using "tN4 Gateway 482 - Custom Integration Tools" and "Tekmar Home Automation
(tHA) Protocol" from: [https://www.watts.com/products/hvac-hot-water-solutions/controls/control-accessories/482/482](https://www.watts.com/products/hvac-hot-water-solutions/controls/control-accessories/482/482)

Tekmar, tekmarNet, tN4, tN2, and related logos and trademarks are copyright 2021 Watts.

## Project Sponsors

None yet...
