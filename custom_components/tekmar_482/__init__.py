"""The Tekmar 482 Gateway Integration."""

import asyncio
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.storage import Store

from . import hub
from .const import CONF_SETBACK_ENABLE, DOMAIN, STORAGE_KEY, STORAGE_VERSION_MAJOR

PLATFORMS: list[str] = [
    Platform.SENSOR,
    Platform.CLIMATE,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
]


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

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = tekmar_gateway

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


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""

    store: Store[dict[str, Any]] = Store(
        hass,
        STORAGE_VERSION_MAJOR,
        STORAGE_KEY,
    )

    data = await store.async_load()
    del data[entry.entry_id]
    await store.async_save(data)
