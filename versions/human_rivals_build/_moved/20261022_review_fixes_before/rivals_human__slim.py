"""The slim copy of a common export (SPEC_HUMAN.txt 1.3; PLAN ATTENTION 3; PROT ATTENTION H-A2) and its reader.

`slim` keeps what the human rivals need from one lead of a common export BEFORE the owner deletes it: keys, role
flags, train y, the normals per link, the history block, the problem's named extra columns, the guard-side block, the
test keys (no y: the export has none) and units.parquet. Every value is read through the common harness's verified
reader (ExportLead.read_table -> ExportLead.path(verify=True), H:737-757). One group file at a time (RAM < 2 GB).

`SlimLead.read_set(name)` gives the keys, y (train sets), normals by link, history and extras with the guard-side
substitution of ExportLead._group_block (H:859-877). The test set is readable only with a valid human lock (A2).
"""
# Provenance: SPEC_HUMAN.txt 1.3, A2, A3, A5; harness.py:577 export_identity, :595 check_accept_seal, :626
# export_content_sha, :646-925 ExportLead (:778-812 the cut rules, re-implemented here as check_rows and tested equal),
# :1490-1510 keep_export_files (bytes copy of units.parquet and the manifest); layout.py:174-175 role flags.

import datetime as _dt
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from rivals_human import config as C
from rivals_human.common import HumanCommand, check_common_board, load, refuse

_VERIFIED: Dict[str, tuple] = {}


# ===================================================================================================== season keys
def season_keys(times: Any, season: Mapping[str, Any]) -> np.ndarray:
    """R2's season key of each time (fit/context.py:264-277): grids ((step - 1) mod steps per year) + 1; a table
    package (event_month) the calendar month of the day ordinal; one class on annual or constant data."""
    t = np.asarray(times, dtype=np.int64)
    kind = (season or {}).get("kind")
    if kind == "event_month":
        return np.array([_dt.date.fromordinal(int(v)).month for v in t.tolist()], dtype=np.int64)
    if kind in ("month_of_year", "composite_number", "step_position_in_year", "constant"):
        per_year = int((season or {}).get("steps_per_year") or 1)
        if per_year < 1:
            refuse("season steps_per_year %r is below 1" % per_year)
        return np.mod(t - 1, per_year) + 1
    refuse("unknown season key kind %r (derived R2)" % (kind,))


def run_season(run: Any) -> Dict[str, Any]:
    v = run.derived.get("R2", {}).get("value") or {}
    return {"kind": v.get("kind"), "steps_per_year": v.get("steps_per_year")}


def run_offset(run: Any) -> int:
    """R17 start_offset_steps (0 when the run keeps none, e.g. the neighbour kind's empty R17)."""
    v = run.derived.get("R17", {}).get("value") or {}
    return int(v.get("start_offset_steps") or 0)


def history_columns(run: Any) -> List[str]:
    return [C.X_PREFIX + h for h in (run.plan.get("history_columns") or [])]


