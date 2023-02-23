from .fields import FieldList, Int8, Int16, Int32, Record
from .packet import TYPE_TRPC, Packet

# *****************************************************************************
# Define the formats of tRPC messages according to their method ID.
#
empty_field_list = FieldList("empty_field_list")

# Note that the bitfields read starting from the LSB and working downwards.
# Also note that this table assumes little-endian byte-ordering.

service_formats = {
    # *********************************************************************
    0x00: FieldList(
        "Update",
    ),
    # *********************************************************************
    0x01: FieldList(
        "Request",
    ),
    # *********************************************************************
    0x02: FieldList(
        "Report",
    ),
    # *********************************************************************
    0x03: FieldList(
        "Response:Update",
    ),
    # *********************************************************************
    0x04: FieldList(
        "Response:Request",
    ),
}

# *****************************************************************************
# Lookup service IDs from service names.
#
name_from_serviceID = dict(
    list(
        zip(
            list(service_formats.keys()),
            (f.name for f in list(service_formats.values())),
        )
    )
)

# *****************************************************************************
# Lookup service names from service IDs.  This is the reverse of
# name_from_serviceID.
#
serviceID_from_name = dict(
    list(zip(list(name_from_serviceID.values()), list(name_from_serviceID.keys())))
)

method_formats = {
    # *********************************************************************
    0x00000000: FieldList(
        "NullMethod",
    ),
    # *********************************************************************
    0x00000107: FieldList("NetworkError", Int16("error")),
    # *********************************************************************
    0x0000010F: FieldList("ReportingState", Int8("state")),
    # *********************************************************************
    0x00000117: FieldList("OutdoorTemperature", Int16("temp")),
    # *********************************************************************
    0x0000011F: FieldList("DeviceAttributes", Int16("address"), Int16("attributes")),
    # *********************************************************************
    0x00000127: FieldList("ModeSetting", Int16("address"), Int8("mode")),
    # *********************************************************************
    0x0000012F: FieldList("ActiveDemand", Int16("address"), Int8("demand")),
    # *********************************************************************
    0x00000137: FieldList("CurrentTemperature", Int16("address"), Int16("temp")),
    # *********************************************************************
    0x00000138: FieldList("CurrentFloorTemperature", Int16("address"), Int16("temp")),
    # *********************************************************************
    0x0000013D: FieldList("SetpointGroupEnable", Int8("groupid"), Int8("enable")),
    # *********************************************************************
    0x0000013E: FieldList(
        "SetpointDevice", Int16("address"), Int8("setback"), Int16("temp")
    ),
    # *********************************************************************
    0x0000013F: FieldList(
        "HeatSetpoint", Int16("address"), Int8("setback"), Int8("setpoint")
    ),
    # *********************************************************************
    0x00000147: FieldList(
        "CoolSetpoint", Int16("address"), Int8("setback"), Int8("setpoint")
    ),
    # *********************************************************************
    0x0000014F: FieldList(
        "SlabSetpoint", Int16("address"), Int8("setback"), Int8("setpoint")
    ),
    # *********************************************************************
    0x00000150: FieldList(
        "RelativeHumidity",
        Int16("address"),
        Int8("percent"),
    ),
    # *********************************************************************
    0x00000151: FieldList(
        "HumiditySetMax",
        Int16("address"),
        Int8("percent"),
    ),
    # *********************************************************************
    0x00000152: FieldList(
        "HumiditySetMin",
        Int16("address"),
        Int8("percent"),
    ),
    # *********************************************************************
    0x00000157: FieldList(
        "FanPercent", Int16("address"), Int8("setback"), Int8("percent")
    ),
    # *********************************************************************
    0x0000015F: FieldList("TakingAddress", Int16("old_address"), Int16("new_address")),
    # *********************************************************************
    0x00000167: FieldList(
        "DeviceInventory",
        Int16("address"),
    ),
    # *********************************************************************
    0x0000016F: FieldList("SetbackEnable", Int8("enable")),
    # *********************************************************************
    0x00000177: FieldList("SetbackState", Int16("address"), Int8("setback")),
    # *********************************************************************
    0x0000017F: FieldList("SetbackEvents", Int16("address"), Int8("events")),
    # *********************************************************************
    0x00000187: FieldList(
        "FirmwareRevision",
        Int16("revision"),
    ),
    # *********************************************************************
    0x0000018F: FieldList(
        "ProtocolVersion",
        Int16("version"),
    ),
    # *********************************************************************
    0x00000197: FieldList("DeviceType", Int16("address"), Int32("type")),
    # *********************************************************************
    0x0000019F: FieldList("DeviceVersion", Int16("address"), Int32("j_number")),
    # *********************************************************************
    0x000001A7: FieldList(
        "DateTime",
        Int16("year"),
        Int8("month"),
        Int8("day"),
        Int8("weekday"),
        Int8("hour"),
        Int8("minute"),
    ),
}

