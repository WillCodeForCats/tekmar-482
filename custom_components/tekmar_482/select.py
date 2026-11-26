"""Component to allow selecting an option from a list as platforms."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
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

    for device in hub.tha_devices:
        if DEVICE_TYPES[device.tha_device["type"]] == ThaType.THERMOSTAT:
            if DEVICE_FEATURES[device.tha_device["type"]]["fan"]:
                entities.append(ThaFanSelect(device, config_entry))

    if entities:
        async_add_entities(entities)


class ThaSelectBase(ThaEntity, SelectEntity):
    """Base class for Tekmar select entities."""


class ThaFanSelect(ThaSelectBase):
    """Fan cycle selector for a Tekmar thermostat."""

    _attr_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:fan"

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-fan-percent"
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return "Fan Percent"

    @property
    def available(self) -> bool:
        """Return the available."""
        if (
            self._tekmar_tha.fan_percent == ThaValue.NA_8
            or self._tekmar_tha.fan_percent is None
            or self._tekmar_tha.tha_device["attributes"].FanPercent == 0
        ):
            return False

        return super().available

    @property
    def options(self):
        """Return the options."""
        if self._tekmar_tha.config_vent_mode is True:
            return ["0", "10", "20", "30", "40", "50", "60", "70", "80", "90", "100"]
        return ["0", "100"]

    @property
    def current_option(self) -> str:
        """Return the current option."""
        if (
            self._tekmar_tha.tha_device["type"] in [99203, 99202, 99201]
            and self._tekmar_tha.fan_percent is not None
        ):
            return str(self._tekmar_tha.fan_percent * 10)

        return str(self._tekmar_tha.fan_percent)

    async def async_select_option(self, option: str) -> None:
        """Select option."""
        if option in ["0", "10", "20", "30", "40", "50", "60", "70", "80", "90", "100"]:
            if self._tekmar_tha.tha_device["type"] in [99203, 99202, 99201]:
                value = int(option) // 10
                await self._tekmar_tha.set_fan_percent_txqueue(value)

            else:
                value = int(option)
                await self._tekmar_tha.set_fan_percent_txqueue(value)

        else:
            raise ValueError
