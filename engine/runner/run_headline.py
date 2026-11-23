"""Safe runner for the headline runs: crash-safe restarts and a short, readable progress view.

It sits OUTSIDE the engine (not under treeroute/ or treeroute_report/), so it changes no engine
hash and no freeze lock. It only starts the engine's own command:

    py -3.9 -W "ignore:DataFrame is highly fragmented" -u -m treeroute run datasets/<package>

What it adds:
  * before each start: waits until enough RAM and D: space are free, names the programs that use
    the most RAM, moves a stale heavy-job lock aside, and removes the engine temp files of dead runs
    (the runs' own scratch);
  * while running: keeps Windows awake, writes EVERY engine line to a log file, and prints only the
    important lines plus a progress line (census files, R30 regions, saved steps) with an estimate;
  * after a stop: when the engine refused because RAM or disk ran short, it waits until there is
    room again and starts the same command, which resumes from the last saved step; any other
    refusal or crash stops the chain and writes LAST_FAILURE_<package>.txt.

Usage (from the engine folder):
    py -3.9 runner/run_headline.py fire defo ndvi       run in this order; finished ones are skipped
    py -3.9 runner/run_headline.py --status             one-screen progress of every package
"""

import argparse
import ctypes
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import psutil

ENGINE = Path(__file__).resolve().parent.parent
RUN_ROOT = Path("D:/treeroute/runs")
TEMP_DIR = Path("D:/treeroute/tmp")
LOG_DIR = Path("D:/treeroute/runner_logs")
STATE_FILE = LOG_DIR / "runner_state.json"
LOCK_FILE = TEMP_DIR / "treeroute_heavy_job.lock"
GIB = 1024 ** 3
WARN_FILTER = "ignore:DataFrame is highly fragmented"
POLL_S = 60
MAX_RETRIES = 30
DEFAULT_MIN_RAM_GIB = 7.0
DEFAULT_MIN_DISK_GIB = 5.0
WARN_RAM_GIB = 3.5      # warn (beep + popup) when free RAM falls below this while a run is going (5.0 was too
                        # noisy: the engine itself sizes its count blocks to the free RAM)
WARN_EVERY_S = 120
NOISY = ("last value (", "PerformanceWarning", "self.raw[c]", "out[c] =", "right[c] =",
         "target reader:", "driver store ")
TEMP_FILE = re.compile(r"^treeroute_(\d+)_(\d+)_[A-Za-z0-9_\-]+\.mm$")
TEMP_RUN_DIR = re.compile(r"^treeroute_run_[0-9a-f]+_(\d+)$")
RE_GROUPS = re.compile(r"groups: (\d+) in the data")
RE_CENSUS = re.compile(r"census: (\d+) of (\d+) files")
RE_R30 = re.compile(r"R30 test-year shares: group (\S+) (counted|loaded from checkpoint)")
RE_RAM = re.compile(r"needs (?:about )?([\d.]+) GiB of RAM|RAM needs ([\d.]+) GiB")
RE_DISK = re.compile(r"disk at (\S+) needs ([\d.]+) GiB")
RE_AVAIL = re.compile(r"([\d.]+) GiB available")


def now():
    return dt.datetime.now().strftime("%H:%M:%S")


def say(msg):
    print("[runner %s] %s" % (now(), msg), flush=True)


def beep():
    try:
        import winsound
        winsound.MessageBeep()
    except Exception:
        pass


def keep_awake(on):
    """Ask Windows not to sleep while a run is going (no system setting is changed)."""
    try:
        flags = 0x80000000 | (0x00000001 if on else 0)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        ctypes.windll.kernel32.SetThreadExecutionState(flags)
    except Exception:
        pass


def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(str(tmp), str(STATE_FILE))


def alive(pid, created_ms=None):
    try:
        p = psutil.Process(int(pid))
        return created_ms is None or int(p.create_time() * 1000) == int(created_ms)
    except Exception:
        return False


def free_ram_gib():
    return psutil.virtual_memory().available / GIB


def free_disk_gib(path="D:/"):
    return shutil.disk_usage(path).free / GIB


