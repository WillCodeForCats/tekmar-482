from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_FEATURES, DEVICE_TYPES, DOMAIN, THA_NA_8, THA_TYPE_THERMOSTAT


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:

    hub = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    for gateway in hub.tha_gateway:
        if hub.tha_pr_ver in [2,3]:
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
        if DEVICE_TYPES[device.tha_device['type']] == THA_TYPE_THERMOSTAT:
            if DEVICE_FEATURES[device.tha_device['type']]['emer']:
                entities.append(ConfigEmergencyHeat(device, config_entry))
            if DEVICE_FEATURES[device.tha_device['type']]['fan']:
                entities.append(ConfigVentMode(device, config_entry))

    if entities:
        async_add_entities(entities)

class ThaSwitchBase(SwitchEntity):
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
        return self._config_entry.data['name']

    async def async_added_to_hass(self):
        self._tekmar_tha.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self._tekmar_tha.remove_callback(self.async_write_ha_state)

class ThaSetpointGroup(ThaSwitchBase):
    icon = 'mdi:select-group'

    def __init__(self, tekmar_tha, config_entry, group: int):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)
        
        self._setpoint_group = group
        self._attr_unique_id = f"{self.config_entry_id}-gateway-setpoint-group-{int(self._setpoint_group):02d}"
        self._attr_name = f"{self.config_entry_name.capitalize()} Gateway Setpoint Group {int(self._setpoint_group):02d}"

    async def async_turn_on(self, **kwargs):
        await self._tekmar_tha.set_setpoint_group_txqueue(self._setpoint_group, 0x01)

    async def async_turn_off(self, **kwargs):
        await self._tekmar_tha.set_setpoint_group_txqueue(self._setpoint_group, 0x00)

    @property
    def available(self) -> bool:
        setpoint_groups = self._tekmar_tha.setpoint_groups
        
        if setpoint_groups[self._setpoint_group] == None:
            return False
            
        elif setpoint_groups[self._setpoint_group] == THA_NA_8:
            return False
            
        else:
            return True

    @property
    def is_on(self):
        setpoint_groups = self._tekmar_tha.setpoint_groups
        
        if setpoint_groups[self._setpoint_group] == 0x00:
            return False
        elif setpoint_groups[self._setpoint_group] == 0x01:
            return True
        else:
            raise NotImplementedError

class ConfigEmergencyHeat(ThaSwitchBase):
    entity_category = EntityCategory.CONFIG
    icon = 'mdi:hvac'

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)
        
        self._attr_unique_id = f"{self.config_entry_id}-{self._tekmar_tha.model}-{self._tekmar_tha.device_id}-config-emer-heat"
        self._attr_name = f"{self._tekmar_tha.tha_full_device_name} Emergency/Aux Heat"

    async def async_turn_on(self, **kwargs):
        await self._tekmar_tha.set_config_emer_heat(True)

    async def async_turn_off(self, **kwargs):
        await self._tekmar_tha.set_config_emer_heat(False)

    @property
    def available(self) -> bool:        
        if DEVICE_FEATURES[self._tekmar_tha.tha_device['type']]['emer']:
            return True
        else:
            return False

    @property
    def is_on(self):        
        if self._tekmar_tha.config_emergency_heat is True:
            return True
        else:
            return False

class ConfigVentMode(ThaSwitchBase):
    entity_category = EntityCategory.CONFIG
    icon = 'mdi:fan-plus'

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)
        
        self._attr_unique_id = f"{self.config_entry_id}-{self._tekmar_tha.model}-{self._tekmar_tha.device_id}-config-vent-mode"
        self._attr_name = f"{self._tekmar_tha.tha_full_device_name} Enable Vent Mode"

    async def async_turn_on(self, **kwargs):
        await self._tekmar_tha.set_config_vent_mode(True)

    async def async_turn_off(self, **kwargs):
        await self._tekmar_tha.set_config_vent_mode(False)

    @property
    def available(self) -> bool:        
        if DEVICE_FEATURES[self._tekmar_tha.tha_device['type']]['fan']:
            return True
        else:
            return False

    @property
    def is_on(self):        
        if self._tekmar_tha.config_vent_mode is True:
            return True
        else:
            return False
