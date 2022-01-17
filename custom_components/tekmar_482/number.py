from homeassistant.components.number import (
    NumberEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE, TEMP_CELSIUS
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import (
    DeviceInfo,
    EntityCategory,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, StateType

from .const import (
    DOMAIN,
    THA_NA_8, THA_NA_16
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:

    hub = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    for device in hub.tha_devices:
        if DEVICE_FEATURES[device.tha_device['type']]['fan']:
            entities.append(TheHumiditySetMax(device, config_entry))
            entities.append(TheHumiditySetMin(device, config_entry))

    if entities:
        async_add_entities(entities)


class ThaNumberBase(NumberEntity):

    should_poll = False

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        self._tekmar_tha = tekmar_tha
        self._config_entry = config_entry

    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return self._tekmar_tha.device_info

    @property
    def available(self) -> bool:
        """Return True if roller and hub is available."""
        return self._tekmar_tha.online and self._tekmar_tha.hub.online

    @property
    def config_entry_id(self):
        """Return True if roller and hub is available."""
        return self._config_entry.entry_id

    @property
    def config_entry_name(self):
        return self._config_entry.data['name']

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        self._tekmar_tha.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        self._tekmar_tha.remove_callback(self.async_write_ha_state)

class TheHumiditySetMax(ThaNumberBase):

    unit_of_measurement = PERCENTAGE
    icon = 'mdi:water-percent'
    min_value = 20
    max_value = 80
    
    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

        self._attr_unique_id = f"{self.config_entry_id}-{self._tekmar_tha.model}-{self._tekmar_tha.device_id}-humidity-max-setpoint"
        self._attr_name = f"{self._tekmar_tha.tha_full_device_name} Humidity Maximum Setpoint"

    #async def async_set_value(self, value: float) -> None:

    @property
    def available(self) -> bool:        
        if self._tekmar_tha.humidity_setpoint_max == THA_NA_8:
            return False
        else:
            return True

    @property
    def value(self):
        return self._tekmar_tha.humidity_setpoint_max

class TheHumiditySetMin(ThaNumberBase):

    unit_of_measurement = PERCENTAGE
    icon = 'mdi:water-percent'
    min_value = 20
    max_value = 80
    
    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

        self._attr_unique_id = f"{self.config_entry_id}-{self._tekmar_tha.model}-{self._tekmar_tha.device_id}-humidity-min-setpoint"
        self._attr_name = f"{self._tekmar_tha.tha_full_device_name} Humidity Minimum Setpoint"

    #async def async_set_value(self, value: float) -> None:

    @property
    def available(self) -> bool:        
        if self._tekmar_tha.humidity_setpoint_min == THA_NA_8:
            return False
        else:
            return True

    @property
    def value(self):
        return self._tekmar_tha.humidity_setpoint_min