# ===================================================================================================== cut rules
def check_rows(run: Any, lead: int, set_name: str, keys: pd.DataFrame, where: Any) -> None:
    """The cut rule of a set, re-implemented from ExportLead._check_rows (H:778-812): refit <= fit cut; tune /
    guardfit <= the lead's guard cut; inner / guard after the nowcast guard cut and <= the fit cut; test after the
    fit cut; issue = time - lead and the lead on every row."""
    if not len(keys):
        return
    t = keys["time"].to_numpy(np.int64)
    fit_cut = int(run.cuts[int(lead)]["fit_cut"])
    guard_cut = int(run.cuts[int(lead)]["guard_cut"])
    guard0 = int(run.cuts[0]["guard_cut"])
    if set_name == "refit":
        bad, rule = t > fit_cut, "at or before the fit cut %d" % fit_cut
    elif set_name in ("tune", "guardfit"):
        bad, rule = t > guard_cut, "at or before the guard cut %d" % guard_cut
    elif set_name in ("inner", "guard"):
        bad = (t <= guard0) | (t > fit_cut)
        rule = "after the nowcast guard cut %d and at or before the fit cut %d" % (guard0, fit_cut)
    elif set_name == "test":
        bad, rule = t <= fit_cut, "after the fit cut %d" % fit_cut
    else:
        refuse("internal: unknown set %s" % set_name)
    if bad.any():
        refuse("%s: %d %s row(s) break the cut rule (%s); first time %d"
               % (where, int(bad.sum()), set_name, rule, int(t[bad][0])),
               fix="the export or slim copy is wrong; re-export / re-slim it and report the defect")
    if "issue" in keys.columns and "lead" in keys.columns:
        iss = keys["issue"].to_numpy(np.int64)
        ld = keys["lead"].to_numpy(np.int64)
        if not np.array_equal(iss, t - ld):
            refuse("%s: %s rows where issue != time - lead" % (where, set_name))
        if (ld != int(lead)).any():
            refuse("%s: %s rows of another lead" % (where, set_name))


def guard_flags(lead: int):
    return ("r_tune", "r_inner") if int(lead) == 0 else ("r_guardfit", "r_guard")


SET_FLAG = {"refit": "r_refit", "tune": "r_tune", "inner": "r_inner", "guardfit": "r_guardfit", "guard": "r_guard"}
GUARD_SIDE_SETS = ("tune", "inner", "guardfit", "guard")


# ===================================================================================================== slim
def extra_columns(registry: Mapping[str, Any]) -> List[str]:
    """The union of the registry's slim_extra_columns, in first-seen order."""
    out: List[str] = []
    for r in registry["rivals"]:
        for c in r.get("slim_extra_columns") or []:
            if c not in out:
                out.append(str(c))
    return out


