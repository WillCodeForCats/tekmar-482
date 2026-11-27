"""Provides functionality to interact with climate devices."""

from __future__ import annotations

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
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
from .entity import ThaEntity
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


class ThaClimateBase(ThaEntity, ClimateEntity):
    """Base class for Tekmar climate entities."""


class ThaClimateThermostat(ThaClimateBase):
    """A Tekmar thermostat entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_max_humidity = 80
    _attr_min_humidity = 20

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the entity."""
        super().__init__(tekmar_tha, config_entry)
        self._requested_hvac_mode = None
        self._requested_from_mode_setting = None

    async def async_added_to_hass(self):
        """Added to hass."""
        self._tekmar_tha.register_callback(self._async_device_updated)

    async def async_will_remove_from_hass(self):
        """Will remove from hass."""
        self._tekmar_tha.remove_callback(self._async_device_updated)

    def _async_device_updated(self) -> None:
        """Drop a pending mode request once the device reports a mode change."""
        if self._requested_hvac_mode is not None and (
            self.hvac_mode == self._requested_hvac_mode
            or self._tekmar_tha.mode_setting != self._requested_from_mode_setting
        ):
            self._requested_hvac_mode = None
            self._requested_from_mode_setting = None
        self.async_write_ha_state()

    @property
    def _routing_hvac_mode(self):
        """Return the requested HVAC mode if pending, else the reported one."""
        if self._requested_hvac_mode is not None:
            return self._requested_hvac_mode
        return self.hvac_mode

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-climate"
        )

    @property
    def name(self) -> str | None:
        """Return the name."""
        return None

    @property
    def _floor_only(self) -> bool:
        """Return True if the thermostat only controls a slab setpoint."""
        attributes = self._tekmar_tha.tha_device["attributes"]
        return (
            attributes.ZoneHeating == 0
            and attributes.ZoneCooling == 0
            and attributes.SlabSetpoint == 1
        )

    @property
    def _single_setpoint(self) -> str | None:
        """Return which setpoint a single target temperature maps to."""
        attributes = self._tekmar_tha.tha_device["attributes"]
        if attributes.ZoneHeating == 1:
            return "heat"
        if attributes.ZoneCooling == 1:
            if (
                attributes.SlabSetpoint == 1
                and self._routing_hvac_mode == HVACMode.HEAT
            ):
                return "slab"
            return "cool"
        if attributes.SlabSetpoint == 1:
            return "slab"
        return None

    @property
    def max_temp(self):
        """Return the max temp."""
        if self.hvac_mode == HVACMode.OFF:
            return None

        if self._floor_only:
            return self._tekmar_tha.config_slab_setpoint_max

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

        if self._floor_only:
            return self._tekmar_tha.config_slab_setpoint_min

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

        if (
            self._tekmar_tha.tha_device["attributes"].ZoneHeating == 1
            or self._tekmar_tha.tha_device["attributes"].SlabSetpoint == 1
        ):
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
        setpoint = self._single_setpoint
        if setpoint == "heat":
            this_device_setpoint = self._tekmar_tha.heat_setpoint

        elif setpoint == "cool":
            this_device_setpoint = self._tekmar_tha.cool_setpoint

        elif setpoint == "slab":
            this_device_setpoint = self._tekmar_tha.slab_setpoint

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
        slab_setpoint = None

        if (hvac_mode := kwargs.get(ATTR_HVAC_MODE)) is not None:
            await self.async_set_hvac_mode(hvac_mode)

        if self.supported_features & Feature.TARGET_TEMPERATURE:
            setpoint = self._single_setpoint
            if setpoint == "heat":
                heat_setpoint = kwargs.get(ATTR_TEMPERATURE)

            elif setpoint == "cool":
                cool_setpoint = kwargs.get(ATTR_TEMPERATURE)

            elif setpoint == "slab":
                slab_setpoint = kwargs.get(ATTR_TEMPERATURE)

        elif self.supported_features & Feature.TARGET_TEMPERATURE_RANGE:
            heat_setpoint = kwargs.get(ATTR_TARGET_TEMP_LOW)
            cool_setpoint = kwargs.get(ATTR_TARGET_TEMP_HIGH)

        if heat_setpoint is not None:
            heat_setpoint = int(round(degCtoE(heat_setpoint), 0))
            await self._tekmar_tha.set_heat_setpoint_txqueue(heat_setpoint)

        if cool_setpoint is not None:
            cool_setpoint = int(round(degCtoE(cool_setpoint), 0))
            await self._tekmar_tha.set_cool_setpoint_txqueue(cool_setpoint)

        if slab_setpoint is not None:
            slab_setpoint = int(round(degCtoE(slab_setpoint), 0))
            await self._tekmar_tha.set_slab_setpoint_txqueue(slab_setpoint)

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
        self._requested_from_mode_setting = self._tekmar_tha.mode_setting
        self._requested_hvac_mode = hvac_mode

    async def async_turn_off(self):
        """Turn the entity off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

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