def ram_hogs(limit=5):
    rows = []
    for p in psutil.process_iter(["name", "memory_info"]):
        try:
            name = (p.info["name"] or "").lower()
            if name.startswith(("python", "py.exe", "system", "memory compression")):
                continue
            rows.append((p.info["memory_info"].rss, p.info["name"]))
        except Exception:
            continue
    by_name = {}
    for rss, name in rows:
        by_name[name] = by_name.get(name, 0) + rss
    top = sorted(by_name.items(), key=lambda kv: -kv[1])[:limit]
    return ", ".join("%s %.1f GB" % (n, b / GIB) for n, b in top if b > 0.3 * GIB)


def finished(pkg):
    root = RUN_ROOT / pkg / "headline"
    return root.is_dir() and any((d / "DONE.json").is_file() for d in root.iterdir() if d.is_dir())


def latest_run_dir(pkg):
    root = RUN_ROOT / pkg / "headline"
    if not root.is_dir():
        return None
    dirs = sorted((d for d in root.iterdir() if d.is_dir()), key=lambda d: d.stat().st_mtime)
    return dirs[-1] if dirs else None


def saved_steps(run_dir):
    if run_dir is None or not (run_dir / "phases").is_dir():
        return []
    return sorted(p.name for p in (run_dir / "phases").iterdir() if (p / "DONE").exists())


def clean_before_start():
    """Move a stale heavy-job lock aside; remove engine temp files whose process is gone."""
    if LOCK_FILE.exists():
        try:
            owner = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        except Exception:
            owner = {}
        if alive(owner.get("pid"), owner.get("pid_created_ms")):
            say("another engine job (pid %s) is still running; waiting for it" % owner.get("pid"))
            while alive(owner.get("pid"), owner.get("pid_created_ms")):
                time.sleep(POLL_S)
        else:
            aside = LOG_DIR / "stale_locks"
            aside.mkdir(parents=True, exist_ok=True)
            target = aside / ("heavy_job_%s.lock" % dt.datetime.now().strftime("%Y%m%d_%H%M%S"))
            shutil.move(str(LOCK_FILE), str(target))
            say("moved a stale heavy-job lock (dead pid %s) to %s" % (owner.get("pid"), target))
    if TEMP_DIR.is_dir():
        for entry in TEMP_DIR.iterdir():
            m = TEMP_FILE.match(entry.name)
            if m and not alive(m.group(1), m.group(2)):
                size = entry.stat().st_size / GIB
                entry.unlink()
                say("removed a dead run's temp file %s (%.2f GB)" % (entry.name, size))
                continue
            m = TEMP_RUN_DIR.match(entry.name)
            if m and entry.is_dir() and not alive(m.group(1)):
                shutil.rmtree(str(entry))
                say("removed a dead run's temp folder %s" % entry.name)


def wait_for_room(min_ram, min_disk):
    """Block until RAM and D: space are enough; say what to close while waiting."""
    told = 0.0
    while True:
        ram, disk = free_ram_gib(), free_disk_gib()
        if ram >= min_ram and disk >= min_disk:
            return
        if time.time() - told > 600:
            parts = []
            if ram < min_ram:
                parts.append("RAM %.1f GB free, need %.1f (biggest users: %s)" % (ram, min_ram, ram_hogs()))
            if disk < min_disk:
                parts.append("D: %.1f GB free, need %.1f (free %.1f GB on D:)" % (disk, min_disk, min_disk - disk))
            say("WAITING: " + "; ".join(parts) + ". It starts by itself when there is room.")
            beep()
            told = time.time()
        time.sleep(POLL_S)


class Progress(object):
    """Turns engine lines into one short progress line with an estimate."""

    def __init__(self):
        self.groups = None
        self.r30_done = 0
        self.r30_start = None
        self.last = ""

    def feed(self, line):
        m = RE_GROUPS.search(line)
        if m:
            self.groups = int(m.group(1))
        m = RE_CENSUS.search(line)
        if m:
            self.last = "reading data: %s of %s files" % (m.group(1), m.group(2))
            return self.last
        m = RE_R30.search(line)
        if m:
            self.r30_done += 1
            if m.group(2) != "counted":          # loaded from a saved checkpoint: counts, but no timing
                self.r30_loaded = getattr(self, "r30_loaded", 0) + 1
                self.last = "counting missing values: region %d of %s (loaded from save)" % (
                    self.r30_done, self.groups or "?")
                return None
            fresh = self.r30_done - getattr(self, "r30_loaded", 0)
            if self.r30_start is None:
                self.r30_start = time.time()
            text = "counting missing values: region %d of %s" % (self.r30_done, self.groups or "?")
            if self.groups and fresh > 1:
                per = (time.time() - self.r30_start) / (fresh - 1)
                left = per * (self.groups - self.r30_done)
                text += " (about %.1f h left for this stage)" % (left / 3600.0)
            self.last = text
            return text
        return None


