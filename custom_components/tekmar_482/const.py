import ctypes
c_uint = ctypes.c_uint

DOMAIN = "tekmar_482"
ATTR_MANUFACTURER = "Tekmar"
DEFAULT_NAME = "tekmarnet"
DEFAULT_HOST = ""
DEFAULT_PORT = 3000
DEFAULT_SETBACK_ENABLE = False
CONF_SETBACK_ENABLE = "setback_enable"

THA_WAKE_4  = 0x00
THA_UNOCC_4 = 0x01
THA_OCC_4   = 0x02
THA_SLEEP_4 = 0x03
THA_OCC_2   = 0x04
THA_UNOCC_2 = 0x05
THA_AWAY    = 0x06
THA_CURRENT = 0x07

THA_NA_8  = 0xFF
THA_NA_16 = 0xFFFF
THA_NA_32 = 0xFFFFFFFF

THA_TYPE_THERMOSTAT = 'thermostat'
THA_TYPE_SETPOINT = 'setpoint'
THA_TYPE_SNOWMELT = 'snowmelt'

ACTIVE_DEMAND = {
    0x00: "None",
    0x01: "Heat",
    0x03: "Cool"
}

ACTIVE_MODE = {
    0x00: "Off",
    0x01: "Heat",
    0x02: "Auto",
    0x03: "Cool",
    0x04: "Vent",
    0x05: "Not used",
    0x06: "Emergency"
}

SETBACK_STATE = {
    THA_WAKE_4: "WAKE_4",
    THA_UNOCC_4: "UNOCC_4",
    THA_OCC_4: "OCC_4",
    THA_SLEEP_4: "SLEEP_4",
    THA_OCC_2: "OCC_2",
    THA_UNOCC_2: "UNOCC_2",
    THA_AWAY: "AWAY"
}

SETBACK_DESCRIPTION = {
    THA_WAKE_4: "Awake",
    THA_UNOCC_4: "Sleep",
    THA_OCC_4: "Awake",
    THA_SLEEP_4: "Sleep",
    THA_OCC_2: "Awake",
    THA_UNOCC_2: "Sleep",
    THA_AWAY: "Away"
}

SETBACK_SETPOINT_MAP = {
    THA_WAKE_4: 0x00,
    THA_UNOCC_4: 0x01,
    THA_OCC_4: 0x00,
    THA_SLEEP_4: 0x01,
    THA_OCC_2: 0x00,
    THA_UNOCC_2: 0x01,
    THA_AWAY: 0x02
}

SETBACK_FAN_MAP = {
    THA_WAKE_4: 0x00,
    THA_UNOCC_4: 0x01,
    THA_OCC_4: 0x00,
    THA_SLEEP_4: 0x01,
    THA_OCC_2: 0x00,
    THA_UNOCC_2: 0x01,
    THA_AWAY: 0x01
}

DEVICE_TYPES = {
    101101: THA_TYPE_SETPOINT,
    101102: THA_TYPE_SETPOINT,
    102301: THA_TYPE_THERMOSTAT,
    102302: THA_TYPE_THERMOSTAT,
    102303: THA_TYPE_THERMOSTAT,
    102304: THA_TYPE_THERMOSTAT,
    100102: THA_TYPE_THERMOSTAT,
    100103: THA_TYPE_THERMOSTAT,
    100101: THA_TYPE_THERMOSTAT,
    99301: THA_TYPE_THERMOSTAT,
    99302: THA_TYPE_THERMOSTAT,
    99401: THA_TYPE_THERMOSTAT,
    99203: THA_TYPE_THERMOSTAT,
    99202: THA_TYPE_THERMOSTAT,
    99201: THA_TYPE_THERMOSTAT,
    107201: THA_TYPE_THERMOSTAT,
    105103: THA_TYPE_THERMOSTAT,
    105102: THA_TYPE_THERMOSTAT,
    105101: THA_TYPE_THERMOSTAT,
    104401: THA_TYPE_THERMOSTAT,
    105801: THA_TYPE_SNOWMELT,
    108401: THA_TYPE_SNOWMELT,
    108402: THA_TYPE_SNOWMELT,
}

