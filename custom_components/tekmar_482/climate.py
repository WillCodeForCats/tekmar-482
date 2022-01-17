from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE, SUPPORT_TARGET_TEMPERATURE_RANGE, SUPPORT_FAN_MODE,
    SUPPORT_TARGET_HUMIDITY,
    HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_HEAT_COOL, HVAC_MODE_FAN_ONLY,
    CURRENT_HVAC_OFF, CURRENT_HVAC_IDLE, CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL,
    ATTR_TARGET_TEMP_LOW, ATTR_TARGET_TEMP_HIGH,
    PRESET_HOME, PRESET_AWAY, PRESET_SLEEP,
    FAN_ON, FAN_AUTO
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE, TEMP_CELSIUS
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    DEVICE_FEATURES,
    THA_NA_8, THA_NA_16,
)

def degCtoF(degC):
    """ convert Celcius to degF """
    return ((degC * 9/5) + 32)

def degEtoC(degE):
    """ convert degE to degC """
    #degE = 2*(degC)
    return (degE / 2)

def degCtoE(degC):
    """ convert degE to degC """
    #degE = 2*(degC)
    return (2 * degC)

def degHtoF(degH):
    """ convert degH to degF """
    #degH = 10*(degF) + 850
    return ((degH - 850) / 10)

def degFtoC(degF):
    """ convert degF to degC """
    #degC = (degF - 32) / 1.8
    return ((degF - 32) / 1.8)
    
def degHtoC(degH):
    return degFtoC(degHtoF(degH))


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:

    hub = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    for device in hub.tha_devices:
        entities.append(ThaClimateThermostat(device, config_entry))

    if entities:
        async_add_entities(entities)


class ThaClimateBase(ClimateEntity):

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

