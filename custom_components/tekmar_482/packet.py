from .fields import Field, FieldList, Int8

# ******************************************************************************
# Supported packet types.

(
    TYPE_GENERAL,
    TYPE_TN4,
    TYPE_HW_OVR_TEXT,
    TYPE_HW_OVR_BINARY,
    TYPE_DISPLAY,
    TYPE_NVM,
    TYPE_TRPC,
) = list(range(7))


# ******************************************************************************
class Packet:

    # --------------------------------------------------------------------------
    format = FieldList("PacketFormat", Int8(None))

    # --------------------------------------------------------------------------
    def __init__(self, type=TYPE_GENERAL, data=[]):
        self.type = type
        self.data = data

    # --------------------------------------------------------------------------
    def __str__(self):
        """Create a string-representation of the packet (see the docs for the
        module.
        """
        lst = ["%02X" % b for b in self.joined()]
        lst.append("\n")
        return "".join(lst)

    # --------------------------------------------------------------------------
    def joined(self):
        """Join the type and data into a single sequence and return the
        result.
        """
        lst = [self.type]
        lst.extend(self.data)
        return lst

    # --------------------------------------------------------------------------
    def from_str(s):
        """Convert a packet in string form (see the module docs) into a
        a packet object and return the result.
        """
        ln = len(s)
        if ln & 1:
            ln -= 1
        if ln == 0:
            return Packet()
        try:
            type, data = Packet.format.unpack(
                list(
                    [int(x, 16) for x in [s[idx : idx + 2] for idx in range(0, ln, 2)]]
                )
            )
            return Packet(type[0], data)
        except ValueError:
            return Packet()

    from_str = staticmethod(from_str)
