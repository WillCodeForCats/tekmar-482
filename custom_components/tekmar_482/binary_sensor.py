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


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    for gateway in hub.tha_gateway:
        entities.append(ReportingState(gateway, config_entry))
        entities.append(SetbackEnable(gateway, config_entry))

    if entities:
        async_add_entities(entities)


class ThaBinarySensorBase(BinarySensorEntity):
    """Base class for Tekmar binary sensor entities."""

    should_poll = False

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        self._tekmar_tha = tekmar_tha
        self._config_entry = config_entry

    @property
    def device_info(self):
        """Return device information for the device registry."""
        return self._tekmar_tha.device_info

    @property
    def available(self) -> bool:
        """Return True if the device and hub are online."""
        return self._tekmar_tha.online and self._tekmar_tha.hub.online

    @property
    def config_entry_id(self):
        """Return the config entry ID."""
        return self._config_entry.entry_id

    @property
    def config_entry_name(self):
        """Return the config entry name."""
        return self._config_entry.data["name"]

    async def async_added_to_hass(self):
        """Register for state updates when added to Home Assistant."""
        self._tekmar_tha.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Remove the state update callback before removal."""
        self._tekmar_tha.remove_callback(self.async_write_ha_state)


class ReportingState(ThaBinarySensorBase):
    """Boolean status for gateway reporting state."""

    entity_category = EntityCategory.DIAGNOSTIC
    device_class = BinarySensorDeviceClass.RUNNING

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the entity."""
        return f"{self.config_entry_id}-gateway-reporting-state"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"{self.config_entry_name.capitalize()} Gateway Reporting State"

    @property
    def is_on(self):
        """Return True if the gateway is reporting."""
        return self._tekmar_tha.reporting_state == ThaValue.ON


class SetbackEnable(ThaBinarySensorBase):
    """Boolean status for gateway setback mode."""

    entity_category = EntityCategory.DIAGNOSTIC
    device_class = BinarySensorDeviceClass.RUNNING

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the entity."""
        return f"{self.config_entry_id}-gateway-setback-enable"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"{self.config_entry_name.capitalize()} Gateway Setback Enable"

    @property
    def available(self) -> bool:
        """Return True if setback enable is known and the device is online."""
        if (
            self._tekmar_tha.setback_enable is None
            or self._tekmar_tha.setback_enable == ThaValue.NA_8
        ):
            return False

        return super().available

    @property
    def is_on(self):
        """Return True if setback is enabled on the gateway."""
        return self._tekmar_tha.setback_enable == ThaValue.ON
