"""Component to interface with switches that can be controlled remotely."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_FEATURES, DEVICE_TYPES, DOMAIN, ThaType, ThaValue


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up setpoint group, emergency heat, and vent switches."""
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


class ThaSwitchBase(SwitchEntity):
    """Base class for Tekmar switch entities."""

    should_poll = False

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the switch."""
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


class ThaSetpointGroup(ThaSwitchBase):
    """A switch to enable or disable a gateway setpoint group."""

    icon = "mdi:select-group"

    def __init__(self, tekmar_tha, config_entry, group: int):
        """Initialize the switch for a setpoint group (1-12)."""
        super().__init__(tekmar_tha, config_entry)
        self._setpoint_group = group

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the entity."""
        return (
            f"{self.config_entry_id}-gateway-setpoint-group-"
            f"{int(self._setpoint_group):02d}"
        )

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return (
            f"{self.config_entry_name.capitalize()} Gateway Setpoint Group "
            f"{int(self._setpoint_group):02d}"
        )

    @property
    def available(self) -> bool:
        """Return True if the setpoint group state is known and online."""
        setpoint_groups = self._tekmar_tha.setpoint_groups

        if (
            setpoint_groups[self._setpoint_group] is None
            or setpoint_groups[self._setpoint_group] == ThaValue.NA_8
        ):
            return False

        return super().available

    @property
    def is_on(self):
        """Return True if the setpoint group is enabled."""
        setpoint_groups = self._tekmar_tha.setpoint_groups

        if setpoint_groups[self._setpoint_group] == ThaValue.OFF:
            return False
        if setpoint_groups[self._setpoint_group] == ThaValue.ON:
            return True
        raise NotImplementedError

    async def async_turn_on(self, **kwargs):
        """Enable the setpoint group."""
        await self._tekmar_tha.set_setpoint_group_txqueue(self._setpoint_group, 0x01)

    async def async_turn_off(self, **kwargs):
        """Disable the setpoint group."""
        await self._tekmar_tha.set_setpoint_group_txqueue(self._setpoint_group, 0x00)


class EmergencyHeat(ThaSwitchBase):
    """Turn emergency/aux heat on or off.

    This is a distinct hvac_mode on Tekmar thermostats, but climate entity doesn't have
    a matching HVACMode. Instead the climate entity will show 'heat' mode when
    emergency/aux is active since HA can't show the true mode of the thermostat.
    This switch will show if the thermostat is in emergency/aux mode (and set it).
    """

    entity_category = EntityCategory.CONFIG
    icon = "mdi:hvac"

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the switch, defaulting the restore mode to heat."""
        super().__init__(tekmar_tha, config_entry)

        # Default to Heat mode when coming out of Emergency. We can't know the true
        # last mode if HA restarted or the integration reloaded, and Heat is
        # safer than going to Off (i.e. could cause freezing conditions)
        self._last_mode_setting = 0x01

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the entity."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-emergency-heat"
        )

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"{self._tekmar_tha.tha_full_device_name} Emergency Heat"

    @property
    def is_on(self):
        """Return True if the thermostat is in emergency heat mode."""
        return self._tekmar_tha.mode_setting == 0x06

    async def async_turn_on(self, **kwargs):
        """Save the current mode and switch to emergency heat."""
        self._last_mode_setting = self._tekmar_tha.mode_setting
        await self._tekmar_tha.set_mode_setting_txqueue(0x06)

    async def async_turn_off(self, **kwargs):
        """Restore the mode used before emergency heat."""
        await self._tekmar_tha.set_mode_setting_txqueue(self._last_mode_setting)


class ConfigVentMode(ThaSwitchBase):
    """Config option for thermostat vent mode (can't be read via network)."""

    entity_category = EntityCategory.CONFIG
    icon = "mdi:fan-plus"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the entity."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-config-vent-mode"
        )

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"{self._tekmar_tha.tha_full_device_name} Enable Vent Mode"

    @property
    def is_on(self):
        """Return True if vent mode is enabled."""
        return self._tekmar_tha.config_vent_mode

    async def async_turn_on(self, **kwargs):
        """Enable vent mode."""
        await self._tekmar_tha.set_config_vent_mode(True)

    async def async_turn_off(self, **kwargs):
        """Disable vent mode."""
        await self._tekmar_tha.set_config_vent_mode(False)
