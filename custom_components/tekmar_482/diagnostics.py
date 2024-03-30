"""Diagnostics support for Tekmar Gateway 482."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

REDACT_CONFIG = {"unique_id", "host"}
REDACT_GATEWAY = {}
REDACT_DEVICE = {}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    hub = hass.data[DOMAIN][config_entry.entry_id]

    data: dict[str, Any] = {
        "config_entry": async_redact_data(config_entry.as_dict(), REDACT_CONFIG)
    }

    for gateway in hub.tha_gateway:
        gateway: dict[str, Any] = {
            "gateway": {
                "fw_ver": gateway.hub.tha_fw_ver,
                "pr_ver": gateway.hub.tha_pr_ver,
                "reporting_state": gateway.reporting_state,
                "setback_enable": gateway.setback_enable,
            }
        }
        data.update(async_redact_data(gateway, REDACT_GATEWAY))

    for device in hub.tha_devices:
        device: dict[str, Any] = {
            f"device_{device.device_id}": {
                "id": device.device_id,
                "type": device.tha_device_type,
                "firmware": device.firmware_version,
                "model": device.model,
                "full_name": device.tha_full_device_name,
            }
        }
        data.update(async_redact_data(device, REDACT_DEVICE))

    data.update({"ignored": hub.tha_ignore_addr})

    return data
