"""Component to allow numeric input for platforms."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_FEATURES, DEVICE_TYPES, DOMAIN, ThaType, ThaValue
from .helpers import degCtoE, degEtoC


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup entry."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    for device in hub.tha_devices:
        if DEVICE_TYPES[device.tha_device["type"]] == ThaType.THERMOSTAT:
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
                entities.append(ThaSlabSetpoint(device, config_entry))

            if DEVICE_FEATURES[device.tha_device["type"]]["humid"]:
                entities.append(ThaHumiditySetMax(device, config_entry))
                entities.append(ThaHumiditySetMin(device, config_entry))

    if entities:
        async_add_entities(entities)


class ThaNumberBase(NumberEntity):
    """Base class for Tekmar number entities."""

    _attr_should_poll = False

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the number entity."""
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


class ThaHumiditySetMax(ThaNumberBase):
    """Maximum humidity setpoint for a Tekmar thermostat."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:water-percent"
    _attr_native_min_value = 20
    _attr_native_max_value = 80

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-humidity-max-setpoint"
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self._tekmar_tha.tha_full_device_name} Humidity Maximum Setpoint"

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return the entity registry enabled default."""
        if self._tekmar_tha.humidity_setpoint_max is not None and ThaValue.NA_8 not in (
            self._tekmar_tha.humidity_setpoint_min,
            self._tekmar_tha.humidity_setpoint_max,
        ):
            return True
        return False

    @property
    def available(self) -> bool:
        """Return the available."""
        if self._tekmar_tha.humidity_setpoint_max == ThaValue.NA_8:
            return False

        return super().available

    @property
    def native_value(self):
        """Return the native value."""
        return self._tekmar_tha.humidity_setpoint_max

    async def async_set_native_value(self, value: float) -> None:
        """Set native value."""
        value = int(value)
        await self._tekmar_tha.set_humidity_setpoint_max_txqueue(value)


class ThaHumiditySetMin(ThaNumberBase):
    """Minimum humidity setpoint for a Tekmar thermostat."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:water-percent"
    _attr_native_min_value = 20
    _attr_native_max_value = 80

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-humidity-min-setpoint"
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self._tekmar_tha.tha_full_device_name} Humidity Minimum Setpoint"

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return the entity registry enabled default."""
        if self._tekmar_tha.humidity_setpoint_min is not None and ThaValue.NA_8 not in (
            self._tekmar_tha.humidity_setpoint_min,
            self._tekmar_tha.humidity_setpoint_max,
        ):
            return True
        return False

    @property
    def available(self) -> bool:
        """Return the available."""
        if self._tekmar_tha.humidity_setpoint_min == ThaValue.NA_8:
            return False

        return super().available

    @property
    def native_value(self):
        """Return the native value."""
        return self._tekmar_tha.humidity_setpoint_min

    async def async_set_native_value(self, value: float) -> None:
        """Set native value."""
        value = int(value)
        await self._tekmar_tha.set_humidity_setpoint_min_txqueue(value)


class ThaHeatSetpoint(ThaNumberBase):
    """Heating setpoint for a Tekmar thermostat."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermostat"

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-heat-setpoint"
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self._tekmar_tha.tha_full_device_name} Heat Setpoint"

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return the entity registry enabled default."""
        return self._tekmar_tha.setback_enable is False

    @property
    def available(self) -> bool:
        """Return the available."""
        if (
            self._tekmar_tha.heat_setpoint == ThaValue.NA_8
            or self._tekmar_tha.tha_device["attributes"].ZoneHeating == 0
        ):
            return False

        return super().available

    @property
    def native_value(self):
        """Return the native value."""
        try:
            return degEtoC(self._tekmar_tha.heat_setpoint)
        except TypeError:
            return None

    @property
    def native_min_value(self):
        """Return the native min value."""
        return self._tekmar_tha.config_heat_setpoint_min

    @property
    def native_max_value(self):
        """Return the native max value."""
        return self._tekmar_tha.config_heat_setpoint_max

    async def async_set_native_value(self, value: float) -> None:
        """Set native value."""
        heat_setpoint = int(round(degCtoE(value), 0))
        await self._tekmar_tha.set_heat_setpoint_txqueue(heat_setpoint)


