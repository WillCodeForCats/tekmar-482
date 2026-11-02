"""The Tekmar Gateway 482 hub module."""

import asyncio
from collections.abc import Callable
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_MANUFACTURER,
    DEFAULT_SETBACK_ENABLE,
    DEVICE_FEATURES,
    DEVICE_TYPES,
    DOMAIN,
    SETBACK_FAN_MAP,
    SETBACK_SETPOINT_MAP,
    STORAGE_KEY,
    STORAGE_VERSION_MAJOR,
    DeviceAttributes,
    ThaDefault,
    ThaSetback,
    ThaType,
    ThaValue,
)
from .fields import Record
from .trpc_msg import TrpcPacket, name_from_methodID
from .trpc_sock import TrpcSocket

_LOGGER = logging.getLogger(__name__)

# Updates from the gateway
_GATEWAY_UPDATES = {
    "ReportingState": ("set_reporting_state", ("state",)),
    "NetworkError": ("set_network_error", ("error",)),
    "OutdoorTemperature": ("set_outdoor_temperature", ("temp",)),
    "SetpointGroupEnable": ("set_setpoint_group", ("groupid", "enable")),
}

# Updates from a device behind the gateway
_DEVICE_UPDATES = {
    "CurrentTemperature": ("set_current_temperature", ("temp",)),
    "CurrentFloorTemperature": ("set_current_floor_temperature", ("temp",)),
    "HeatSetpoint": ("set_heat_setpoint", ("setpoint", "setback")),
    "CoolSetpoint": ("set_cool_setpoint", ("setpoint", "setback")),
    "SlabSetpoint": ("set_slab_setpoint", ("setpoint", "setback")),
    "FanPercent": ("set_fan_percent", ("percent", "setback")),
    "RelativeHumidity": ("set_relative_humidity", ("percent",)),
    "SetbackEvents": ("set_setback_events", ("events",)),
    "ModeSetting": ("set_mode_setting", ("mode",)),
    "HumiditySetMin": ("set_humidity_setpoint_min", ("percent",)),
    "HumiditySetMax": ("set_humidity_setpoint_max", ("percent",)),
    "SetpointDevice": ("set_setpoint_target", ("temp", "setback")),
}


