import asyncio
import logging
import pickle
from os.path import exists
from threading import Lock
from typing import Any, Callable, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt

from .const import (
    ATTR_MANUFACTURER,
    DEFAULT_SETBACK_ENABLE,
    DEVICE_ATTRIBUTES,
    DEVICE_FEATURES,
    DEVICE_TYPES,
    DOMAIN,
    SETBACK_FAN_MAP,
    SETBACK_SETPOINT_MAP,
    ThaDefault,
    ThaSetback,
    ThaType,
)
from .trpc_msg import TrpcPacket, name_from_methodID
from .trpc_sock import TrpcSocket

_LOGGER = logging.getLogger(__name__)


class TekmarHub:
    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        host: str,
        port: int,
        opt_setback_enable: bool,
    ) -> None:
        self._hass = hass
        self._entry_id = entry_id
        self._name = name
        self._host = host
        self._port = port

        if opt_setback_enable is None:
            self._opt_setback_enable = DEFAULT_SETBACK_ENABLE
        else:
            self._opt_setback_enable = opt_setback_enable

        self._id = name.lower()
        self._sock = TrpcSocket(host, port)

        self._data_file = hass.config.path(
            f"{format(DOMAIN)}.{format(self._name)}.pickle"
        )
        self._storage = StoredData(self._data_file)
        self.storage_put(f"{format(DOMAIN)}.{format(self._name)}.pickle", True)

        self._tha_inventory = {}
        self.tha_gateway = []
        self.tha_devices = []
        self.online = False

        self._tha_fw_ver = None
        self._tha_pr_ver = None
        self._tha_reporting_state = None
        self._tha_setback_enable = None

        self._inRun = False
        self._inSetup = False
        self._inReconnect = False

        self._tx_queue = []

    async def async_init_tha(self) -> None:
        self._inSetup = True

        if await self._sock.open() is False:
            _LOGGER.error(self._sock.error)
            ir.async_create_issue(
                self._hass,
                DOMAIN,
                "check_configuration",
                is_fixable=True,
                severity=ir.IssueSeverity.ERROR,
                translation_key="check_configuration",
                data={"entry_id": self._entry_id},
            )
            raise ConfigEntryNotReady(
                f"Connection to packet server '{self._host}' failed"
            )

        await self._sock.write(
            TrpcPacket(service="Update", method="ReportingState", states=0x00)
        )

        self._tx_queue.append(
            TrpcPacket(
                service="Request",
                method="FirmwareRevision",
            )
        )

        self._tx_queue.append(
            TrpcPacket(
                service="Request",
                method="ProtocolVersion",
            )
        )

        if self._opt_setback_enable is True:
            packet_setback_enable = 0x01
        else:
            packet_setback_enable = 0x00

        self._tx_queue.append(
            TrpcPacket(
                service="Update", method="SetbackEnable", enable=packet_setback_enable
            )
        )

        # inventory must be last
        self._tx_queue.append(
            TrpcPacket(service="Request", method="DeviceInventory", address=0x0)
        )

        while self._inSetup is True:
            if len(self._tx_queue) != 0:
                try:
                    await self._sock.write(self._tx_queue.pop(0))
                    await asyncio.sleep(0.1)  # writing too fast causes errors
                except Exception as e:
                    _LOGGER.error(f"Write error: {e}")
                    raise ConfigEntryNotReady("Write error while in setup.")

            try:
                async with asyncio.timeout(5):
                    p = await self._sock.read()

            except Exception as e:
                _LOGGER.error(f"Read error: {e}")
                raise ConfigEntryNotReady("Read error while in setup.")

            if p is not None:
                try:
                    h = p.header
                    b = p.body
                    tha_method = name_from_methodID[h["methodID"]]

                    if tha_method in ["FirmwareRevision"]:
                        self._tha_fw_ver = b["revision"]

                    elif tha_method in ["ProtocolVersion"]:
                        self._tha_pr_ver = b["version"]

                    elif tha_method in ["SetbackEnable"]:
                        self._tha_setback_enable = b["enable"]

                    elif tha_method in ["ReportingState"]:
                        self._tha_reporting_state = b["state"]

                        if self._tha_reporting_state == 1:
                            self._inSetup = False

                    elif tha_method in ["DeviceInventory"]:
                        if b["address"] > 0:
                            _LOGGER.debug(f"Setting up address {b['address']}")

                            self._tha_inventory[b["address"]] = {
                                "entity": "",
                                "type": "",
                                "version": "",
                                "events": "",
                                "attributes": DEVICE_ATTRIBUTES(),
                            }

                            self._tx_queue.append(
                                TrpcPacket(
                                    service="Request",
                                    method="DeviceType",
                                    address=b["address"],
                                )
                            )
                            self._tx_queue.append(
                                TrpcPacket(
                                    service="Request",
                                    method="DeviceVersion",
                                    address=b["address"],
                                )
                            )
                            self._tx_queue.append(
                                TrpcPacket(
                                    service="Request",
                                    method="DeviceAttributes",
                                    address=b["address"],
                                )
                            )
                            self._tx_queue.append(
                                TrpcPacket(
                                    service="Request",
                                    method="SetbackEvents",
                                    address=b["address"],
                                )
                            )
                        else:
                            # inventory complete
                            self._tx_queue.append(
                                TrpcPacket(
                                    service="Update",
                                    method="ReportingState",
                                    state=0x01,
                                )
                            )

                    elif tha_method in ["DeviceType"]:
                        try:
                            self._tha_inventory[b["address"]]["type"] = b["type"]
                            self._tha_inventory[b["address"]][
                                "entity"
                            ] = "{3} {0} {1} {2}".format(
                                DEVICE_TYPES[
                                    self._tha_inventory[b["address"]]["type"]
                                ].capitalize(),
                                DEVICE_FEATURES[
                                    self._tha_inventory[b["address"]]["type"]
                                ]["model"],
                                b["address"],
                                self._name.capitalize(),
                            )
                            _LOGGER.debug(f"Address {b['address']} type {b['type']}")

                        except KeyError:
                            _LOGGER.warning(
                                (
                                    f"Unknown device type {b['type']}. "
                                    "Try power cycling your Gateway 482."
                                )
                            )
                            raise ConfigEntryNotReady(
                                f"Unknown device type {b['type']}."
                            )

                    elif tha_method in ["DeviceAttributes"]:
                        _LOGGER.debug(
                            f"Address {b['address']} attributes {b['attributes']}"
                        )
                        self._tha_inventory[b["address"]]["attributes"].attrs = int(
                            b["attributes"]
                        )

                    elif tha_method in ["DeviceVersion"]:
                        _LOGGER.debug(f"Address {b['address']} version {b['j_number']}")
                        self._tha_inventory[b["address"]]["version"] = b["j_number"]

                    elif tha_method in ["SetbackEvents"]:
                        _LOGGER.debug(
                            f"Address {b['address']} setback events {b['events']}"
                        )
                        self._tha_inventory[b["address"]]["events"] = b["events"]

                    else:
                        _LOGGER.warning(f"Ignored method {p} during setup.")

                except KeyError as e:
                    _LOGGER.debug(f"Ignored unknown key: {e}")
                    pass

        else:
            self.tha_gateway = [
                TekmarGateway(f"{self._id}", f"{self._host}", self),
            ]

            for address in self._tha_inventory:
                if (
                    DEVICE_TYPES[self._tha_inventory[address]["type"]]
                    == ThaType.THERMOSTAT
                ):
                    self.tha_devices.append(
                        TekmarThermostat(address, self._tha_inventory[address], self)
                    )

                elif (
                    DEVICE_TYPES[self._tha_inventory[address]["type"]]
                    == ThaType.SETPOINT
                ):
                    self.tha_devices.append(
                        TekmarSetpoint(address, self._tha_inventory[address], self)
                    )

                elif (
                    DEVICE_TYPES[self._tha_inventory[address]["type"]]
                    == ThaType.SNOWMELT
                ):
                    self.tha_devices.append(
                        TekmarSnowmelt(address, self._tha_inventory[address], self)
                    )

                else:
                    _LOGGER.error(f"Unknown device at address {address}")

            self.online = True

    async def run(self) -> None:
        self._inRun = True

        while self._inRun is True:
            if len(self._tx_queue) != 0:
                try:
                    await self._sock.write(self._tx_queue.pop(0))
                    await asyncio.sleep(0.1)

                except Exception as e:
                    _LOGGER.warning(f"Write error: {e} - reloading integration...")
                    await self._hass.config_entries.async_reload(self._entry_id)

            try:
                async with asyncio.timeout(65):
                    p = await self._sock.read()

            except TimeoutError as e:
                _LOGGER.warning(f"Timeout waiting for report: {e}")

                if self._sock.is_open:
                    await self._sock.close()

                if await self._sock.open() is False:
                    _LOGGER.error(self._sock.error)
                    ir.async_create_issue(
                        self._hass,
                        DOMAIN,
                        "check_configuration",
                        is_fixable=True,
                        severity=ir.IssueSeverity.ERROR,
                        translation_key="check_configuration",
                        data={"entry_id": self._entry_id},
                    )

                await asyncio.sleep(30)

                p = None

            except Exception as e:
                _LOGGER.warning(f"Read error: {e} - reloading integration...")
                await self._hass.config_entries.async_reload(self._entry_id)

            if p is not None:
                try:
                    h = p.header
                    b = p.body
                    tha_method = name_from_methodID[h["methodID"]]

                    if tha_method in ["ReportingState"]:
                        for gateway in self.tha_gateway:
                            await gateway.set_reporting_state(b["state"])

                    elif tha_method in ["NetworkError"]:
                        for gateway in self.tha_gateway:
                            await gateway.set_network_error(b["error"])

                    elif tha_method in ["OutdoorTemperature"]:
                        for gateway in self.tha_gateway:
                            await gateway.set_outdoor_temperature(p.body["temp"])

                    elif tha_method in ["CurrentTemperature"]:
                        for device in self.tha_devices:
                            if device.device_id == b["address"]:
                                await device.set_current_temperature(p.body["temp"])

                    elif tha_method in ["CurrentFloorTemperature"]:
                        for device in self.tha_devices:
                            if device.device_id == b["address"]:
                                await device.set_current_floor_temperature(
                                    p.body["temp"]
                                )

                    elif tha_method in ["HeatSetpoint"]:
                        for device in self.tha_devices:
                            if device.device_id == b["address"]:
                                # await device.set_setback_state(p.body['setback'])
                                await device.set_heat_setpoint(
                                    p.body["setpoint"], p.body["setback"]
                                )

                    elif tha_method in ["CoolSetpoint"]:
                        for device in self.tha_devices:
                            if device.device_id == b["address"]:
                                # await device.set_setback_state(p.body['setback'])
                                await device.set_cool_setpoint(
                                    p.body["setpoint"], p.body["setback"]
                                )

                    elif tha_method in ["SlabSetpoint"]:
                        for device in self.tha_devices:
                            if device.device_id == b["address"]:
                                # await device.set_setback_state(p.body['setback'])
                                await device.set_slab_setpoint(
                                    p.body["setpoint"], p.body["setback"]
                                )

                    elif tha_method in ["FanPercent"]:
                        for device in self.tha_devices:
                            if device.device_id == b["address"]:
                                await device.set_fan_percent(
                                    p.body["percent"], p.body["setback"]
                                )

                    elif tha_method in ["RelativeHumidity"]:
                        for device in self.tha_devices:
                            if device.device_id == b["address"]:
                                await device.set_relative_humidity(p.body["percent"])

                    elif tha_method in ["ActiveDemand"]:
                        try:
                            if (
                                DEVICE_TYPES[self._tha_inventory[b["address"]]["type"]]
                                == ThaType.THERMOSTAT
                            ):
                                self._tx_queue.append(
                                    TrpcPacket(
                                        service="Request",
                                        method="ModeSetting",
                                        address=b["address"],
                                    )
                                )
                        except KeyError as e:
                            _LOGGER.error(
                                (
                                    f"Device address {e} not in inventory. "
                                    "Reloading integration..."
                                )
                            )
                            await self._hass.config_entries.async_reload(self._entry_id)

                        for device in self.tha_devices:
                            if device.device_id == b["address"]:
                                await device.set_active_demand(p.body["demand"])

                    elif tha_method in ["SetbackState"]:
                        try:
                            if self._tha_inventory[b["address"]][
                                "attributes"
                            ].Fan_Percent:
                                self._tx_queue.append(
                                    TrpcPacket(
                                        service="Request",
                                        method="FanPercent",
                                        setback=ThaSetback.CURRENT,
                                        address=b["address"],
                                    )
                                )
                            for device in self.tha_devices:
                                if device.device_id == b["address"]:
                                    await device.set_setback_state(p.body["setback"])
                        except KeyError as e:
                            _LOGGER.error(
                                (
                                    f"Device address {e} not in inventory. "
                                    "Reloading integration..."
                                )
                            )
                            await self._hass.config_entries.async_reload(self._entry_id)

                    elif tha_method in ["SetbackEvents"]:
                        for device in self.tha_devices:
                            if device.device_id == b["address"]:
                                await device.set_setback_events(p.body["events"])

                    elif tha_method in ["ModeSetting"]:
                        for device in self.tha_devices:
                            if device.device_id == b["address"]:
                                await device.set_mode_setting(p.body["mode"])

                    elif tha_method in ["HumiditySetMin"]:
                        for device in self.tha_devices:
                            if device.device_id == b["address"]:
                                await device.set_humidity_setpoint_min(
                                    p.body["percent"]
                                )

                    elif tha_method in ["HumiditySetMax"]:
                        for device in self.tha_devices:
                            if device.device_id == b["address"]:
                                await device.set_humidity_setpoint_max(
                                    p.body["percent"]
                                )

                    elif tha_method in ["SetpointGroupEnable"]:
                        for gateway in self.tha_gateway:
                            await gateway.set_setpoint_group(
                                p.body["groupid"], p.body["enable"]
                            )

                    elif tha_method in ["SetpointDevice"]:
                        for device in self.tha_devices:
                            if device.device_id == b["address"]:
                                await device.set_setpoint_target(
                                    p.body["temp"], p.body["setback"]
                                )

                    elif tha_method in ["TakingAddress"]:
                        _LOGGER.error(
                            (
                                f"Device at address {p.body['old_address']} moved to "
                                f"{p.body['new_address']}. Reloading integration..."
                            )
                        )
                        await self._hass.config_entries.async_reload(self._entry_id)

                    elif tha_method in ["DeviceAttributes"]:
                        _LOGGER.error(
                            (
                                f"Device attributes for {b['address']} changed. "
                                "Reloading integration..."
                            )
                        )
                        await self._hass.config_entries.async_reload(self._entry_id)

                    elif tha_method in ["NullMethod"]:
                        pass

                    elif tha_method in ["DateTime"]:
                        pass

                    else:
                        _LOGGER.warning(f"Unhandeled method: {p}")

                except KeyError as e:
                    _LOGGER.debug(f"Ignored unknown key: {e}")
                    pass

    async def timekeeper(self, interval: int = 86400) -> None:
        while self._inRun is True:
            if not self._inReconnect:
                datetime = dt.now()
                await self.async_queue_message(
                    TrpcPacket(
                        service="Update",
                        method="DateTime",
                        year=int(datetime.strftime("%Y")),
                        month=int(datetime.strftime("%m")),
                        day=int(datetime.strftime("%d")),
                        weekday=int(datetime.strftime("%u")),
                        hour=int(datetime.strftime("%H")),
                        minute=int(datetime.strftime("%M")),
                    )
                )
            await asyncio.sleep(interval)

    async def async_queue_message(self, message: TrpcPacket) -> bool:
        self._tx_queue.append(message)
        return True

    def queue_message(self, message: TrpcPacket) -> None:
        self._tx_queue.append(message)

    async def shutdown(self) -> None:
        self._tx_queue = []
        self._inRun = False

        if await self._sock.open():
            await self._sock.write(
                TrpcPacket(service="Update", method="ReportingState", states=0)
            )
            await self._sock.close()

    @property
    def hub_id(self) -> str:
        return self._id

    @property
    def tha_fw_ver(self) -> int:
        return self._tha_fw_ver

    @property
    def tha_pr_ver(self) -> int:
        return self._tha_pr_ver

    @property
    def tha_reporting_state(self) -> int:
        return self._tha_reporting_state

    @property
    def tha_setback_enable(self) -> bool:
        if self._tha_setback_enable:
            return True
        else:
            return False

    def storage_get(self, key: Any) -> Any:
        return self._storage.get_setting(key)

    def storage_put(self, key: Any, value: Any) -> None:
        self._storage.put_setting(key, value)