def slim(run_folder: Any, export_dir: Any, config: Any = None) -> Path:
    """Copy the human tool's columns out of one export lead (spec 1.3). Returns the slim lead folder."""
    cfg = C.load_config(config)
    LY, H = load(cfg)
    run = H.Run(run_folder)
    export_dir = Path(export_dir)
    mpath = export_dir / LY.EXPORT_MANIFEST
    if not mpath.is_file():
        refuse("export %s has no %s (the export writes it LAST)" % (export_dir, LY.EXPORT_MANIFEST),
               fix="finish the export of this lead first")
    lead = int(json.loads(mpath.read_bytes().decode("utf-8")).get("lead", -1))
    if lead not in run.cuts:
        refuse("export %s is lead %d; the run's leads are %s" % (export_dir, lead, run.leads))
    out_run = C.slim_run_dir(cfg, run.package, run.name)
    out = C.slim_lead_dir(cfg, run.package, run.name, lead)
    with HumanCommand("slim", out_run, cfg) as ctx:
        ctx.mkdir(out_run)
        ex = H.ExportLead(export_dir, lead, run)
        H.check_accept_seal(ex, run)
        ident = H.export_identity(ex.manifest)
        cb = check_common_board(H, cfg, run.package, run.name, required=False)
        if cb is not None:
            want = cb["board"]["export"]["identity"]
            diff = sorted(k for k in set(want) | set(ident) if H._clean(want.get(k)) != H._clean(ident.get(k)))
            if diff:
                refuse("export %s differs from the common board's export identity in %s" % (export_dir, diff))
        registry = C.load_registry(cfg, run.package)
        extras = extra_columns(registry)
        hist = history_columns(run)
        missing = [c for c in extras + hist if c not in ex.train_columns]
        if missing:
            refuse("the export %s holds no column %s (named by the registry's slim_extra_columns or plan.json "
                   "history_columns; A5)" % (export_dir, missing),
                   fix="OWNER ITEM: the columns must come from another source (spec A5: a panel pass)")
        man_path = out / C.SLIM_MANIFEST
        if man_path.is_file():
            old = C.read_json(man_path)
            if old.get("source_export_content_sha256") != ex.content_sha:
                refuse("%s exists for another export (content %s vs %s)"
                       % (man_path, str(old.get("source_export_content_sha256"))[:16], ex.content_sha[:16]),
                       fix="move the slim lead folder aside to slim again")
            ctx.log("slim", message="lead %d is already slimmed (%s); nothing written" % (lead, man_path))
            return out
        ctx.mkdir(out)
        flags = list(H.FLAGS)
        nfit = [H.NFIT_PREFIX + l for l in run.links]
        ngd = [H.NGD_PREFIX + l for l in run.links]
        train_cols = _uniq(list(H.KEYS) + flags + ["y"] + nfit + hist + extras)
        h_cols = list(ex.h_cols)
        files: List[Dict[str, Any]] = []
        t0 = time.time()
        stems = {part: sorted(ex._entry.get(part, {})) for part in (H.TRAIN_DIR, H.GUARD_DIR, H.TEST_DIR)}
        for part in (H.TRAIN_DIR, H.GUARD_DIR, H.TEST_DIR):
            for stem in stems[part]:
                entry = ex._entry[part][stem]
                rec = _slim_file(ctx, H, ex, run, lead, part, stem, entry, out, train_cols, h_cols, ngd, nfit,
                                 hist, extras)
                files.append(rec)
        ctx.log("slim", seconds=time.time() - t0, message="lead %d: %d files copied" % (lead, len(files)))
        # units.parquet and the export manifest: bytes, checked (as H.keep_export_files, H:1490-1510)
        ubytes = ex.path(H.UNITS_PART, Path(H.UNITS_FILE).stem).read_bytes()
        ctx.replace_bytes(out / H.UNITS_FILE, ubytes)
        ctx.replace_bytes(out / LY.EXPORT_MANIFEST, ex.manifest_bytes)
        counts: Dict[str, int] = {}
        for f in files:
            for k, v in (f.get("counts") or {}).items():
                counts[k] = counts.get(k, 0) + int(v)
        doc = {"format": C.FORMAT_SLIM, "lead": lead, "run": {"folder": str(run.folder), "name": run.name,
                                                             "fingerprint": run.fingerprint, "package": run.package},
               "source_export_dir": str(export_dir), "source_export_manifest_sha256": ex.manifest_sha,
               "source_export_content_sha256": ex.content_sha, "source_export_files_sha256": ex.files_sha(),
               "export_identity": ident, "common_harness_sha256": H.harness_code_sha(),
               "common_board": None if cb is None else {"path": cb["path"], "sha256": cb["sha256"]},
               "cuts": {"fit_cut": int(run.cuts[lead]["fit_cut"]), "guard_cut": int(run.cuts[lead]["guard_cut"])},
               "links": list(run.links), "c": ex.manifest.get("c"), "legal": list(run.legal),
               "season": ex.manifest.get("season") or run_season(run), "offset_steps": run_offset(run),
               "columns": {"keys": list(H.KEYS), "flags": flags, "nfit": nfit, "ngd": ngd, "history": hist,
                           "h": h_cols, "extras": extras},
               "files": files, "counts": counts, "export_counts": ex.manifest.get("counts"),
               "units": {"path": H.UNITS_FILE, "sha256": H.sha256_bytes(ubytes)},
               "export_manifest": {"path": LY.EXPORT_MANIFEST, "sha256": ex.manifest_sha},
               "registry": {"path": registry["_file"], "sha256": H.sha256_file(registry["_file"])},
               "utc": H.utc_now()}
        for role, n in (ex.manifest.get("counts") or {}).items():
            if role in counts and int(counts[role]) != int(n):
                refuse("lead %d: the slim copy holds %d %s rows; the export manifest counts %d"
                       % (lead, counts[role], role, int(n)))
        ctx.write_once_json(man_path, doc)
        ctx.log("slim", message="lead %d done: %s" % (lead, ", ".join("%s %d" % kv for kv in sorted(counts.items()))))
        return out


