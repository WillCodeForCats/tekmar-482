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
    ClimateEntityFeature as Feature,
    HVACAction,
    HVACMode,
)
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
    """Setup entry."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        ThaClimateThermostat(device, config_entry)
        for device in hub.tha_devices
        if DEVICE_TYPES[device.tha_device["type"]] == ThaType.THERMOSTAT
    ]

    if entities:
        async_add_entities(entities)


class ThaClimateBase(ClimateEntity):
    """Base class for Tekmar climate entities."""

    _attr_should_poll = False

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the climate entity."""
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


class ThaClimateThermostat(ThaClimateBase):
    """A Tekmar thermostat entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_max_humidity = 80
    _attr_min_humidity = 20

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-climate"
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self._tekmar_tha.tha_full_device_name}"

    @property
    def max_temp(self):
        """Return the max temp."""
        if self.hvac_mode == HVACMode.OFF:
            return None

        if (
            self._tekmar_tha.config_heat_setpoint_max
            >= self._tekmar_tha.config_cool_setpoint_max
        ):
            return self._tekmar_tha.config_heat_setpoint_max
        return self._tekmar_tha.config_cool_setpoint_max

    @property
    def min_temp(self):
        """Return the min temp."""
        if self.hvac_mode == HVACMode.OFF:
            return None

        if (
            self._tekmar_tha.config_heat_setpoint_min
            <= self._tekmar_tha.config_cool_setpoint_min
        ):
            return self._tekmar_tha.config_heat_setpoint_min
        return self._tekmar_tha.config_cool_setpoint_min

    @property
    def supported_features(self):
        """Return the supported features."""
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
                ThaValue.NA_8
                not in (
                    self._tekmar_tha.humidity_setpoint_min,
                    self._tekmar_tha.humidity_setpoint_max,
                )
            ):
                supported_features = supported_features | Feature.TARGET_HUMIDITY

        return supported_features

    @property
    def current_temperature(self):
        """Return the current temperature."""
        if (
            self._tekmar_tha.current_temperature == ThaValue.NA_16
            or self._tekmar_tha.current_temperature is None
        ):
            return None

        try:
            return degHtoC(self._tekmar_tha.current_temperature)
            # temp = degHtoC(self._tekmar_tha.current_temperature)
            # return round(temp, 0)

        except TypeError:
            return None

    @property
    def current_humidity(self):
        """Return the current humidity."""
        if (
            self._tekmar_tha.relative_humidity == ThaValue.NA_8
            or self._tekmar_tha.relative_humidity is None
        ):
            return None

        return self._tekmar_tha.relative_humidity

    @property
    def hvac_modes(self) -> list[str]:
        """Return the hvac modes."""
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
        """Return the hvac mode."""
        if self._tekmar_tha.mode_setting == ThaDeviceMode.OFF:
            return HVACMode.OFF
        if self._tekmar_tha.mode_setting == ThaDeviceMode.HEAT:
            return HVACMode.HEAT
        if self._tekmar_tha.mode_setting == ThaDeviceMode.AUTO:
            return HVACMode.HEAT_COOL
        if self._tekmar_tha.mode_setting == ThaDeviceMode.COOL:
            return HVACMode.COOL
        if self._tekmar_tha.mode_setting == ThaDeviceMode.VENT:
            return HVACMode.FAN_ONLY
        if self._tekmar_tha.mode_setting == ThaDeviceMode.EMERGENCY:
            return HVACMode.HEAT
        return None

    @property
    def fan_modes(self):
        """Return the fan modes."""
        if self._tekmar_tha.tha_device["attributes"].FanPercent == 1:
            return [FAN_ON, FAN_AUTO]
        return None

    @property
    def fan_mode(self):
        """Return the fan mode."""
        if self._tekmar_tha.tha_device["type"] in [99203, 99202, 99201]:
            if self._tekmar_tha.fan_percent == 10:
                return FAN_ON
            return FAN_AUTO

        if self._tekmar_tha.fan_percent == 100:
            return FAN_ON
        return FAN_AUTO

    @property
    def target_humidity(self):
        """Return the target humidity."""
        if (
            self._tekmar_tha.humidity_setpoint_min != ThaValue.NA_8
            and self._tekmar_tha.humidity_setpoint_max == ThaValue.NA_8
        ):
            return self._tekmar_tha.humidity_setpoint_min

        if (
            self._tekmar_tha.humidity_setpoint_min == ThaValue.NA_8
            and self._tekmar_tha.humidity_setpoint_max != ThaValue.NA_8
        ):
            return self._tekmar_tha.humidity_setpoint_max

        if (
            self._tekmar_tha.humidity_setpoint_min == ThaValue.NA_8
            and self._tekmar_tha.humidity_setpoint_max == ThaValue.NA_8
        ):
            return None

        return None

    @property
    def preset_mode(self):
        """Return the preset mode."""
        if self._tekmar_tha.setback_state == 0x00:
            return PRESET_HOME

        if self._tekmar_tha.setback_state == 0x01:
            return PRESET_SLEEP

        if self._tekmar_tha.setback_state == 0x02:
            return PRESET_HOME

        if self._tekmar_tha.setback_state == 0x03:
            return PRESET_SLEEP

        if self._tekmar_tha.setback_state == 0x04:
            return PRESET_HOME

        if self._tekmar_tha.setback_state == 0x05:
            return PRESET_SLEEP

        if self._tekmar_tha.setback_state == 0x06:
            return PRESET_AWAY

        return None

    @property
    def hvac_action(self):
        """Return the hvac action."""
        if self._tekmar_tha.mode_setting == ThaDeviceMode.OFF:
            return HVACAction.OFF

        if self._tekmar_tha.active_demand == ThaActiveDemand.IDLE:
            return HVACAction.IDLE

        if self._tekmar_tha.active_demand == ThaActiveDemand.HEAT:
            return HVACAction.HEATING

        if self._tekmar_tha.active_demand == ThaActiveDemand.COOL:
            return HVACAction.COOLING

        return None

    @property
    def target_temperature(self):
        """Return the target temperature."""
        if self._tekmar_tha.tha_device["attributes"].ZoneHeating == 1:
            this_device_setpoint = self._tekmar_tha.heat_setpoint

        elif self._tekmar_tha.tha_device["attributes"].ZoneCooling == 1:
            this_device_setpoint = self._tekmar_tha.cool_setpoint

        else:
            return None

        if this_device_setpoint == ThaValue.NA_8 or this_device_setpoint is None:
            return None

        try:
            # temp = degEtoC(this_device_setpoint)
            # return round(temp, 0)
            return degEtoC(this_device_setpoint)

        except TypeError:
            return None

    @property
    def target_temperature_high(self):
        """Return the target temperature high."""
        if (
            self._tekmar_tha.cool_setpoint == ThaValue.NA_8
            or self._tekmar_tha.cool_setpoint is None
        ):
            return None

        try:
            return degEtoC(self._tekmar_tha.cool_setpoint)

        except TypeError:
            return None

    @property
    def target_temperature_low(self):
        """Return the target temperature low."""
        if (
            self._tekmar_tha.heat_setpoint == ThaValue.NA_8
            or self._tekmar_tha.heat_setpoint is None
        ):
            return None

        try:
            return degEtoC(self._tekmar_tha.heat_setpoint)

        except TypeError:
            return None

    async def async_set_temperature(self, **kwargs):
        """Set temperature."""
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
        """Set hvac mode."""
        if hvac_mode == HVACMode.OFF:
            value = ThaDeviceMode.OFF
        elif hvac_mode == HVACMode.HEAT:
            value = ThaDeviceMode.HEAT
        elif hvac_mode == HVACMode.COOL:
            value = ThaDeviceMode.COOL
        elif hvac_mode == HVACMode.HEAT_COOL:
            value = ThaDeviceMode.AUTO
        else:
            raise NotImplementedError

        await self._tekmar_tha.set_mode_setting_txqueue(value)

    async def async_turn_off(self):
        """Turn the entity off."""
        await self.async_set_hvac_mode(self, HVACMode.OFF)

    async def async_set_fan_mode(self, fan_mode):
        """Set fan mode."""
        if fan_mode == FAN_ON:
            if self._tekmar_tha.tha_device["type"] in [99203, 99202, 99201]:
                value = 10
            else:
                value = 100

        elif fan_mode == FAN_AUTO:
            value = 0

        else:
            raise NotImplementedError

        await self._tekmar_tha.set_fan_percent_txqueue(value)

    async def async_set_humidity(self, humidity):
        """Set humidity."""
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
