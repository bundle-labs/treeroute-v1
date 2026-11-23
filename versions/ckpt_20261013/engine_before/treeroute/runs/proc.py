"""Process identity: pid plus start time, so a reused pid is never taken for a live engine process."""

import os

import psutil


def create_time_ms(pid):
    """Start time of process ``pid`` in whole milliseconds, or None if it does not exist."""
    try:
        return int(psutil.Process(pid).create_time() * 1000)
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return None


def own_identity():
    """(pid, start time in ms) of this process."""
    pid = os.getpid()
    return pid, create_time_ms(pid)


def is_alive(pid, created_ms):
    """True if process ``pid`` exists AND started at ``created_ms`` (same process, not a reuse)."""
    if pid is None or created_ms is None:
        return False
    try:
        pid = int(pid)
        created_ms = int(created_ms)
    except (TypeError, ValueError):
        return False
    if not psutil.pid_exists(pid):
        return False
    return create_time_ms(pid) == created_ms