def _uniq(cols: Sequence[str]) -> List[str]:
    out: List[str] = []
    for c in cols:
        if c not in out:
            out.append(c)
    return out


def _slim_file(ctx, H, ex, run, lead, part, stem, entry, out, train_cols, h_cols, ngd, nfit, hist, extras):
    rel = str(entry["path"])
    dest = out / rel
    prog = out / C.SLIM_PROGRESS / part / (stem + ".json")
    if prog.is_file() and dest.is_file():
        pr = C.read_json(prog)
        if pr.get("source_sha256") == str(entry["sha256"]) and H.sha256_file(dest) == pr.get("sha256"):
            return pr
    where = "%s/%s" % (part, stem)
    counts: Dict[str, int] = {}
    if part == H.TRAIN_DIR:
        t = ex.read_table(part, stem, train_cols)
        if t.duplicated(subset=["unit", "time", "issue"]).any():
            refuse("export %s %s names a (unit, time, issue) twice" % (ex.dir, where))
        for s, flag in SET_FLAG.items():
            m = t[flag].to_numpy(bool)
            if m.any():
                check_rows(run, lead, s, t.loc[m, list(H.KEYS)], "export %s %s" % (ex.dir, where))
                counts[s] = int(m.sum())
        y = t["y"].to_numpy(np.float64)
        anyrole = np.zeros(len(t), dtype=bool)
        for flag in H.FLAGS:
            anyrole |= t[flag].to_numpy(bool)
        if not np.isfinite(y[anyrole]).all():
            refuse("export %s %s holds %d missing labels on role rows" % (ex.dir, where,
                                                                         int((~np.isfinite(y[anyrole])).sum())))
        frame = t[train_cols]
    elif part == H.GUARD_DIR:
        cols = list(H.KEYS) + h_cols + ngd
        frame = ex.read_table(part, stem, cols)
        counts["guardside"] = int(len(frame))
    else:
        path = ex.path(part, stem)
        names = pq.read_schema(path).names
        if "y" in names:
            refuse("export test file %s holds a y column; test labels never leave the vault" % path)
        cols = _uniq(list(H.KEYS) + (["saved_row"] if "saved_row" in names else []) + nfit + hist + extras)
        miss = [c for c in cols if c not in names]
        if miss:
            refuse("export test file %s lacks %s" % (path, miss))
        frame = ex.read_table(part, stem, cols)
        if frame.duplicated(subset=["unit", "time", "issue"]).any():
            refuse("export %s %s names a (unit, time, issue) twice" % (ex.dir, where))
        check_rows(run, lead, "test", frame[list(H.KEYS)], "export %s %s" % (ex.dir, where))
        counts["test"] = int(len(frame))
    ctx.mkdir(dest.parent)
    ctx.write_parquet(dest, frame.reset_index(drop=True))
    rec = {"part": part, "group": str(entry.get("group")), "stem": stem, "path": rel,
           "source_path": rel, "source_sha256": str(entry["sha256"]), "source_rows": int(entry["rows"]),
           "sha256": H.sha256_file(dest), "rows": int(len(frame)), "columns": list(frame.columns),
           "counts": counts}
    if int(entry["rows"]) != len(frame):
        refuse("export %s %s: %d rows read, the manifest lists %d" % (ex.dir, where, len(frame), int(entry["rows"])))
    ctx.mkdir(prog.parent)
    ctx.replace_json(prog, rec)
    return rec


# ===================================================================================================== the reader
@dataclass
class SlimSet:
    """One set of one slim lead: keys, y (train sets; None for test), {link: normal}, the history block (x__ names,
    guard-side substituted), the extra columns."""
    name: str
    keys: pd.DataFrame
    y: Optional[np.ndarray]
    normal: Dict[str, np.ndarray]
    history: pd.DataFrame
    extras: pd.DataFrame


