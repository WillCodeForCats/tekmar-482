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
                if device.tha_device["attributes"].Slab_Setpoint:
                    entities.append(ThaSlabSetpoint(device, config_entry))

            if DEVICE_FEATURES[device.tha_device["type"]]["humid"]:
                entities.append(ThaHumiditySetMax(device, config_entry))
                entities.append(ThaHumiditySetMin(device, config_entry))

    if entities:
        async_add_entities(entities)


class ThaNumberBase(NumberEntity):
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
        return self._config_entry.data["name"]

    async def async_added_to_hass(self):
        self._tekmar_tha.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self._tekmar_tha.remove_callback(self.async_write_ha_state)


class ThaHumiditySetMax(ThaNumberBase):
    native_unit_of_measurement = PERCENTAGE
    icon = "mdi:water-percent"
    native_min_value = 20
    native_max_value = 80

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-humidity-max-setpoint"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Humidity Maximum Setpoint"

    @property
    def entity_registry_enabled_default(self) -> bool:
        if (
            self._tekmar_tha.humidity_setpoint_max is not None
            and self._tekmar_tha.humidity_setpoint_min != ThaValue.NA_8
            and self._tekmar_tha.humidity_setpoint_max != ThaValue.NA_8
        ):
            return True
        else:
            return False

    @property
    def available(self) -> bool:
        if self._tekmar_tha.humidity_setpoint_max == ThaValue.NA_8:
            return False
        else:
            return True

    @property
    def native_value(self):
        return self._tekmar_tha.humidity_setpoint_max

    async def async_set_native_value(self, value: float) -> None:
        value = int(value)
        await self._tekmar_tha.set_humidity_setpoint_max_txqueue(value)


class ThaHumiditySetMin(ThaNumberBase):
    native_unit_of_measurement = PERCENTAGE
    icon = "mdi:water-percent"
    native_min_value = 20
    native_max_value = 80

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-humidity-min-setpoint"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Humidity Minimum Setpoint"

    @property
    def entity_registry_enabled_default(self) -> bool:
        if (
            self._tekmar_tha.humidity_setpoint_min is not None
            and self._tekmar_tha.humidity_setpoint_min != ThaValue.NA_8
            and self._tekmar_tha.humidity_setpoint_max != ThaValue.NA_8
        ):
            return True
        else:
            return False

    @property
    def available(self) -> bool:
        if self._tekmar_tha.humidity_setpoint_min == ThaValue.NA_8:
            return False
        else:
            return True

    @property
    def native_value(self):
        return self._tekmar_tha.humidity_setpoint_min

    async def async_set_native_value(self, value: float) -> None:
        value = int(value)
        await self._tekmar_tha.set_humidity_setpoint_min_txqueue(value)


class ThaHeatSetpoint(ThaNumberBase):
    device_class = NumberDeviceClass.TEMPERATURE
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    icon = "mdi:thermostat"

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-heat-setpoint"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Heat Setpoint"

    @property
    def entity_registry_enabled_default(self) -> bool:
        if self._tekmar_tha.setback_enable is False:
            return True
        else:
            return False

    @property
    def available(self) -> bool:
        if self._tekmar_tha.heat_setpoint == ThaValue.NA_8:
            return False

        elif self._tekmar_tha.tha_device["attributes"].Zone_Heating == 0:
            return False

        else:
            return True

    @property
    def native_value(self):
        try:
            return degEtoC(self._tekmar_tha.heat_setpoint)
        except TypeError:
            return None

    @property
    def native_min_value(self):
        return self._tekmar_tha.config_heat_setpoint_min

    @property
    def native_max_value(self):
        return self._tekmar_tha.config_heat_setpoint_max

    async def async_set_native_value(self, value: float) -> None:
        heat_setpoint = int(degCtoE(value))
        await self._tekmar_tha.set_heat_setpoint_txqueue(heat_setpoint)


class ThaHeatSetpointDay(ThaHeatSetpoint):
    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-heat-setpoint-day"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Heat Setpoint Day"

    @property
    def available(self) -> bool:
        if self._tekmar_tha.heat_setpoint_day == ThaValue.NA_8:
            return False

        elif self._tekmar_tha.tha_device["attributes"].Zone_Heating == 0:
            return False

        else:
            return True

    @property
    def native_value(self):
        try:
            return degEtoC(self._tekmar_tha.heat_setpoint_day)
        except TypeError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        heat_setpoint = int(degCtoE(value))
        await self._tekmar_tha.set_heat_setpoint_txqueue(heat_setpoint, 0x00)


class ThaHeatSetpointNight(ThaHeatSetpoint):
    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-heat-setpoint-night"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Heat Setpoint Night"

    @property
    def available(self) -> bool:
        if self._tekmar_tha.heat_setpoint_day == ThaValue.NA_8:
            return False

        elif self._tekmar_tha.tha_device["attributes"].Zone_Heating == 0:
            return False

        else:
            return True

    @property
    def native_value(self):
        try:
            return degEtoC(self._tekmar_tha.heat_setpoint_night)
        except TypeError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        heat_setpoint = int(degCtoE(value))
        await self._tekmar_tha.set_heat_setpoint_txqueue(heat_setpoint, 0x03)


