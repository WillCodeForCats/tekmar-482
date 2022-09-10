from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    FAN_AUTO,
    FAN_ON,
    PRESET_AWAY,
    PRESET_HOME,
    PRESET_SLEEP,
)
from homeassistant.components.climate.const import ClimateEntityFeature as Feature
from homeassistant.components.climate.const import HVACAction, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DEVICE_FEATURES,
    DEVICE_TYPES,
    DOMAIN,
    THA_NA_8,
    THA_NA_16,
    THA_TYPE_THERMOSTAT,
)
from .helpers import degCtoE, degEtoC, degHtoC


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:

    hub = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    for device in hub.tha_devices:
        if DEVICE_TYPES[device.tha_device['type']] == THA_TYPE_THERMOSTAT:
            entities.append(ThaClimateThermostat(device, config_entry))

    if entities:
        async_add_entities(entities)


class ThaClimateBase(ClimateEntity):
    should_poll = False

    def __init__(self, tekmar_tha, config_entry):
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

class ThaClimateThermostat(ThaClimateBase):
    temperature_unit = TEMP_CELSIUS
    max_humidity = 80
    min_humidity = 20

    def __init__(self, tekmar_tha, config_entry):
        super().__init__(tekmar_tha, config_entry)

        self._attr_unique_id = f"{self.config_entry_id}-{self._tekmar_tha.model}-{self._tekmar_tha.device_id}-climate"
        self._attr_name = f"{self._tekmar_tha.tha_full_device_name} Climate"
        
        self._last_mode_setting = 0x00
    
    @property
    def max_temp(self):
        if self.hvac_mode == HVACMode.OFF:
            return None
        
        else:
            if self._tekmar_tha.config_heat_setpoint_max >= self._tekmar_tha.config_cool_setpoint_max:
                return self._tekmar_tha.config_heat_setpoint_max
            else:
                return self._tekmar_tha.config_cool_setpoint_max
        
    @property
    def min_temp(self):
        if self.hvac_mode == HVACMode.OFF:
            return None
        
        else:
            if self._tekmar_tha.config_heat_setpoint_min <= self._tekmar_tha.config_cool_setpoint_min:
                return self._tekmar_tha.config_heat_setpoint_min
            else:
                return self._tekmar_tha.config_cool_setpoint_min
    
    @property
    def supported_features(self):
        supported_features = 0
        
        if (
            self._tekmar_tha.tha_device['attributes'].Zone_Heating == 1 and
            self._tekmar_tha.tha_device['attributes'].Zone_Cooling == 1
        ):
            supported_features = supported_features | Feature.TARGET_TEMPERATURE_RANGE
        else:
            supported_features = supported_features | Feature.TARGET_TEMPERATURE
    
        if self._tekmar_tha.tha_device['attributes'].Fan_Percent == 1:
            supported_features = supported_features | Feature.FAN_MODE

        if DEVICE_FEATURES[self._tekmar_tha.tha_device['type']]['humid']:
            if (
                (self._tekmar_tha.humidity_setpoint_min != THA_NA_8 or
                self._tekmar_tha.humidity_setpoint_max != THA_NA_8) and not
                (self._tekmar_tha.humidity_setpoint_min != THA_NA_8 and
                self._tekmar_tha.humidity_setpoint_max != THA_NA_8)
            ):
                supported_features =  supported_features | Feature.TARGET_HUMIDITY
        
        if self._tekmar_tha.config_emergency_heat is True:
            supported_features = supported_features | Feature.AUX_HEAT
        
        return supported_features

    @property
    def current_temperature (self):
        if self._tekmar_tha.current_temperature == THA_NA_16:
            return None

        elif self._tekmar_tha.current_temperature == None:
            return None

        else:
            try:
                return degHtoC(self._tekmar_tha.current_temperature)
                #temp = degHtoC(self._tekmar_tha.current_temperature)
                #return round(temp, 0)

            except TypeError:
                return None

    @property
    def current_humidity (self):
        if (
            self._tekmar_tha.relative_humidity == THA_NA_8 or
            self._tekmar_tha.relative_humidity == None
        ):
            return None

        else:
            return self._tekmar_tha.relative_humidity
    
    @property
    def hvac_modes(self) -> list[str]:

        hvac_modes = [HVACMode.OFF]
        
        if self._tekmar_tha.tha_device['attributes'].Zone_Heating == 1:
            hvac_modes.append(HVACMode.HEAT)

        if self._tekmar_tha.tha_device['attributes'].Zone_Cooling == 1:
            hvac_modes.append(HVACMode.COOL)
            
        if (
            self._tekmar_tha.tha_device['attributes'].Zone_Heating == 1 and
            self._tekmar_tha.tha_device['attributes'].Zone_Cooling == 1
        ):
            hvac_modes.append(HVACMode.HEAT_COOL)

        return hvac_modes

    @property
    def hvac_mode(self):
        if self._tekmar_tha.mode_setting == 0x00:
            return HVACMode.OFF
        elif self._tekmar_tha.mode_setting == 0x01:
            return HVACMode.HEAT
        elif self._tekmar_tha.mode_setting == 0x02:
            return HVACMode.HEAT_COOL
        elif self._tekmar_tha.mode_setting == 0x03:
            return HVACMode.COOL
        elif self._tekmar_tha.mode_setting == 0x04:
            return HVACMode.FAN_ONLY
        elif self._tekmar_tha.mode_setting == 0x05:
            return None
        elif self._tekmar_tha.mode_setting == 0x06:
            return HVACMode.HEAT
        else:
            return None

    @property
    def fan_modes(self):
        if self._tekmar_tha.tha_device['attributes'].Fan_Percent == 1:
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
            return HVACAction.OFF
            
        elif self._tekmar_tha.active_demand == 0x00:
            return HVACAction.IDLE
            
        elif self._tekmar_tha.active_demand == 0x01:
            return HVACAction.HEATING
        
        elif self._tekmar_tha.active_demand == 0x03:
            return HVACAction.COOLING
        
        else:
            return None

    @property
    def target_temperature(self):
        if self._tekmar_tha.tha_device['attributes'].Zone_Heating == 1:
            this_device_setpoint = self._tekmar_tha.heat_setpoint
    
        elif self._tekmar_tha.tha_device['attributes'].Zone_Cooling == 1:
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
                #temp = degEtoC(this_device_setpoint)
                #return round(temp, 0)
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
        heat_setpoint = None
        cool_setpoint = None
        
        if self.supported_features & Feature.TARGET_TEMPERATURE:
            if self._tekmar_tha.tha_device['attributes'].Zone_Heating == 1:
                heat_setpoint = kwargs.get(ATTR_TEMPERATURE)

            elif self._tekmar_tha.tha_device['attributes'].Zone_Cooling == 1:
                cool_setpoint = kwargs.get(ATTR_TEMPERATURE)
     
        elif self.supported_features & Feature.TARGET_TEMPERATURE_RANGE:        
            heat_setpoint = kwargs.get(ATTR_TARGET_TEMP_LOW)
            cool_setpoint = kwargs.get(ATTR_TARGET_TEMP_HIGH)
                 
        if heat_setpoint is not None:
            heat_setpoint = int(degCtoE(heat_setpoint))
            await self._tekmar_tha.set_heat_setpoint_txqueue(heat_setpoint)
            
        if cool_setpoint is not None:
            cool_setpoint = int(degCtoE(cool_setpoint))
            await self._tekmar_tha.set_cool_setpoint_txqueue(cool_setpoint)

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.OFF:
            value = 0x00
        elif hvac_mode == HVACMode.HEAT:
            value = 0x01
        elif hvac_mode == HVACMode.COOL:
            value = 0x03
        elif hvac_mode == HVACMode.HEAT_COOL:
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

    async def async_turn_aux_heat_on(self):
        self._last_mode_setting = self._tekmar_tha.mode_setting
        await self._tekmar_tha.set_mode_setting_txqueue(0x06)
        
    async def async_turn_aux_heat_off(self):
        await self._tekmar_tha.set_mode_setting_txqueue(self._last_mode_setting)
