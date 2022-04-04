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

from .helpers import degEtoC

from .const import (
    DOMAIN,
    THA_NA_8, THA_NA_16,
    DEVICE_FEATURES, DEVICE_TYPES, THA_TYPE_THERMOSTAT,
    THA_DEFAULT_COOL_SETPOINT_MAX, THA_DEFAULT_COOL_SETPOINT_MIN,
    THA_DEFAULT_HEAT_SETPOINT_MAX, THA_DEFAULT_HEAT_SETPOINT_MIN
)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:

    hub = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    for device in hub.tha_devices:
        if DEVICE_TYPES[device.tha_device['type']] == THA_TYPE_THERMOSTAT:
            if hub.tha_setback_enable is True:
                entities.append(ThaHeatSetpointDay(device, config_entry))
                entities.append(ThaHeatSetpointNight(device, config_entry))
                entities.append(ThaHeatSetpointAway(device, config_entry))
                entities.append(ThaCoolSetpointDay(device, config_entry))
                entities.append(ThaCoolSetpointNight(device, config_entry))
                entities.append(ThaCoolSetpointAway(device, config_entry))
            else:
                entities.append(ThaHeatSetpoint(device, config_entry))
                entities.append(ThaCoolSetpoint(device, config_entry))

            if DEVICE_FEATURES[device.tha_device['type']]['humid']:
                entities.append(ThaHumiditySetMax(device, config_entry))
                entities.append(ThaHumiditySetMin(device, config_entry))

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
        return self._tekmar_tha.online and self._tekmar_tha.hub.online

    @property
    def config_entry_id(self):
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


class ThaHumiditySetMax(ThaNumberBase):

    unit_of_measurement = PERCENTAGE
    icon = 'mdi:water-percent'
    min_value = 20
    max_value = 80
    
    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

        self._attr_unique_id = f"{self.config_entry_id}-{self._tekmar_tha.model}-{self._tekmar_tha.device_id}-humidity-max-setpoint"
        self._attr_name = f"{self._tekmar_tha.tha_full_device_name} Humidity Maximum Setpoint"

    async def async_set_value(self, value: float) -> None:
        value = int(value)
        await self._tekmar_tha.set_humidity_setpoint_max_txqueue(value)

    @property
    def entity_registry_enabled_default(self) -> bool:
        if (
            self._tekmar_tha.humidity_setpoint_max is not None and
            self._tekmar_tha.humidity_setpoint_min != THA_NA_8 and
            self._tekmar_tha.humidity_setpoint_max != THA_NA_8
        ):
            return True
        else:
            return False

    @property
    def available(self) -> bool:        
        if self._tekmar_tha.humidity_setpoint_max == THA_NA_8:
            return False
        else:
            return True

    @property
    def value(self):
        return self._tekmar_tha.humidity_setpoint_max

class ThaHumiditySetMin(ThaNumberBase):

    unit_of_measurement = PERCENTAGE
    icon = 'mdi:water-percent'
    min_value = 20
    max_value = 80
    
    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

        self._attr_unique_id = f"{self.config_entry_id}-{self._tekmar_tha.model}-{self._tekmar_tha.device_id}-humidity-min-setpoint"
        self._attr_name = f"{self._tekmar_tha.tha_full_device_name} Humidity Minimum Setpoint"

    async def async_set_value(self, value: float) -> None:
        value = int(value)
        await self._tekmar_tha.set_humidity_setpoint_min_txqueue(value)

    @property
    def entity_registry_enabled_default(self) -> bool:
        if (
            self._tekmar_tha.humidity_setpoint_min is not None and
            self._tekmar_tha.humidity_setpoint_min != THA_NA_8 and
            self._tekmar_tha.humidity_setpoint_max != THA_NA_8
        ):
            return True
        else:
            return False

    @property
    def available(self) -> bool:        
        if self._tekmar_tha.humidity_setpoint_min == THA_NA_8:
            return False
        else:
            return True

    @property
    def value(self):
        return self._tekmar_tha.humidity_setpoint_min

class ThaHeatSetpoint(ThaNumberBase):

    unit_of_measurement = TEMP_CELSIUS
    icon = 'mdi:thermostat'
    
    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

        self._attr_unique_id = f"{self.config_entry_id}-{self._tekmar_tha.model}-{self._tekmar_tha.device_id}-heat-setpoint"
        self._attr_name = f"{self._tekmar_tha.tha_full_device_name} Heat Setpoint"

    #async def async_set_value(self, value: float) -> None:
    #    value = int(value)
    #    await self._tekmar_tha.set_humidity_setpoint_min_txqueue(value)

    @property
    def entity_registry_enabled_default(self) -> bool:
        if self._tekmar_tha.setback_enable is False:
            return True
        else:
            return False

    @property
    def available(self) -> bool:        
        if self._tekmar_tha.heat_setpoint == THA_NA_8:
            return False

        elif self._tekmar_tha.tha_device['attributes'].Zone_Heating == 0:
            return False
            
        else:
            return True

    @property
    def value(self):
        try:
            return degEtoC(self._tekmar_tha.heat_setpoint)
        except TypeError:
            return None

    @property
    def min_value(self):
        if self._tekmar_tha._config_heat_setpoint_min is None:
            return self._tekmar_tha.hub.convert_temp(THA_DEFAULT_HEAT_SETPOINT_MIN)
        else:
            return self._tekmar_tha.hub.convert_temp(self._tekmar_tha._config_heat_setpoint_min)
    
    @property
    def max_value(self):
        if self._tekmar_tha._config_heat_setpoint_max is None:
            return self._tekmar_tha.hub.convert_temp(THA_DEFAULT_HEAT_SETPOINT_MAX)
        else:
            return self._tekmar_tha.hub.convert_temp(self._tekmar_tha._config_heat_setpoint_max)
    
class ThaCoolSetpoint(ThaNumberBase):

    unit_of_measurement = TEMP_CELSIUS
    icon = 'mdi:thermostat'
    
    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

        self._attr_unique_id = f"{self.config_entry_id}-{self._tekmar_tha.model}-{self._tekmar_tha.device_id}-cool-setpoint"
        self._attr_name = f"{self._tekmar_tha.tha_full_device_name} Cool Setpoint"

    #async def async_set_value(self, value: float) -> None:
    #    value = int(value)
    #    await self._tekmar_tha.set_humidity_setpoint_min_txqueue(value)

    @property
    def entity_registry_enabled_default(self) -> bool:
        if self._tekmar_tha.setback_enable is False:
            return True
        else:
            return False

    @property
    def available(self) -> bool:        
        if self._tekmar_tha.cool_setpoint == THA_NA_8:
            return False
        
        elif self._tekmar_tha.tha_device['attributes'].Zone_Cooling == 0:
            return False
            
        else:
            return True

    @property
    def value(self):
        try:
            return degEtoC(self._tekmar_tha.cool_setpoint)
        except TypeError:
            return None
    
    @property
    def min_value(self):
        if self._tekmar_tha._config_cool_setpoint_min is None:
            return self._tekmar_tha.hub.convert_temp(THA_DEFAULT_COOL_SETPOINT_MIN)
        else:
            return self._tekmar_tha.hub.convert_temp(self._tekmar_tha._config_cool_setpoint_min)
    
    @property
    def max_value(self):
        if self._tekmar_tha._config_cool_setpoint_max is None:
            return self._tekmar_tha.hub.convert_temp(THA_DEFAULT_COOL_SETPOINT_MAX)
        else:
            return self._tekmar_tha.hub.convert_temp(self._tekmar_tha._config_cool_setpoint_max)
