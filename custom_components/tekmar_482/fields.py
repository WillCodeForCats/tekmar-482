"""Field definitions for packing and unpacking binary records."""

LITTLE_ENDIAN = False
BIG_ENDIAN = True

DEFAULT_BYTE_ORDER = LITTLE_ENDIAN


# ******************************************************************************
class FieldError(Exception):
    """Raised when a field definition is invalid."""


# ******************************************************************************
class Field:
    """Base class for a named field of a fixed size."""

    # --------------------------------------------------------------------------
    def __init__(self, name, size):
        """A field has a name and a size.  The size is in bytes."""
        self.name = name
        self.size = size


# ******************************************************************************
class Bitmask(Field):
    """Naming utility.

    This is the same as a field, but is implemented for readability reasons
    when creating Bitfield objects.
    """


# ******************************************************************************
class Int8(Field):
    """An unsigned 8-bit integer field."""

    # --------------------------------------------------------------------------
    def __init__(self, name):
        """Create a named 1-byte field."""
        Field.__init__(self, name, 1)

    # --------------------------------------------------------------------------
    def unpack(self, data):
        """Unpack one byte; return the value and remaining bytes."""
        b = data.pop(0)
        return [b], data

    # --------------------------------------------------------------------------
    def pack(self, values):
        """Pack one value into a byte; return it and remaining values."""
        val = values.pop(0)
        return [val & 0xFF], values


# ******************************************************************************
class Int16(Field):
    """An unsigned 16-bit integer field."""

    # --------------------------------------------------------------------------
    def __init__(self, name, order=DEFAULT_BYTE_ORDER):
        """Create a named 2-byte field with the given byte order."""
        Field.__init__(self, name, 2)
        self.order = order

    # --------------------------------------------------------------------------
    def unpack(self, data):
        """Unpack two bytes; return the value and remaining bytes."""
        b0 = data.pop(0)
        b1 = data.pop(0)
        if self.order == LITTLE_ENDIAN:
            val = b0 | (b1 << 8)
        else:
            val = b1 | (b0 << 8)
        return [val], data

    # --------------------------------------------------------------------------
    def pack(self, values):
        """Pack one value into two bytes; return them and remaining values."""
        val = values.pop(0)
        if self.order == LITTLE_ENDIAN:
            b = [val & 0xFF, (val >> 8) & 0xFF]
        else:
            b = [(val >> 8) & 0xFF, val & 0xFF]
        return b, values


# ******************************************************************************
class Int24(Field):
    """An unsigned 24-bit integer field."""

    # --------------------------------------------------------------------------
    def __init__(self, name, order=DEFAULT_BYTE_ORDER):
        """Create a named 3-byte field with the given byte order."""
        Field.__init__(self, name, 3)
        self.order = order

    # --------------------------------------------------------------------------
    def unpack(self, data):
        """Unpack three bytes; return the value and remaining bytes."""
        b0 = data.pop(0)
        b1 = data.pop(0)
        b2 = data.pop(0)
        if self.order == LITTLE_ENDIAN:
            val = b0 | (b1 << 8) | (b2 << 16)
        else:
            val = b2 | (b1 << 8) | (b0 << 16)
        return [val], data

    # --------------------------------------------------------------------------
    def pack(self, values):
        """Pack one value into three bytes; return them and remaining values."""
        val = values.pop(0)
        if self.order == LITTLE_ENDIAN:
            b = [val & 0xFF, (val >> 8) & 0xFF, (val >> 16) & 0xFF]
        else:
            b = [(val >> 16) & 0xFF, (val >> 8) & 0xFF, val & 0xFF]
        return b, values