class TekmarThermostat:
    def __init__(self, address: int, tha_device: [], hub: TekmarHub) -> None:
        self._id = address
        self.hub = hub
        self.tha_device = tha_device
        self._callbacks = set()

        self._tha_current_temperature = None  # degH
        self._tha_current_floor_temperature = None  # degH
        self._tha_active_demand = None
        self._tha_relative_humidity = None
        self._tha_setback_state = None
        self._tha_mode_setting = None
        self._tha_humidity_setpoint_min = None
        self._tha_humidity_setpoint_max = None

        self._config_vent_mode = self.hub.storage_get(f"{self._id}_config_vent_mode")
        self._config_emergency_heat = self.hub.storage_get(
            f"{self._id}_config_emergency_heat"
        )
        self._config_cooling = self.hub.storage_get(f"{self._id}_config_cooling")
        self._config_heating = self.hub.storage_get(f"{self._id}_config_heating")
        self._config_cool_setpoint_max = self.hub.storage_get(
            f"{self._id}_config_cool_setpoint_max"
        )
        self._config_cool_setpoint_min = self.hub.storage_get(
            f"{self._id}_config_cool_setpoint_min"
        )
        self._config_heat_setpoint_max = self.hub.storage_get(
            f"{self._id}_config_heat_setpoint_max"
        )
        self._config_heat_setpoint_min = self.hub.storage_get(
            f"{self._id}_config_heat_setpoint_min"
        )

        self._tha_heat_setpoints = {  # degE
            0x00: None,  # day
            0x01: None,  # night
            0x02: None,  # away
        }

        self._tha_cool_setpoints = {  # degE
            0x00: None,
            0x01: None,
            0x02: None,
        }

        self._tha_slab_setpoints = {  # degE
            0x00: None,
            0x01: None,
        }

        self._tha_fan_percent = {  # degE
            0x00: None,
            0x01: None,
        }

        # Some static information about this device
        self._device_type = DEVICE_TYPES[self.tha_device["type"]]
        self._tha_full_device_name = self.tha_device["entity"]
        self.firmware_version = self.tha_device["version"]
        self.model = DEVICE_FEATURES[self.tha_device["type"]]["model"]

        self._device_info = {
            "identifiers": {(DOMAIN, self._id)},
            "name": (
                f"{hub.hub_id.capitalize()} {self._device_type.capitalize()} "
                f"{self.model} {self._id}"
            ),
            "manufacturer": ATTR_MANUFACTURER,
            "model": self.model,
            "sw_version": self.firmware_version,
        }

        self.hub.queue_message(
            TrpcPacket(
                service="Request",
                method="SetbackState",
                address=self._id,
            )
        )

        self.hub.queue_message(
            TrpcPacket(
                service="Request",
                method="CurrentTemperature",
                address=self._id,
            )
        )

        self.hub.queue_message(
            TrpcPacket(
                service="Request",
                method="ModeSetting",
                address=self._id,
            )
        )

        self.hub.queue_message(
            TrpcPacket(
                service="Request",
                method="ActiveDemand",
                address=self._id,
            )
        )

        if self.setback_enable is True:
            if self.tha_device["attributes"].Zone_Cooling:
                self.hub.queue_message(
                    TrpcPacket(
                        service="Request",
                        method="CoolSetpoint",
                        address=self._id,
                        setback=0x00,
                    )
                )
                self.hub.queue_message(
                    TrpcPacket(
                        service="Request",
                        method="CoolSetpoint",
                        address=self._id,
                        setback=0x03,
                    )
                )
                self.hub.queue_message(
                    TrpcPacket(
                        service="Request",
                        method="CoolSetpoint",
                        address=self._id,
                        setback=0x06,
                    )
                )

            if self.tha_device["attributes"].Zone_Heating:
                self.hub.queue_message(
                    TrpcPacket(
                        service="Request",
                        method="HeatSetpoint",
                        address=self._id,
                        setback=0x00,
                    )
                )
                self.hub.queue_message(
                    TrpcPacket(
                        service="Request",
                        method="HeatSetpoint",
                        address=self._id,
                        setback=0x03,
                    )
                )
                self.hub.queue_message(
                    TrpcPacket(
                        service="Request",
                        method="HeatSetpoint",
                        address=self._id,
                        setback=0x06,
                    )
                )

        else:
            if self.tha_device["attributes"].Zone_Cooling:
                self.hub.queue_message(
                    TrpcPacket(
                        service="Request",
                        method="CoolSetpoint",
                        address=self._id,
                        setback=ThaSetback.CURRENT,
                    )
                )

            if self.tha_device["attributes"].Zone_Heating:
                self.hub.queue_message(
                    TrpcPacket(
                        service="Request",
                        method="HeatSetpoint",
                        address=self._id,
                        setback=ThaSetback.CURRENT,
                    )
                )

        if self.tha_device["attributes"].Fan_Percent:
            self.hub.queue_message(
                TrpcPacket(
                    service="Request",
                    method="FanPercent",
                    address=self._id,
                    setback=0x04,
                )
            )
            self.hub.queue_message(
                TrpcPacket(
                    service="Request",
                    method="FanPercent",
                    address=self._id,
                    setback=0x05,
                )
            )

        if self.tha_device["attributes"].Slab_Setpoint:
            self.hub.queue_message(
                TrpcPacket(
                    service="Request",
                    method="SlabSetpoint",
                    address=self._id,
                    setback=ThaSetback.CURRENT,
                )
            )

        if DEVICE_FEATURES[self.tha_device["type"]]["humid"] and hub.tha_pr_ver in [
            2,
            3,
        ]:
            self.hub.queue_message(
                TrpcPacket(
                    service="Request", method="RelativeHumidity", address=self._id
                )
            )
            self.hub.queue_message(
                TrpcPacket(service="Request", method="HumiditySetMax", address=self._id)
            )
            self.hub.queue_message(
                TrpcPacket(service="Request", method="HumiditySetMin", address=self._id)
            )

    @property
    def device_id(self) -> str:
        return self._id

    @property
    def tha_device_type(self) -> str:
        return self._device_type

    @property
    def tha_full_device_name(self) -> str:
        return self._tha_full_device_name

    @property
    def current_temperature(self) -> str:
        return self._tha_current_temperature

    @property
    def current_floor_temperature(self) -> str:
        if self.hub.tha_pr_ver not in [3]:
            return None
        else:
            return self._tha_current_floor_temperature

    @property
    def relative_humidity(self) -> str:
        if self.hub.tha_pr_ver not in [2, 3]:
            return None
        else:
            return self._tha_relative_humidity

    @property
    def cool_setpoint(self) -> str:
        try:
            return self._tha_cool_setpoints[
                SETBACK_SETPOINT_MAP[self._tha_setback_state]
            ]
        except KeyError:
            return None

    @property
    def cool_setpoint_day(self) -> str:
        return self._tha_cool_setpoints[0x00]

    @property
    def cool_setpoint_night(self) -> str:
        return self._tha_cool_setpoints[0x01]

    @property
    def cool_setpoint_away(self) -> str:
        return self._tha_cool_setpoints[0x02]

    @property
    def heat_setpoint(self) -> str:
        try:
            return self._tha_heat_setpoints[
                SETBACK_SETPOINT_MAP[self._tha_setback_state]
            ]
        except KeyError:
            return None

    @property
    def heat_setpoint_day(self) -> str:
        return self._tha_heat_setpoints[0x00]

    @property
    def heat_setpoint_night(self) -> str:
        return self._tha_heat_setpoints[0x01]

    @property
    def heat_setpoint_away(self) -> str:
        return self._tha_heat_setpoints[0x02]

    @property
    def config_emergency_heat(self) -> bool:
        return self._config_emergency_heat

    @property
    def config_vent_mode(self) -> bool:
        return self._config_vent_mode

    @property
    def config_heat_setpoint_max(self) -> int:
        if self._config_heat_setpoint_max is None:
            return ThaDefault.HEAT_MAX
        else:
            return self._config_heat_setpoint_max

    @property
    def config_heat_setpoint_min(self) -> int:
        if self._config_heat_setpoint_min is None:
            return ThaDefault.HEAT_MIN
        else:
            return self._config_heat_setpoint_min

    @property
    def config_cool_setpoint_max(self) -> int:
        if self._config_cool_setpoint_max is None:
            return ThaDefault.COOL_MAX
        else:
            return self._config_cool_setpoint_max

    @property
    def config_cool_setpoint_min(self) -> int:
        if self._config_cool_setpoint_min is None:
            return ThaDefault.COOL_MIN
        else:
            return self._config_cool_setpoint_min

    @property
    def slab_setpoint(self) -> str:
        return self._tha_slab_setpoint

    @property
    def active_demand(self) -> str:
        return self._tha_active_demand

    @property
    def setback_enable(self) -> bool:
        return self.hub.tha_setback_enable

    @property
    def setback_state(self) -> str:
        return self._tha_setback_state

    @property
    def setback_events(self) -> str:
        return self.tha_device["events"]

    @property
    def mode_setting(self) -> str:
        return self._tha_mode_setting

    @property
    def fan_percent(self) -> str:
        try:
            return self._tha_fan_percent[SETBACK_FAN_MAP[self.setback_state]]
        except KeyError:
            return None

    @property
    def humidity_setpoint_min(self) -> str:
        if self.hub.tha_pr_ver not in [2, 3]:
            return None
        else:
            return self._tha_humidity_setpoint_min

    @property
    def humidity_setpoint_max(self) -> str:
        if self.hub.tha_pr_ver not in [2, 3]:
            return None
        else:
            return self._tha_humidity_setpoint_max

    async def set_config_emer_heat(self, value: bool) -> None:
        self._config_emergency_heat = value
        self.hub.storage_put(f"{self._id}_config_emergency_heat", value)
        await self.publish_updates()

    async def set_config_vent_mode(self, value: bool) -> None:
        self._config_vent_mode = value
        self.hub.storage_put(f"{self._id}_config_vent_mode", value)
        await self.publish_updates()

    async def set_current_temperature(self, temp: int) -> None:
        self._tha_current_temperature = temp
        await self.publish_updates()

    async def set_current_floor_temperature(self, temp: int) -> None:
        self._tha_current_floor_temperature = temp
        await self.publish_updates()

    async def set_relative_humidity(self, humidity: int) -> None:
        self._tha_relative_humidity = humidity
        await self.publish_updates()

    async def set_heat_setpoint(self, setpoint: int, setback: int) -> None:
        self._tha_heat_setpoints[SETBACK_SETPOINT_MAP[setback]] = setpoint
        await self.publish_updates()

    async def set_heat_setpoint_txqueue(
        self, value: int, setback: int = ThaSetback.CURRENT
    ) -> None:
        await self.hub.async_queue_message(
            TrpcPacket(
                service="Update",
                method="HeatSetpoint",
                address=self._id,
                setback=setback,
                setpoint=value,
            )
        )

    async def set_cool_setpoint(self, setpoint: int, setback: int) -> None:
        self._tha_cool_setpoints[SETBACK_SETPOINT_MAP[setback]] = setpoint
        await self.publish_updates()

    async def set_cool_setpoint_txqueue(
        self, value: int, setback: int = ThaSetback.CURRENT
    ) -> None:
        await self.hub.async_queue_message(
            TrpcPacket(
                service="Update",
                method="CoolSetpoint",
                address=self._id,
                setback=setback,
                setpoint=value,
            )
        )

    async def set_slab_setpoint(self, setpoint: int, setback: int) -> None:
        self._tha_slab_setpoints[SETBACK_SETPOINT_MAP[setback]] = setpoint
        await self.publish_updates()

    async def set_fan_percent(self, percent: int, setback: int) -> None:
        self._tha_fan_percent[SETBACK_FAN_MAP[setback]] = percent
        await self.publish_updates()

    async def set_fan_percent_txqueue(
        self, percent: int, setback: int = ThaSetback.CURRENT
    ) -> None:
        await self.hub.async_queue_message(
            TrpcPacket(
                service="Update",
                method="FanPercent",
                address=self._id,
                setback=setback,
                percent=percent,
            )
        )

    async def set_active_demand(self, demand: int) -> None:
        self._tha_active_demand = demand
        await self.publish_updates()

    async def set_setback_state(self, setback: int) -> None:
        self._tha_setback_state = setback
        await self.publish_updates()

    async def set_mode_setting(self, mode: int) -> None:
        self._tha_mode_setting = mode

        if mode == 0x06:
            self.hub.storage_put(f"{self._id}_config_emergency_heat", True)
            self._config_emergency_heat = True

        await self.publish_updates()

    async def set_mode_setting_txqueue(self, value: int) -> None:
        await self.hub.async_queue_message(
            TrpcPacket(
                service="Update", method="ModeSetting", address=self._id, mode=value
            )
        )

    async def set_humidity_setpoint_min(self, percent: int) -> None:
        self._tha_humidity_setpoint_min = percent
        await self.publish_updates()

    async def set_humidity_setpoint_min_txqueue(self, value: int) -> None:
        await self.hub.async_queue_message(
            TrpcPacket(
                service="Update",
                method="HumiditySetMin",
                address=self._id,
                percent=int(value),
            )
        )

    async def set_humidity_setpoint_max(self, percent: int) -> None:
        self._tha_humidity_setpoint_max = percent
        await self.publish_updates()

    async def set_humidity_setpoint_max_txqueue(self, value: int) -> None:
        await self.hub.async_queue_message(
            TrpcPacket(
                service="Update",
                method="HumiditySetMax",
                address=self._id,
                percent=int(value),
            )
        )

    async def set_setback_events(self, events: int) -> None:
        self.tha_device["events"] = events
        await self.publish_updates()

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register callback, called when TekmarThermostat changes state."""
        self._callbacks.add(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove previously registered callback."""
        self._callbacks.discard(callback)

    async def publish_updates(self) -> None:
        """Schedule call all registered callbacks."""
        for callback in self._callbacks:
            callback()

    @property
    def online(self) -> float:
        """Device is online."""
        return True

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return self._device_info


