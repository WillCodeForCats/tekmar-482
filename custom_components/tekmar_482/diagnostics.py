"""Diagnostics support for Tekmar Gateway 482."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

REDACT_CONFIG = {"unique_id", "host"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    data: dict[str, Any] = {
        "config_entry": async_redact_data(config_entry.as_dict(), REDACT_CONFIG)
    }

    return data