class SlimLead(object):
    """One slim lead folder (read-only), checked against its run."""

    def __init__(self, folder: Any, run: Any):
        self.dir = Path(folder)
        mp = self.dir / C.SLIM_MANIFEST
        if not mp.is_file():
            refuse("%s has no %s (slim writes it LAST)" % (self.dir, C.SLIM_MANIFEST),
                   fix="run slim for this lead (owner command) before the export is deleted")
        self.manifest_bytes = mp.read_bytes()
        self.manifest = json.loads(self.manifest_bytes.decode("utf-8"))
        m = self.manifest
        if m.get("format") != C.FORMAT_SLIM:
            refuse("%s is not a %s file" % (mp, C.FORMAT_SLIM))
        self.run = run
        if m["run"]["fingerprint"] != run.fingerprint:
            refuse("slim %s is of run %s, not %s" % (self.dir, m["run"]["fingerprint"][:16], run.fingerprint[:16]))
        self.lead = int(m["lead"])
        for k in ("fit_cut", "guard_cut"):
            if int(m["cuts"][k]) != int(run.cuts[self.lead][k]):
                refuse("slim %s %s %r differs from the run's R11 %r" % (self.dir, k, m["cuts"][k],
                                                                       run.cuts[self.lead][k]))
        if list(m["links"]) != list(run.links):
            refuse("slim %s links %s differ from the run's %s" % (self.dir, m["links"], run.links))
        self.links = list(run.links)
        self.season = m.get("season") or run_season(run)
        cols = m["columns"]
        self.history = list(cols["history"])
        self.h_cols = list(cols["h"])
        self.extras_cols = list(cols["extras"])
        self.files: Dict[str, Dict[str, Mapping[str, Any]]] = {}
        for f in m["files"]:
            self.files.setdefault(f["part"], {})[f["stem"]] = f
        self.train_stems = sorted(self.files.get("train", {}))
        self.test_stems = sorted(self.files.get("test", {}))
        self.guard_stems = set(self.files.get("guardside", {}))
        self.manifest_sha = _sha_bytes(self.manifest_bytes)

    # --- verified access -------------------------------------------------------------------------
    def path(self, part: str, stem: str) -> Path:
        e = self.files.get(part, {}).get(stem)
        if e is None:
            refuse("slim %s: %s/%s is not listed in its manifest" % (self.dir, part, stem))
        p = self.dir / str(e["path"])
        if not p.is_file():
            refuse("slim %s: the listed file %s is missing" % (self.dir, p))
        st = os.stat(str(p))
        key = os.path.normcase(str(p.resolve()))
        hit = _VERIFIED.get(key)
        if hit is None or hit != (int(st.st_size), int(st.st_mtime_ns), str(e["sha256"])):
            sha = _sha_file(p)
            if sha != str(e["sha256"]):
                refuse("slim file %s has sha256 %s; its manifest lists %s" % (p, sha[:16], str(e["sha256"])[:16]),
                       fix="slim this lead again from its export")
            _VERIFIED[key] = (int(st.st_size), int(st.st_mtime_ns), sha)
        return p

    def _read(self, part: str, stem: str, columns: Sequence[str]) -> pd.DataFrame:
        with pq.ParquetFile(str(self.path(part, stem))) as pf:
            return pf.read(columns=list(columns)).to_pandas()

    def units(self) -> pd.DataFrame:
        p = self.dir / str(self.manifest["units"]["path"])
        if _sha_file(p) != self.manifest["units"]["sha256"]:
            refuse("slim %s: units.parquet does not match its manifest" % self.dir)
        return pq.read_table(str(p)).to_pandas()

    def export_manifest(self) -> Dict[str, Any]:
        p = self.dir / str(self.manifest["export_manifest"]["path"])
        b = p.read_bytes()
        if _sha_bytes(b) != self.manifest["export_manifest"]["sha256"]:
            refuse("slim %s: the kept export manifest does not match" % self.dir)
        return json.loads(b.decode("utf-8"))

    def file_shas(self) -> Dict[str, str]:
        return {"%s/%s" % (f["part"], f["stem"]): f["sha256"] for f in self.manifest["files"]}

    # --- keys -------------------------------------------------------------------------------------
    def keys(self, name: str, lock: Any = None) -> pd.DataFrame:
        """Keys (no y, no feature) of a set: refit, tune, inner, guardfit, guard, train (every train-file row), test
        (test keys only; no lock needed: keys are not labels), all (train + test)."""
        keys = list(C.KEYS)
        if name in SET_FLAG or name == "train":
            parts = []
            for s in self.train_stems:
                cols = keys + ([SET_FLAG[name]] if name in SET_FLAG else [])
                t = self._read("train", s, cols)
                if name in SET_FLAG:
                    t = t.loc[t[SET_FLAG[name]].to_numpy(bool), keys]
                    check_rows(self.run, self.lead, name, t, "slim %s train/%s" % (self.dir, s))
                parts.append(t[keys])
            return _concat(parts, keys)
        if name == "test":
            parts = [self._read("test", s, keys) for s in self.test_stems]
            k = _concat(parts, keys)
            check_rows(self.run, self.lead, "test", k, "slim %s test" % self.dir)
            return k
        if name == "all":
            return pd.concat([self.keys("train"), self.keys("test")], ignore_index=True)
        refuse("unknown set %r" % name)

    def count(self, name: str) -> int:
        return int(len(self.keys(name)))

    # --- sets -------------------------------------------------------------------------------------
    def read_set(self, name: str, lock: Any = None, with_y: bool = True, extras: bool = True) -> SlimSet:
        """A set's keys, y, normals, history and extras. Guard-side sets take h__ for the history and ngd__ for the
        normal (H:859-877). The test set needs a valid human lock token (lockfile.verify_lock); with_y=False drops y."""
        keys = list(C.KEYS)
        if name == "test":
            from rivals_human import lockfile
            lockfile.require_token(lock, self.run.fingerprint, "reading the slim test rows")
            cols = keys + ["nfit__" + l for l in self.links] + self.history + (self.extras_cols if extras else [])
            parts = [self._read("test", s, _uniq(cols)) for s in self.test_stems]
            t = _concat(parts, _uniq(cols))
            check_rows(self.run, self.lead, "test", t[keys], "slim %s test" % self.dir)
            return SlimSet(name, t[keys].reset_index(drop=True), None,
                           {l: t["nfit__" + l].to_numpy(np.float64) for l in self.links},
                           t[self.history].reset_index(drop=True),
                           t[self.extras_cols].reset_index(drop=True) if extras else pd.DataFrame(index=t.index))
        if name not in SET_FLAG:
            refuse("unknown set %r" % name)
        flag = SET_FLAG[name]
        guard_side = name in GUARD_SIDE_SETS
        if guard_side and flag not in guard_flags(self.lead):
            refuse("set %s is not a guard-side set at lead %d" % (name, self.lead))
        out_k, out_y, out_h, out_e = [], [], [], []
        out_n: Dict[str, List[np.ndarray]] = {l: [] for l in self.links}
        cols = _uniq(keys + ["r_refit", "r_tune", "r_inner", "r_guardfit", "r_guard", "y"]
                     + ["nfit__" + l for l in self.links] + self.history + (self.extras_cols if extras else []))
        for s in self.train_stems:
            t = self._read("train", s, cols)
            mask = t[flag].to_numpy(bool)
            if not mask.any():
                continue
            k = t.loc[mask, keys].reset_index(drop=True)
            check_rows(self.run, self.lead, name, k, "slim %s train/%s" % (self.dir, s))
            hist = t.loc[mask, self.history].reset_index(drop=True)
            if guard_side:
                union = np.zeros(len(t), dtype=bool)
                for f in guard_flags(self.lead):
                    union |= t[f].to_numpy(bool)
                if s not in self.guard_stems:
                    refuse("slim %s: train/%s holds %s rows but no guardside file" % (self.dir, s, name))
                g = self._read("guardside", s, keys + self.h_cols + ["ngd__" + l for l in self.links])
                if len(g) != int(union.sum()):
                    refuse("slim %s guardside/%s holds %d rows; the train flags mark %d" % (self.dir, s, len(g),
                                                                                         int(union.sum())))
                pos = (np.cumsum(union) - 1)[mask]
                gsel = g.iloc[pos].reset_index(drop=True)
                for kk in ("unit", "time", "issue"):
                    if not np.array_equal(gsel[kk].to_numpy(), k[kk].to_numpy()):
                        refuse("slim %s guardside/%s rows are not in train order (key %s)" % (self.dir, s, kk))
                for h in self.h_cols:
                    xname = C.X_PREFIX + h[len("h__"):]
                    if xname in hist.columns:
                        hist[xname] = gsel[h].to_numpy()
                for l in self.links:
                    out_n[l].append(gsel["ngd__" + l].to_numpy(np.float64))
            else:
                for l in self.links:
                    out_n[l].append(t.loc[mask, "nfit__" + l].to_numpy(np.float64))
            out_k.append(k)
            out_y.append(t.loc[mask, "y"].to_numpy(np.float64))
            out_h.append(hist)
            if extras:
                out_e.append(t.loc[mask, self.extras_cols].reset_index(drop=True))
        if not out_k:
            refuse("slim %s holds no %s row at lead %d" % (self.dir, name, self.lead))
        K = pd.concat(out_k, ignore_index=True)
        if K.duplicated(subset=["unit", "time", "issue"]).any():
            refuse("slim set %s names a (unit, time, issue) twice" % name)
        y = np.concatenate(out_y)
        if not np.isfinite(y).all():
            refuse("slim set %s holds %d missing labels" % (name, int((~np.isfinite(y)).sum())))
        return SlimSet(name, K, y if with_y else None, {l: np.concatenate(v) for l, v in out_n.items()},
                       pd.concat(out_h, ignore_index=True),
                       pd.concat(out_e, ignore_index=True) if extras else pd.DataFrame(index=K.index))

    def extras_of(self, name: str) -> pd.DataFrame:
        """Keys + the extra columns of a set (never a history column, never y); the test set's extras need no lock
        (they are features, not labels; the history block is never returned here)."""
        keys = list(C.KEYS)
        if name == "test":
            parts = [self._read("test", s, _uniq(keys + self.extras_cols)) for s in self.test_stems]
            return _concat(parts, _uniq(keys + self.extras_cols))
        if name == "train":
            parts = [self._read("train", s, _uniq(keys + self.extras_cols)) for s in self.train_stems]
            return _concat(parts, _uniq(keys + self.extras_cols))
        if name not in SET_FLAG:
            refuse("unknown set %r" % name)
        parts = []
        for s in self.train_stems:
            t = self._read("train", s, _uniq(keys + [SET_FLAG[name]] + self.extras_cols))
            parts.append(t.loc[t[SET_FLAG[name]].to_numpy(bool), _uniq(keys + self.extras_cols)])
        return _concat(parts, _uniq(keys + self.extras_cols))


def _concat(parts: List[pd.DataFrame], cols: Sequence[str]) -> pd.DataFrame:
    if not parts:
        return pd.DataFrame({c: [] for c in cols})
    return pd.concat(parts, ignore_index=True)


def _sha_bytes(b: bytes) -> str:
    import hashlib
    return hashlib.sha256(b).hexdigest()


def _sha_file(p: Any) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def open_slim(cfg: Any, run: Any, lead: int) -> SlimLead:
    return SlimLead(C.slim_lead_dir(cfg, run.package, run.name, lead), run)
