"""Windows-safe temporary memory-mapped matrices (G-DISK).

On Windows a file with a live memory map cannot be deleted (os.remove raises PermissionError). A
bare ``except: pass`` around that delete once let tens of GB of temp matrices pile up silently. So
the lifecycle here is fixed:

  create  -> a NEW file named treeroute_<pid>_<start ms>_<tag>.mm (an existing file is refused);
  use     -> row blocks through ``write_rows`` / ``read_rows`` (read_rows returns a copy), or the
             ``array`` property for code that needs the memmap itself;
  release -> drop the holder's reference, gc.collect(), check no reference survives, then delete.
             Any failure raises TempMatrixError naming the file. Nothing is swallowed.

A caller that keeps its own alias (``A = tm.array``) must ``del A`` (and clear any container that
holds it) before the ``with`` block ends; otherwise release refuses loudly and leaves the file.

numpy is imported inside the functions, so importing this module does not load it.
"""

import gc
import os
import re
import weakref
from contextlib import contextmanager
from pathlib import Path

from treeroute.errors import TempMatrixError
from treeroute.runs import proc
from treeroute.runs.preflight import TEMP_PREFIX, TEMP_SUFFIX

_TAG = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


def temp_matrix_path(temp_dir, tag):
    """The file name this process uses for ``tag`` (pid and start time make it unique)."""
    if not _TAG.match(tag):
        raise ValueError("temp matrix tag must be 1-64 letters, digits, '_' or '-', got %r" % (tag,))
    pid, created = proc.own_identity()
    return Path(temp_dir) / ("%s%d_%d_%s%s" % (TEMP_PREFIX, pid, created, tag, TEMP_SUFFIX))


class TempMatrix(object):
    def __init__(self, path, array):
        self.path = Path(path)
        self._array = array
        self.shape = tuple(array.shape)
        self.dtype = str(array.dtype)

    @property
    def closed(self):
        return self._array is None

    @property
    def array(self):
        if self._array is None:
            raise TempMatrixError("temp matrix %s was released" % self.path)
        return self._array

    def write_rows(self, start, block):
        """Write a contiguous block of whole rows starting at row ``start`` (never column-wise)."""
        arr = self.array
        stop = start + len(block)
        if start < 0 or stop > arr.shape[0]:
            raise IndexError("rows %d:%d outside 0:%d" % (start, stop, arr.shape[0]))
        arr[start:stop] = block
        del arr

    def read_rows(self, start, stop):
        """A COPY of rows start:stop, so no alias to the memmap escapes."""
        import numpy as np

        arr = self.array
        out = np.array(arr[start:stop], copy=True)
        del arr
        return out

    def release(self):
        """Drop the reference, collect, verify nothing still holds the map, then delete loudly."""
        if self._array is None:
            return
        arr = self._array
        self._array = None
        ref = weakref.ref(arr)
        del arr
        gc.collect()
        if ref() is not None:
            holders = len(gc.get_referrers(ref()))
            raise TempMatrixError(
                "temp matrix %s is still referenced (%d referrer(s)) after the engine dropped its "
                "own reference. Delete every alias and clear every container holding it before the "
                "block ends. The file is left on disk; after the process exits, preflight lists it "
                "as an orphan." % (self.path, holders))
        try:
            os.remove(str(self.path))
        except OSError as exc:
            raise TempMatrixError("could not delete temp matrix %s: %s. The file is left on disk."
                                  % (self.path, exc)) from exc


@contextmanager
def temp_memmap(temp_dir, tag, shape, dtype):
    """Create a NEW temp memmap, yield its TempMatrix, and always release it (loudly)."""
    import numpy as np

    temp_dir = Path(temp_dir)
    if not temp_dir.is_dir():
        raise TempMatrixError("temp dir %s does not exist" % temp_dir)
    path = temp_matrix_path(temp_dir, tag)
    if os.path.lexists(str(path)):
        raise TempMatrixError("refusing to overwrite existing file %s" % path)
    array = np.memmap(str(path), dtype=dtype, mode="w+", shape=tuple(shape))
    holder = TempMatrix(path, array)
    del array
    try:
        yield holder
    finally:
        holder.release()