class ThaClimateThermostat(ThaClimateBase):

    temperature_unit = TEMP_CELSIUS
    max_humidity = 80
    min_humidity = 20

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

        self._attr_unique_id = f"{self.config_entry_id}-{self._tekmar_tha.model}-{self._tekmar_tha.device_id}-climate"
        self._attr_name = f"{self._tekmar_tha.tha_full_device_name} Climate"
        
    @property
    def supported_features(self):
        supported_features = SUPPORT_TARGET_TEMPERATURE_RANGE
    
        if DEVICE_FEATURES[self._tekmar_tha.tha_device['type']]['fan']:
            supported_features = supported_features | SUPPORT_FAN_MODE

        if DEVICE_FEATURES[self._tekmar_tha.tha_device['type']]['humid']:
            if (
                (self._tekmar_tha.humidity_setpoint_min != THA_NA_8 or
                self._tekmar_tha.humidity_setpoint_max != THA_NA_8) and not
                (self._tekmar_tha.humidity_setpoint_min != THA_NA_8 and
                self._tekmar_tha.humidity_setpoint_max != THA_NA_8)
            ):
                supported_features =  supported_features | SUPPORT_TARGET_HUMIDITY
        
        return supported_features

    @property
    def current_temperature (self):
        if self._tekmar_tha.current_temperature == THA_NA_16:
            return None

        elif self._tekmar_tha.current_temperature == None:
            return None

        else:
            try:
                temp = degHtoC(self._tekmar_tha.current_temperature) # degH need degC
                return round(temp, 0)

            except TypeError:
                return None

    @property
    def current_humidity (self):
        """Return the state of the sensor."""
        if (
            self._tekmar_tha.relative_humidity == THA_NA_8 or
            self._tekmar_tha.relative_humidity == None
        ):
            return None

        else:
            return self._tekmar_tha.relative_humidity
    
    @property
    def hvac_modes(self) -> list[str]:

        hvac_modes = [HVAC_MODE_OFF]
        
        if self._tekmar_tha.tha_device['attributes'].Zone_Heating:
            hvac_modes.append(HVAC_MODE_HEAT)

        if self._tekmar_tha.tha_device['attributes'].Zone_Cooling:
            hvac_modes.append(HVAC_MODE_COOL)
            
        if (
            self._tekmar_tha.tha_device['attributes'].Zone_Heating and
            self._tekmar_tha.tha_device['attributes'].Zone_Cooling
        ):
            hvac_modes.append(HVAC_MODE_HEAT_COOL)

        return hvac_modes

    @property
    def hvac_mode(self):
        if self._tekmar_tha.mode_setting == 0x00:
            return HVAC_MODE_OFF
        elif self._tekmar_tha.mode_setting == 0x01:
            return HVAC_MODE_HEAT
        elif self._tekmar_tha.mode_setting == 0x02:
            return HVAC_MODE_HEAT_COOL
        elif self._tekmar_tha.mode_setting == 0x03:
            return HVAC_MODE_COOL
        elif self._tekmar_tha.mode_setting == 0x04:
            return HVAC_MODE_FAN_ONLY
        elif self._tekmar_tha.mode_setting == 0x05:
            return None
        elif self._tekmar_tha.mode_setting == 0x06:
            #tekmar "emergency" mode, HA does not have equivalent
            return HVAC_MODE_HEAT
        else:
            return None

    @property
    def fan_modes(self):
        if DEVICE_FEATURES[self._tekmar_tha.tha_device['type']]['fan']:
            return [FAN_ON, FAN_AUTO]
        else:
            return None

    @property
    def fan_mode(self):
        if self._tekmar_tha.tha_device['type'] in [99203, 99202, 99201]:
            if self._tekmar_tha.fan_percent == 10:
                return FAN_ON
            else:
                return FAN_AUTO
        
        else:
            if self._tekmar_tha.fan_percent == 100:
                return FAN_ON
            else:
                return FAN_AUTO
                    
    @property
    def is_aux_heat(self):
        if self._tekmar_tha.mode_setting == 0x06:
            return True
        else:
            return False

    @property
    def target_humidity(self):
        if (
            self._tekmar_tha.humidity_setpoint_min != THA_NA_8 and
            self._tekmar_tha.humidity_setpoint_max == THA_NA_8
        ):
            return self._tekmar_tha.humidity_setpoint_min
            
        elif (
            self._tekmar_tha.humidity_setpoint_min == THA_NA_8 and
            self._tekmar_tha.humidity_setpoint_max != THA_NA_8
        ):
            return self._tekmar_tha.humidity_setpoint_max
        
        elif (
            self._tekmar_tha.humidity_setpoint_min == THA_NA_8 and
            self._tekmar_tha.humidity_setpoint_max == THA_NA_8
        ):
            return None
        
        else:
            return None
            
    @property
    def preset_mode(self):
        if self._tekmar_tha.setback_state == 0x00:
            return PRESET_HOME
            
        elif self._tekmar_tha.setback_state == 0x01:
            return PRESET_SLEEP
            
        elif self._tekmar_tha.setback_state == 0x02:
            return PRESET_HOME
        
        elif self._tekmar_tha.setback_state == 0x03:
            return PRESET_SLEEP
        
        elif self._tekmar_tha.setback_state == 0x04:
            return PRESET_HOME
        
        elif self._tekmar_tha.setback_state == 0x05:
            return PRESET_SLEEP
        
        elif self._tekmar_tha.setback_state == 0x06:
            return PRESET_AWAY
        
        else:
            return None        

    @property
    def hvac_action(self):
        if self._tekmar_tha.mode_setting == 0x00:
            return CURRENT_HVAC_OFF
            
        elif self._tekmar_tha.active_demand == 0x00:
            return CURRENT_HVAC_IDLE
            
        elif self._tekmar_tha.active_demand == 0x01:
            return CURRENT_HVAC_HEAT
        
        elif self._tekmar_tha.active_demand == 0x03:
            return CURRENT_HVAC_COOL
        
        else:
            return None

    @property
    def target_temperature(self):
        if (
            self._tekmar_tha.tha_device['attributes'].Zone_Heating and
            self._tekmar_tha.mode_setting == 0x03
        ):
            this_device_setpoint = self._tekmar_tha.heat_setpoint
    
        elif (
            self._tekmar_tha.tha_device['attributes'].Zone_Cooling and
            self._tekmar_tha.mode_setting == 0x01
        ):
            this_device_setpoint = self._tekmar_tha.cool_setpoint
        
        else:
            return None
        
        if (
            this_device_setpoint == THA_NA_8 or
            this_device_setpoint == None
        ):
            return None

        else:
            try:
                return degEtoC(this_device_setpoint)

            except TypeError:
                return None

    @property
    def target_temperature_high(self):
        if (
            self._tekmar_tha.cool_setpoint == THA_NA_8 or
            self._tekmar_tha.cool_setpoint == None
        ):
            return None

        else:
            try:
                temp = degEtoC(self._tekmar_tha.cool_setpoint) # degH need degC
                return round(temp, 0)

            except TypeError:
                return None

    @property
    def target_temperature_low(self):
        if (
            self._tekmar_tha.heat_setpoint == THA_NA_8 or
            self._tekmar_tha.heat_setpoint == None
        ):
            return None

        else:
            try:
                temp = degEtoC(self._tekmar_tha.heat_setpoint) # degH need degC
                return round(temp, 0)

            except TypeError:
                return None

    async def async_set_temperature(self, **kwargs):
        # for SUPPORT_TARGET_TEMPERATURE
        # ATTR_TEMPERATURE
        # for SUPPORT_TARGET_TEMPERATURE_RANGE
        # ATTR_TARGET_TEMP_LOW, ATTR_TARGET_TEMP_HIGH
        #value = kwargs[ATTR_TEMPERATURE]
        #await self._tekmar_tha.async_set_temperature(value)
        
        heat_setpoint = kwargs.get(ATTR_TARGET_TEMP_LOW)
        cool_setpoint = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        
        if heat_setpoint is not None:
            heat_setpoint = int(degCtoE(heat_setpoint))
            await self._tekmar_tha.set_heat_setpoint_txqueue(heat_setpoint)
            
        if cool_setpoint is not None:
            cool_setpoint = int(degCtoE(cool_setpoint))
            await self._tekmar_tha.set_cool_setpoint_txqueue(cool_setpoint)

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVAC_MODE_OFF:
            value = 0x00
        elif hvac_mode == HVAC_MODE_HEAT:
            value = 0x01
        elif hvac_mode == HVAC_MODE_COOL:
            value = 0x03
        elif hvac_mode == HVAC_MODE_HEAT_COOL:
            value = 0x02
        else:
            raise NotImplementedError()
        
        await self._tekmar_tha.set_mode_setting_txqueue(value)

    async def async_set_fan_mode(self, fan_mode):
        if fan_mode == FAN_ON:
            if self._tekmar_tha.tha_device['type'] in [99203, 99202, 99201]:
                value = 10
            else:
                value = 100
            
        elif fan_mode == FAN_AUTO:
            value = 0
            
        else:
            raise NotImplementedError()
            
    async def async_set_humidity(self, humidity):

        if (
            self._tekmar_tha.humidity_setpoint_min != THA_NA_8 and
            self._tekmar_tha.humidity_setpoint_max == THA_NA_8
        ):
            await self._tekmar_tha.set_humidity_setpoint_min_txqueue(humidity)
            
        elif (
            self._tekmar_tha.humidity_setpoint_min == THA_NA_8 and
            self._tekmar_tha.humidity_setpoint_max != THA_NA_8
        ):
            await self._tekmar_tha.set_humidity_setpoint_max_txqueue(humidity)
        
        elif (
            self._tekmar_tha.humidity_setpoint_min == THA_NA_8 and
            self._tekmar_tha.humidity_setpoint_max == THA_NA_8
        ):
            pass
        
        else:
            pass