def important(line):
    s = line.strip()
    if "[waiting]" in s:            # the engine's wait-for-room notes (runs/room.py): always shown, never filtered
        return True
    if not s or any(k in s for k in NOISY):
        return False
    return s.startswith("[") or "refused" in s or "Traceback" in s or "Error" in s or "finished" in s


_popup_open = {"on": False}


def _popup(text):
    """A Windows warning box on top of other windows (one at a time; never blocks the run)."""
    if _popup_open["on"]:
        return
    _popup_open["on"] = True
    try:
        ctypes.windll.user32.MessageBoxW(0, text, "treeroute: LOW RAM - close programs now", 0x00001030)
    except Exception:
        pass
    finally:
        _popup_open["on"] = False


def ram_watchdog(proc):
    """While the engine runs, warn loudly when free RAM gets low, before the engine has to stop."""
    import threading
    last = 0.0
    while proc.poll() is None:
        ram = free_ram_gib()
        if ram < WARN_RAM_GIB and time.time() - last > WARN_EVERY_S:
            msg = ("Only %.1f GB of RAM is free, so the engine may stop. Saved work is kept: a stop "
                   "during reading or counting costs the region in progress plus about 40 min of restart "
                   "setup; a stop in a later step costs that step. If a big program is listed, close it. "
                   "Biggest users: %s" % (ram, ram_hogs()))
            say("RAM WARNING: " + msg)
            beep()
            threading.Thread(target=_popup, args=(msg,), daemon=True).start()
            last = time.time()
        time.sleep(15)