class TekmarSetpoint:
    def __init__(self, address: int, tha_device: [], hub: TekmarHub) -> None:
        self._id = address
        self.hub = hub
        self.tha_device = tha_device
        self._callbacks = set()

        self._tha_current_temperature = None  # degH
        self._tha_current_floor_temperature = None  # degH
        self._tha_setpoint_target_temperature = None  # degH
        self._tha_active_demand = None
        self._tha_setback_state = None

        # Some static information about this device
        self._device_type = DEVICE_TYPES[self.tha_device["type"]]
        self._tha_full_device_name = self.tha_device["entity"]
        self.firmware_version = self.tha_device["version"]
        self.model = DEVICE_FEATURES[self.tha_device["type"]]["model"]

        self._device_info = {
            "identifiers": {(DOMAIN, self._id)},
            "name": (
                f"{hub.hub_id.capitalize()} {self._device_type.capitalize()} "
                f"{self.model} {self._id}"
            ),
            "manufacturer": ATTR_MANUFACTURER,
            "model": self.model,
            "sw_version": self.firmware_version,
        }

        self.hub.queue_message(
            TrpcPacket(
                service="Request",
                method="SetbackState",
                address=self._id,
            )
        )

        self.hub.queue_message(
            TrpcPacket(
                service="Request",
                method="ActiveDemand",
                address=self._id,
            )
        )

        self.hub.queue_message(
            TrpcPacket(
                service="Request",
                method="CurrentTemperature",
                address=self._id,
            )
        )

        # self.hub.queue_message(
        #    TrpcPacket(
        #        service = 'Request',
        #        method = 'CurrentFloorTemperature',
        #        address = self._id,
        #    )
        # )

        self.hub.queue_message(
            TrpcPacket(
                service="Request",
                method="SetpointDevice",
                setback=ThaSetback.CURRENT,
                address=self._id,
            )
        )

    @property
    def device_id(self) -> str:
        return self._id

    @property
    def tha_device_type(self) -> str:
        return self._device_type

    @property
    def tha_full_device_name(self) -> str:
        return self._tha_full_device_name

    @property
    def current_temperature(self) -> str:
        return self._tha_current_temperature

    @property
    def current_floor_temperature(self) -> str:
        if self.hub.tha_pr_ver not in [3]:
            return None
        else:
            return self._tha_current_floor_temperature

    @property
    def setpoint_target(self) -> str:
        return self._tha_setpoint_target_temperature

    @property
    def setback_enable(self) -> bool:
        return self.hub.tha_setback_enable

    @property
    def setback_state(self) -> str:
        return self._tha_setback_state

    @property
    def active_demand(self) -> str:
        return self._tha_active_demand

    async def set_current_temperature(self, temp: int) -> None:
        self._tha_current_temperature = temp
        await self.publish_updates()

    async def set_current_floor_temperature(self, temp: int) -> None:
        self._tha_current_floor_temperature = temp
        await self.publish_updates()

    async def set_setpoint_target(self, temp: int, setback: int) -> None:
        self._tha_setpoint_target_temperature = temp
        await self.publish_updates()

    async def set_active_demand(self, demand: int) -> None:
        self._tha_active_demand = demand
        await self.publish_updates()

    async def set_setback_state(self, setback: int) -> None:
        self._tha_setback_state = setback
        await self.publish_updates()

    def register_callback(self, callback: Callable[[], None]) -> None:
        self._callbacks.add(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        self._callbacks.discard(callback)

    async def publish_updates(self) -> None:
        for callback in self._callbacks:
            callback()

    @property
    def online(self) -> float:
        """Device is online."""
        return True

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return self._device_info


class TekmarSnowmelt:
    def __init__(self, address: int, tha_device: [], hub: TekmarHub) -> None:
        self._id = address
        self.hub = hub
        self.tha_device = tha_device
        self._callbacks = set()

        self._tha_active_demand = None

        # Some static information about this device
        self._device_type = DEVICE_TYPES[self.tha_device["type"]]
        self._tha_full_device_name = self.tha_device["entity"]
        self.firmware_version = self.tha_device["version"]
        self.model = DEVICE_FEATURES[self.tha_device["type"]]["model"]

        self._device_info = {
            "identifiers": {(DOMAIN, self._id)},
            "name": (
                f"{hub.hub_id.capitalize()} {self._device_type.capitalize()} "
                f"{self.model} {self._id}"
            ),
            "manufacturer": ATTR_MANUFACTURER,
            "model": self.model,
            "sw_version": self.firmware_version,
        }

    @property
    def device_id(self) -> str:
        return self._id

    @property
    def tha_device_type(self) -> str:
        return self._device_type

    @property
    def tha_full_device_name(self) -> str:
        return self._tha_full_device_name

    @property
    def active_demand(self) -> str:
        return self._tha_active_demand

    async def set_active_demand(self, demand: int) -> None:
        self._tha_active_demand = demand
        await self.publish_updates()

    def register_callback(self, callback: Callable[[], None]) -> None:
        self._callbacks.add(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        self._callbacks.discard(callback)

    async def publish_updates(self) -> None:
        for callback in self._callbacks:
            callback()

    @property
    def online(self) -> float:
        """Device is online."""
        return True

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return self._device_info


class TekmarGateway:
    def __init__(self, gatewayid: str, host: str, hub: TekmarHub) -> None:
        self._id = gatewayid
        self._host = host
        self.hub = hub
        self._callbacks = set()

        self._tha_network_error = 0x0
        self._tha_outdoor_temperature = None
        self._tha_setpoint_groups = {
            1: None,
            2: None,
            3: None,
            4: None,
            5: None,
            6: None,
            7: None,
            8: None,
            9: None,
            10: None,
            11: None,
            12: None,
        }

        # Some static information about this device
        self.firmware_version = f"{hub.tha_fw_ver} protocol {hub.tha_pr_ver}"
        self.model = "482"

        self._device_info = {
            "identifiers": {(DOMAIN, self.hub.hub_id)},
            "name": f"{hub.hub_id.capitalize()} Gateway",
            "manufacturer": ATTR_MANUFACTURER,
            "model": self.model,
            "sw_version": self.firmware_version,
        }

        self.hub.queue_message(
            TrpcPacket(service="Request", method="OutdoorTemperature")
        )

        for group in range(1, 13):
            self.hub.queue_message(
                TrpcPacket(
                    service="Request", method="SetpointGroupEnable", groupid=group
                )
            )

    @property
    def gateway_id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._host

    async def set_reporting_state(self, state: int) -> None:
        self.hub._tha_reporting_state = state
        await self.publish_updates()

    async def set_outdoor_temperature(self, temp: int) -> None:
        self._tha_outdoor_temperature = temp
        await self.publish_updates()

    async def set_network_error(self, neterr: int) -> None:
        self._tha_network_error = neterr
        await self.publish_updates()

    async def set_setpoint_group(self, group: int, value: int) -> None:
        if group in list(range(1, 13)):
            self._tha_setpoint_groups[group] = value
            await self.publish_updates()

    async def set_setpoint_group_txqueue(self, group: int, value: bool) -> None:
        await self.hub.async_queue_message(
            TrpcPacket(
                service="Update",
                method="SetpointGroupEnable",
                groupid=group,
                enable=value,
            )
        )

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register callback, called when TekmarGateway changes state."""
        self._callbacks.add(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove previously registered callback."""
        self._callbacks.discard(callback)

    async def publish_updates(self) -> None:
        """Schedule call all registered callbacks."""
        for callback in self._callbacks:
            callback()

    @property
    def online(self) -> float:
        """Device is online."""
        return True

    @property
    def reporting_state(self) -> int:
        return self.hub.tha_reporting_state

    @property
    def setback_enable(self) -> bool:
        return self.hub.tha_setback_enable

    @property
    def outdoor_temprature(self) -> int:
        return self._tha_outdoor_temperature

    @property
    def network_error(self) -> int:
        return self._tha_network_error

    @property
    def setpoint_groups(self) -> Dict[int, Any]:
        return self._tha_setpoint_groups

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return self._device_info


class StoredData(object):
    """Abstraction over pickle data storage."""

    def __init__(self, data_file):
        """Initialize pickle data storage."""
        self._data_file = data_file
        self._lock = Lock()
        self._cache_outdated = True
        self._data = {}
        self._fetch_data()

    def _fetch_data(self):
        """Fetch data stored into pickle file."""
        if self._cache_outdated and exists(self._data_file):
            try:
                _LOGGER.debug(f"Fetching data from file {self._data_file}")
                with self._lock, open(self._data_file, "rb") as myfile:
                    self._data = pickle.load(myfile) or {}
                    self._cache_outdated = False

            except Exception:
                _LOGGER.error(f"Error loading data from pickled file {self._data_file}")

    def get_setting(self, key):
        self._fetch_data()
        return self._data.get(key)

    def put_setting(self, key, value):
        self._fetch_data()
        with self._lock, open(self._data_file, "wb") as myfile:
            self._data.update({key: value})
            _LOGGER.debug(f"Writing {key}:{value} in storage file {self._data_file}")
            try:
                pickle.dump(self._data, myfile)

            except Exception:
                _LOGGER.error(f"Error saving pickled data to {self._data_file}")

        self._cache_outdated = True