class ThaHeatSetpointAway(ThaHeatSetpoint):
    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-heat-setpoint-away"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Heat Setpoint Away"

    @property
    def available(self) -> bool:
        if self._tekmar_tha.heat_setpoint_day == ThaValue.NA_8:
            return False

        elif self._tekmar_tha.tha_device["attributes"].Zone_Heating == 0:
            return False

        else:
            return True

    @property
    def native_value(self):
        try:
            return degEtoC(self._tekmar_tha.heat_setpoint_away)
        except TypeError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        heat_setpoint = int(degCtoE(value))
        await self._tekmar_tha.set_heat_setpoint_txqueue(heat_setpoint, 0x06)


class ThaCoolSetpoint(ThaNumberBase):
    device_class = NumberDeviceClass.TEMPERATURE
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    icon = "mdi:thermostat"

    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-cool-setpoint"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Cool Setpoint"

    @property
    def entity_registry_enabled_default(self) -> bool:
        if self._tekmar_tha.setback_enable is False:
            return True
        else:
            return False

    @property
    def available(self) -> bool:
        if self._tekmar_tha.cool_setpoint == ThaValue.NA_8:
            return False

        elif self._tekmar_tha.tha_device["attributes"].Zone_Cooling == 0:
            return False

        else:
            return True

    @property
    def native_value(self):
        try:
            return degEtoC(self._tekmar_tha.cool_setpoint)
        except TypeError:
            return None

    @property
    def native_min_value(self):
        return self._tekmar_tha.config_cool_setpoint_min

    @property
    def native_max_value(self):
        return self._tekmar_tha.config_cool_setpoint_max

    async def async_set_native_value(self, value: float) -> None:
        cool_setpoint = int(degCtoE(value))
        await self._tekmar_tha.set_cool_setpoint_txqueue(cool_setpoint)


class ThaCoolSetpointDay(ThaCoolSetpoint):
    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-cool-setpoint-day"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Cool Setpoint Day"

    @property
    def available(self) -> bool:
        if self._tekmar_tha.cool_setpoint_day == ThaValue.NA_8:
            return False

        elif self._tekmar_tha.tha_device["attributes"].Zone_Cooling == 0:
            return False

        else:
            return True

    @property
    def native_value(self):
        try:
            return degEtoC(self._tekmar_tha.cool_setpoint_day)
        except TypeError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        cool_setpoint = int(degCtoE(value))
        await self._tekmar_tha.set_cool_setpoint_txqueue(cool_setpoint, 0x00)


class ThaCoolSetpointNight(ThaCoolSetpoint):
    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-cool-setpoint-night"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Cool Setpoint Night"

    @property
    def available(self) -> bool:
        if self._tekmar_tha.cool_setpoint_day == ThaValue.NA_8:
            return False

        elif self._tekmar_tha.tha_device["attributes"].Zone_Cooling == 0:
            return False

        else:
            return True

    @property
    def native_value(self):
        try:
            return degEtoC(self._tekmar_tha.cool_setpoint_night)
        except TypeError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        cool_setpoint = int(degCtoE(value))
        await self._tekmar_tha.set_cool_setpoint_txqueue(cool_setpoint, 0x03)


class ThaCoolSetpointAway(ThaCoolSetpoint):
    def __init__(self, tekmar_tha, config_entry):
        """Initialize the sensor."""
        super().__init__(tekmar_tha, config_entry)

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-cool-setpoint-away"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Cool Setpoint Away"

    @property
    def available(self) -> bool:
        if self._tekmar_tha.cool_setpoint_day == ThaValue.NA_8:
            return False

        elif self._tekmar_tha.tha_device["attributes"].Zone_Cooling == 0:
            return False

        else:
            return True

    @property
    def native_value(self):
        try:
            return degEtoC(self._tekmar_tha.cool_setpoint_away)
        except TypeError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        cool_setpoint = int(degCtoE(value))
        await self._tekmar_tha.set_cool_setpoint_txqueue(cool_setpoint, 0x06)


class ThaSlabSetpoint(ThaNumberBase):
    device_class = NumberDeviceClass.TEMPERATURE
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    icon = "mdi:thermostat"

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-slab-setpoint"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Floor Setpoint"

    @property
    def available(self) -> bool:
        if (
            self._tekmar_tha.slab_setpoint == ThaValue.NA_8
            or not self._tekmar_tha.tha_device["attributes"].Slab_Setpoint
        ):
            return False

        return super().available

    @property
    def native_value(self):
        try:
            return degEtoC(self._tekmar_tha.slab_setpoint)
        except TypeError:
            return None

    @property
    def native_min_value(self):
        return self._tekmar_tha.config_slab_setpoint_min

    @property
    def native_max_value(self):
        return self._tekmar_tha.config_slab_setpoint_max

    async def async_set_native_value(self, value: float) -> None:
        slab_setpoint = int(degCtoE(value))
        await self._tekmar_tha.set_slab_setpoint_txqueue(slab_setpoint)