class TekmarHub:
    """Tekmar hub for communicating with the gateway addon."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        host: str,
        port: int,
        opt_setback_enable: bool,
    ) -> None:
        """Initialize the Tekmar hub."""
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
        self._online = False
        self._sock = TrpcSocket(host, port)

        self._storage = StoredData(self._hass, self._entry_id)

        self._tha_inventory = {}
        self.tha_gateway = []
        self.tha_devices = []
        self.tha_ignore_addr = []

        self._tha_fw_ver = None
        self._tha_pr_ver = None
        self._tha_reporting_state = None
        self._tha_setback_enable = None

        self._inRun = False
        self._inSetup = False
        self._inReconnect = False

        self._tx_queue = []
        self._tasks: list[asyncio.Task] = []

    def add_task(self, task: asyncio.Task) -> None:
        """Track a background task so shutdown() can cancel it."""
        self._tasks.append(task)

    async def async_init_tha(self) -> None:
        """Connect to the gateway, read its inventory, and create devices."""
        self._inSetup = True

        await self.storage_put("storage", True)

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
            TrpcPacket(service="Update", method="ReportingState", state=ThaValue.OFF)
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
                    write_packet = self._tx_queue.pop(0)
                    _LOGGER.debug("Setup %s", write_packet)
                    await self._sock.write(write_packet)
                    await asyncio.sleep(0.1)  # writing too fast causes errors
                except OSError as e:
                    _LOGGER.error("Write error: %s", e)
                    raise ConfigEntryNotReady("Write error while in setup.") from e

            try:
                p = await self._sock.read()

            except (OSError, ValueError) as e:
                _LOGGER.error("Read error: %s", e)
                raise ConfigEntryNotReady("Read error while in setup.") from e

            if p is not None:
                try:
                    self._handle_setup_packet(p)
                except KeyError as e:
                    _LOGGER.debug("Ignored unknown key: %s", e)

        new_gateway = TekmarGateway(f"{self._id}", f"{self._host}", self)
        new_gateway.init_device()
        self.tha_gateway = [
            new_gateway,
        ]

        for address in self._tha_inventory:
            if address in self.tha_ignore_addr:
                _LOGGER.debug("Ignored address %s while creating devices.", address)
                continue

            if DEVICE_TYPES[self._tha_inventory[address]["type"]] == ThaType.THERMOSTAT:
                new_thermostat = TekmarThermostat(
                    address, self._tha_inventory[address], self
                )
                await new_thermostat.init_device()
                self.tha_devices.append(new_thermostat)

            elif DEVICE_TYPES[self._tha_inventory[address]["type"]] == ThaType.SETPOINT:
                new_setpoint = TekmarSetpoint(
                    address, self._tha_inventory[address], self
                )
                new_setpoint.init_device()
                self.tha_devices.append(new_setpoint)

            elif DEVICE_TYPES[self._tha_inventory[address]["type"]] == ThaType.SNOWMELT:
                new_snowmelt = TekmarSnowmelt(
                    address, self._tha_inventory[address], self
                )
                new_snowmelt.init_device()
                self.tha_devices.append(new_snowmelt)

            else:
                _LOGGER.warning("Unknown device at address %s", address)

        if not self.online:
            ir.async_delete_issue(self._hass, DOMAIN, "check_configuration")

        self.online = True

    def _handle_setup_packet(self, p: TrpcPacket) -> None:
        """Process a packet received during setup."""
        h = p.header
        b = p.body
        tha_method = name_from_methodID[h["methodID"]]

        _LOGGER.debug("Setup %s", p)

        if tha_method == "FirmwareRevision":
            self._tha_fw_ver = b["revision"]

        elif tha_method == "ProtocolVersion":
            self._tha_pr_ver = b["version"]

        elif tha_method == "SetbackEnable":
            self._tha_setback_enable = b["enable"]

        elif tha_method == "ReportingState":
            self._tha_reporting_state = b["state"]

            if self._tha_reporting_state == 1:
                self._inSetup = False

        elif tha_method == "DeviceInventory":
            if b["address"] > 0:
                _LOGGER.debug("Setting up address %s", b["address"])

                self._tha_inventory[b["address"]] = {
                    "entity": "",
                    "type": "",
                    "version": "",
                    "events": "",
                    "attributes": DeviceAttributes(),
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
                        state=ThaValue.ON,
                    )
                )

        elif tha_method == "DeviceType":
            try:
                self._tha_inventory[b["address"]]["type"] = b["type"]
                type_name = DEVICE_TYPES[b["type"]].capitalize()
                model = DEVICE_FEATURES[b["type"]]["model"]
                self._tha_inventory[b["address"]]["entity"] = (
                    f"{self._name.capitalize()} {type_name} {model} {b['address']}"
                )
                _LOGGER.debug("Address %s type %s", b["address"], b["type"])

            except KeyError:
                _LOGGER.warning(
                    "Unknown device type %s at address %s. This address will be ignored.",
                    b["type"],
                    b["address"],
                )

                self.tha_ignore_addr.append(b["address"])

        elif tha_method == "DeviceAttributes":
            _LOGGER.debug("Address %s attributes %s", b["address"], b["attributes"])
            self._tha_inventory[b["address"]]["attributes"].attrs = int(b["attributes"])

        elif tha_method == "DeviceVersion":
            _LOGGER.debug("Address %s version %s", b["address"], b["j_number"])
            self._tha_inventory[b["address"]]["version"] = b["j_number"]

        elif tha_method == "SetbackEvents":
            _LOGGER.debug("Address %s setback events %s", b["address"], b["events"])
            self._tha_inventory[b["address"]]["events"] = b["events"]

        else:
            _LOGGER.warning("Ignored method %s during setup.", tha_method)

    async def run(self) -> None:
        """Process the transmit queue and incoming packets until shutdown."""
        self._inRun = True
        read_cycle = 0

        while self._inRun is True:
            try:
                if not self._sock.is_open:
                    read_cycle = 0
                    if await self._sock.open() is False:
                        raise ConnectionError(f"Connection to {self._host} failed")

                    # make sure reporting is on when we reconnect
                    self._tx_queue.append(
                        TrpcPacket(
                            service="Update",
                            method="ReportingState",
                            state=ThaValue.ON,
                        )
                    )

                if len(self._tx_queue) != 0:
                    write_packet = self._tx_queue.pop(0)
                    _LOGGER.debug("Run %s", write_packet)
                    await self._sock.write(write_packet)
                    await asyncio.sleep(0.1)

                read_cycle += 1
                p = await self._sock.read()

                if read_cycle > 130:
                    raise ConnectionError(f"No reports from {self._host}")

            except (OSError, ValueError) as e:
                _LOGGER.warning("Socket error: %s - reconnecting.", e)
                await self._sock.close()
                await asyncio.sleep(5)
                p = None

            if p is not None:
                read_cycle = 0

                try:
                    await self._async_handle_run_packet(p)
                except KeyError as e:
                    _LOGGER.debug("Ignored unknown key: %s", e)

    async def _async_handle_run_packet(self, p: TrpcPacket) -> None:
        """Process a packet received while running."""
        b = p.body
        tha_method = name_from_methodID[p.header["methodID"]]

        _LOGGER.debug("Run %s", p)

        if b["address"] in self.tha_ignore_addr:
            _LOGGER.debug("Ignored %s from address %s", tha_method, b["address"])
            return

        if tha_method in _GATEWAY_UPDATES:
            setter, fields = _GATEWAY_UPDATES[tha_method]
            for gateway in self.tha_gateway:
                await getattr(gateway, setter)(*(b[f] for f in fields))

        elif tha_method in _DEVICE_UPDATES:
            setter, fields = _DEVICE_UPDATES[tha_method]
            for device in self.tha_devices:
                if device.device_id == b["address"]:
                    await getattr(device, setter)(*(b[f] for f in fields))

        elif tha_method == "ActiveDemand":
            await self._async_handle_active_demand(b)

        elif tha_method == "SetbackState":
            await self._async_handle_setback_state(b)

        elif tha_method == "TakingAddress":
            _LOGGER.warning(
                "Device at address %s moved to %s. Reloading integration...",
                b["old_address"],
                b["new_address"],
            )
            await self._hass.config_entries.async_reload(self._entry_id)

        elif tha_method == "DeviceAttributes":
            _LOGGER.debug(
                "Ignoring attributes from %s in run: received %s setup with %s",
                b["address"],
                int(b["attributes"]),
                self._tha_inventory[b["address"]]["attributes"].attrs,
            )

        elif tha_method in ("NullMethod", "DateTime"):
            pass

        else:
            _LOGGER.warning("Unhandled method: %s", tha_method)

    async def _async_handle_active_demand(self, b: Record) -> None:
        """Store active demand and request the mode setting for thermostats."""
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
            _LOGGER.warning(
                "Device address %s not in inventory. Reloading integration...",
                e,
            )
            await self._hass.config_entries.async_reload(self._entry_id)

        for device in self.tha_devices:
            if device.device_id == b["address"]:
                await device.set_active_demand(b["demand"])

    async def _async_handle_setback_state(self, b: Record) -> None:
        """Store setback state and request the fan percent if supported."""
        try:
            if self._tha_inventory[b["address"]]["attributes"].FanPercent:
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
                    await device.set_setback_state(b["setback"])
        except KeyError as e:
            _LOGGER.warning(
                "Device address %s not in inventory. Reloading integration...",
                e,
            )
            await self._hass.config_entries.async_reload(self._entry_id)

    async def timekeeper(self, interval: int = 86400) -> None:
        """Periodically send the current date and time."""
        while self._inRun is True:
            if not self._inReconnect:
                datetime = dt_util.now()
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
        """Add a packet to the transmit queue."""
        self._tx_queue.append(message)
        return True

    def queue_message(self, message: TrpcPacket) -> None:
        """Add a packet to the transmit queue."""
        self._tx_queue.append(message)

    async def shutdown(self) -> None:
        """Stop the run loop and turn off gateway reporting."""
        self._tx_queue = []
        self._inRun = False

        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        if await self._sock.open():
            await self._sock.write(
                TrpcPacket(
                    service="Update", method="ReportingState", state=ThaValue.OFF
                )
            )
            await self._sock.close()

    @property
    def hub_id(self) -> str:
        """Return the hub id."""
        return self._id

    @property
    def online(self) -> bool:
        """Return the online."""
        return self._online

    @online.setter
    def online(self, value: bool) -> None:
        if value is True:
            self._online = True
        else:
            self._online = False

    @property
    def tha_fw_ver(self) -> int:
        """Return the tha fw ver."""
        return self._tha_fw_ver

    @property
    def tha_pr_ver(self) -> int:
        """Return the tha pr ver."""
        return self._tha_pr_ver

    @property
    def tha_reporting_state(self) -> int:
        """Return the tha reporting state."""
        return self._tha_reporting_state

    @tha_reporting_state.setter
    def tha_reporting_state(self, value: int) -> None:
        self._tha_reporting_state = value

    @property
    def tha_setback_enable(self) -> bool:
        """Return the tha setback enable."""
        if self._tha_setback_enable:
            return True
        return False

    async def storage_get(self, key: Any) -> Any:
        """Return a stored setting."""
        return await self._storage.get_setting(key)

    async def storage_put(self, key: Any, value: Any) -> None:
        """Save a setting to storage."""
        await self._storage.put_setting(key, value)


class TekmarThermostat:
    """Tekmar thermostat device."""

    def __init__(self, address: int, tha_device: [], hub: TekmarHub) -> None:
        """Initialize the Tekmar thermostat."""
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
        self._config_vent_mode = None
        self._config_emergency_heat = None
        self._config_cooling = None
        self._config_heating = None
        self._config_cool_setpoint_max = None
        self._config_cool_setpoint_min = None
        self._config_heat_setpoint_max = None
        self._config_heat_setpoint_min = None
        self._config_slab_setpoint_max = None
        self._config_slab_setpoint_min = None

        self._tha_heat_setpoints = {  # degE
            0x00: None,  # day
            0x01: None,  # night
            0x02: None,  # away
        }

        self._tha_cool_setpoints = {  # degE
            0x00: None,  # day
            0x01: None,  # night
            0x02: None,  # away
        }

        self._tha_slab_setpoints = {  # degE
            0x00: None,  # day
            0x01: None,  # night
            0x02: None,  # away
        }

        self._tha_fan_percent = {  # degE
            0x00: None,  # day
            0x01: None,  # night
        }

    async def init_device(self) -> None:
        """Load stored settings and request the initial device state."""
        self._config_vent_mode = await self.hub.storage_get(
            f"{self._id}_config_vent_mode"
        )
        self._config_emergency_heat = await self.hub.storage_get(
            f"{self._id}_config_emergency_heat"
        )
        self._config_cooling = await self.hub.storage_get(f"{self._id}_config_cooling")
        self._config_heating = await self.hub.storage_get(f"{self._id}_config_heating")
        self._config_cool_setpoint_max = await self.hub.storage_get(
            f"{self._id}_config_cool_setpoint_max"
        )
        self._config_cool_setpoint_min = await self.hub.storage_get(
            f"{self._id}_config_cool_setpoint_min"
        )
        self._config_heat_setpoint_max = await self.hub.storage_get(
            f"{self._id}_config_heat_setpoint_max"
        )
        self._config_heat_setpoint_min = await self.hub.storage_get(
            f"{self._id}_config_heat_setpoint_min"
        )

        # Some static information about this device
        self._device_type = DEVICE_TYPES[self.tha_device["type"]]
        self._tha_full_device_name = self.tha_device["entity"]
        self.firmware_version = str(self.tha_device["version"])
        self.model = DEVICE_FEATURES[self.tha_device["type"]]["model"]

        self._device_info = {
            "identifiers": {(DOMAIN, self._id)},
            "name": (
                f"{self.hub.hub_id.capitalize()} {self._device_type.capitalize()} "
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
            if self.tha_device["attributes"].ZoneCooling:
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

            if self.tha_device["attributes"].ZoneHeating:
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
            if self.tha_device["attributes"].ZoneCooling:
                self.hub.queue_message(
                    TrpcPacket(
                        service="Request",
                        method="CoolSetpoint",
                        address=self._id,
                        setback=ThaSetback.CURRENT,
                    )
                )

            if self.tha_device["attributes"].ZoneHeating:
                self.hub.queue_message(
                    TrpcPacket(
                        service="Request",
                        method="HeatSetpoint",
                        address=self._id,
                        setback=ThaSetback.CURRENT,
                    )
                )

        if self.tha_device["attributes"].FanPercent:
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

        if self.tha_device["attributes"].SlabSetpoint:
            self.hub.queue_message(
                TrpcPacket(
                    service="Request",
                    method="SlabSetpoint",
                    address=self._id,
                    setback=ThaSetback.CURRENT,
                )
            )

        if DEVICE_FEATURES[self.tha_device["type"]][
            "humid"
        ] and self.hub.tha_pr_ver in [
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
        """Return the device id."""
        return self._id

    @property
    def tha_device_type(self) -> str:
        """Return the tha device type."""
        return self._device_type

    @property
    def tha_full_device_name(self) -> str:
        """Return the tha full device name."""
        return self._tha_full_device_name

    @property
    def current_temperature(self) -> str:
        """Return the current temperature in degH."""
        return self._tha_current_temperature

    @property
    def current_floor_temperature(self) -> str:
        """Return the current floor temperature in degH."""
        if self.hub.tha_pr_ver != 3:
            return None
        return self._tha_current_floor_temperature

    @property
    def relative_humidity(self) -> str:
        """Return the relative humidity."""
        if self.hub.tha_pr_ver not in [2, 3]:
            return None
        return self._tha_relative_humidity

    @property
    def cool_setpoint(self) -> str:
        """Return the cool setpoint in degE."""
        try:
            return self._tha_cool_setpoints[
                SETBACK_SETPOINT_MAP[self._tha_setback_state]
            ]
        except KeyError:
            return None

    @property
    def cool_setpoint_day(self) -> str:
        """Return the cool setpoint day in degE."""
        return self._tha_cool_setpoints[0x00]

    @property
    def cool_setpoint_night(self) -> str:
        """Return the cool setpoint night in degE."""
        return self._tha_cool_setpoints[0x01]

    @property
    def cool_setpoint_away(self) -> str:
        """Return the cool setpoint away in degE."""
        return self._tha_cool_setpoints[0x02]

    @property
    def heat_setpoint(self) -> str:
        """Return the heat setpoint in degE."""
        try:
            return self._tha_heat_setpoints[
                SETBACK_SETPOINT_MAP[self._tha_setback_state]
            ]
        except KeyError:
            return None

    @property
    def heat_setpoint_day(self) -> str:
        """Return the heat setpoint day in degE."""
        return self._tha_heat_setpoints[0x00]

    @property
    def heat_setpoint_night(self) -> str:
        """Return the heat setpoint night in degE."""
        return self._tha_heat_setpoints[0x01]

    @property
    def heat_setpoint_away(self) -> str:
        """Return the heat setpoint away in degE."""
        return self._tha_heat_setpoints[0x02]

    @property
    def config_vent_mode(self) -> bool:
        """Return the config vent mode."""
        return self._config_vent_mode

    @property
    def config_heat_setpoint_max(self) -> int:
        """Return the config heat setpoint max."""
        if self._config_heat_setpoint_max is None:
            return ThaDefault.HEAT_MAX
        return self._config_heat_setpoint_max

    @property
    def config_heat_setpoint_min(self) -> int:
        """Return the config heat setpoint min."""
        if self._config_heat_setpoint_min is None:
            return ThaDefault.HEAT_MIN
        return self._config_heat_setpoint_min

    @property
    def config_cool_setpoint_max(self) -> int:
        """Return the config cool setpoint max."""
        if self._config_cool_setpoint_max is None:
            return ThaDefault.COOL_MAX
        return self._config_cool_setpoint_max

    @property
    def config_cool_setpoint_min(self) -> int:
        """Return the config cool setpoint min."""
        if self._config_cool_setpoint_min is None:
            return ThaDefault.COOL_MIN
        return self._config_cool_setpoint_min

    @property
    def config_slab_setpoint_max(self) -> int:
        """Return the config slab setpoint max."""
        if self._config_slab_setpoint_max is None:
            return ThaDefault.SLAB_MAX
        return self._config_slab_setpoint_max

    @property
    def config_slab_setpoint_min(self) -> int:
        """Return the config slab setpoint min."""
        if self._config_slab_setpoint_min is None:
            return ThaDefault.SLAB_MIN
        return self._config_slab_setpoint_min

    @property
    def slab_setpoint(self) -> str:
        """Return the slab setpoint in degE."""
        try:
            return self._tha_slab_setpoints[
                SETBACK_SETPOINT_MAP[self._tha_setback_state]
            ]
        except KeyError:
            return None

    @property
    def active_demand(self) -> str:
        """Return the active demand."""
        return self._tha_active_demand

    @property
    def setback_enable(self) -> bool:
        """Return the setback enable."""
        return self.hub.tha_setback_enable

    @property
    def setback_state(self) -> str:
        """Return the setback state."""
        return self._tha_setback_state

    @property
    def setback_events(self) -> str:
        """Return the setback events."""
        return self.tha_device["events"]

    @property
    def mode_setting(self) -> str:
        """Return the mode setting."""
        return self._tha_mode_setting

    @property
    def fan_percent(self) -> str:
        """Return the fan percent."""
        try:
            return self._tha_fan_percent[SETBACK_FAN_MAP[self.setback_state]]
        except KeyError:
            return None

    @property
    def humidity_setpoint_min(self) -> str:
        """Return the humidity setpoint min."""
        if self.hub.tha_pr_ver not in [2, 3]:
            return None
        return self._tha_humidity_setpoint_min

    @property
    def humidity_setpoint_max(self) -> str:
        """Return the humidity setpoint max."""
        if self.hub.tha_pr_ver not in [2, 3]:
            return None
        return self._tha_humidity_setpoint_max

    async def set_config_vent_mode(self, value: bool) -> None:
        """Store the vent mode setting, persist it, and notify."""
        self._config_vent_mode = value
        await self.hub.storage_put(f"{self._id}_config_vent_mode", value)
        await self.publish_updates()

    async def set_current_temperature(self, temp: int) -> None:
        """Store the current temperature (degH) and notify."""
        self._tha_current_temperature = temp
        await self.publish_updates()

    async def set_current_floor_temperature(self, temp: int) -> None:
        """Store the current floor temperature (degH) and notify."""
        self._tha_current_floor_temperature = temp
        await self.publish_updates()

    async def set_relative_humidity(self, humidity: int) -> None:
        """Store the relative humidity and notify."""
        self._tha_relative_humidity = humidity
        await self.publish_updates()

    async def set_heat_setpoint(self, setpoint: int, setback: int) -> None:
        """Store a heat setpoint (degE) for a setback state and notify."""
        self._tha_heat_setpoints[SETBACK_SETPOINT_MAP[setback]] = setpoint
        await self.publish_updates()

    async def set_heat_setpoint_txqueue(
        self, value: int, setback: int = ThaSetback.CURRENT
    ) -> None:
        """Queue a heat setpoint (degE) update to the device."""
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
        """Store a cool setpoint (degE) for a setback state and notify."""
        self._tha_cool_setpoints[SETBACK_SETPOINT_MAP[setback]] = setpoint
        await self.publish_updates()

    async def set_cool_setpoint_txqueue(
        self, value: int, setback: int = ThaSetback.CURRENT
    ) -> None:
        """Queue a cool setpoint (degE) update to the device."""
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
        """Store a slab setpoint (degE) for a setback state and notify."""
        self._tha_slab_setpoints[SETBACK_SETPOINT_MAP[setback]] = setpoint
        await self.publish_updates()

    async def set_slab_setpoint_txqueue(
        self, value: int, setback: int = ThaSetback.CURRENT
    ) -> None:
        """Queue a slab setpoint (degE) update to the device."""
        await self.hub.async_queue_message(
            TrpcPacket(
                service="Update",
                method="SlabSetpoint",
                address=self._id,
                setback=setback,
                setpoint=value,
            )
        )

    async def set_fan_percent(self, percent: int, setback: int) -> None:
        """Store a fan percentage for a setback state and notify."""
        self._tha_fan_percent[SETBACK_FAN_MAP[setback]] = percent
        await self.publish_updates()

    async def set_fan_percent_txqueue(
        self, percent: int, setback: int = ThaSetback.CURRENT
    ) -> None:
        """Queue a fan percentage update to the device."""
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
        """Store the active demand and notify."""
        self._tha_active_demand = demand
        await self.publish_updates()

    async def set_setback_state(self, setback: int) -> None:
        """Store the setback state and notify."""
        self._tha_setback_state = setback
        await self.publish_updates()

    async def set_mode_setting(self, mode: int) -> None:
        """Store the mode setting and notify."""
        self._tha_mode_setting = mode
        await self.publish_updates()

    async def set_mode_setting_txqueue(self, value: int) -> None:
        """Queue a mode setting update to the device."""
        await self.hub.async_queue_message(
            TrpcPacket(
                service="Update", method="ModeSetting", address=self._id, mode=value
            )
        )

    async def set_humidity_setpoint_min(self, percent: int) -> None:
        """Store the minimum humidity setpoint and notify."""
        self._tha_humidity_setpoint_min = percent
        await self.publish_updates()

    async def set_humidity_setpoint_min_txqueue(self, value: int) -> None:
        """Queue a minimum humidity setpoint update to the device."""
        await self.hub.async_queue_message(
            TrpcPacket(
                service="Update",
                method="HumiditySetMin",
                address=self._id,
                percent=int(value),
            )
        )

    async def set_humidity_setpoint_max(self, percent: int) -> None:
        """Store the maximum humidity setpoint and notify."""
        self._tha_humidity_setpoint_max = percent
        await self.publish_updates()

    async def set_humidity_setpoint_max_txqueue(self, value: int) -> None:
        """Queue a maximum humidity setpoint update to the device."""
        await self.hub.async_queue_message(
            TrpcPacket(
                service="Update",
                method="HumiditySetMax",
                address=self._id,
                percent=int(value),
            )
        )

    async def set_setback_events(self, events: int) -> None:
        """Store the setback events and notify."""
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
    def device_info(self) -> dict[str, Any] | None:
        """Return the device info."""
        return self._device_info


class TekmarSetpoint:
    """Tekmar setpoint device."""

    def __init__(self, address: int, tha_device: [], hub: TekmarHub) -> None:
        """Initialize the Tekmar setpoint."""
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
        self.firmware_version = str(self.tha_device["version"])
        self.model = DEVICE_FEATURES[self.tha_device["type"]]["model"]

        self._device_info = {
            "identifiers": {(DOMAIN, self._id)},
            "name": (
                f"{self.hub.hub_id.capitalize()} {self._device_type.capitalize()} "
                f"{self.model} {self._id}"
            ),
            "manufacturer": ATTR_MANUFACTURER,
            "model": self.model,
            "sw_version": self.firmware_version,
        }

    def init_device(self) -> None:
        """Request the initial device state."""
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
        """Return the device id."""
        return self._id

    @property
    def tha_device_type(self) -> str:
        """Return the tha device type."""
        return self._device_type

    @property
    def tha_full_device_name(self) -> str:
        """Return the tha full device name."""
        return self._tha_full_device_name

    @property
    def current_temperature(self) -> str:
        """Return the current temperature in degH."""
        return self._tha_current_temperature

    @property
    def current_floor_temperature(self) -> str:
        """Return the current floor temperature in degH."""
        if self.hub.tha_pr_ver != 3:
            return None
        return self._tha_current_floor_temperature

    @property
    def setpoint_target(self) -> str:
        """Return the setpoint target in degH."""
        return self._tha_setpoint_target_temperature

    @property
    def setback_enable(self) -> bool:
        """Return the setback enable."""
        return self.hub.tha_setback_enable

    @property
    def setback_state(self) -> str:
        """Return the setback state."""
        return self._tha_setback_state

    @property
    def active_demand(self) -> str:
        """Return the active demand."""
        return self._tha_active_demand

    async def set_current_temperature(self, temp: int) -> None:
        """Store the current temperature (degH) and notify."""
        self._tha_current_temperature = temp
        await self.publish_updates()

    async def set_current_floor_temperature(self, temp: int) -> None:
        """Store the current floor temperature (degH) and notify."""
        self._tha_current_floor_temperature = temp
        await self.publish_updates()

    async def set_setpoint_target(self, temp: int, setback: int) -> None:
        """Store the setpoint target temperature (degH) and notify."""
        self._tha_setpoint_target_temperature = temp
        await self.publish_updates()

    async def set_active_demand(self, demand: int) -> None:
        """Store the active demand and notify."""
        self._tha_active_demand = demand
        await self.publish_updates()

    async def set_setback_state(self, setback: int) -> None:
        """Store the setback state and notify."""
        self._tha_setback_state = setback
        await self.publish_updates()

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register callback, called when TekmarSetpoint changes state."""
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
    def device_info(self) -> dict[str, Any] | None:
        """Return the device info."""
        return self._device_info


