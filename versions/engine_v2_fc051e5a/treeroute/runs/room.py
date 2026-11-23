"""Room to work: in-run RAM and temp-disk checks WAIT instead of refusing (owner ruling Q1), and memory is given
back before the big steps (a gc pass and the Windows working-set trim).

Ruling Q1 (the owner rulings file, section Q): inside a run, a RAM or temp-disk go/refuse prints what it needs
and the biggest programs using memory, checks again every P7.room_poll_seconds, writes a note at most every
P7.room_note_seconds, continues as soon as there is room, and refuses as it does today (the same exception, with the
numbers of its last check) after P7.room_max_wait_seconds. Plan-time pre-flights that run before any work starts keep
refusing at once (they do not call wait_for_room).

No number can change here: a check decides only WHEN the next step starts, and that step computes the same bytes
whenever it starts. The first check runs exactly as before (no gc, no trim, no wait); only a check that would refuse
releases memory, checks again at once, and then waits.

The working-set trim (trim_working_set: psapi EmptyWorkingSet on this process, else SetProcessWorkingSetSize(-1, -1))
moves the process's resident pages to the standby list. Clean file-backed pages (the pools' and stores' memmaps) are
then counted as available RAM; a page the process touches again is faulted back with the same bytes. It never
raises; TRIMS counts whether it ran.

Waiting only where waiting can help (a fix of the install review): a refusal waits only when it is a SHORTAGE, marked by
the check that raised it (runs.preflight.mark_shortage: the RAM and temp-disk bytes it needs). It refuses at once,
with no release and no wait, when the refusal carries no such mark (a missing folder, a rule: waiting cannot fix
it), when the RAM it needs is above the machine's total RAM, or when the disk it needs is above the disk's total
size (no program can close to make that room).

Every note goes through the run's echo (its run.log and console: the RunLog stamps "[hh:mm:ss] ") and starts with
WAITING ("[waiting]"), so a note reads "[hh:mm:ss] [waiting] room: ..."; without a run echo, stamped_print stamps it
the same way.
"""

import datetime
import gc
import sys
import time

from treeroute import engine_constants as K
from treeroute.errors import PreflightRefusal

GIB = float(1 << 30)
TRIMS = {"ran": 0, "failed": 0, "skipped": 0}       # what trim_working_set did in this process
WAITING = "[waiting]"                                 # the first word of every wait_for_room note


def stamped_print(line):
    """The echo when a site has no run echo: the line stamped "[hh:mm:ss] " as the RunLog stamps it."""
    print("[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), line), flush=True)


def trim_working_set():
    """Empty this process's working set (Windows). Returns True when it ran; never raises."""
    if not sys.platform.startswith("win"):
        TRIMS["skipped"] += 1
        return False
    ok = False
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)     # own instances: no global argtypes
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        handle = kernel32.GetCurrentProcess()
        try:
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            psapi.EmptyWorkingSet.argtypes = [wintypes.HANDLE]
            psapi.EmptyWorkingSet.restype = wintypes.BOOL
            ok = bool(psapi.EmptyWorkingSet(handle))
        except Exception:
            ok = False
        if not ok:
            setter = kernel32.SetProcessWorkingSetSize
            setter.argtypes = [wintypes.HANDLE, ctypes.c_size_t, ctypes.c_size_t]
            setter.restype = wintypes.BOOL
            ok = bool(setter(handle, ctypes.c_size_t(-1), ctypes.c_size_t(-1)))
    except Exception:
        ok = False
    TRIMS["ran" if ok else "failed"] += 1
    return ok


def release_memory():
    """A gc pass, then the working-set trim. Returns {'gc_collected': objects, 'trimmed': bool}; never raises."""
    try:
        collected = int(gc.collect())
    except Exception:
        collected = -1
    return {"gc_collected": collected, "trimmed": trim_working_set()}


def top_programs(count=None):
    """The programs with the largest working sets: [(bytes, name, pid)], largest first ([] when unreadable)."""
    count = int(K.ROOM_TOP_PROGRAMS if count is None else count)
    try:
        import psutil

        rows = []
        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            info = proc.info
            mem = info.get("memory_info")
            if mem is None:
                continue
            rows.append((int(mem.rss), str(info.get("name") or "?"), int(info.get("pid") or 0)))
        rows.sort(key=lambda r: (-r[0], r[1], r[2]))
        return rows[:count]
    except Exception:
        return []


