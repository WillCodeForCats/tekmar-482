"""Constants used by Tekmar Gateway 482 components."""
from __future__ import annotations

import ctypes
import re
import sys
from enum import IntEnum

if sys.version_info.minor >= 11:
    # Needs Python 3.11
    from enum import StrEnum
else:
    try:
        from homeassistant.backports.enum import StrEnum

    except ImportError:
        from enum import Enum

        class StrEnum(str, Enum):
            pass


c_uint = ctypes.c_uint

DOMAIN = "tekmar_482"
ATTR_MANUFACTURER = "Tekmar"
DEFAULT_NAME = "tekmarNet"
DEFAULT_HOST = ""
DEFAULT_PORT = 3000
DEFAULT_SETBACK_ENABLE = False
CONF_SETBACK_ENABLE = "setback_enable"

# from voluptuous/validators.py
DOMAIN_REGEX = re.compile(
    # start anchor, because fullmatch is not available in python 2.7
    "(?:"
    # domain
    r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+"
    r"(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?$)"
    # host name only
    r"|(?:^[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)"
    # end anchor, because fullmatch is not available in python 2.7
    r")\Z",
    re.IGNORECASE,
)


class ThaSetback(IntEnum):
    WAKE_4 = 0x00
    UNOCC_4 = 0x01
    OCC_4 = 0x02
    SLEEP_4 = 0x03
    OCC_2 = 0x04
    UNOCC_2 = 0x05
    AWAY = 0x06
    CURRENT = 0x07


class ThaValue(IntEnum):
    ON = 0x01
    OFF = 0x00
    NA_8 = 0xFF
    NA_16 = 0xFFFF
    NA_32 = 0xFFFFFFFF


class ThaType(StrEnum):
    THERMOSTAT = "thermostat"
    SETPOINT = "setpoint"
    SNOWMELT = "snowmelt"


class ThaDefault(IntEnum):
    HEAT_MIN = 7
    HEAT_MAX = 29
    COOL_MIN = 10
    COOL_MAX = 30
    SLAB_MIN = 5
    SLAB_MAX = 30


ACTIVE_DEMAND = {0x00: "None", 0x01: "Heat", 0x03: "Cool"}

ACTIVE_MODE = {
    0x00: "Off",
    0x01: "Heat",
    0x02: "Auto",
    0x03: "Cool",
    0x04: "Vent",
    0x05: "Not used",
    0x06: "Emergency",
}

SETBACK_STATE = {
    ThaSetback.WAKE_4: "WAKE_4",
    ThaSetback.UNOCC_4: "UNOCC_4",
    ThaSetback.OCC_4: "OCC_4",
    ThaSetback.SLEEP_4: "SLEEP_4",
    ThaSetback.OCC_2: "OCC_2",
    ThaSetback.UNOCC_2: "UNOCC_2",
    ThaSetback.AWAY: "AWAY",
}

SETBACK_DESCRIPTION = {
    ThaSetback.WAKE_4: "Awake",
    ThaSetback.UNOCC_4: "Sleep",
    ThaSetback.OCC_4: "Awake",
    ThaSetback.SLEEP_4: "Sleep",
    ThaSetback.OCC_2: "Awake",
    ThaSetback.UNOCC_2: "Sleep",
    ThaSetback.AWAY: "Away",
}

SETBACK_SETPOINT_MAP = {
    ThaSetback.WAKE_4: 0x00,
    ThaSetback.UNOCC_4: 0x01,
    ThaSetback.OCC_4: 0x00,
    ThaSetback.SLEEP_4: 0x01,
    ThaSetback.OCC_2: 0x00,
    ThaSetback.UNOCC_2: 0x01,
    ThaSetback.AWAY: 0x02,
}

SETBACK_FAN_MAP = {
    ThaSetback.WAKE_4: 0x00,
    ThaSetback.UNOCC_4: 0x01,
    ThaSetback.OCC_4: 0x00,
    ThaSetback.SLEEP_4: 0x01,
    ThaSetback.OCC_2: 0x00,
    ThaSetback.UNOCC_2: 0x01,
    ThaSetback.AWAY: 0x01,
}

