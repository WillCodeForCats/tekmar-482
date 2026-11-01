"""Generic packets exchanged with the gateway packet server.

In string form, a packet is a sequence of two-digit uppercase hex
values, one per byte: the packet type first, followed by the data
bytes, and terminated by a newline.
"""

from .fields import FieldList, Int8

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
    """A packet with a type and a sequence of data bytes."""

    # --------------------------------------------------------------------------
    format = FieldList("PacketFormat", Int8(None))

    # --------------------------------------------------------------------------
    def __init__(self, pkt_type=TYPE_GENERAL, data=None):
        """Create a packet with a type and optional data bytes."""
        if data is None:
            self.data = []
        else:
            self.data = list(data)

        self.type = pkt_type

    # --------------------------------------------------------------------------
    def __str__(self):
        """Create a string representation of the packet.

        See the module docs for the format.
        """
        lst = [f"{b:02X}" for b in self.joined()]
        lst.append("\n")
        return "".join(lst)

    # --------------------------------------------------------------------------
    def joined(self):
        """Join the type and data into a single sequence and return it."""
        lst = [self.type]
        lst.extend(self.data)
        return lst

    # --------------------------------------------------------------------------
    @staticmethod
    def from_str(s):
        """Convert a packet in string form into a packet object.

        See the module docs for the string format.  Return the result.
        """
        ln = len(s)
        if ln & 1:
            ln -= 1
        if ln == 0:
            return Packet()
        try:
            pkt_type, data = Packet.format.unpack(
                list(
                    [int(x, 16) for x in [s[idx : idx + 2] for idx in range(0, ln, 2)]]
                )
            )
            return Packet(pkt_type[0], data)
        except ValueError:
            return Packet()