# ******************************************************************************
class Int32(Field):
    """An unsigned 32-bit integer field."""

    # --------------------------------------------------------------------------
    def __init__(self, name, order=DEFAULT_BYTE_ORDER):
        """Create a named 4-byte field with the given byte order."""
        Field.__init__(self, name, 4)
        self.order = order

    # --------------------------------------------------------------------------
    def unpack(self, data):
        """Unpack four bytes; return the value and remaining bytes."""
        b0 = data.pop(0)
        b1 = data.pop(0)
        b2 = data.pop(0)
        b3 = data.pop(0)
        if self.order == LITTLE_ENDIAN:
            val = b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)
        else:
            val = b3 | (b2 << 8) | (b1 << 16) | (b0 << 24)
        return [val], data

    # --------------------------------------------------------------------------
    def pack(self, values):
        """Pack one value into four bytes; return them and remaining values."""
        val = values.pop(0)
        if self.order == LITTLE_ENDIAN:
            b = [val & 0xFF, (val >> 8) & 0xFF, (val >> 16) & 0xFF, (val >> 24) & 0xFF]
        else:
            b = [(val >> 24) & 0xFF, (val >> 16) & 0xFF, (val >> 8) & 0xFF, val & 0xFF]
        return b, values


# ******************************************************************************
class FieldList(Field):
    """List of field objects.

    This is the heart of how a packed field is formatted.  It specifies
    the fields as field objects, thus providing them with a name and a
    method of packing and unpacking data.
    """

    # --------------------------------------------------------------------------
    def __init__(self, name, *lst):
        """Name the list of fields and provide the fields that define it.

        lst is a sequence of Field or FieldList objects that specify the
        format of the data.
        """
        self.name = name
        self.size = sum([f.size for f in lst])
        self.fields = lst

    # --------------------------------------------------------------------------
    def names(self):
        """Return a list of the field names.

        The list is ordered according to the data order.
        """
        name_list = []
        for f in self.fields:
            if isinstance(f, FieldList):
                name_list.extend(f.names())
            else:
                name_list.append(f.name)
        return name_list

    # --------------------------------------------------------------------------
    def unpack(self, data):
        """Unpack a series of Fields and FieldLists.

        Similar to the unpack method for the Field object except a series
        of Fields and FieldLists can be unpacked.
        """
        vals = []
        for f in self.fields:
            v, data = f.unpack(data)
            vals.extend(v)
        return vals, data

    # --------------------------------------------------------------------------
    def pack(self, values):
        """Pack a series of Fields and FieldLists.

        Similar to the pack method for the Field object except a series
        of Fields and FieldLists can be packed.
        """
        data = []
        for f in self.fields:
            b, values = f.pack(values)
            data.extend(b)
        return data, values


# ******************************************************************************
class Bitfield(FieldList):
    """Bit-granular FieldList.

    This object provides a means of specifying the format of packed
    bitfields that are up to 32-bits wide.

    The byte-order must be specified when creating a Bitfield object.
    """

    # --------------------------------------------------------------------------
    width_table = (
        0x00000000,
        0x00000001,
        0x00000003,
        0x00000007,
        0x0000000F,
        0x0000001F,
        0x0000003F,
        0x0000007F,
        0x000000FF,
        0x000001FF,
        0x000003FF,
        0x000007FF,
        0x00000FFF,
        0x00001FFF,
        0x00003FFF,
        0x00007FFF,
        0x0000FFFF,
        0x0001FFFF,
        0x0003FFFF,
        0x0007FFFF,
        0x000FFFFF,
        0x001FFFFF,
        0x003FFFFF,
        0x007FFFFF,
        0x00FFFFFF,
        0x01FFFFFF,
        0x03FFFFFF,
        0x07FFFFFF,
        0x0FFFFFFF,
        0x1FFFFFFF,
        0x3FFFFFFF,
        0x7FFFFFFF,
        0xFFFFFFFF,
    )

    # --------------------------------------------------------------------------
    def __init__(self, name, order, *lst):
        """Create a bitfield from bit-sized fields, packed in the given byte order."""
        self.name = name
        self.order = order
        self.fields = lst
        size = (sum([f.size for f in lst]) + 7) / 8
        if size == 1:
            self.helper = Int8(None)
        elif size == 2:
            self.helper = Int16(None, order)
        elif size == 3:
            self.helper = Int24(None, order)
        elif size == 4:
            self.helper = Int32(None, order)
        else:
            raise FieldError("Maximum bitfield width of 32 exceeded.")
        self.size = self.helper.size

    # --------------------------------------------------------------------------
    def unpack(self, data):
        """Unpack a series of bit-granular Fields and FieldLists.

        Similar to the unpack method for the Field object except a series
        of bit-granular Fields and FieldLists can be unpacked.
        """
        total, data = self.helper.unpack(data)
        total = total[0]
        vals = []
        for f in [f.size for f in self.fields]:
            vals.append(total & Bitfield.width_table[f])
            total >>= f
        return vals, data

    # --------------------------------------------------------------------------
    def pack(self, values):
        """Pack a series of bit-granular Fields and FieldLists.

        Similar to the pack method for the Field object except a series
        of bit-granular Fields and FieldLists can be packed.
        """
        val = 0
        offset = 0
        for f in [f.size for f in self.fields]:
            val |= (values.pop(0) & Bitfield.width_table[f]) << offset
            offset += f
        values.insert(0, val)
        return self.helper.pack(values)


