"""The Tekmar 482 Gateway Integration."""

from . import hub

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_PORT
)
from homeassistant.core import HomeAssistant
from .const import (
    DOMAIN,
    CONF_SETBACK_ENABLE
)

PLATFORMS: list[str] = ["sensor", "climate", "select", "switch"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Tekmar Gateway from config entry."""
    tekmar_gateway = hub.TekmarHub(
        hass,
        entry.entry_id,
        entry.data[CONF_NAME],
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_SETBACK_ENABLE]
        )
    
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = tekmar_gateway

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    
    asyncio.create_task(tekmar_gateway.listen())
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        tekmar_gateway = hass.data[DOMAIN][entry.entry_id]
        await tekmar_gateway.shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
