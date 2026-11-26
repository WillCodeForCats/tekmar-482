"""Component to interface with binary sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ThaValue
from .entity import ThaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup entry."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    for gateway in hub.tha_gateway:
        entities.append(ReportingState(gateway, config_entry))
        entities.append(SetbackEnable(gateway, config_entry))

    if entities:
        async_add_entities(entities)


class ThaBinarySensorBase(ThaEntity, BinarySensorEntity):
    """Base class for Tekmar binary sensor entities."""


class ReportingState(ThaBinarySensorBase):
    """Boolean status for gateway reporting state."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return f"{self.config_entry_id}-gateway-reporting-state"

    @property
    def name(self) -> str:
        """Return the name."""
        return "Reporting State"

    @property
    def is_on(self):
        """Return True if on."""
        return self._tekmar_tha.reporting_state == ThaValue.ON


class SetbackEnable(ThaBinarySensorBase):
    """Boolean status for gateway setback mode."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return f"{self.config_entry_id}-gateway-setback-enable"

    @property
    def name(self) -> str:
        """Return the name."""
        return "Setback Enable"

    @property
    def available(self) -> bool:
        """Return the available."""
        if (
            self._tekmar_tha.setback_enable is None
            or self._tekmar_tha.setback_enable == ThaValue.NA_8
        ):
            return False

        return super().available

    @property
    def is_on(self):
        """Return True if on."""
        return self._tekmar_tha.setback_enable == ThaValue.ON
