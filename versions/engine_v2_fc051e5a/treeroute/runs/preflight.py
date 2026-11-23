"""Pre-flight: disk and RAM go/refuse, orphan temp files, and the one-heavy-job lock (G-DISK).

Disk and RAM decide only go or refuse (plan 1.7). They never set a unit count or any other number.
A refusal prints the fix ("free X GiB": sizes in 2^30 bytes). The needs come from the pipeline;
this module only compares them with what the machine has.

Orphans: engine temp files are named ``treeroute_<pid>_<start ms>_<tag>.mm`` (runs/tempmem.py).
A temp file whose process is gone is an orphan. The engine never deletes it (it may belong to a
run someone wants to inspect); it refuses and names the files.

Heavy-job lock: one heavy job per machine. The lock file holds the owner's pid and start time. A
lock held by a live process refuses; a lock left by a dead process also refuses, naming the file
to remove by hand.
"""

import os
import re
import shutil
from pathlib import Path

import psutil

from treeroute.errors import PreflightRefusal
from treeroute.runs import proc
from treeroute.runs.atomic import dumps, read_json

GIB = float(1 << 30)
TEMP_PREFIX = "treeroute_"
TEMP_SUFFIX = ".mm"
TEMP_NAME = re.compile(r"^treeroute_(\d+)_(\d+)_[A-Za-z0-9_\-]+\.mm$")
HEAVY_LOCK_FILE = "treeroute_heavy_job.lock"


def _existing_ancestor(path):
    path = Path(os.path.abspath(os.fspath(path)))
    for candidate in [path] + list(path.parents):
        if candidate.exists():
            return candidate
    raise PreflightRefusal("G-DISK", "no existing folder above %s" % path)


def free_disk_bytes(path):
    return shutil.disk_usage(str(_existing_ancestor(path))).free


def available_ram_bytes():
    return int(psutil.virtual_memory().available)


def total_ram_bytes():
    """The machine's total RAM (runs.room: a need above it can never fit, so it is refused without waiting)."""
    return int(psutil.virtual_memory().total)


def total_disk_bytes(path):
    """The total size of the disk holding ``path`` (runs.room: a need above it can never fit)."""
    return int(shutil.disk_usage(str(_existing_ancestor(path))).total)


def mark_shortage(exc, need_ram=None, need_disk=None, disk_path=None):
    """Mark a refusal as a SHORTAGE (returns exc): the RAM and the disk bytes (at disk_path) that were short. Only a
    marked refusal may wait for room (runs.room.wait_for_room); the mark changes no message."""
    exc.shortage = {"need_ram": None if need_ram is None else int(need_ram),
                    "need_disk": None if need_disk is None else int(need_disk),
                    "disk_path": None if disk_path is None else str(disk_path)}
    return exc


def check_resources(disk_path, need_disk_bytes, need_ram_bytes):
    """Go (returns the measured numbers) or refuse with the fix. Never shrinks a run. A refusal is marked as a
    shortage (mark_shortage) with the needs that did not fit."""
    free_disk = free_disk_bytes(disk_path)
    free_ram = available_ram_bytes()
    problems = []
    if need_disk_bytes > free_disk:
        problems.append("disk at %s needs %.2f GiB, %.2f GiB free: free %.2f GiB"
                        % (disk_path, need_disk_bytes / GIB, free_disk / GIB,
                           (need_disk_bytes - free_disk) / GIB))
    if need_ram_bytes > free_ram:
        problems.append("RAM needs %.2f GiB, %.2f GiB available: free %.2f GiB (close other programs)"
                        % (need_ram_bytes / GIB, free_ram / GIB, (need_ram_bytes - free_ram) / GIB))
    if problems:
        raise mark_shortage(PreflightRefusal("G-DISK", "; ".join(problems),
                                             fix="free the space named above; the run size is never reduced"),
                            need_ram=need_ram_bytes if need_ram_bytes > free_ram else None,
                            need_disk=need_disk_bytes if need_disk_bytes > free_disk else None,
                            disk_path=disk_path)
    return {"disk_path": str(disk_path), "free_disk_bytes": int(free_disk),
            "need_disk_bytes": int(need_disk_bytes), "available_ram_bytes": int(free_ram),
            "need_ram_bytes": int(need_ram_bytes)}


# ---------------------------------------------------------------------------------------------------
# RAM estimates of the streamed target design (go/refuse only; they never set a number). The target is
# read file by file into a census (derive/census.py); full rows are read again only for the picked units.
CENSUS_FILE_ROW_BYTES = 1200      # one target file in flight: the reader's frame, its checks and the census updates
CENSUS_KEY_BYTES = 24             # one driver row's key while its group streams (unit code, coordinate, sorted copy)
CENSUS_UNIT_BYTES = 700           # one unit in the census table (its id text, the id map, group, row count);
#                                   two full-size monthly measurements (2.03M units) peaked at 3.48 and 3.62 GiB
#                                   of commit; 700 puts the estimate on their true counts at 3.83 GiB (400 gave 3.27)
CENSUS_BLOCK_ROW_BYTES = 64       # one row of a unit block while the bits are read (positions, gaps)