DEVICE_FEATURES = {
    101101: {
        "model": "161", "type": DEVICE_TYPES[101101],
        "heat": 1, "cool": 0, "fan": 0, "humid": 0, "snow": 0, "emer": 0
    },
    101102: {
        "model": "162", "type": DEVICE_TYPES[101102],
        "heat": 1, "cool": 1, "fan": 0, "humid": 0, "snow": 0, "emer": 0
    },
    102301: {
        "model": "527", "type": DEVICE_TYPES[102301],
        "heat": 1, "cool": 0, "fan": 0, "humid": 0, "snow": 0, "emer": 0
        },
    102302: {
        "model": "528", "type": DEVICE_TYPES[102302],
        "heat": 1, "cool": 0, "fan": 0, "humid": 0, "snow": 0, "emer": 0
        },
    102303: {
        "model": "529", "type": DEVICE_TYPES[102303],
        "heat": 2, "cool": 0, "fan": 0, "humid": 0, "snow": 0, "emer": 0
        },
    102304: {
        "model": "530", "type": DEVICE_TYPES[102304],
        "heat": 1, "cool": 1, "fan": 1, "humid": 0, "snow": 0, "emer": 0
        },
    100102: {
        "model": "537", "type": DEVICE_TYPES[100102],
        "heat": 1, "cool": 0, "fan": 0, "humid": 0, "snow": 0, "emer": 0
        },
    100103: {
        "model": "538", "type": DEVICE_TYPES[100103],
        "heat": 1, "cool": 0, "fan": 0, "humid": 0, "snow": 0, "emer": 0
        },
    100101: {
        "model": "540", "type": DEVICE_TYPES[100101],
        "heat": 1, "cool": 1, "fan": 1, "humid": 0, "snow": 0, "emer": 0
        },
    99301: {
        "model": "541", "type": DEVICE_TYPES[99301],
        "heat": 1, "cool": 0, "fan": 0, "humid": 0, "snow": 0, "emer": 0
        },
    99302: {
        "model": "542", "type": DEVICE_TYPES[99302],
        "heat": 1, "cool": 0, "fan": 0, "humid": 0, "snow": 0, "emer": 0
        },
    99401: {
        "model": "543", "type": DEVICE_TYPES[99401],
        "heat": 2, "cool": 0, "fan": 0, "humid": 0, "snow": 0, "emer": 0
        },
    99203: { 
        "model": "544", "type": DEVICE_TYPES[99203],
        "heat": 1, "cool": 1, "fan": 1, "humid": 0, "snow": 0, "emer": 0
        },
    99202: {
        "model": "545", "type": DEVICE_TYPES[99202],
        "heat": 2, "cool": 1, "fan": 1, "humid": 0, "snow": 0, "emer": 0
        },
    99201: {
        "model": "546", "type": DEVICE_TYPES[99201],
        "heat": 2, "cool": 2, "fan": 2, "humid": 0, "snow": 0, "emer": 0
        },
    107201: {
        "model": "532", "type": DEVICE_TYPES[107201],
        "heat": 1, "cool": 0, "fan": 0, "humid": 0, "snow": 0, "emer": 0
        },
    105103: {
        "model": "552", "type": DEVICE_TYPES[105103],
        "heat": 1, "cool": 0, "fan": 0, "humid": 0, "snow": 0, "emer": 0
        },
    105102: {
        "model": "553", "type": DEVICE_TYPES[105102],
        "heat": 2, "cool": 1, "fan": 1, "humid": 1, "snow": 0, "emer": 0
        },
    105101: {
        "model": "554", "type": DEVICE_TYPES[105101],
        "heat": 1, "cool": 1, "fan": 1, "humid": 0, "snow": 0, "emer": 0
        },
    104401: {
        "model": "557", "type": DEVICE_TYPES[104401],
        "heat": 2, "cool": 2, "fan": 1, "humid": 1, "snow": 0, "emer": 1
        },
    105801: {
        "model": "654", "type": DEVICE_TYPES[105801],
        "heat": 0, "cool": 0, "fan": 0, "humid": 0, "snow": 1, "emer": 0
        },
    108401: {
        "model": "670", "type": DEVICE_TYPES[108401],
        "heat": 0, "cool": 0, "fan": 0, "humid": 0, "snow": 1, "emer": 0
        },
    108402: {
        "model": "671", "type": DEVICE_TYPES[108402],
        "heat": 0, "cool": 0, "fan": 0, "humid": 0, "snow": 1, "emer": 0
        },
}

class _DEVICE_ATTRIBUTES( ctypes.LittleEndianStructure ):
    _fields_ = [
                ("Zone_Heating",   c_uint, 1 ),  
                ("Zone_Cooling",   c_uint, 1 ),  
                ("Slab_Setpoint",  c_uint, 1 ), 
                ("Fan_Percent",    c_uint, 1 ),
               ]

class DEVICE_ATTRIBUTES( ctypes.Union ):
    _anonymous_ = ("bit",)
    _fields_ = [
                ("bit",    _DEVICE_ATTRIBUTES ),
                ("attrs", c_uint    )
               ]

NETWORK_ERRORS = {
    0x00: "No Errors",
    0x01: "EEPROM Error",
    0x02: "Internal Error",
    0x03: "Address error or Master Device error",
    0x04: "Device lost error",
    0x05: "Mixing configuration error",
    0x06: "tN4 Bus communications error",
    0x07: "Schedule master error",
    0x08: "Cool group error",
    0x09: "Device configuration error",
    0x0A: "Alert input error",
    0x0B: "Primary pump proof error",
    0x0C: "No pumps are running, but the flow-proof demand input is active",
    0x0D: "Combustion-air proof is missing",
    0x0E: "No combustion-air damper is open, but the proof demand input is active",
    0x0F: "Dewpoint configuration error",
    0x80: "Outdoor sensor error",
    0x81: "System supply sensor error",
    0x82: "System return sensor error",
    0x83: "Heating device supply sensor error",
    0x84: "Heating device return sensor error",
    0x85: "Heating device outlet sensor error",
    0x86: "Heating device inlet sensor error",
    0x87: "Cooling device supply sensor error",
    0x88: "Cooling device return sensor error",
    0x89: "Cooling device inlet sensor error",
    0x8A: "Cooling device outlet sensor error",
    0x8B: "Mixing supply sensor error",
    0x8C: "Mixing return sensor error",
    0x8D: "DHW tank sensor error",
    0x8E: "Room sensor error",
    0x8F: "Slab sensor error",
    0x90: "Duct sensor error",
    0x91: "Remote sensor error",
    0x92: "Coil return sensor error",
    0x93: "Tank sensor error",
    0x94: "Humidity sensor error",
    0x95: "Heat Pump error",
    0x96: "Brown/Slab error",
    0x97: "Yellow error",
    0x98: "Blue error",
    0x99: "Tandem error",
    0xC0: "Hot room warning",
    0xC1: "Cold room warning",
    0xC2: "Freeze protect warning",
    0xC3: "Filter change warning",
    0xC4: "Snow/Ice Sensor Heater not Heating",
    0xC5: "Snow/Ice Sensor Overheating",
    0xC6: "Snow/Ice Sensor Temperature Drift",
    0xC7: "Maximum Melt Time Exceeded"
}