# *****************************************************************************
# Lookup method IDs from method names.
#
name_from_methodID = dict(
    list(
        zip(
            list(method_formats.keys()), (f.name for f in list(method_formats.values()))
        )
    )
)

# *****************************************************************************
# Lookup method names from method IDs.  This is the reverse of
# name_from_methodID.
#
methodID_from_name = dict(
    list(zip(list(name_from_methodID.values()), list(name_from_methodID.keys())))
)


# *****************************************************************************
class TrpcPacket:
    # *************************************************************************
    # Format of all tRPC packets (except the message body - that has to be
    # determined based on method ID.
    #
    format = FieldList("header", Int8("serviceID"), Int32("methodID"))

    # *************************************************************************
    def __init__(self, **kwargs):
        """Create a TrpcPacket from a set of keyword arguments.  Return
        the created packet.

        kwargs is expected to contain at least one of name or id in order
        to identify the format of the message.  If neith6er are provided or
        if evaluating them can not find a valid formatter object, an
        empty packet is created.

        If both a name and ID are provided, the name is ignored and the
        id is used to determine the message format.
        """

        # Create the header no matter what else is provided.
        self.header, _ = Record.create(TrpcPacket.format)

        # Determine the format of the message body.
        if "serviceID" in kwargs:
            # Get the format based on MethodID.  If the method lookup fails, use
            # an empty message.
            format = service_formats.get(kwargs["serviceID"], empty_field_list)

        else:
            try:
                # Three-stage lookup:
                # - Lookup 'service' in keyword arguments
                # - Lookup the serviceID for that name
                # - Lookup the format for that service.
                service_id = serviceID_from_name[kwargs["service"]]
                kwargs["serviceID"] = service_id
                format = service_formats[service_id]

            except KeyError:
                # If any of the above lookups fails, the format is unknown
                # and we'll use the empty field list.
                format = empty_field_list

        # Determine the format of the message body.
        if "methodID" in kwargs:
            # Get the format based on MethodID.  If the method lookup fails, use
            # an empty message.
            format = method_formats.get(kwargs["methodID"], empty_field_list)

        else:
            try:
                # Three-stage lookup:
                # - Lookup 'method' in keyword arguments
                # - Lookup the methodID for that name
                # - Lookup the format for that method.
                method_id = methodID_from_name[kwargs["method"]]
                kwargs["methodID"] = method_id
                format = method_formats[method_id]

            except KeyError:
                # If any of the above lookups fails, the format is unknown
                # and we'll use the empty field list.
                format = empty_field_list

        # Apply the formatting.
        self.body, self.extra = Record.create(format)

        # Fill any provided values that are relevant.  Note here that if any
        # field names in the header and data match, they will be assigned
        # to the data, AND NOT THE HEADER.
        for v in kwargs:
            if v in self.body:
                self.body[v] = kwargs[v]

            elif v in self.header:
                self.header[v] = kwargs[v]

    # *************************************************************************
    def from_rx_packet(pck_str):
        """Create a TrpcPacket from a packet string (as it would be received
        from a socket connection.
        """
        p = Packet.from_str(pck_str)
        if p.type != TYPE_TRPC:
            return None

        else:
            trpc = TrpcPacket()
            trpc.header, d = Record.create(TrpcPacket.format, p.data)

            try:
                trpc.body, trpc.extra = Record.create(
                    method_formats[trpc.header["methodID"]], d
                )

            except KeyError:
                trpc.body, trpc.extra = Record.create(empty_field_list, d)

            return trpc

    from_rx_packet = staticmethod(from_rx_packet)

    # *************************************************************************
    def to_tpck(self):
        """Take the packet in all its glory and boil it down to a basic
        Packet object.

        Return the converted packet.
        """
        p = Packet()
        p.type = TYPE_TRPC
        p.data = self.header.pack()[0]
        p.data.extend(self.body.pack()[0])
        p.data.extend(self.extra)
        return p

    # *************************************************************************
    def __str__(self):
        """String representation of the packet."""
        try:
            service_name = name_from_serviceID[self.header["serviceID"]]
        except KeyError:
            service_name = "0x%04X" % self.header["serviceID"]

        service_name = service_name.ljust(16)

        try:
            method_name = name_from_methodID[self.header["methodID"]]
        except KeyError:
            method_name = "0x%04X" % self.header["methodID"]

        method_name = method_name.ljust(18)

        hs = "%s %s" % (service_name, method_name)

        d, _ = self.body.pack()
        d.extend(self.extra)
        if len(d) == 0:
            return hs
        else:
            return "".join([hs, " <", "".join(["%02X" % x for x in d]), ">"])
