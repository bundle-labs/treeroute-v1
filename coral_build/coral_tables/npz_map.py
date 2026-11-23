"""Read-only memory maps of STORED members of a .npz file (package-side helper, not engine code).

Written 2026-10-19 for the coral table builder (D:/treeroute/coral_build/SPEC_CORAL_TABLES.md section 4).
Why: np.load ignores mmap_mode for .npz files, so the legacy builder read the whole 889 MB SST compact into
RAM (coral_forecast.py:87-88). Every member of D:/coral/drivers/sst_compact_all.npz is STORED (compress_type 0,
measured 2026-10-19), so a member is one contiguous .npy blob inside the zip and can be memory-mapped at its
byte offset. A compressed member is refused (fail loud): it cannot be mapped.
"""
import struct
import zipfile

import numpy as np

_LOCAL_HEADER = 30  # fixed part of a zip local file header (PKWARE APPNOTE 4.3.7)


def member_map(path, member):
    """np.memmap (mode 'r') of one STORED .npy member of a .npz file. Never writes."""
    with zipfile.ZipFile(path) as z:
        info = z.getinfo(member)
        if info.compress_type != zipfile.ZIP_STORED:
            raise ValueError("%s:%s is compressed (type %d); it cannot be memory-mapped"
                             % (path, member, info.compress_type))
        offset = info.header_offset
    with open(path, "rb") as f:
        f.seek(offset)
        head = f.read(_LOCAL_HEADER)
        if head[:4] != b"PK\x03\x04":
            raise ValueError("%s:%s has no local file header at %d" % (path, member, offset))
        name_len, extra_len = struct.unpack("<HH", head[26:30])
        f.seek(offset + _LOCAL_HEADER + name_len + extra_len)
        version = np.lib.format.read_magic(f)
        if version == (1, 0):
            shape, fortran, dtype = np.lib.format.read_array_header_1_0(f)
        elif version == (2, 0):
            shape, fortran, dtype = np.lib.format.read_array_header_2_0(f)
        else:
            raise ValueError("%s:%s has .npy version %r" % (path, member, version))
        data_offset = f.tell()
    if fortran or dtype.hasobject:
        raise ValueError("%s:%s is Fortran-ordered or holds objects" % (path, member))
    return np.memmap(path, dtype=dtype, mode="r", offset=data_offset, shape=shape, order="C")
