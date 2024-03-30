"""The Tekmar 482 Gateway Integration."""

import asyncio

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.typing import ConfigType

from . import hub
from .const import CONF_SETBACK_ENABLE, DOMAIN

PLATFORMS: list[str] = [
    Platform.SENSOR,
    Platform.CLIMATE,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
]


REMAP_SCHEMA = vol.Schema(
    {
        vol.Required(cv.int): cv.int,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                "remap": vol.All(
                    cv.ensure_list,
                    [
                        vol.Any(REMAP_SCHEMA),
                    ],
                ),
            },
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Tekmar Gateway advanced YAML config."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["yaml"] = config.get(DOMAIN, {})

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Tekmar Gateway from config entry."""
    tekmar_gateway = hub.TekmarHub(
        hass,
        entry.entry_id,
        entry.data[CONF_NAME],
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.options.get(CONF_SETBACK_ENABLE),
    )

    await tekmar_gateway.async_init_tha()

    hass.data[DOMAIN][entry.entry_id] = tekmar_gateway

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    asyncio.create_task(tekmar_gateway.run())
    asyncio.create_task(tekmar_gateway.timekeeper())

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        tekmar_gateway = hass.data[DOMAIN][entry.entry_id]
        await tekmar_gateway.shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle an options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Allow the user to delete a device from the UI."""

    return True
