"""The ONE place that imports the signed common rival package (SPEC_HUMAN.txt 1.2; ruling AB, Q2.HQ1 a).

- sys.dont_write_bytecode is set BEFORE the import: an import must not write __pycache__ into the common build.
- The common build root is put first on sys.path; `rivals` must come from there (never a legacy rivals.py).
- The harness code hash (harness.harness_code_sha) must equal the config's pin AND, where a common board of the run
  exists, that board's harness_code_sha256 must be the pin or an older harness the owner accepted in writing
  (config common_harness_accepted_boards; ruling AG, Part 613). Anything else is a loud refusal (PLAN R4).

Also here: the human command context (heavy-job lock + RAM watchdog, the pattern of harness._Command) and the human
tool's own code hash.
"""
# Provenance: SPEC_HUMAN.txt 1.2, 1.11, 1.13; D:/treeroute/rivals_build/rivals/harness.py:183-189 (code hash),
# :243 Engine, :261-332 Ctx, :379-402 Watchdog, :418-446 _Command; layout.py:84 load_roots, :108 import_engine.

import os
import sys
import time

sys.dont_write_bytecode = True

from pathlib import Path                                         # noqa: E402
from typing import Any, Dict, Optional, Tuple                     # noqa: E402

from rivals_human import config as C                             # noqa: E402

_STATE: Dict[str, Any] = {"LY": None, "H": None, "root": None}


class HumanRefusal(RuntimeError):
    """A human-tool rule refused. Nothing catches it (fail loud)."""


def refuse(message: str, fix: Optional[str] = None):
    raise HumanRefusal(message + ("" if not fix else "  FIX: " + fix))


def load(cfg: Any = None) -> Tuple[Any, Any]:
    """(layout, harness) of the signed common package, imported read-only and checked against the pinned hash."""
    cfg = C.load_config(cfg)
    root = Path(str(cfg["common_build_root"])).resolve()
    if _STATE["H"] is not None:
        if _STATE["root"] != root:
            refuse("the common package was imported from %s; this config names %s" % (_STATE["root"], root))
        check_pin(_STATE["H"], cfg)
        return _STATE["LY"], _STATE["H"]
    if not (root / "rivals" / "harness.py").is_file():
        refuse("%s holds no rivals/harness.py (the signed common package)" % root)
    sys.dont_write_bytecode = True
    if str(root) in sys.path:
        sys.path.remove(str(root))
    sys.path.insert(0, str(root))
    loaded = sys.modules.get("rivals")
    if loaded is not None:
        got = Path(getattr(loaded, "__file__", "") or "").resolve().parent
        if os.path.normcase(str(got)) != os.path.normcase(str(root / "rivals")):
            refuse("a module 'rivals' is already imported from %s, not the common package %s" % (got, root / "rivals"))
    from rivals import layout as LY
    from rivals import harness as H
    got = Path(H.__file__).resolve().parent
    if os.path.normcase(str(got)) != os.path.normcase(str(root / "rivals")):
        refuse("rivals.harness was imported from %s, not from %s" % (got, root / "rivals"))
    if tuple(LY.ROOT_KEYS) != tuple(C.ROOT_KEYS):
        refuse("the common layout's ROOT_KEYS %s differ from the human config's %s" % (LY.ROOT_KEYS, C.ROOT_KEYS))
    _STATE.update(LY=LY, H=H, root=root)
    check_pin(H, cfg)
    return LY, H


def check_pin(H: Any, cfg: Any) -> str:
    sha = H.harness_code_sha()
    want = str(cfg["common_harness_sha256"])
    if sha != want:
        refuse("the common harness code sha256 is %s; the human tool is pinned to %s (PLAN R4)" % (sha, want),
               fix="re-pin only after a signed change of the common harness (a new Part)")
    return sha


def check_common_board(H: Any, cfg: Any, package: str, run_name: str, required: bool = True) -> Optional[Dict[str, Any]]:
    """The common board of the run: its harness_code_sha256 must be the pin (spec 1.2) or an older harness the owner
    accepted (ruling AG5; then its legal range must be bounded). Returns {path, sha256, board, harness_accepted_as}
    or None (no board yet, only when not required)."""
    p = C.common_board_dir(cfg, package, run_name) / C.COMMON_BOARD_FILE
    if not p.is_file():
        if required:
            refuse("the common board %s does not exist; the human board is tied to it (PROT H0)" % p,
                   fix="init the common board of this run first (its export must exist)")
        return None
    board = C.read_json(p)
    accepted = board_harness_ok(cfg, board.get("harness_code_sha256"), p, board.get("run", {}).get("legal"))
    if board.get("run", {}).get("name") not in (None, run_name):
        refuse("the common board %s is of run %s, not %s" % (p, board["run"].get("name"), run_name))
    return {"path": str(p), "sha256": H.sha256_file(p), "board": board, "harness_accepted_as": accepted}