class ThaHeatSetpointDay(ThaHeatSetpoint):
    """Heating setpoint for a Tekmar thermostat (day setback)."""

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-heat-setpoint-day"
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self._tekmar_tha.tha_full_device_name} Heat Setpoint Day"

    @property
    def available(self) -> bool:
        """Return the available."""
        if (
            self._tekmar_tha.heat_setpoint_day == ThaValue.NA_8
            or self._tekmar_tha.tha_device["attributes"].ZoneHeating == 0
        ):
            return False

        return super().available

    @property
    def native_value(self):
        """Return the native value."""
        try:
            return degEtoC(self._tekmar_tha.heat_setpoint_day)
        except TypeError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set native value."""
        heat_setpoint = int(round(degCtoE(value), 0))
        await self._tekmar_tha.set_heat_setpoint_txqueue(heat_setpoint, 0x00)


class ThaHeatSetpointNight(ThaHeatSetpoint):
    """Heating setpoint for a Tekmar thermostat (night setback)."""

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-heat-setpoint-night"
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self._tekmar_tha.tha_full_device_name} Heat Setpoint Night"

    @property
    def available(self) -> bool:
        """Return the available."""
        if (
            self._tekmar_tha.heat_setpoint_day == ThaValue.NA_8
            or self._tekmar_tha.tha_device["attributes"].ZoneHeating == 0
        ):
            return False

        return super().available

    @property
    def native_value(self):
        """Return the native value."""
        try:
            return degEtoC(self._tekmar_tha.heat_setpoint_night)
        except TypeError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set native value."""
        heat_setpoint = int(round(degCtoE(value), 0))
        await self._tekmar_tha.set_heat_setpoint_txqueue(heat_setpoint, 0x03)


class ThaHeatSetpointAway(ThaHeatSetpoint):
    """Heating setpoint for a Tekmar thermostat (away setback)."""

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-heat-setpoint-away"
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self._tekmar_tha.tha_full_device_name} Heat Setpoint Away"

    @property
    def available(self) -> bool:
        """Return the available."""
        if (
            self._tekmar_tha.heat_setpoint_day == ThaValue.NA_8
            or self._tekmar_tha.tha_device["attributes"].ZoneHeating == 0
        ):
            return False

        return super().available

    @property
    def native_value(self):
        """Return the native value."""
        try:
            return degEtoC(self._tekmar_tha.heat_setpoint_away)
        except TypeError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set native value."""
        heat_setpoint = int(round(degCtoE(value), 0))
        await self._tekmar_tha.set_heat_setpoint_txqueue(heat_setpoint, 0x06)


class ThaCoolSetpoint(ThaNumberBase):
    """Cooling setpoint for a Tekmar thermostat."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermostat"

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-cool-setpoint"
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self._tekmar_tha.tha_full_device_name} Cool Setpoint"

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return the entity registry enabled default."""
        if self._tekmar_tha.setback_enable is False:
            return True
        return False

    @property
    def available(self) -> bool:
        """Return the available."""
        if (
            self._tekmar_tha.cool_setpoint == ThaValue.NA_8
            or self._tekmar_tha.tha_device["attributes"].ZoneCooling == 0
        ):
            return False

        return super().available

    @property
    def native_value(self):
        """Return the native value."""
        try:
            return degEtoC(self._tekmar_tha.cool_setpoint)
        except TypeError:
            return None

    @property
    def native_min_value(self):
        """Return the native min value."""
        return self._tekmar_tha.config_cool_setpoint_min

    @property
    def native_max_value(self):
        """Return the native max value."""
        return self._tekmar_tha.config_cool_setpoint_max

    async def async_set_native_value(self, value: float) -> None:
        """Set native value."""
        cool_setpoint = int(round(degCtoE(value), 0))
        await self._tekmar_tha.set_cool_setpoint_txqueue(cool_setpoint)


class ThaCoolSetpointDay(ThaCoolSetpoint):
    """Cooling setpoint for a Tekmar thermostat (day setback)."""

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-cool-setpoint-day"
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self._tekmar_tha.tha_full_device_name} Cool Setpoint Day"

    @property
    def available(self) -> bool:
        """Return the available."""
        if (
            self._tekmar_tha.cool_setpoint_day == ThaValue.NA_8
            or self._tekmar_tha.tha_device["attributes"].ZoneCooling == 0
        ):
            return False

        return super().available

    @property
    def native_value(self):
        """Return the native value."""
        try:
            return degEtoC(self._tekmar_tha.cool_setpoint_day)
        except TypeError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set native value."""
        cool_setpoint = int(round(degCtoE(value), 0))
        await self._tekmar_tha.set_cool_setpoint_txqueue(cool_setpoint, 0x00)


