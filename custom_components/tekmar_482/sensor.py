"""Component to interface with various sensors that can be monitored."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DEVICE_FEATURES,
    DEVICE_TYPES,
    DOMAIN,
    SETBACK_DESCRIPTION,
    SETBACK_STATE,
    TN_ERRORS,
    ThaActiveDemand,
    ThaType,
    ThaValue,
)
from .helpers import degHtoC, regBytes


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    for gateway in hub.tha_gateway:
        entities.append(OutdoorTemprature(gateway, config_entry))
        entities.append(NetworkError(gateway, config_entry))

    for device in hub.tha_devices:
        if DEVICE_TYPES[device.tha_device["type"]] == ThaType.THERMOSTAT:
            entities.append(CurrentTemperature(device, config_entry))
            entities.append(SetbackState(device, config_entry))

            if DEVICE_FEATURES[device.tha_device["type"]][
                "humid"
            ] and hub.tha_pr_ver in [2, 3]:
                entities.append(RelativeHumidity(device, config_entry))

            if hub.tha_pr_ver in [3]:
                entities.append(CurrentFloorTemperature(device, config_entry))

        if DEVICE_TYPES[device.tha_device["type"]] == ThaType.SETPOINT:
            if hub.tha_pr_ver in [3]:
                entities.append(CurrentFloorTemperature(device, config_entry))
            entities.append(CurrentTemperature(device, config_entry))
            entities.append(SetbackState(device, config_entry))
            entities.append(SetpointTarget(device, config_entry))
            entities.append(SetpointDemand(device, config_entry))

    if entities:
        async_add_entities(entities)


class ThaSensorBase(SensorEntity):
    """Base class for Tekmar sensor entities."""

    suggested_display_precision = None
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
        return self._config_entry.data["name"]

    async def async_added_to_hass(self):
        self._tekmar_tha.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self._tekmar_tha.remove_callback(self.async_write_ha_state)


class OutdoorTemprature(ThaSensorBase):
    """Outdoor temperature sensor."""

    device_class = SensorDeviceClass.TEMPERATURE
    state_class = SensorStateClass.MEASUREMENT
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    suggested_display_precision = 1

    @property
    def unique_id(self) -> str:
        return f"{self.config_entry_id}-outdoor-temperature"

    @property
    def name(self) -> str:
        return f"{self.config_entry_name.capitalize()} Outdoor Temperature"

    @property
    def available(self) -> bool:
        if (
            self._tekmar_tha.outdoor_temprature == ThaValue.NA_16
            or self._tekmar_tha.outdoor_temprature is None
        ):
            return False

        return super().available

    @property
    def native_value(self):
        try:
            return degHtoC(self._tekmar_tha.outdoor_temprature)  # degH need degC

        except TypeError:
            return None


class NetworkError(ThaSensorBase):
    """TN4 network error sensor."""

    entity_category = EntityCategory.DIAGNOSTIC
    icon = "mdi:alert-outline"

    @property
    def unique_id(self) -> str:
        return f"{self.config_entry_id}-network-error"

    @property
    def name(self) -> str:
        return f"{self.config_entry_name.capitalize()} Network Error"

    @property
    def native_value(self):
        return hex(self._tekmar_tha.network_error)

    @property
    def extra_state_attributes(self):
        err_high, err_low = regBytes(self._tekmar_tha.network_error)
        try:
            if err_low != 0x00:
                if err_low in [
                    0x80,
                    0x83,
                    0x84,
                    0x85,
                    0x86,
                    0x87,
                    0x88,
                    0x89,
                    0x8A,
                    0x8B,
                    0x8C,
                    0x8D,
                    0x8E,
                    0x8F,
                    0x90,
                    0x91,
                    0x92,
                    0x93,
                    0x94,
                ]:
                    if err_high & 0x20 != 0:
                        sen_err = "open"
                    else:
                        sen_err = "short"

                    if err_low in [0x90, 0x92, 0x93, 0x94]:
                        ag_id = err_high & 0x0F
                        return {
                            "description": f"{TN_ERRORS[err_low]} {sen_err} {ag_id}"
                        }
                    else:
                        return {"description": f"{TN_ERRORS[err_low]} {sen_err}"}

                elif err_low in [0x04]:
                    device_id = err_high & 0x1F
                    return {"description": f"{TN_ERRORS[err_low]}: device {device_id}"}

                else:
                    return {"description": f"{TN_ERRORS[err_low]}"}

            else:
                return {"description": f"{TN_ERRORS[err_low]}"}

        except KeyError:
            return {"description": "Unknown Error"}


class CurrentTemperature(ThaSensorBase):
    """Current temperature sensor for a Tekmar thermostat."""

    device_class = SensorDeviceClass.TEMPERATURE
    state_class = SensorStateClass.MEASUREMENT
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    suggested_display_precision = 1

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}"
            f"-{self._tekmar_tha.device_id}-current-temperature"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Current Temperature"

    @property
    def available(self) -> bool:
        if (
            self._tekmar_tha.current_temperature == ThaValue.NA_16
            or self._tekmar_tha.current_temperature == ThaValue.OFF
            or self._tekmar_tha.current_temperature is None
        ):
            return False

        return super().available

    @property
    def native_value(self):
        try:
            return degHtoC(self._tekmar_tha.current_temperature)

        except TypeError:
            return None


class CurrentFloorTemperature(ThaSensorBase):
    """Current floor temperature sensor for a Tekmar thermostat."""

    device_class = SensorDeviceClass.TEMPERATURE
    state_class = SensorStateClass.MEASUREMENT
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    suggested_display_precision = 1

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-current-floor-temperature"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Current Floor Temperature"

    @property
    def entity_registry_enabled_default(self) -> bool:
        return self._tekmar_tha.tha_device["attributes"].SlabSetpoint

    @property
    def available(self) -> bool:
        if (
            self._tekmar_tha.current_floor_temperature == ThaValue.NA_16
            or self._tekmar_tha.current_floor_temperature == ThaValue.OFF
            or self._tekmar_tha.current_floor_temperature is None
        ):
            return False

        return super().available

    @property
    def native_value(self):
        try:
            return degHtoC(self._tekmar_tha.current_floor_temperature)

        except TypeError:
            return None


class RelativeHumidity(ThaSensorBase):
    """Current humidity sensor for a Tekmar thermostat."""

    device_class = SensorDeviceClass.HUMIDITY
    state_class = SensorStateClass.MEASUREMENT
    native_unit_of_measurement = PERCENTAGE
    suggested_display_precision = 0

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-relative-humidity"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Relative Humidity"

    @property
    def available(self) -> bool:
        if (
            self._tekmar_tha.relative_humidity == ThaValue.NA_8
            or self._tekmar_tha.relative_humidity is None
        ):
            return False

        return super().available

    @property
    def native_value(self):
        return self._tekmar_tha.relative_humidity


class SetbackState(ThaSensorBase):
    """Current setback state for a Tekmar thermostat."""

    icon = "mdi:format-list-bulleted"

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-setback-state"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Setback State"

    @property
    def entity_registry_enabled_default(self) -> bool:
        if self._tekmar_tha.setback_enable is True:
            return True
        else:
            return False

    @property
    def available(self) -> bool:
        if (
            self._tekmar_tha.setback_state == ThaValue.NA_8
            or self._tekmar_tha.setback_enable == 0x00
        ):
            return False

        return super().available

    @property
    def native_value(self):
        try:
            return SETBACK_STATE[self._tekmar_tha.setback_state]

        except KeyError:
            return None

    @property
    def extra_state_attributes(self):
        try:
            return {"description": SETBACK_DESCRIPTION[self._tekmar_tha.setback_state]}
        except KeyError:
            return None


class SetpointTarget(ThaSensorBase):
    """Current setpoint sensor for a Tekmar setpoint control."""

    device_class = SensorDeviceClass.TEMPERATURE
    state_class = SensorStateClass.MEASUREMENT
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    suggested_display_precision = 1

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-setpoint-target"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Setpoint Target"

    @property
    def available(self) -> bool:
        if (
            self._tekmar_tha.setpoint_target == ThaValue.NA_16
            or self._tekmar_tha.setpoint_target == ThaValue.OFF
            or self._tekmar_tha.setpoint_target is None
        ):
            return False

        return super().available

    @property
    def native_value(self):
        try:
            return degHtoC(self._tekmar_tha.setpoint_target)

        except TypeError:
            return None


class SetpointDemand(ThaSensorBase):
    """Current setpoint demand for a Tekmar setpoint control."""

    icon = "mdi:format-list-bulleted"

    @property
    def unique_id(self) -> str:
        return (
            f"{self.config_entry_id}-{self._tekmar_tha.model}-"
            f"{self._tekmar_tha.device_id}-active-demand"
        )

    @property
    def name(self) -> str:
        return f"{self._tekmar_tha.tha_full_device_name} Active Demand"

    @property
    def available(self) -> bool:
        if self._tekmar_tha.active_demand == ThaValue.NA_8:
            return False

        return super().available

    @property
    def native_value(self):
        try:
            return ThaActiveDemand(self._tekmar_tha.active_demand).name

        except KeyError:
            return None
