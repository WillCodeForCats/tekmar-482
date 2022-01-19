from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:

    hub = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []

    for gateway in hub.tha_gateway:
        entities.append(ReportingState(gateway, config_entry))
        if hub.tha_pr_ver in [2,3]:
            entities.append(SetbackEnable(gateway, config_entry))

    if entities:
        async_add_entities(entities)


class ThaBinarySensorBase(BinarySensorEntity):

    should_poll = False

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        self._tekmar_tha = tekmar_tha
        self._config_entry = config_entry

    # To link this entity to the cover device, this property must return an
    # identifiers value matching that used in the cover, but no other information such
    # as name. If name is returned, this entity will then also become a device in the
    # HA UI.
    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return self._tekmar_tha.device_info

    # This property is important to let HA know if this entity is online or not.
    # If an entity is offline (return False), the UI will refelect this.
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
        # Sensors should also register callbacks to HA when their state changes
        self._tekmar_tha.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        self._tekmar_tha.remove_callback(self.async_write_ha_state)

class ReportingState(ThaBinarySensorBase):
    entity_category = EntityCategory.DIAGNOSTIC
    device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, tekmar_tha, config_entry):
        super().__init__(tekmar_tha, config_entry)

        self._attr_unique_id = f"{self.config_entry_id}-gateway-reporting-state"
        self._attr_name = f"{self.config_entry_name.capitalize()} Gateway Reporting State"

    @property
    def is_on(self):
        """Return the state of the sensor."""
        if self._tekmar_tha.reporting_state == 0x01:
            return True
        else:
            return False

class SetbackEnable(ThaBinarySensorBase):
    entity_category = EntityCategory.DIAGNOSTIC
    device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, tekmar_tha, config_entry):
        super().__init__(tekmar_tha, config_entry)

        self._attr_unique_id = f"{self.config_entry_id}-gateway-setback-enable"
        self._attr_name = f"{self.config_entry_name.capitalize()} Gateway Setback Enable"

    @property
    def is_on(self):
        """Return the state of the sensor."""
        if self._tekmar_tha.setback_enable == 0x01:
            return True
        else:
            return False