# ******************************************************************************
class Record:
    """Basically a FieldList with data.

    A Record looks, for most purposes, like a dictionary object.  The format
    of the dictionary is specified by the underlying field list and the
    content of the dictionary (values) can come from the unpacking of
    formatted data or from the setting of values via the dictionary API.
    """

    # --------------------------------------------------------------------------
    @staticmethod
    def create(field_list, data=None):
        """Create a record by specifying a field list.

        Optionally provide a sequence of bytes to unpack as record data.  If
        no bytes or if insufficient bytes are provided, the data is padded
        with zeroes to fill in the missing bytes.

        The created record is returned.

        This is the method that should be used to create Record objects
        as opposed to the normal Record() method.
        """
        r = Record(field_list)
        if data is None:
            data = [0] * (field_list.size)
        else:
            data.extend([0] * (field_list.size - len(data)))
        _, extra = r.unpack(data)
        return r, extra

    # --------------------------------------------------------------------------
    def __init__(self, field_list):
        """Create an empty record; use Record.create() instead."""
        self.fields = field_list

    # --------------------------------------------------------------------------
    def unpack(self, data):
        """Unpack the sequence of bytes into the underlying dictionary.

        Any extra data beyond the record is kept track of.

        Return the list of values and the extra data as a tuple.
        """
        vals, extra = self.fields.unpack(data)
        self.values = dict(zip(self.fields.names(), vals, strict=True))
        return vals, extra

    # --------------------------------------------------------------------------
    def pack(self, **values):
        """Pack the record, updating it with any provided field values.

        Pack whatever fields are provided in the keyword arguments (values)
        along with whatever data is already present in the record and
        return the resulting sequence of bytes (and extra data) as a tuple.
        """
        self.set(**values)
        return self.fields.pack([self.values[f] for f in self.fields.names()])

    # --------------------------------------------------------------------------
    def get(self, *names):
        """Return the data that corresponds to the specified field names.

        Return the results as a dictionary.
        """
        rslt = {}.fromkeys(names, 0)
        for n in rslt:
            if n in self.values:
                rslt[n] = self.values[n]
        return rslt

    # --------------------------------------------------------------------------
    def set(self, **values):
        """Set values for the fields specified in the keyword arguments."""
        for name, value in values.items():
            if name in self.values:
                self.values[name] = value

    # --------------------------------------------------------------------------
    def __setitem__(self, key, value):
        """Allow dictionary-type write access to the record data."""
        try:
            self.values[key] = value
        except KeyError:
            pass

    # --------------------------------------------------------------------------
    def __getitem__(self, key):
        """Allow dictionary-type read access to the record data."""
        try:
            return self.values[key]
        except KeyError:
            return 0

    # --------------------------------------------------------------------------
    def __iter__(self):
        """Allow iteration over the record's field names."""
        return iter(list(self.values.keys()))