class ThaCoolSetpointNight(ThaCoolSetpoint):
    """Cooling setpoint for a Tekmar thermostat (night setback)."""

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-cool-setpoint-night"
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self._tekmar_tha.tha_full_device_name} Cool Setpoint Night"

    @property
    def available(self) -> bool:
        """Return the available."""
        if (
            self._tekmar_tha.cool_setpoint_day == ThaValue.NA_8
            or self._tekmar_tha.tha_device["attributes"].ZoneCooling == 0
        ):
            return False

        return super().available

    @property
    def native_value(self):
        """Return the native value."""
        try:
            return degEtoC(self._tekmar_tha.cool_setpoint_night)
        except TypeError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set native value."""
        cool_setpoint = int(round(degCtoE(value), 0))
        await self._tekmar_tha.set_cool_setpoint_txqueue(cool_setpoint, 0x03)


class ThaCoolSetpointAway(ThaCoolSetpoint):
    """Cooling setpoint for a Tekmar thermostat (away setback)."""

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-cool-setpoint-away"
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self._tekmar_tha.tha_full_device_name} Cool Setpoint Away"

    @property
    def available(self) -> bool:
        """Return the available."""
        if (
            self._tekmar_tha.cool_setpoint_day == ThaValue.NA_8
            or self._tekmar_tha.tha_device["attributes"].ZoneCooling == 0
        ):
            return False

        return super().available

    @property
    def native_value(self):
        """Return the native value."""
        try:
            return degEtoC(self._tekmar_tha.cool_setpoint_away)
        except TypeError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set native value."""
        cool_setpoint = int(round(degCtoE(value), 0))
        await self._tekmar_tha.set_cool_setpoint_txqueue(cool_setpoint, 0x06)


class ThaSlabSetpoint(ThaNumberBase):
    """Slab (floor) setpoint for a Tekmar thermostat."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermostat"

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-slab-setpoint"
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self._tekmar_tha.tha_full_device_name} Floor Setpoint"

    @property
    def available(self) -> bool:
        """Return the available."""
        return self._tekmar_tha.slab_setpoint != ThaValue.NA_8 and super().available

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return the entity registry enabled default."""
        return self._tekmar_tha.tha_device["attributes"].SlabSetpoint

    @property
    def native_value(self):
        """Return the native value."""
        try:
            return degEtoC(self._tekmar_tha.slab_setpoint)
        except TypeError:
            return None

    @property
    def native_min_value(self):
        """Return the native min value."""
        return self._tekmar_tha.config_slab_setpoint_min

    @property
    def native_max_value(self):
        """Return the native max value."""
        return self._tekmar_tha.config_slab_setpoint_max

    async def async_set_native_value(self, value: float) -> None:
        """Set native value."""
        slab_setpoint = int(round(degCtoE(value), 0))
        await self._tekmar_tha.set_slab_setpoint_txqueue(slab_setpoint)
