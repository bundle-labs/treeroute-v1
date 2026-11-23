"""status.json heartbeat: phase, message, progress and liveness of the process writing it.

The writer replaces status.json atomically on every beat. A reader that holds the file open (for
example ``treeroute status`` or a later GUI tab reading it) makes the rename fail on Windows; the
beat waits a bounded time for the reader to let go, then fails loudly naming the file
(runs/atomic.py). ``describe`` tells a reader whether the writing process is still alive (same pid
AND same start time) and how old the last beat is. Any ETA is a report-only estimate supplied by
the caller.
"""

import datetime
from pathlib import Path

from treeroute.runs import proc
from treeroute.runs.atomic import read_json, replace_json

STATUS_FILE = "status.json"


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class StatusWriter(object):
    def __init__(self, run_dir, fingerprint):
        self.path = Path(run_dir) / STATUS_FILE
        self.fingerprint = fingerprint
        self.pid, self.pid_created_ms = proc.own_identity()
        self.started = _utc_now().isoformat(timespec="seconds")
        self.beats = 0

    def beat(self, phase, message="", done=None, total=None, eta_seconds=None, state="running"):
        self.beats += 1
        replace_json(self.path, {
            "fingerprint": self.fingerprint,
            "pid": self.pid,
            "pid_created_ms": self.pid_created_ms,
            "state": state,
            "phase": phase,
            "message": message,
            "done": done,
            "total": total,
            "eta_seconds_estimate": eta_seconds,
            "started_utc": self.started,
            "updated_utc": _utc_now().isoformat(timespec="seconds"),
            "beat": self.beats,
        })

    def finish(self, phase="finished", message=""):
        self.beat(phase, message, state="finished")

    def fail(self, phase, message):
        self.beat(phase, message, state="failed")


def read_status(run_dir):
    path = Path(run_dir) / STATUS_FILE
    if not path.is_file():
        return None
    return read_json(path)


def describe(status, now=None):
    """One line for ``treeroute status``."""
    if status is None:
        return "no status.json yet"
    now = now or _utc_now()
    try:
        updated = datetime.datetime.fromisoformat(status["updated_utc"])
        age = int((now - updated).total_seconds())
        age_text = "%ds ago" % age
    except (KeyError, ValueError, TypeError):
        age_text = "unknown age"
    alive = proc.is_alive(status.get("pid"), status.get("pid_created_ms"))
    state = status.get("state")
    if state == "running" and not alive:
        state = "running per status.json, but its process is gone (crashed or killed; resume)"
    progress = ""
    if status.get("done") is not None and status.get("total"):
        progress = " %s/%s" % (status["done"], status["total"])
    return "%s | phase %s%s | %s | last beat %s" % (
        state, status.get("phase"), progress, status.get("message", ""), age_text)
