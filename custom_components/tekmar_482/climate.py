"""Provides functionality to interact with climate devices."""

from __future__ import annotations

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
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DEVICE_FEATURES,
    DEVICE_TYPES,
    DOMAIN,
    ThaActiveDemand,
    ThaDeviceMode,
    ThaType,
    ThaValue,
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
        if DEVICE_TYPES[device.tha_device["type"]] == ThaType.THERMOSTAT:
            entities.append(ThaClimateThermostat(device, config_entry))

    if entities:
        async_add_entities(entities)


class ThaClimateBase(ClimateEntity):
    """Base class for Tekmar climate entities."""

    should_poll = False
    _enable_turn_on_off_backwards_compatibility = False

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
        return self._config_entry.data["name"]

    async def async_added_to_hass(self):
        self._tekmar_tha.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self._tekmar_tha.remove_callback(self.async_write_ha_state)


class ThaClimateThermostat(ThaClimateBase):
    """A Tekmar thermostat entity."""

    temperature_unit = UnitOfTemperature.CELSIUS
    max_humidity = 80
    min_humidity = 20

    def __init__(self, tekmar_tha, config_entry):
        super().__init__(tekmar_tha, config_entry)

        self._last_mode_setting = 0x00

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-climate"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name}"

    @property
    def max_temp(self):
        if self.hvac_mode == HVACMode.OFF:
            return None

        else:
            if (
                self._tekmar_tha.config_heat_setpoint_max
                >= self._tekmar_tha.config_cool_setpoint_max
            ):
                return self._tekmar_tha.config_heat_setpoint_max
            else:
                return self._tekmar_tha.config_cool_setpoint_max

    @property
    def min_temp(self):
        if self.hvac_mode == HVACMode.OFF:
            return None

        else:
            if (
                self._tekmar_tha.config_heat_setpoint_min
                <= self._tekmar_tha.config_cool_setpoint_min
            ):
                return self._tekmar_tha.config_heat_setpoint_min
            else:
                return self._tekmar_tha.config_cool_setpoint_min

    @property
    def supported_features(self):
        supported_features = Feature.TURN_OFF

        if (
            self._tekmar_tha.tha_device["attributes"].ZoneHeating == 1
            and self._tekmar_tha.tha_device["attributes"].ZoneCooling == 1
        ):
            supported_features = supported_features | Feature.TARGET_TEMPERATURE_RANGE
        else:
            supported_features = supported_features | Feature.TARGET_TEMPERATURE

        if self._tekmar_tha.tha_device["attributes"].FanPercent == 1:
            supported_features = supported_features | Feature.FAN_MODE

        if DEVICE_FEATURES[self._tekmar_tha.tha_device["type"]]["humid"]:
            if (
                self._tekmar_tha.humidity_setpoint_min != ThaValue.NA_8
                or self._tekmar_tha.humidity_setpoint_max != ThaValue.NA_8
            ) and not (
                self._tekmar_tha.humidity_setpoint_min != ThaValue.NA_8
                and self._tekmar_tha.humidity_setpoint_max != ThaValue.NA_8
            ):
                supported_features = supported_features | Feature.TARGET_HUMIDITY

        if self._tekmar_tha.config_emergency_heat is True:
            supported_features = supported_features | Feature.AUX_HEAT

        return supported_features

    @property
    def current_temperature(self):
        if self._tekmar_tha.current_temperature == ThaValue.NA_16:
            return None

        elif self._tekmar_tha.current_temperature is None:
            return None

        else:
            try:
                return degHtoC(self._tekmar_tha.current_temperature)
                # temp = degHtoC(self._tekmar_tha.current_temperature)
                # return round(temp, 0)

            except TypeError:
                return None

    @property
    def current_humidity(self):
        if (
            self._tekmar_tha.relative_humidity == ThaValue.NA_8
            or self._tekmar_tha.relative_humidity is None
        ):
            return None

        else:
            return self._tekmar_tha.relative_humidity

    @property
    def hvac_modes(self) -> list[str]:
        hvac_modes = [HVACMode.OFF]

        if self._tekmar_tha.tha_device["attributes"].ZoneHeating == 1:
            hvac_modes.append(HVACMode.HEAT)

        if self._tekmar_tha.tha_device["attributes"].ZoneCooling == 1:
            hvac_modes.append(HVACMode.COOL)

        if (
            self._tekmar_tha.tha_device["attributes"].ZoneHeating == 1
            and self._tekmar_tha.tha_device["attributes"].ZoneCooling == 1
        ):
            hvac_modes.append(HVACMode.HEAT_COOL)

        return hvac_modes

    @property
    def hvac_mode(self):
        if self._tekmar_tha.mode_setting == ThaDeviceMode.OFF:
            return HVACMode.OFF
        elif self._tekmar_tha.mode_setting == ThaDeviceMode.HEAT:
            return HVACMode.HEAT
        elif self._tekmar_tha.mode_setting == ThaDeviceMode.AUTO:
            return HVACMode.HEAT_COOL
        elif self._tekmar_tha.mode_setting == ThaDeviceMode.COOL:
            return HVACMode.COOL
        elif self._tekmar_tha.mode_setting == ThaDeviceMode.VENT:
            return HVACMode.FAN_ONLY
        elif self._tekmar_tha.mode_setting == ThaDeviceMode.EMERGENCY:
            return HVACMode.HEAT
        else:
            return None

    @property
    def fan_modes(self):
        if self._tekmar_tha.tha_device["attributes"].FanPercent == 1:
            return [FAN_ON, FAN_AUTO]
        else:
            return None

    @property
    def fan_mode(self):
        if self._tekmar_tha.tha_device["type"] in [99203, 99202, 99201]:
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
        return self._tekmar_tha.mode_setting == 0x06

    @property
    def target_humidity(self):
        if (
            self._tekmar_tha.humidity_setpoint_min != ThaValue.NA_8
            and self._tekmar_tha.humidity_setpoint_max == ThaValue.NA_8
        ):
            return self._tekmar_tha.humidity_setpoint_min

        elif (
            self._tekmar_tha.humidity_setpoint_min == ThaValue.NA_8
            and self._tekmar_tha.humidity_setpoint_max != ThaValue.NA_8
        ):
            return self._tekmar_tha.humidity_setpoint_max

        elif (
            self._tekmar_tha.humidity_setpoint_min == ThaValue.NA_8
            and self._tekmar_tha.humidity_setpoint_max == ThaValue.NA_8
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
        if self._tekmar_tha.mode_setting == ThaDeviceMode.OFF:
            return HVACAction.OFF

        elif self._tekmar_tha.active_demand == ThaActiveDemand.IDLE:
            return HVACAction.IDLE

        elif self._tekmar_tha.active_demand == ThaActiveDemand.HEAT:
            return HVACAction.HEATING

        elif self._tekmar_tha.active_demand == ThaActiveDemand.COOL:
            return HVACAction.COOLING

        else:
            return None

    @property
    def target_temperature(self):
        if self._tekmar_tha.tha_device["attributes"].ZoneHeating == 1:
            this_device_setpoint = self._tekmar_tha.heat_setpoint

        elif self._tekmar_tha.tha_device["attributes"].ZoneCooling == 1:
            this_device_setpoint = self._tekmar_tha.cool_setpoint

        else:
            return None

        if this_device_setpoint == ThaValue.NA_8 or this_device_setpoint is None:
            return None

        else:
            try:
                # temp = degEtoC(this_device_setpoint)
                # return round(temp, 0)
                return degEtoC(this_device_setpoint)

            except TypeError:
                return None

    @property
    def target_temperature_high(self):
        if (
            self._tekmar_tha.cool_setpoint == ThaValue.NA_8
            or self._tekmar_tha.cool_setpoint is None
        ):
            return None

        else:
            try:
                return degEtoC(self._tekmar_tha.cool_setpoint)

            except TypeError:
                return None

    @property
    def target_temperature_low(self):
        if (
            self._tekmar_tha.heat_setpoint == ThaValue.NA_8
            or self._tekmar_tha.heat_setpoint is None
        ):
            return None

        else:
            try:
                return degEtoC(self._tekmar_tha.heat_setpoint)

            except TypeError:
                return None

    async def async_set_temperature(self, **kwargs):
        heat_setpoint = None
        cool_setpoint = None

        if self.supported_features & Feature.TARGET_TEMPERATURE:
            if self._tekmar_tha.tha_device["attributes"].ZoneHeating == 1:
                heat_setpoint = kwargs.get(ATTR_TEMPERATURE)

            elif self._tekmar_tha.tha_device["attributes"].ZoneCooling == 1:
                cool_setpoint = kwargs.get(ATTR_TEMPERATURE)

        elif self.supported_features & Feature.TARGET_TEMPERATURE_RANGE:
            heat_setpoint = kwargs.get(ATTR_TARGET_TEMP_LOW)
            cool_setpoint = kwargs.get(ATTR_TARGET_TEMP_HIGH)

        if heat_setpoint is not None:
            heat_setpoint = int(round(degCtoE(heat_setpoint), 0))
            await self._tekmar_tha.set_heat_setpoint_txqueue(heat_setpoint)

        if cool_setpoint is not None:
            cool_setpoint = int(round(degCtoE(cool_setpoint), 0))
            await self._tekmar_tha.set_cool_setpoint_txqueue(cool_setpoint)

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.OFF:
            value = ThaDeviceMode.OFF
        elif hvac_mode == HVACMode.HEAT:
            value = ThaDeviceMode.HEAT
        elif hvac_mode == HVACMode.COOL:
            value = ThaDeviceMode.COOL
        elif hvac_mode == HVACMode.HEAT_COOL:
            value = ThaDeviceMode.AUTO
        else:
            raise NotImplementedError()

        await self._tekmar_tha.set_mode_setting_txqueue(value)

    async def async_turn_off(self):
        await self.async_set_hvac_mode(self, HVACMode.OFF)

    async def async_set_fan_mode(self, fan_mode):
        if fan_mode == FAN_ON:
            if self._tekmar_tha.tha_device["type"] in [99203, 99202, 99201]:
                value = 10
            else:
                value = 100

        elif fan_mode == FAN_AUTO:
            value = 0

        else:
            raise NotImplementedError()

        await self._tekmar_tha.set_fan_percent_txqueue(value)

    async def async_set_humidity(self, humidity):
        if (
            self._tekmar_tha.humidity_setpoint_min != ThaValue.NA_8
            and self._tekmar_tha.humidity_setpoint_max == ThaValue.NA_8
        ):
            await self._tekmar_tha.set_humidity_setpoint_min_txqueue(humidity)

        elif (
            self._tekmar_tha.humidity_setpoint_min == ThaValue.NA_8
            and self._tekmar_tha.humidity_setpoint_max != ThaValue.NA_8
        ):
            await self._tekmar_tha.set_humidity_setpoint_max_txqueue(humidity)

        elif (
            self._tekmar_tha.humidity_setpoint_min == ThaValue.NA_8
            and self._tekmar_tha.humidity_setpoint_max == ThaValue.NA_8
        ):
            pass

        else:
            pass

    async def async_turn_aux_heat_on(self):
        self._last_mode_setting = self._tekmar_tha.mode_setting
        await self._tekmar_tha.set_mode_setting_txqueue(0x06)

    async def async_turn_aux_heat_off(self):
        await self._tekmar_tha.set_mode_setting_txqueue(self._last_mode_setting)
