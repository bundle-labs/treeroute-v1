"""Run folders and phase resume, keyed by the run fingerprint (plan 7.1, G-NOOVERWRITE).

Run folder: <run_root>/<package>/<kind>/<yyyymmdd>_<fingerprint[:8]>/ with kind 'headline' or
'smoke'. The folder is found again by its fingerprint suffix, never by parsing the date, so a run
resumed on another day lands in the same folder.

  same fingerprint, unfinished  -> resume (phases already DONE are skipped)
  same fingerprint, finished    -> refused
  new fingerprint               -> a new folder

Inside a run folder:
  run.json                identity (fingerprint, package, kind), written once at creation
  phases/<name>/DONE      one per finished phase, written once, carries the fingerprint
  DONE.json               written once when the whole run finished

A DONE marker whose fingerprint differs from the current one stops the run: a resume never mixes
configurations.
"""

import datetime
import re
from pathlib import Path
from typing import NamedTuple

import treeroute
from treeroute.errors import ResumeRefusal
from treeroute.runs.atomic import read_json, write_json_once

RUN_KINDS = ("headline", "smoke")
RUN_IDENTITY = "run.json"
RUN_DONE = "DONE.json"
PHASES_DIR = "phases"
PHASE_DONE = "DONE"

_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")
_PHASE_NAME = re.compile(r"^[a-z0-9][a-z0-9_]*$")
_PACKAGE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$")


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _check_fingerprint(fingerprint):
    if not isinstance(fingerprint, str) or not _FINGERPRINT.match(fingerprint):
        raise ValueError("a run fingerprint is 64 lower-case hex characters, got %r" % (fingerprint,))


class RunHandle(NamedTuple):
    path: Path
    fingerprint: str
    state: str  # "new" or "resume"


def run_folder_name(fingerprint, today):
    _check_fingerprint(fingerprint)
    return "%s_%s" % (today.strftime("%Y%m%d"), fingerprint[:8])


def find_run_folders(kind_dir, fingerprint):
    """Existing run folders whose name ends with this fingerprint's first 8 characters."""
    kind_dir = Path(kind_dir)
    if not kind_dir.is_dir():
        return []
    suffix = "_" + fingerprint[:8]
    return sorted(p for p in kind_dir.iterdir() if p.is_dir() and p.name.endswith(suffix))


def open_run(run_root, package_name, kind, fingerprint, registry, today=None):
    """Create a new run folder, or return the unfinished one with this fingerprint.

    ``registry`` is a runs.registry.Registry; any folder under a protected root is refused.
    """
    _check_fingerprint(fingerprint)
    if kind not in RUN_KINDS:
        raise ValueError("run kind must be one of %s, got %r" % (RUN_KINDS, kind))
    if not _PACKAGE_NAME.match(package_name):
        raise ValueError("package name %r is not a safe folder name" % package_name)
    # The registry returns the resolved path it checked; only that path is read or created, so the
    # checked path and the written path cannot differ.
    kind_dir = registry.assert_writable(Path(run_root) / package_name / kind)
    matches = find_run_folders(kind_dir, fingerprint)
    if len(matches) > 1:
        raise ResumeRefusal("G-NOOVERWRITE", "more than one run folder matches fingerprint %s: %s"
                            % (fingerprint[:8], ", ".join(str(m) for m in matches)),
                            fix="inspect these folders by hand; the engine never picks one")
    if matches:
        folder = matches[0]
        ident_path = folder / RUN_IDENTITY
        if not ident_path.is_file():
            raise ResumeRefusal("G-NOOVERWRITE", "%s has no %s, so its fingerprint is unknown"
                                % (folder, RUN_IDENTITY), fix="inspect the folder by hand")
        ident = read_json(ident_path)
        if ident.get("fingerprint") != fingerprint:
            raise ResumeRefusal("G-FINGERPRINT", "%s belongs to fingerprint %s, not %s (8-character "
                                "name collision)" % (folder, ident.get("fingerprint"), fingerprint),
                                fix="inspect the folder by hand")
        if (folder / RUN_DONE).exists():
            raise ResumeRefusal("G-NOOVERWRITE", "the run with this fingerprint already finished: %s"
                                % folder, fix="nothing to do; its outputs are final")
        return RunHandle(folder, fingerprint, "resume")
    today = today or datetime.date.today()
    folder = registry.assert_writable(kind_dir / run_folder_name(fingerprint, today))
    folder.mkdir(parents=True, exist_ok=False)
    # re-check after creation: the new folder must still resolve to itself and stay writable
    if registry.assert_writable(folder) != folder:
        raise ResumeRefusal("G-NOOVERWRITE", "the new run folder %s resolves elsewhere after it was "
                            "created (a junction or link appeared in its path)" % folder,
                            fix="inspect the run root by hand")
    write_json_once(folder / RUN_IDENTITY, {
        "fingerprint": fingerprint, "package": package_name, "kind": kind,
        "created_utc": _utc_now(), "engine_version": treeroute.__version__})
    return RunHandle(folder, fingerprint, "new")


def mark_run_finished(run_dir, fingerprint, summary=None):
    _check_fingerprint(fingerprint)
    write_json_once(Path(run_dir) / RUN_DONE, {"fingerprint": fingerprint,
                                               "finished_utc": _utc_now(),
                                               "summary": summary or {}})


class Phases(object):
    """Phase markers of one run folder, all bound to one fingerprint."""

    def __init__(self, run_dir, fingerprint):
        _check_fingerprint(fingerprint)
        self.run_dir = Path(run_dir)
        self.fingerprint = fingerprint

    def _marker(self, name):
        if not isinstance(name, str) or not _PHASE_NAME.match(name):
            raise ValueError("phase names are lower-case letters, digits and '_', got %r" % (name,))
        return self.run_dir / PHASES_DIR / name / PHASE_DONE

    def done(self, name):
        """True if the phase finished under this fingerprint. A different fingerprint stops."""
        marker = self._marker(name)
        if not marker.is_file():
            return False
        info = read_json(marker)
        if info.get("fingerprint") != self.fingerprint:
            raise ResumeRefusal(
                "G-FINGERPRINT", "phase %r in %s was finished by fingerprint %s, not %s"
                % (name, self.run_dir, info.get("fingerprint"), self.fingerprint),
                fix="a resume never mixes configurations; start a new run")
        return True

    def mark_done(self, name, summary=None):
        marker = self._marker(name)
        marker.parent.mkdir(parents=True, exist_ok=True)
        write_json_once(marker, {"fingerprint": self.fingerprint, "phase": name,
                                 "finished_utc": _utc_now(), "summary": summary or {}})

    def completed(self):
        root = self.run_dir / PHASES_DIR
        if not root.is_dir():
            return []
        return sorted(p.name for p in root.iterdir() if (p / PHASE_DONE).is_file())
