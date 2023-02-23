LITTLE_ENDIAN = False
BIG_ENDIAN = True

DEFAULT_BYTE_ORDER = LITTLE_ENDIAN


# ******************************************************************************
class FieldError(Exception):
    pass


# ******************************************************************************
class Field:
    # --------------------------------------------------------------------------
    def __init__(self, name, size):
        """A field has a name and a size.  The size is in bytes."""
        self.name = name
        self.size = size


# ******************************************************************************
class Bitmask(Field):
    """Naming utility.  This is the same as a field, but is implemented for
    readability reasons when creating Bitfield objects.
    """

    pass


# ******************************************************************************
class Int8(Field):
    # --------------------------------------------------------------------------
    def __init__(self, name):
        Field.__init__(self, name, 1)

    # --------------------------------------------------------------------------
    def unpack(self, bytes):
        b = bytes.pop(0)
        return [b], bytes

    # --------------------------------------------------------------------------
    def pack(self, values):
        val = values.pop(0)
        return [val & 0xFF], values


# ******************************************************************************
class Int16(Field):
    # --------------------------------------------------------------------------
    def __init__(self, name, order=DEFAULT_BYTE_ORDER):
        Field.__init__(self, name, 2)
        self.order = order

    # --------------------------------------------------------------------------
    def unpack(self, bytes):
        b0 = bytes.pop(0)
        b1 = bytes.pop(0)
        if self.order == LITTLE_ENDIAN:
            val = b0 | (b1 << 8)
        else:
            val = b1 | (b0 << 8)
        return [val], bytes

    # --------------------------------------------------------------------------
    def pack(self, values):
        val = values.pop(0)
        if self.order == LITTLE_ENDIAN:
            b = [val & 0xFF, (val >> 8) & 0xFF]
        else:
            b = [(val >> 8) & 0xFF, val & 0xFF]
        return b, values


# ******************************************************************************
class Int24(Field):
    # --------------------------------------------------------------------------
    def __init__(self, name, order=DEFAULT_BYTE_ORDER):
        Field.__init__(self, name, 3)
        self.order = order

    # --------------------------------------------------------------------------
    def unpack(self, bytes):
        b0 = bytes.pop(0)
        b1 = bytes.pop(0)
        b2 = bytes.pop(0)
        if self.order == LITTLE_ENDIAN:
            val = b0 | (b1 << 8) | (b2 << 16)
        else:
            val = b2 | (b1 << 8) | (b0 << 16)
        return [val], bytes

    # --------------------------------------------------------------------------
    def pack(self, values):
        val = values.pop(0)
        if self.order == LITTLE_ENDIAN:
            b = [val & 0xFF, (val >> 8) & 0xFF, (val >> 16) & 0xFF]
        else:
            b = [(val >> 16) & 0xFF, (val >> 8) & 0xFF, val & 0xFF]
        return b, values


# ******************************************************************************
class Int32(Field):
    # --------------------------------------------------------------------------
    def __init__(self, name, order=DEFAULT_BYTE_ORDER):
        Field.__init__(self, name, 4)
        self.order = order

    # --------------------------------------------------------------------------
    def unpack(self, bytes):
        b0 = bytes.pop(0)
        b1 = bytes.pop(0)
        b2 = bytes.pop(0)
        b3 = bytes.pop(0)
        if self.order == LITTLE_ENDIAN:
            val = b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)
        else:
            val = b3 | (b2 << 8) | (b1 << 16) | (b0 << 24)
        return [val], bytes

    # --------------------------------------------------------------------------
    def pack(self, values):
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
        """Name the list of fields and provide a list of field or FieldList
        objects that specify the format of the data.
        """
        self.name = name
        self.size = sum([f.size for f in lst])
        self.fields = lst

    # --------------------------------------------------------------------------
    def names(self):
        """Return a list of the field names.  The list is ordered according
        to the data order.
        """
        name_list = []
        for f in self.fields:
            if isinstance(f, FieldList):
                name_list.extend(f.names())
            else:
                name_list.append(f.name)
        return name_list

    # --------------------------------------------------------------------------
    def unpack(self, bytes):
        """Similar to the unpack method for the Field object except a series
        of Fields and FieldLists can be unpacked.
        """
        vals = []
        for f in self.fields:
            v, bytes = f.unpack(bytes)
            vals.extend(v)
        return vals, bytes

    # --------------------------------------------------------------------------
    def pack(self, values):
        """Similar to the pack method for the Field object except a series
        of Fields and FieldLists can be packed.
        """
        bytes = []
        for f in self.fields:
            b, values = f.pack(values)
            bytes.extend(b)
        return bytes, values


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
    def unpack(self, bytes):
        """Similar to the unpack method for the Field object except a series
        of bit-granular Fields and FieldLists can be unpacked.
        """
        total, bytes = self.helper.unpack(bytes)
        total = total[0]
        vals = []
        for f in [f.size for f in self.fields]:
            vals.append(total & Bitfield.width_table[f])
            total >>= f
        return vals, bytes

    # --------------------------------------------------------------------------
    def pack(self, values):
        """Similar to the pack method for the Field object except a series
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
    def create(field_list, bytes=None):
        """Create a record by specifying a field list.  Optionally provide a
        sequence of bytes to unpack as record data.  If no bytes or if
        insufficent bytes are provided, the data is padded with zeroes to
        fill in the missing bytes.

        The created record is returned.

        This is the method that should be used to create Record objects
        as opposed to the normal Record() method.
        """
        r = Record(field_list)
        if bytes is None:
            bytes = [0] * (field_list.size)
        else:
            bytes.extend([0] * (field_list.size - len(bytes)))
        vals, extra = r.unpack(bytes)
        return r, extra

    create = staticmethod(create)

    # --------------------------------------------------------------------------
    def __init__(self, field_list):
        self.fields = field_list

    # --------------------------------------------------------------------------
    def unpack(self, bytes):
        """Unpack the sequence of bytes into the underlying dictionary and
        keep track of any extra data.

        Return the list of values and the extra data as a tuple.
        """
        vals, extra = self.fields.unpack(bytes)
        self.values = dict(list(zip(self.fields.names(), vals)))
        return vals, extra

    # --------------------------------------------------------------------------
    def pack(self, **values):
        """Pack whatever fields are provided in the keyword arguments (values)
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
        """Set values for the fields that are specified in the provided
        keyword arguments.
        """
        for v in values:
            if v in self.values:
                self.values[v] = values[v]

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