def board_harness_ok(cfg: Any, sha: Any, where: Any, legal: Any = None) -> Optional[str]:
    """A common board's harness: None when it is the pin; the owner's written reason when it is an older harness the
    owner accepted (config common_harness_accepted_boards; ruling AG5), which also needs the board's legal range
    `legal` to be bounded at both ends (the premise of AG5: the Part 608 change only reads an open bound differently);
    any other harness refuses."""
    pin = str(cfg["common_harness_sha256"])
    if str(sha) == pin:
        return None
    acc = cfg.accepted_board_harnesses() if hasattr(cfg, "accepted_board_harnesses") else {}
    if str(sha) in acc:
        if not isinstance(legal, (list, tuple)) or len(legal) != 2 or any(v is None for v in legal):
            refuse("the common board %s was made under the accepted older harness %s, but its legal range %r is not "
                   "bounded at both ends; ruling AG5 accepts only bounded-target boards" % (where, str(sha)[:16], legal),
                   fix="re-make this common board under the pinned harness")
        return acc[str(sha)]
    refuse("the common board %s was made under harness %s; the human tool is pinned to %s and accepts no other"
           % (where, str(sha)[:16], pin[:16]),
           fix="only an owner ruling may list an older harness in common_harness_accepted_boards")


def tool_code_sha() -> str:
    """sha256 over [relative name, sha256] of rivals_human/*.py then adapters/*.py (the recipe of
    harness.harness_code_sha, H:183-189, with the folder in the name so two folders never collide)."""
    import hashlib
    import json
    parts = []
    for p in C.code_files():
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        parts.append(["%s/%s" % (p.parent.name, p.name), h])
    text = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode("ascii")).hexdigest()


# ===================================================================================================== commands
class HumanCtx(object):
    """One command's context (the harness Ctx with the human log and status file names). Built on H.Ctx so every
    write goes through the engine registry (Ctx.mkdir / replace_* -> Registry.assert_writable, H:256-291)."""

    def __new__(cls, cfg: Any, out: Any, command: str):
        LY, H = load(cfg)

        class _Ctx(H.Ctx):
            def log(self, stage: str, learner: str = "", trial: str = "", seconds: Optional[float] = None,
                    message: str = "", echo: bool = True):
                self.rss()
                line = "%s | %s | %s | %s | %s | %s | %.2f GiB | %s" % (
                    H.utc_now(), self.command, stage, learner or "-", trial or "-",
                    "-" if seconds is None else "%.1f s" % seconds, self.peak_rss / float(1 << 30), message)
                if self.out.is_dir():
                    lp = self.out / C.LOG_FILE
                    if not lp.is_file():
                        LY.append_line(lp, H.LOG_HEADER, self.eng.registry)
                    LY.append_line(lp, line, self.eng.registry)
                    self.status(stage, learner, trial)
                if echo:
                    print(line, flush=True)

            def status(self, stage: str, learner: str = "", trial: str = ""):
                rec = {"command": self.command, "stage": stage, "rival": learner, "trial": trial,
                       "utc": H.utc_now(), "pid": os.getpid(), "peak_rss_bytes": self.peak_rss}
                self.replace_json(self.out / C.STATUS_FILE, rec)

        hcfg = C.load_config(cfg)
        hc = H.load_config(hcfg.roots_mapping())
        eng = H.Engine(hc)
        ctx = _Ctx(hc, eng, Path(out), command)
        ctx.hcfg = hcfg
        ctx.H, ctx.LY = H, LY
        return ctx


class HumanCommand(object):
    """Context manager for one heavy command: config, engine, the engine's heavy-job lock (from the config's machine
    file), the RAM watchdog (harness.Watchdog), a done / FAILED log line. need_file: a file that must exist in out."""

    def __init__(self, name: str, out: Any, cfg: Any, need_file: Optional[str] = None):
        self.name, self.out, self.cfg, self.need_file = name, Path(out), cfg, need_file

    def __enter__(self):
        LY, H = load(self.cfg)
        self.ctx = HumanCtx(self.cfg, self.out, self.name)
        if self.need_file and not (self.out / self.need_file).is_file():
            refuse("%s holds no %s" % (self.out, self.need_file), fix="run init first")
        self.lock = self.ctx.eng.preflight.HeavyJobLock(self.ctx.eng.machine.temp_dir)
        self.lock.acquire()
        self.dog = H.Watchdog(self.ctx, self.lock)
        self.dog.start()
        self.t0 = time.time()
        return self.ctx

    def __exit__(self, exc_type, exc, tb):
        self.dog.stop()
        try:
            if self.ctx.out.is_dir():
                if exc is not None:
                    self.ctx.log("FAILED", message="%s: %s" % (type(exc).__name__, exc))
                else:
                    self.ctx.log("done", seconds=time.time() - self.t0)
        finally:
            self.lock.release()
        return False


def refusal_types() -> tuple:
    """The refusals the command line prints as one plain line."""
    types = [HumanRefusal, C.ConfigRefusal]
    if _STATE["H"] is not None:
        types += [_STATE["H"].HarnessRefusal, _STATE["LY"].LayoutRefusal]
    try:
        from treeroute.errors import RefusedError
        types.append(RefusedError)
    except ImportError:
        pass
    return tuple(types)