def _programs_text(rows):
    if not rows:
        return "the program list could not be read"
    return ", ".join("%s (pid %d) %.2f GiB" % (name, pid, size / GIB) for size, name, pid in rows)


def _hopeless(exc):
    """Why waiting cannot help this refusal (a text), or None when it is a shortage that may pass: no shortage mark
    (runs.preflight.mark_shortage), or a need above the machine's total RAM or the disk's total size."""
    from treeroute.runs import preflight

    short = getattr(exc, "shortage", None)
    if not isinstance(short, dict):
        return "the refusal is not a shortage of RAM or temp disk"
    need_ram, need_disk = short.get("need_ram"), short.get("need_disk")
    if need_ram is not None:
        total = preflight.total_ram_bytes()
        if int(need_ram) > total:
            return ("it needs %.2f GiB of RAM, more than the machine's total RAM (%.2f GiB)"
                    % (int(need_ram) / GIB, total / GIB))
    if need_disk is not None:
        total = preflight.total_disk_bytes(short.get("disk_path"))
        if int(need_disk) > total:
            return ("it needs %.2f GiB of disk at %s, more than that disk's total size (%.2f GiB)"
                    % (int(need_disk) / GIB, short.get("disk_path"), total / GIB))
    return None


def wait_for_room(check, what, echo=None, retry_on=(PreflightRefusal,), poll_seconds=None, note_seconds=None,
                  max_wait_seconds=None, clock=time.monotonic, sleep=time.sleep):
    """check() until it passes, and return its value (owner ruling Q1; module docstring).

    check: the site's own go/refuse, unchanged; it raises one of retry_on when there is no room. The first call is
    the site's check as before. On a refusal that is a shortage that may pass (_hopeless: marked by
    runs.preflight.mark_shortage, and within the machine's total RAM and the disk's total size): release_memory()
    and check again at once; then, while it still refuses, a note (what, the refusal's own text with the need and
    what is there, the biggest programs) at once and at most every note_seconds, a check every poll_seconds, and
    after max_wait_seconds the last refusal is raised again (today's exception and message). A refusal that is not
    such a shortage is raised again at once (one note says why). poll, note and max wait default to the P7 engine
    constants (read at the call); clock and sleep are injectable for the tests. Any other exception passes through.
    echo: the run's echo (its RunLog: run.log and the console, stamped "[hh:mm:ss] "); None: stamped_print. Every
    note starts with WAITING."""
    say = stamped_print if echo is None else echo

    def note(text):
        say("%s room: %s" % (WAITING, text))

    def refuse_now_if_hopeless(exc, checks):
        why = _hopeless(exc)
        if why is not None:
            note("%s: refusing at once, without waiting (%d check%s): %s"
                 % (what, checks, "" if checks == 1 else "s", why))
            raise exc

    try:
        return check()
    except retry_on as exc:
        last = exc
    refuse_now_if_hopeless(last, 1)
    poll = float(K.ROOM_POLL_SECONDS if poll_seconds is None else poll_seconds)
    note_every = float(K.ROOM_NOTE_SECONDS if note_seconds is None else note_seconds)
    max_wait = float(K.ROOM_MAX_WAIT_SECONDS if max_wait_seconds is None else max_wait_seconds)
    start = clock()
    noted = None
    checks = 1
    while True:
        released = release_memory()
        checks += 1
        try:
            out = check()
        except retry_on as exc:
            last = exc
        else:
            note("%s: room after %s (%d checks, %.0f s; working-set trim %s): continuing"
                 % (what, "waiting" if noted is not None else "the memory release (gc, working-set trim)", checks,
                    clock() - start, "ran" if released["trimmed"] else "did not run"))
            return out
        refuse_now_if_hopeless(last, checks)
        waited = clock() - start
        if waited >= max_wait:
            note("%s: still no room after %.0f s (%d checks; P7.room_max_wait_seconds %.0f): refusing as before"
                 % (what, waited, checks, max_wait))
            raise last
        if noted is None or clock() - noted >= note_every:
            note("%s is waiting for room: %s | biggest programs using memory: %s | checked every %.0f s, waited %.0f "
                 "s of at most %.0f s (P7.room_max_wait_seconds); nothing is lost while it waits: close programs to "
                 "continue (working-set trim %s)"
                 % (what, last, _programs_text(top_programs()), poll, waited, max_wait,
                    "ran" if released["trimmed"] else "did not run"))
            noted = clock()
        sleep(poll)


__all__ = ["wait_for_room", "release_memory", "trim_working_set", "top_programs", "stamped_print",
           "TRIMS", "WAITING"]
