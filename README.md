# Tekmar Gateway 482 (tekmar-482)

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

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

## Installation

Copy the `tekmar_482` folder into to your Home Assistant `config/custom_components` folder,

OR

Install with HACS: Search for "Tekmar Gateway 482" in the default repository.

After rebooting Home Assistant, this integration can be configured through the integration setup UI.

### Configuration

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