def run_once(pkg, log):
    cmd = [sys.executable, "-W", WARN_FILTER, "-u", "-m", "treeroute", "run", "datasets/%s" % pkg]
    say("starting %s (full log: %s)" % (pkg, log))
    tail = []
    prog = Progress()
    with open(log, "a", encoding="utf-8", errors="replace") as fh:
        fh.write("\n===== %s start %s: %s\n" % (pkg, dt.datetime.now().isoformat(), " ".join(cmd)))
        proc = subprocess.Popen(cmd, cwd=str(ENGINE), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", bufsize=1)
        # The low-RAM warning popup was removed at the owner's request (2026-10-13); the engine's own
        # checks and this runner's automatic restart after a RAM stop remain.
        for line in proc.stdout:
            fh.write(line)
            fh.flush()
            tail = (tail + [line.rstrip()])[-120:]
            p = prog.feed(line)
            if p:
                say(p)
            elif important(line):
                print(line.rstrip()[:300], flush=True)
        code = proc.wait()
        fh.write("===== %s exit %s at %s\n" % (pkg, code, dt.datetime.now().isoformat()))
    return code, tail


def classify(code, tail):
    text = "\n".join(tail[-40:])
    if code == 0 and "run finished" in text:
        return "done", None
    if "refused" in text and "[G-DISK]" in text:
        m = RE_DISK.search(text)
        if m and "free" in text:
            return "disk", float(m.group(2))
        m = RE_RAM.search(text)
        if m:
            need = float(m.group(1) or m.group(2))
            a = RE_AVAIL.search(text)
            avail = float(a.group(1)) if a else 0.0
            return "ram", (need, avail)
        if "heavy engine job" in text or "heavy-job lock" in text or "orphan engine temp" in text:
            return "lock", None
    return "fail", None


def run_package(pkg, args, state):
    log = LOG_DIR / ("%s_%s.log" % (pkg, dt.datetime.now().strftime("%Y%m%d_%H%M")))
    need = state.get(pkg, {})
    for attempt in range(1, MAX_RETRIES + 1):
        if finished(pkg):
            say("%s is already finished; skipped" % pkg)
            return True
        # start_ram: free RAM needed BEFORE a start so that the step that stopped last time fits later,
        # when the engine itself holds memory (learned from the last RAM stop; see the RAM branch below)
        min_ram = max(args.min_ram, need.get("start_ram", 0))
        min_disk = max(args.min_disk, need.get("disk", 0) + 1.0)
        wait_for_room(min_ram, min_disk)
        start_free = free_ram_gib()
        clean_before_start()
        steps = saved_steps(latest_run_dir(pkg))
        if steps:
            say("%s: resuming; saved steps (skipped after the data stage): %s. NOTE: the data stage "
                "(census + missing-value count) always runs again first, to re-check the settings" % (pkg, ", ".join(steps)))
        keep_awake(True)
        code, tail = run_once(pkg, log)
        keep_awake(False)
        kind, amount = classify(code, tail)
        if kind == "done":
            say("%s FINISHED: %s" % (pkg, tail[-1] if tail else ""))
            beep()
            return True
        if kind == "ram":
            needed, avail = amount
            short = max(0.0, needed - avail)
            total = psutil.virtual_memory().total / GIB
            want = min(total - 0.5, start_free + short + 0.5)
            need["start_ram"] = max(need.get("start_ram", 0), want)
            state[pkg] = need
            save_state(state)
            say("%s stopped: a step needed %.1f GB of free RAM but only %.1f GB was free (short by %.1f GB). "
                "Saved steps are kept. It will restart by itself only when at least %.1f GB is free "
                "before the start (close big programs such as Opera)." % (pkg, needed, avail, short,
                                                                         need["start_ram"]))
            beep()
            continue
        if kind == "disk":
            need[kind] = amount
            state[pkg] = need
            save_state(state)
            say("%s stopped: not enough DISK (needs %.1f GB). Saved steps are kept; it restarts by itself "
                "when there is room (attempt %d of %d)." % (pkg, amount, attempt, MAX_RETRIES))
            beep()
            continue
        if kind == "lock":
            say("%s stopped on a lock or a dead run's temp files; cleaning and restarting" % pkg)
            continue
        fail = LOG_DIR / ("LAST_FAILURE_%s.txt" % pkg)
        fail.write_text("\n".join(tail), encoding="utf-8")
        say("%s STOPPED with an error (exit %s). The last lines are in %s. Paste them to Claude. "
            "The chain stops here." % (pkg, code, fail))
        beep()
        return False
    say("%s: gave up after %d attempts" % (pkg, MAX_RETRIES))
    return False


def status(pkgs):
    for pkg in pkgs:
        run_dir = latest_run_dir(pkg)
        line = "%-5s " % pkg
        if finished(pkg):
            print(line + "FINISHED (%s)" % run_dir.name)
            continue
        logs = sorted(LOG_DIR.glob("%s_*.log" % pkg)) if LOG_DIR.is_dir() else []
        live = any("treeroute" in " ".join(p.info.get("cmdline") or []) and "datasets/%s" % pkg in
                   " ".join(p.info.get("cmdline") or []) for p in psutil.process_iter(["cmdline"]))
        line += "RUNNING" if live else "not running"
        steps = saved_steps(run_dir)
        line += "; saved steps: %s" % (", ".join(steps) if steps else "none yet")
        if logs:
            prog, last = Progress(), ""
            for l in logs[-1].read_text(encoding="utf-8", errors="replace").splitlines():
                prog.feed(l)
                if important(l):
                    last = l.strip()[:160]
            if prog.last:
                line += "\n      progress: %s" % prog.last
            if last:
                line += "\n      last line: %s" % last
        print(line)
    print("free RAM %.1f GB, free D: %.1f GB" % (free_ram_gib(), free_disk_gib()))


def main():
    ap = argparse.ArgumentParser(description="Crash-safe headline runner with a short progress view.")
    ap.add_argument("packages", nargs="*", default=None)
    ap.add_argument("--status", action="store_true", help="print progress and exit")
    ap.add_argument("--min-ram", type=float, default=DEFAULT_MIN_RAM_GIB, help="GB of free RAM before a start")
    ap.add_argument("--min-disk", type=float, default=DEFAULT_MIN_DISK_GIB, help="GB free on D: before a start")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")  # never die on a character the console cannot show
    except Exception:
        pass
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if args.status:
        status(args.packages or ["pm25", "fire", "defo", "ndvi"])
        return 0
    state = load_state()
    packages = args.packages or ["fire", "defo", "ndvi"]
    for pkg in packages:
        if not run_package(pkg, args, state):
            return 1
    say("all done: %s" % ", ".join(packages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