DEVICE_TYPES = {
    101101: ThaType.SETPOINT,
    101102: ThaType.SETPOINT,
    102301: ThaType.THERMOSTAT,
    102302: ThaType.THERMOSTAT,
    102303: ThaType.THERMOSTAT,
    102304: ThaType.THERMOSTAT,
    100102: ThaType.THERMOSTAT,
    100103: ThaType.THERMOSTAT,
    100101: ThaType.THERMOSTAT,
    99301: ThaType.THERMOSTAT,
    99302: ThaType.THERMOSTAT,
    99401: ThaType.THERMOSTAT,
    99203: ThaType.THERMOSTAT,
    99202: ThaType.THERMOSTAT,
    99201: ThaType.THERMOSTAT,
    107201: ThaType.THERMOSTAT,
    105103: ThaType.THERMOSTAT,
    105102: ThaType.THERMOSTAT,
    105101: ThaType.THERMOSTAT,
    104401: ThaType.THERMOSTAT,
    105801: ThaType.SNOWMELT,
    108401: ThaType.SNOWMELT,
    108402: ThaType.SNOWMELT,
}

DEVICE_FEATURES = {
    101101: {
        "model": "161",
        "type": DEVICE_TYPES[101101],
        "heat": 1,
        "cool": 0,
        "fan": 0,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    101102: {
        "model": "162",
        "type": DEVICE_TYPES[101102],
        "heat": 1,
        "cool": 1,
        "fan": 0,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    102301: {
        "model": "527",
        "type": DEVICE_TYPES[102301],
        "heat": 1,
        "cool": 0,
        "fan": 0,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    102302: {
        "model": "528",
        "type": DEVICE_TYPES[102302],
        "heat": 1,
        "cool": 0,
        "fan": 0,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    102303: {
        "model": "529",
        "type": DEVICE_TYPES[102303],
        "heat": 2,
        "cool": 0,
        "fan": 0,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    102304: {
        "model": "530",
        "type": DEVICE_TYPES[102304],
        "heat": 1,
        "cool": 1,
        "fan": 1,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    100102: {
        "model": "537",
        "type": DEVICE_TYPES[100102],
        "heat": 1,
        "cool": 0,
        "fan": 0,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    100103: {
        "model": "538",
        "type": DEVICE_TYPES[100103],
        "heat": 1,
        "cool": 0,
        "fan": 0,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    100101: {
        "model": "540",
        "type": DEVICE_TYPES[100101],
        "heat": 1,
        "cool": 1,
        "fan": 1,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    99301: {
        "model": "541",
        "type": DEVICE_TYPES[99301],
        "heat": 1,
        "cool": 0,
        "fan": 0,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    99302: {
        "model": "542",
        "type": DEVICE_TYPES[99302],
        "heat": 1,
        "cool": 0,
        "fan": 0,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    99401: {
        "model": "543",
        "type": DEVICE_TYPES[99401],
        "heat": 2,
        "cool": 0,
        "fan": 0,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    99203: {
        "model": "544",
        "type": DEVICE_TYPES[99203],
        "heat": 1,
        "cool": 1,
        "fan": 1,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    99202: {
        "model": "545",
        "type": DEVICE_TYPES[99202],
        "heat": 2,
        "cool": 1,
        "fan": 1,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    99201: {
        "model": "546",
        "type": DEVICE_TYPES[99201],
        "heat": 2,
        "cool": 2,
        "fan": 2,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    107201: {
        "model": "532",
        "type": DEVICE_TYPES[107201],
        "heat": 1,
        "cool": 0,
        "fan": 0,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    105103: {
        "model": "552",
        "type": DEVICE_TYPES[105103],
        "heat": 1,
        "cool": 0,
        "fan": 0,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    105102: {
        "model": "553",
        "type": DEVICE_TYPES[105102],
        "heat": 2,
        "cool": 1,
        "fan": 1,
        "humid": 1,
        "snow": 0,
        "emer": 0,
    },
    105101: {
        "model": "554",
        "type": DEVICE_TYPES[105101],
        "heat": 1,
        "cool": 1,
        "fan": 1,
        "humid": 0,
        "snow": 0,
        "emer": 0,
    },
    104401: {
        "model": "557",
        "type": DEVICE_TYPES[104401],
        "heat": 2,
        "cool": 2,
        "fan": 1,
        "humid": 1,
        "snow": 0,
        "emer": 1,
    },
    105801: {
        "model": "654",
        "type": DEVICE_TYPES[105801],
        "heat": 0,
        "cool": 0,
        "fan": 0,
        "humid": 0,
        "snow": 1,
        "emer": 0,
    },
    108401: {
        "model": "670",
        "type": DEVICE_TYPES[108401],
        "heat": 0,
        "cool": 0,
        "fan": 0,
        "humid": 0,
        "snow": 1,
        "emer": 0,
    },
    108402: {
        "model": "671",
        "type": DEVICE_TYPES[108402],
        "heat": 0,
        "cool": 0,
        "fan": 0,
        "humid": 0,
        "snow": 1,
        "emer": 0,
    },
}


class _DEVICE_ATTRIBUTES(ctypes.LittleEndianStructure):
    _fields_ = [
        ("Zone_Heating", c_uint, 1),
        ("Zone_Cooling", c_uint, 1),
        ("Slab_Setpoint", c_uint, 1),
        ("Fan_Percent", c_uint, 1),
    ]


class DEVICE_ATTRIBUTES(ctypes.Union):
    _anonymous_ = ("bit",)
    _fields_ = [("bit", _DEVICE_ATTRIBUTES), ("attrs", c_uint)]


TN_ERRORS = {
    0x00: "No Errors",
    0x01: "EEPROM Error",
    0x02: "Internal Error",
    0x03: "Address Error or Master Device Error",
    0x04: "Device Lost Error",
    0x05: "Mixing Configuration Error",
    0x06: "tN4 Bus Communications Error",
    0x07: "Schedule Master Error",
    0x08: "Cool Group Error",
    0x09: "Device Configuration Error",
    0x0A: "Alert Input Error",
    0x0B: "Primary Pump Proof Error",
    0x0C: "No Pumps Are Running, Flow Proof Demand Input is Active",
    0x0D: "Combustion Air Proof is Missing",
    0x0E: "Combustion Air Damper is Closed, Proof Demand Input is Active",
    0x0F: "Dewpoint Configuration Error",
    0x80: "Outdoor Sensor Error",
    0x81: "System Supply Sensor Error",
    0x82: "System Return Sensor Error",
    0x83: "Heating Device Supply Sensor Error",
    0x84: "Heating Device Return Sensor Error",
    0x85: "Heating Device Outlet Sensor Error",
    0x86: "Heating Device Inlet Sensor Error",
    0x87: "Cooling Device Supply Sensor Error",
    0x88: "Cooling Device Return Sensor Error",
    0x89: "Cooling Device Inlet Sensor Error",
    0x8A: "Cooling Device Outlet Sensor Error",
    0x8B: "Mixing Supply Sensor Error",
    0x8C: "Mixing Return Sensor Error",
    0x8D: "Dhw Tank Sensor Error",
    0x8E: "Room Sensor Error",
    0x8F: "Slab Sensor Error",
    0x90: "Duct Sensor Error",
    0x91: "Remote Sensor Error",
    0x92: "Coil Return Sensor Error",
    0x93: "Tank Sensor Error",
    0x94: "Humidity Sensor Error",
    0x95: "Heat Pump Error",
    0x96: "Brown/Slab Error",
    0x97: "Yellow Error",
    0x98: "Blue Error",
    0x99: "Tandem Error",
    0xC0: "Hot Room Warning",
    0xC1: "Cold Room Warning",
    0xC2: "Freeze Protect Warning",
    0xC3: "Filter Change Warning",
    0xC4: "Snow/Ice Sensor Heater Not Heating",
    0xC5: "Snow/Ice Sensor Overheating",
    0xC6: "Snow/Ice Sensor Temperature Drift",
    0xC7: "Maximum Melt Time Exceeded",
}