class TekmarSnowmelt:
    """Temkar snowmelt device."""

    def __init__(self, address: int, tha_device: [], hub: TekmarHub) -> None:
        """Initialize the Tekmar snowmelt."""
        self._id = address
        self.hub = hub
        self.tha_device = tha_device
        self._callbacks = set()

        self._tha_active_demand = None

        # Some static information about this device
        self._device_type = DEVICE_TYPES[self.tha_device["type"]]
        self._tha_full_device_name = self.tha_device["entity"]
        self.firmware_version = str(self.tha_device["version"])
        self.model = DEVICE_FEATURES[self.tha_device["type"]]["model"]

        self._device_info = {
            "identifiers": {(DOMAIN, self._id)},
            "name": (
                f"{self.hub.hub_id.capitalize()} {self._device_type.capitalize()} "
                f"{self.model} {self._id}"
            ),
            "manufacturer": ATTR_MANUFACTURER,
            "model": self.model,
            "sw_version": self.firmware_version,
        }

    def init_device(self) -> None:
        """Initialize the device; nothing to request yet."""

    @property
    def device_id(self) -> str:
        """Return the device id."""
        return self._id

    @property
    def tha_device_type(self) -> str:
        """Return the tha device type."""
        return self._device_type

    @property
    def tha_full_device_name(self) -> str:
        """Return the tha full device name."""
        return self._tha_full_device_name

    @property
    def active_demand(self) -> str:
        """Return the active demand."""
        return self._tha_active_demand

    async def set_active_demand(self, demand: int) -> None:
        """Store the active demand and notify."""
        self._tha_active_demand = demand
        await self.publish_updates()

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register callback, called when TekmarSnowmelt changes state."""
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
    def device_info(self) -> dict[str, Any] | None:
        """Return the device info."""
        return self._device_info


class TekmarGateway:
    """Tekmar 482 Gateway device."""

    def __init__(self, gatewayid: str, host: str, hub: TekmarHub) -> None:
        """Initialize the Tekmar gateway."""
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
        self.firmware_version = f"{self.hub.tha_fw_ver} protocol {self.hub.tha_pr_ver}"
        self.model = "482"

        self._device_info = {
            "identifiers": {(DOMAIN, self.hub.hub_id)},
            "name": f"{self.hub.hub_id.capitalize()} Gateway",
            "manufacturer": ATTR_MANUFACTURER,
            "model": self.model,
            "sw_version": self.firmware_version,
        }

    def init_device(self) -> None:
        """Request outdoor temperature and setpoint group states."""
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
        """Return the gateway id."""
        return self._id

    @property
    def name(self) -> str:
        """Return the name."""
        return self._host

    async def set_reporting_state(self, state: int) -> None:
        """Store the hub reporting state and notify."""
        self.hub.tha_reporting_state = state
        await self.publish_updates()

    async def set_outdoor_temperature(self, temp: int) -> None:
        """Store the outdoor temperature (degH) and notify."""
        self._tha_outdoor_temperature = temp
        await self.publish_updates()

    async def set_network_error(self, neterr: int) -> None:
        """Store the network error code and notify."""
        self._tha_network_error = neterr
        await self.publish_updates()

    async def set_setpoint_group(self, group: int, value: int) -> None:
        """Store a setpoint group enable state and notify."""
        if group in list(range(1, 13)):
            self._tha_setpoint_groups[group] = value
            await self.publish_updates()

    async def set_setpoint_group_txqueue(self, group: int, value: bool) -> None:
        """Queue a setpoint group enable update to the gateway."""
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
        """Return the reporting state."""
        return self.hub.tha_reporting_state

    @property
    def setback_enable(self) -> bool:
        """Return the setback enable."""
        return self.hub.tha_setback_enable

    @property
    def outdoor_temprature(self) -> int:
        """Return the outdoor temprature in degH."""
        return self._tha_outdoor_temperature

    @property
    def network_error(self) -> int:
        """Return the network error."""
        return self._tha_network_error

    @property
    def setpoint_groups(self) -> dict[int, Any]:
        """Return the setpoint groups."""
        return self._tha_setpoint_groups

    @property
    def device_info(self) -> dict[str, Any] | None:
        """Return the device info."""
        return self._device_info


class StoredData:
    """Abstraction over Home Assistant Store."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the stored data."""
        self._hass = hass
        self._entry_id = entry_id
        self._data = None

        self.store: Store[dict[str, Any]] = TekmarStore(
            self._hass,
            STORAGE_VERSION_MAJOR,
            STORAGE_KEY,
        )

    async def get_setting(self, key: str) -> Any:
        """Return a setting for this config entry."""
        if self._data is None:
            self._data = await self.store.async_load()

        return self._data.get(self._entry_id).get(key)

    async def put_setting(self, key: str, value: Any) -> None:
        """Save a setting for this config entry."""
        self._data = await self.store.async_load()
        if self._data is None:
            self._data = {}

        self._data.update([(self._entry_id, {key: value})])
        await self.store.async_save(self._data)


class TekmarStore(Store):
    """Tekmar data storage."""

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Migrate to the new version."""

        raise NotImplementedError
