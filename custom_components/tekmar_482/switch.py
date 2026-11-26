"""Component to interface with switches that can be controlled remotely."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_FEATURES, DEVICE_TYPES, DOMAIN, ThaType, ThaValue
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
        if hub.tha_pr_ver in [2, 3]:
            entities.append(ThaSetpointGroup(gateway, config_entry, 0x01))
            entities.append(ThaSetpointGroup(gateway, config_entry, 0x02))
            entities.append(ThaSetpointGroup(gateway, config_entry, 0x03))
            entities.append(ThaSetpointGroup(gateway, config_entry, 0x04))
            entities.append(ThaSetpointGroup(gateway, config_entry, 0x05))
            entities.append(ThaSetpointGroup(gateway, config_entry, 0x06))
            entities.append(ThaSetpointGroup(gateway, config_entry, 0x07))
            entities.append(ThaSetpointGroup(gateway, config_entry, 0x08))
            entities.append(ThaSetpointGroup(gateway, config_entry, 0x09))
            entities.append(ThaSetpointGroup(gateway, config_entry, 0x0A))
            entities.append(ThaSetpointGroup(gateway, config_entry, 0x0B))
            entities.append(ThaSetpointGroup(gateway, config_entry, 0x0C))

    for device in hub.tha_devices:
        if DEVICE_TYPES[device.tha_device["type"]] == ThaType.THERMOSTAT:
            if DEVICE_FEATURES[device.tha_device["type"]]["emer"]:
                entities.append(EmergencyHeat(device, config_entry))
            if DEVICE_FEATURES[device.tha_device["type"]]["fan"]:
                entities.append(ConfigVentMode(device, config_entry))

    if entities:
        async_add_entities(entities)


class ThaSwitchBase(ThaEntity, SwitchEntity):
    """Base class for Tekmar switch entities."""


class ThaSetpointGroup(ThaSwitchBase):
    """A switch to enable or disable a gateway setpoint group."""

    _attr_icon = "mdi:select-group"

    def __init__(self, tekmar_tha, config_entry, group: int):
        """Initialize the setpoint group."""
        super().__init__(tekmar_tha, config_entry)
        self._setpoint_group = group

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-gateway-setpoint-group-"
            f"{int(self._setpoint_group):02d}"
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return f"Setpoint Group {int(self._setpoint_group):02d}"

    @property
    def available(self) -> bool:
        """Return the available."""
        setpoint_groups = self._tekmar_tha.setpoint_groups

        if (
            setpoint_groups[self._setpoint_group] is None
            or setpoint_groups[self._setpoint_group] == ThaValue.NA_8
        ):
            return False

        return super().available

    @property
    def is_on(self):
        """Return True if on."""
        setpoint_groups = self._tekmar_tha.setpoint_groups

        if setpoint_groups[self._setpoint_group] == ThaValue.OFF:
            return False
        if setpoint_groups[self._setpoint_group] == ThaValue.ON:
            return True
        raise NotImplementedError

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._tekmar_tha.set_setpoint_group_txqueue(self._setpoint_group, 0x01)

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._tekmar_tha.set_setpoint_group_txqueue(self._setpoint_group, 0x00)


class EmergencyHeat(ThaSwitchBase):
    """Turn emergency/aux heat on or off.

    This is a distinct hvac_mode on Tekmar thermostats, but climate entity doesn't have
    a matching HVACMode. Instead the climate entity will show 'heat' mode when
    emergency/aux is active since HA can't show the true mode of the thermostat.
    This switch will show if the thermostat is in emergency/aux mode (and set it).
    """

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:hvac"

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the emergency heat."""
        super().__init__(tekmar_tha, config_entry)

        # Default to Heat mode when coming out of Emergency. We can't know the true
        # last mode if HA restarted or the integration reloaded, and Heat is
        # safer than going to Off (i.e. could cause freezing conditions)
        self._last_mode_setting = 0x01

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-emergency-heat"
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return "Emergency Heat"

    @property
    def is_on(self):
        """Return True if on."""
        return self._tekmar_tha.mode_setting == 0x06

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        self._last_mode_setting = self._tekmar_tha.mode_setting
        await self._tekmar_tha.set_mode_setting_txqueue(0x06)

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._tekmar_tha.set_mode_setting_txqueue(self._last_mode_setting)


class ConfigVentMode(ThaSwitchBase):
    """Config option for thermostat vent mode (can't be read via network)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:fan-plus"

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-config-vent-mode"
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return "Enable Vent Mode"

    @property
    def is_on(self):
        """Return True if on."""
        return self._tekmar_tha.config_vent_mode

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._tekmar_tha.set_config_vent_mode(True)

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._tekmar_tha.set_config_vent_mode(False)
