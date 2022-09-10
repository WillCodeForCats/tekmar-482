from typing import Any, Dict, Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, StateType

from .const import (
    ATTR_MANUFACTURER,
    DEVICE_FEATURES,
    DEVICE_TYPES,
    DOMAIN,
    NETWORK_ERRORS,
    THA_NA_8,
    THA_NA_16,
    THA_TYPE_THERMOSTAT,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:

    hub = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    for device in hub.tha_devices:
        if DEVICE_TYPES[device.tha_device["type"]] == THA_TYPE_THERMOSTAT:
            if DEVICE_FEATURES[device.tha_device["type"]]["fan"]:
                entities.append(ThaFanSelect(device, config_entry))

    if entities:
        async_add_entities(entities)


class ThaSelectBase(SelectEntity):
    should_poll = False

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        self._tekmar_tha = tekmar_tha
        self._config_entry = config_entry

    @property
    def device_info(self):
        return self._tekmar_tha.device_info

    @property
    def available(self) -> bool:
        return self._tekmar_tha.online and self._tekmar_tha.hub.online

    @property
    def config_entry_id(self):
        return self._config_entry.entry_id

    @property
    def config_entry_name(self):
        return self._config_entry.data["name"]

    async def async_added_to_hass(self):
        self._tekmar_tha.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self._tekmar_tha.remove_callback(self.async_write_ha_state)


class ThaFanSelect(ThaSelectBase):
    unit_of_measurement = PERCENTAGE
    icon = "mdi:fan"

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

        self._attr_unique_id = f"{self.config_entry_id}-{self._tekmar_tha.model}-{self._tekmar_tha.device_id}-fan-percent"
        self._attr_name = f"{self._tekmar_tha.tha_full_device_name} Fan Percent"

    async def async_select_option(self, option: str) -> None:
        if option in ["0", "10", "20", "30", "40", "50", "60", "70", "80", "90", "100"]:

            if self._tekmar_tha.tha_device["type"] in [99203, 99202, 99201]:
                value = int(option / 10)
                await self._tekmar_tha.set_fan_percent_txqueue(value)

            else:
                value = int(option)
                await self._tekmar_tha.set_fan_percent_txqueue(value)

        else:
            raise ValueError

    @property
    def available(self) -> bool:
        if self._tekmar_tha.fan_percent == THA_NA_8:
            return False

        elif self._tekmar_tha.tha_device["attributes"].Fan_Percent == 0:
            return False

        else:
            return True

    @property
    def options(self):
        if self._tekmar_tha.config_vent_mode is True:
            return ["0", "10", "20", "30", "40", "50", "60", "70", "80", "90", "100"]
        else:
            return ["0", "100"]

    @property
    def current_option(self) -> str:
        return str(self._tekmar_tha.fan_percent)
