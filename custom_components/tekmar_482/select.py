"""Component to allow selecting an option from a list as platforms."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_FEATURES, DEVICE_TYPES, DOMAIN, ThaType, ThaValue


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


class ThaSelectBase(SelectEntity):
    """Base class for Tekmar select entities."""

    _attr_should_poll = False

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
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
        return f"{self._tekmar_tha.tha_full_device_name} Fan Percent"

    @property
    def available(self) -> bool:
        """Return the available."""
        if (
            self._tekmar_tha.fan_percent == ThaValue.NA_8
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
        return str(self._tekmar_tha.fan_percent)

    async def async_select_option(self, option: str) -> None:
        """Select option."""
        if option in ["0", "10", "20", "30", "40", "50", "60", "70", "80", "90", "100"]:
            if self._tekmar_tha.tha_device["type"] in [99203, 99202, 99201]:
                value = int(option / 10)
                await self._tekmar_tha.set_fan_percent_txqueue(value)

            else:
                value = int(option)
                await self._tekmar_tha.set_fan_percent_txqueue(value)

        else:
            raise ValueError
