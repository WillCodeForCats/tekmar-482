"""Base entity for Tekmar Gateway 482 platforms."""

from __future__ import annotations

from homeassistant.helpers.entity import Entity

# Entities that depend on a floor sensor: (platform, unique_id suffix)
FLOOR_ENTITIES = (
    ("sensor", "current-floor-temperature"),
    ("number", "slab-setpoint"),
    ("number", "slab-setpoint-day"),
    ("number", "slab-setpoint-night"),
    ("number", "slab-setpoint-away"),
)


class ThaEntity(Entity):
    """Base class for Tekmar entities on every platform."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the entity."""
        self._tekmar_tha = tekmar_tha
        self._config_entry = config_entry
        self._attr_device_info = tekmar_tha.device_info

    @property
    def available(self) -> bool:
        """Return the available."""
        return self._tekmar_tha.online and self._tekmar_tha.hub.online

    @property
    def config_entry_id(self):
        """Return the config entry id."""
        return self._config_entry.entry_id

    @property
    def config_entry_name(self):
        """Return the config entry name."""
        return self._config_entry.data["name"]

    async def async_added_to_hass(self):
        """Added to hass."""
        self._tekmar_tha.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Will remove from hass."""
        self._tekmar_tha.remove_callback(self.async_write_ha_state)