def census_pass_ram_bytes(units, coords, biggest_file_rows, biggest_group_rows, presence_stores, hist_bins,
                          unit_block):
    """The census pass: one file in flight, one group's driver keys per presence store, two bit matrices
    (row exists, label valid) of coords x units bits, the unit table, one label histogram of hist_bins
    int64 per coordinate, and one block of unit_block units unpacked (booleans and row positions). The
    per-row and per-unit costs were measured on a full-size monthly target."""
    bits = 2 * int(coords) * ((int(units) + 7) // 8)
    return int(int(biggest_file_rows) * CENSUS_FILE_ROW_BYTES
               + int(biggest_group_rows) * int(presence_stores) * CENSUS_KEY_BYTES
               + bits + CENSUS_UNIT_BYTES * int(units) + int(coords) * int(hist_bins) * 8
               + int(coords) * int(unit_block) * (1 + CENSUS_BLOCK_ROW_BYTES))


# The column reader (pipeline/data.py ColumnReader: the driver rows read and joined, the sentinel mask, the
# feature script's outputs, then the lagged, last-value-filled kept columns) at its PEAK while it is built and
# lagged, per target row: a fixed part and a part per frame column. Measured on full-size monthly stores
# (scratch reader_bytes.py, sampled RSS): 102 frame columns 4.05-4.24 KB a row at the peak (1.9-2.1 KB held
# once built), 964 columns 23.6-24.4 KB (12.7-13.7 KB held). These give 5.3 KB and 29.4 KB: about 20% over
# the measured peaks. (The earlier 120 + 16 x columns, 1.75 KB a row at 102 columns, was below even the
# held size.)
READER_PEAK_ROW_BYTES = 2400
READER_PEAK_VALUE_BYTES = 28


def column_reader_peak_bytes(rows, n_columns):
    """A column reader of `rows` target rows and `n_columns` frame columns at its peak (the picked units'
    reader, or one unit block of R30's streamed test-year count)."""
    return int(int(rows) * (READER_PEAK_ROW_BYTES + READER_PEAK_VALUE_BYTES * int(n_columns)))


# One driver file in flight while a column reader reads it (ColumnReader._read_drivers reads a whole file's needed
# columns, then keeps only its units' rows): per file row, the read columns as float64 values and the unit id's text
# twice (as read, and cast for the unit filter). A per-group reader holds few rows, so the biggest driver file of a
# big group is its peak, not its rows. The byte sizes are engine constants with their origins (P1.reader_file_*).
def driver_file_bytes(rows, n_columns):
    """One driver file of `rows` rows with `n_columns` read columns in flight inside a column reader."""
    from treeroute import engine_constants as K

    return int(int(rows) * (int(K.READER_FILE_ROW_BYTES) + int(K.READER_FILE_VALUE_BYTES) * int(n_columns)))


def find_orphan_temp_files(temp_dir):
    """Engine temp files in ``temp_dir`` whose owning process is gone."""
    temp_dir = Path(temp_dir)
    if not temp_dir.is_dir():
        return []
    orphans = []
    for entry in sorted(temp_dir.iterdir(), key=lambda p: p.name):
        match = TEMP_NAME.match(entry.name)
        if match and not proc.is_alive(int(match.group(1)), int(match.group(2))):
            orphans.append(entry)
    return orphans


def refuse_orphans(temp_dir):
    orphans = find_orphan_temp_files(temp_dir)
    if orphans:
        total = sum(p.stat().st_size for p in orphans if p.is_file())
        raise PreflightRefusal(
            "G-DISK", "%d orphan engine temp file(s) (%.2f GiB) from dead processes: %s"
            % (len(orphans), total / GIB, ", ".join(str(p) for p in orphans)),
            fix="check no run needs them, then delete them by hand")


class HeavyJobLock(object):
    """Context manager: one heavy engine job per machine."""

    def __init__(self, lock_dir):
        self.path = Path(lock_dir) / HEAVY_LOCK_FILE
        self.held = False

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        pid, created = proc.own_identity()
        text = dumps({"pid": pid, "pid_created_ms": created}) + "\n"
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                owner = read_json(self.path)
            except Exception as exc:
                raise PreflightRefusal("G-DISK", "heavy-job lock %s exists but is unreadable (%s)"
                                       % (self.path, exc),
                                       fix="check no engine job runs, then delete it by hand")
            if proc.is_alive(owner.get("pid"), owner.get("pid_created_ms")):
                raise PreflightRefusal("G-DISK", "another heavy engine job (pid %s) holds %s"
                                       % (owner.get("pid"), self.path),
                                       fix="wait for it to finish; one heavy job per machine")
            raise PreflightRefusal("G-DISK", "stale heavy-job lock %s from dead pid %s"
                                   % (self.path, owner.get("pid")),
                                   fix="check no engine job runs, then delete the lock by hand")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        self.held = True
        return self

    def release(self):
        """Remove the lock only if this process wrote it; any failure is loud."""
        if not self.held:
            return
        owner = read_json(self.path)
        pid, created = proc.own_identity()
        if owner.get("pid") != pid or owner.get("pid_created_ms") != created:
            raise PreflightRefusal("G-DISK", "heavy-job lock %s is no longer ours (%r)"
                                   % (self.path, owner))
        os.remove(str(self.path))
        self.held = False

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False
