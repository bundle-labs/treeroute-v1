"""The index table (an adapter's only output), the adapter context, the timing rules T1 / T2 and `check`
(SPEC_HUMAN.txt 1.4, 1.5; PROT H1, H2).

An index table holds one row per slim key of a lead (every role, and the test rows): the keys, at most 3 x__<stat>
columns (NaN = not covered), info_end (newest data time used), target_obs_end (newest time of an observation of the
target or its direct source; NaN = none), product_cell and src. A rival that reads target observations inside the
test window writes it in two stages: `train` (the train-file rows) before the human lock, `test` after it (A2).

Timing rules are read from the run, nothing hand-set:
  T1 (driver inputs): info_end <= boundary. Grids: issue - S, S = max `steps` of the run's R8 entries of the
     rival's t1_kind_columns (all R8 entries when it names none). Tables: issue + plan.json
     max_feature_end_minus_issue_day of the lead.
  T2 (target observations): target_obs_end <= the newest readable label step. Grids: timing.latest_label_step(t, L)
     minus R17 start_offset_steps (t - 1 at lead 0, t - L at lead L, then minus the offset). Tables: strictly before
     the issue day (issue - 1).
Tier P, L or X rows must pass both on every covered row; a tier-A row must break one (else the registry is wrong).
"""
# Provenance: SPEC_HUMAN.txt 1.4, 1.5, 6 (AdapterCtx, adapter and runner contracts); engine timing/cuts.py:50-60
# latest_label_step, pipeline/ladder.py:880-893 (hist_last_1 reads that step), pipeline/table_ladder.py:390-396
# (last label before the issue day); derived.json R8 `steps`, R17 start_offset_steps.

import contextlib
import datetime as _dt
import importlib
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from rivals_human import config as C
from rivals_human import slim as S
from rivals_human.common import HumanCommand, load, refuse, tool_code_sha

_PRODUCT_SHA: Dict[str, tuple] = {}


# ===================================================================================================== timing
class Timing(object):
    """T1 boundary and T2 step of one rival at one lead, read from the run."""

    def __init__(self, run: Any, rival: Mapping[str, Any], lead: int):
        self.lead = int(lead)
        self.is_table = "max_feature_end_minus_issue_day" in run.plan
        self.offset = S.run_offset(run)
        cols = list(rival.get("t1_kind_columns") or [])
        if self.is_table:
            mfe = run.plan["max_feature_end_minus_issue_day"]
            if str(self.lead) not in mfe:
                refuse("plan.json max_feature_end_minus_issue_day has no lead %d" % self.lead)
            self.t1_shift = int(mfe[str(self.lead)])
            self.t1_rule = "info_end <= issue + %d (plan.json max_feature_end_minus_issue_day, lead %d)" % (
                self.t1_shift, self.lead)
            self.s_steps = None
        else:
            r8 = (run.derived.get("R8") or {}).get("value") or {}
            if cols:
                unknown = [c for c in cols if c not in r8]
                if unknown:
                    refuse("rival %s names t1_kind_columns %s that are not R8 entries of the run"
                           % (rival.get("id"), unknown))
                entries = [r8[c] for c in cols]
                basis = "R8 entries of %s" % cols
            else:
                entries = list(r8.values())
                basis = "every R8 entry (%d)" % len(entries)
            steps = [int(e.get("steps")) for e in entries if isinstance(e, Mapping) and e.get("steps") is not None]
            self.s_steps = max(steps) if steps else 0
            self.t1_shift = -int(self.s_steps)
            self.t1_rule = "info_end <= issue - %d (S = max steps over %s)" % (self.s_steps, basis if steps
                                                                                else "no R8 entry: S = 0")
        if self.is_table:
            self.t2_rule = "target_obs_end <= issue - 1 (strictly before the issue day)"
        else:
            back = 1 if self.lead == 0 else self.lead
            self.t2_rule = "target_obs_end <= time - %d - %d (latest_label_step minus R17 offset)" % (back, self.offset)

    def t1_boundary(self, keys: pd.DataFrame) -> np.ndarray:
        return keys["issue"].to_numpy(np.int64) + int(self.t1_shift)

    def t2_step(self, keys: pd.DataFrame) -> np.ndarray:
        if self.is_table:
            return keys["issue"].to_numpy(np.int64) - 1
        t = keys["time"].to_numpy(np.int64)
        back = 1 if self.lead == 0 else self.lead
        return t - back - int(self.offset)

    def record(self) -> Dict[str, Any]:
        return {"lead": self.lead, "is_table": self.is_table, "t1_rule": self.t1_rule, "t1_shift": self.t1_shift,
                "s_steps": self.s_steps, "t2_rule": self.t2_rule, "offset_steps": self.offset}


def timing_breaks(timing: Timing, keys: pd.DataFrame, info_end: np.ndarray,
                  target_obs_end: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """(breaks T1, breaks T2) per row."""
    b1 = np.asarray(info_end, dtype=np.int64) > timing.t1_boundary(keys)
    toe = np.asarray(target_obs_end, dtype=np.float64)
    b2 = np.isfinite(toe) & (toe > timing.t2_step(keys).astype(np.float64))
    return b1, b2


def check_tier_timing(tier: str, timing: Timing, keys: pd.DataFrame, info_end: Any, target_obs_end: Any,
                      covered: np.ndarray, what: str) -> Dict[str, int]:
    """P / L / X rows must pass T1 and T2 on every covered row; an A row must break one on every covered row."""
    b1, b2 = timing_breaks(timing, keys, info_end, target_obs_end)
    cov = np.asarray(covered, dtype=bool)
    rec = {"covered": int(cov.sum()), "t1_breaks": int((b1 & cov).sum()), "t2_breaks": int((b2 & cov).sum())}
    if tier in ("P", "L", "X"):
        if (b1 & cov).any() or (b2 & cov).any():
            bad = np.flatnonzero((b1 | b2) & cov)[:3]
            refuse("%s: tier %s rows break the timing rules (T1 %d rows: %s; T2 %d rows: %s); first rows %s"
                   % (what, tier, rec["t1_breaks"], timing.t1_rule, rec["t2_breaks"], timing.t2_rule,
                      keys.iloc[bad][["unit", "time", "issue"]].to_dict("records")),
                   fix="a parity row may read no later than the run's own features and labels (PLAN 3.3)")
    elif tier == "A":
        ok = cov & ~b1 & ~b2
        if ok.any():
            refuse("%s: %d tier-A rows break neither T1 nor T2, so they are parity rows: the registry is wrong"
                   % (what, int(ok.sum())), fix="make the rival tier P, or fix its index table")
    else:
        refuse("internal: timing check of tier %r" % tier)
    return rec


# ===================================================================================================== products
def product_manifest_path(cfg: Any, products: Mapping[str, Any], pid: str) -> Path:
    if pid not in products:
        refuse("product %r is not in the product registry %s" % (pid, cfg["on_disk_products"]),
               fix="builder A adds it to registry/_products.yaml")
    rec = products[pid]
    if rec.get("manifest"):
        return Path(str(rec["manifest"]))
    return C.product_out_manifest(cfg, pid)


def product_manifest(cfg: Any, products: Mapping[str, Any], pid: str) -> Dict[str, Any]:
    p = product_manifest_path(cfg, products, pid)
    if not p.is_file():
        line = products[pid].get("waiting_line") or (
            "product %s has no manifest at %s: run `py -3.9 -B -m rivals_human.cli manifest --product %s` first"
            % (pid, p, pid))
        refuse(line)
    m = C.read_json(p)
    if not isinstance(m.get("files"), Mapping) or not m["files"]:
        refuse("the product manifest %s lists no file" % p)
    if m.get("complete") is False:
        refuse("the product manifest %s says the product is not complete" % p)
    return m


def product_root(cfg: Any, products: Mapping[str, Any], pid: str) -> Path:
    """The folder the manifest's file names are relative to: a download's manifest folder, a product folder, or the
    folder of a one-file product."""
    rec = products[pid]
    if rec.get("manifest") and not rec.get("path"):
        return Path(str(rec["manifest"])).parent
    p = Path(str(rec["path"]))
    return p.parent if p.is_file() else p


def product_status(cfg: Any, products: Mapping[str, Any], pid: str) -> Tuple[bool, str]:
    """(on disk with a manifest, plain line)."""
    try:
        m = product_manifest(cfg, products, pid)
    except Exception as exc:                             # the refusal text is the line
        return False, str(exc)
    return True, "%d files" % len(m["files"])


def verify_product_file(path: Path, want_sha: str) -> str:
    st = os.stat(str(path))
    key = os.path.normcase(str(path.resolve()))
    hit = _PRODUCT_SHA.get(key)
    if hit is None or hit != (int(st.st_size), int(st.st_mtime_ns), want_sha):
        sha = S._sha_file(path)
        if sha != want_sha:
            refuse("product file %s has sha256 %s; its manifest lists %s" % (path, sha[:16], want_sha[:16]),
                   fix="the product changed after its manifest: restore it, or re-hash it in a new Part")
        _PRODUCT_SHA[key] = (int(st.st_size), int(st.st_mtime_ns), sha)
    return want_sha


# ===================================================================================================== adapter ctx
class AdapterCtx(object):
    """What an adapter (and an M runner) receives (spec 6). No label is reachable except ctx.fit_labels(fit_set)
    INSIDE a runner's fit on that same fit set (methods.run_fit opens the scope); the test set's features only with a
    lock token. The slim reader is private (review issue 2: a public reader handed out y of every train set)."""

    def __init__(self, cfg: Any, hctx: Any, run: Any, registry: Mapping[str, Any], products: Mapping[str, Any],
                 rival: Mapping[str, Any], lead: int, stage: str, slim: S.SlimLead, lock_token: Any = None):
        self.cfg, self._hctx, self.run, self.package, self.products = cfg, hctx, run, registry, products
        self.rival, self.lead, self.stage, self._slim = dict(rival), int(lead), stage, slim
        self._token = lock_token
        self._fit_set: Optional[str] = None
        self.opened: Dict[str, Dict[str, str]] = {}
        self.timing = Timing(run, rival, lead)
        self.season = slim.season
        self.steps_per_year = self.season.get("steps_per_year")
        self.is_table = self.timing.is_table
        self.log_lines: List[str] = []

    # --- rows ---------------------------------------------------------------------------------------
    def keys(self, set_name: str = "stage") -> pd.DataFrame:
        if set_name == "stage":
            set_name = {C.STAGE_ALL: "all", C.STAGE_TRAIN: "train", C.STAGE_TEST: "test"}[self.stage]
        if set_name in ("test", "all") and self.stage == C.STAGE_TRAIN:
            refuse("stage train of rival %s may not read test keys" % self.rival["id"])
        return self._slim.keys(set_name)

    def units(self) -> pd.DataFrame:
        return self._slim.units()

    def extras(self, set_name: str) -> pd.DataFrame:
        if set_name == "test" and self.stage == C.STAGE_TRAIN:
            refuse("stage train of rival %s may not read test rows" % self.rival["id"])
        return self._slim.extras_of(set_name)

    @contextlib.contextmanager
    def _fitting(self, fit_set: str):
        """The label scope of one runner fit (opened only by methods.run_fit): inside it fit_labels answers THIS fit
        set and nothing else; outside it (adapters, coverage functions, predict) fit_labels refuses."""
        if fit_set not in C.FIT_SETS:
            refuse("internal: a label scope is opened for a fit set %s, not %r" % (C.FIT_SETS, fit_set))
        if self._fit_set is not None:
            refuse("internal: a label scope is already open (%s)" % self._fit_set)
        self._fit_set = fit_set
        try:
            yield self
        finally:
            self._fit_set = None

    def fit_labels(self, set_name: str):
        """(keys, y, {link: normal}) of the fit set being fitted (refit, tune or guardfit), inside a runner's fit only;
        inner, guard and test refuse, so does any other fit set and any call outside a fit (review issue 2)."""
        if set_name not in C.FIT_SETS:
            refuse("rival %s asked the labels of set %r; only the fit sets %s give labels (spec 6)"
                   % (self.rival["id"], set_name, C.FIT_SETS))
        if self._fit_set is None:
            refuse("rival %s asked the labels of set %r outside a runner's fit; labels are given only to "
                   "fit(ctx, rival, lead, fit_set), of that fit set (spec 6)" % (self.rival["id"], set_name))
        if set_name != self._fit_set:
            refuse("rival %s is being fitted on set %r and asked the labels of set %r; a fit sees the labels of its "
                   "own fit set only (spec 6)" % (self.rival["id"], self._fit_set, set_name))
        s = self._slim.read_set(set_name, extras=False)
        return s.keys, s.y, s.normal

    def features(self, set_name: str) -> S.SlimSet:
        """Keys, normals, history (guard-side substituted) and extras of a set, never y. The test set needs the lock."""
        if set_name == "test":
            return self._slim.read_set("test", lock=self._token)
        s = self._slim.read_set(set_name, with_y=False)
        return s

    # --- time helpers --------------------------------------------------------------------------------
    def season_keys(self, times: Any) -> np.ndarray:
        return S.season_keys(times, self.season)

    def _per_year(self) -> int:
        p = self.steps_per_year
        if not p or int(p) < 1:
            refuse("the run's season has no steps_per_year (a table package uses day ordinals)")
        return int(p)

    def step_year(self, step: Any) -> np.ndarray:
        return (np.asarray(step, dtype=np.int64) - 1) // self._per_year()

    def step_position(self, step: Any) -> np.ndarray:
        return np.mod(np.asarray(step, dtype=np.int64) - 1, self._per_year()) + 1

    def step_of(self, year: Any, position: Any) -> np.ndarray:
        return np.asarray(year, dtype=np.int64) * self._per_year() + np.asarray(position, dtype=np.int64)

    @staticmethod
    def day_to_date(ordinal: int) -> _dt.date:
        return _dt.date.fromordinal(int(ordinal))

    @staticmethod
    def date_to_day(d: _dt.date) -> int:
        return int(d.toordinal())

    def t1_boundary(self, keys: pd.DataFrame) -> np.ndarray:
        return self.timing.t1_boundary(keys)

    def t2_step(self, keys: pd.DataFrame) -> np.ndarray:
        return self.timing.t2_step(keys)

    # --- products ------------------------------------------------------------------------------------
    def _allowed(self, pid: str) -> None:
        if pid not in (self.rival.get("products") or []):
            refuse("rival %s opened product %r, which its registry entry does not list" % (self.rival["id"], pid))

    def product_available(self, pid: str) -> bool:
        """True when the product has its manifest (never refuses; the plain line is product_status's)."""
        self._allowed(pid)
        return bool(product_status(self.cfg, self.products, pid)[0])

    def require_human_lock(self) -> Any:
        """The verified human lock token (stage test, and every read of a test feature); refuses without it."""
        from rivals_human import lockfile
        return lockfile.require_token(self._token, self.run.fingerprint, "rival %s stage %s" % (self.rival["id"],
                                                                                            self.stage))

    def product_files(self, pid: str) -> List[str]:
        self._allowed(pid)
        return sorted(product_manifest(self.cfg, self.products, pid)["files"])

    def product_root(self, pid: str) -> Path:
        self._allowed(pid)
        return product_root(self.cfg, self.products, pid)

    def open_product(self, pid: str, name: str) -> Path:
        """The path of one product file after a sha256 check against its manifest (recorded for `check`)."""
        self._allowed(pid)
        m = product_manifest(self.cfg, self.products, pid)
        e = m["files"].get(name)
        if e is None:
            refuse("product %s's manifest does not list %r" % (pid, name))
        p = product_root(self.cfg, self.products, pid) / name
        if not p.is_file():
            refuse("product file %s is missing" % p)
        verify_product_file(p, str(e["sha256"]))
        self.opened.setdefault(pid, {})[name] = str(e["sha256"])
        return p

    # --- writes ----------------------------------------------------------------------------------------
    def work_dir(self) -> Path:
        d = C.index_work_dir(self.cfg, self.run.package, self.run.name, self.rival["id"])
        return self._hctx.mkdir(d)

    def write_bytes(self, path: Any, data: bytes) -> Path:
        p = Path(path)
        wd = C.index_work_dir(self.cfg, self.run.package, self.run.name, self.rival["id"]).resolve()
        try:
            p.resolve().relative_to(wd)
        except ValueError:
            refuse("an adapter writes only under its work folder %s, not %s" % (wd, p))
        self._hctx.mkdir(p.parent)
        self._hctx.replace_bytes(p, data)
        return p

    def log(self, message: str) -> None:
        self.log_lines.append(message)
        self._hctx.log("adapter", self.rival["id"], "lead %d" % self.lead, message=str(message))


# ===================================================================================================== index files
def index_files(cfg: Any, run: Any, rival_id: str, lead: int) -> Dict[str, Path]:
    d = C.index_rival_dir(cfg, run.package, run.name, rival_id)
    return {"dir": d, "manifest": d / (C.INDEX_MANIFEST % int(lead)), C.STAGE_ALL: d / (C.INDEX_FILE % int(lead)),
            C.STAGE_TRAIN: d / (C.INDEX_STAGE_FILE % (int(lead), C.STAGE_TRAIN)),
            C.STAGE_TEST: d / (C.INDEX_STAGE_FILE % (int(lead), C.STAGE_TEST))}


def stages_of(rival: Mapping[str, Any]) -> Tuple[str, ...]:
    return (C.STAGE_TRAIN, C.STAGE_TEST) if rival.get("reads_target_in_test_window") else (C.STAGE_ALL,)


def read_index_manifest(cfg: Any, run: Any, rival_id: str, lead: int) -> Optional[Dict[str, Any]]:
    p = index_files(cfg, run, rival_id, lead)["manifest"]
    return C.read_json(p) if p.is_file() else None


def read_index(cfg: Any, run: Any, rival: Mapping[str, Any], lead: int, stages: Optional[Sequence[str]] = None,
               lock_token: Any = None) -> pd.DataFrame:
    """The index table of a rival at a lead (the stages asked, verified by their recorded sha256). Stage test needs a
    lock token."""
    files = index_files(cfg, run, rival["id"], lead)
    man = read_index_manifest(cfg, run, rival["id"], lead)
    if man is None:
        refuse("rival %s has no index table at lead %d (%s)" % (rival["id"], lead, files["manifest"]),
               fix="py -3.9 -B -m rivals_human.cli adapt --run <run> --rival %s --lead %d" % (rival["id"], lead))
    stages = list(stages or stages_of(rival))
    parts = []
    for st in stages:
        if st == C.STAGE_TEST:
            from rivals_human import lockfile
            lockfile.require_token(lock_token, run.fingerprint, "reading the test stage of index %s" % rival["id"])
        rec = (man.get("stages") or {}).get(st)
        if rec is None:
            refuse("rival %s lead %d: index stage %s is not written" % (rival["id"], lead, st),
                   fix="adapt --stage %s (stage test only after the human lock)" % st)
        p = files[st]
        if S._sha_file(p) != rec["sha256"]:
            refuse("index table %s changed after it was written (sha differs)" % p)
        parts.append(pq.read_table(str(p)).to_pandas())
    return pd.concat(parts, ignore_index=True) if len(parts) > 1 else parts[0]


def index_shas(cfg: Any, run: Any, rival_id: str, lead: int, stages: Sequence[str]) -> Dict[str, Optional[str]]:
    """The recorded sha256 of each stage (None: not written), each re-checked against its file now."""
    man = read_index_manifest(cfg, run, rival_id, lead)
    if man is None:
        return {st: None for st in stages}
    out = {}
    files = index_files(cfg, run, rival_id, lead)
    for st in stages:
        sha = ((man.get("stages") or {}).get(st) or {}).get("sha256")
        if sha is not None and S._sha_file(files[st]) != sha:
            refuse("the index table of %s lead %d stage %s changed after it was written (%s)"
                   % (rival_id, int(lead), st, files[st]))
        out[st] = sha
    return out


# ===================================================================================================== frame checks
def check_frame(frame: pd.DataFrame, expected_keys: pd.DataFrame, rival: Mapping[str, Any], timing: Timing,
                tier: str, legal: Tuple[float, float], opened: Mapping[str, Mapping[str, str]],
                manifests: Mapping[str, Mapping[str, Any]], what: str) -> Dict[str, Any]:
    """The 1.4 refusals: columns and types; one row per expected key (no missing, extra or duplicate key); no +-inf;
    every src named on a covered row was opened with the sha its product manifest lists; the T1 / T2 rule of the
    tier on covered rows; N-kind values inside [legal_min - slack, legal_max] (I kind: counted, warn only)."""
    stats = list(rival["stats"])
    want = list(C.INDEX_FIXED_COLUMNS) + stats
    have = list(frame.columns)
    if sorted(have) != sorted(want):
        refuse("%s: the index columns %s differ from the 1.4 schema %s (missing %s, unknown %s)"
               % (what, have, want, sorted(set(want) - set(have)), sorted(set(have) - set(want))))
    for s in stats:
        if frame[s].dtype != np.float64:
            refuse("%s: %s must be float64, got %s" % (what, s, frame[s].dtype))
    if frame[C.COL_INFO_END].dtype != np.int64:
        refuse("%s: info_end must be int64, got %s" % (what, frame[C.COL_INFO_END].dtype))
    if frame[C.COL_TARGET_OBS_END].dtype.kind not in "fi":
        refuse("%s: target_obs_end must be numeric (NaN = none), got %s" % (what, frame[C.COL_TARGET_OBS_END].dtype))
    for c in (C.COL_PRODUCT_CELL, C.COL_SRC):
        if not all(isinstance(v, str) for v in frame[c].tolist()):
            refuse("%s: %s must be text on every row" % (what, c))
    if frame.duplicated(subset=list(C.JOIN_KEYS)).any():
        refuse("%s: the index names a key %s twice (%d rows)" % (what, C.JOIN_KEYS,
                                                                int(frame.duplicated(subset=list(C.JOIN_KEYS)).sum())))
    ek = expected_keys[list(C.KEYS)].copy()
    fk = frame[list(C.KEYS)].copy()
    for k in ("unit", "group"):
        ek[k] = ek[k].astype(str)
        fk[k] = fk[k].astype(str)
    j = ek.merge(fk, on=list(C.JOIN_KEYS), how="outer", indicator=True, suffixes=("", "_index"))
    miss = int((j["_merge"] == "left_only").sum())
    extra = int((j["_merge"] == "right_only").sum())
    if miss or extra:
        refuse("%s: %d slim keys have no index row; %d index rows name no slim key" % (what, miss, extra))
    if (j["group"] != j["group_index"]).any():
        refuse("%s: %d index rows name another group than the slim key" % (what, int((j["group"] != j["group_index"]).sum())))
    X = frame[stats].to_numpy(np.float64)
    if np.isinf(X).any():
        refuse("%s: the index holds %d infinite values (NaN = not covered)" % (what, int(np.isinf(X).sum())))
    covered = np.isfinite(X).any(axis=1)
    # src: every file named on a covered row was opened with its manifest sha
    bad_src = []
    names = set()
    for v in frame.loc[covered, C.COL_SRC].unique().tolist():
        for n in str(v).split(C.SRC_SEPARATOR):
            if n:
                names.add(n)
    if covered.any() and not names:
        refuse("%s: covered rows name no src file" % what)
    for n in sorted(names):
        hits = [(pid, sha) for pid, files in opened.items() for nm, sha in files.items() if nm == n]
        if not hits:
            bad_src.append("%s (never opened through ctx.open_product)" % n)
            continue
        for pid, sha in hits:
            ms = ((manifests.get(pid) or {}).get("files") or {}).get(n, {}).get("sha256")
            if ms != sha:
                bad_src.append("%s (opened sha %s, manifest %s)" % (n, str(sha)[:16], str(ms)[:16]))
    if bad_src:
        refuse("%s: src files whose sha256 is not the product manifest's: %s" % (what, bad_src[:5]))
    rec = check_tier_timing(tier, timing, frame[list(C.KEYS)], frame[C.COL_INFO_END].to_numpy(np.int64),
                            frame[C.COL_TARGET_OBS_END].to_numpy(np.float64), covered, what)
    lo, hi = float(legal[0]) - C.N_RANGE_SLACK, float(legal[1])
    out_range = int(((X < lo) | (X > hi))[np.isfinite(X)].sum())
    if out_range and rival["kind"] == "N":
        refuse("%s: %d N-kind values lie outside [%r, %r] before any map" % (what, out_range, lo, hi))
    rec.update(rows=int(len(frame)), out_of_legal_range=out_range,
               covered_by_stat={s: int(np.isfinite(frame[s].to_numpy(np.float64)).sum()) for s in stats})
    return rec


# ===================================================================================================== adapt
def load_adapter(spec: str):
    """'module:function' from the build root (adapters/ is a namespace package; no __init__ needed)."""
    if ":" not in str(spec):
        refuse("adapter %r must be 'module:function'" % spec)
    mod, fn = str(spec).split(":", 1)
    if str(C.BUILD_ROOT) not in sys.path:
        sys.path.insert(0, str(C.BUILD_ROOT))
    m = importlib.import_module(mod)
    f = getattr(m, fn, None)
    if f is None:
        refuse("adapter module %s has no function %s" % (mod, fn))
    return f


def rival_of(registry: Mapping[str, Any], rival_id: str) -> Dict[str, Any]:
    for r in registry["rivals"]:
        if r["id"] == rival_id:
            return r
    refuse("the registry %s has no rival %r" % (registry.get("_file"), rival_id))


def adapt(run_folder: Any, rival_id: str, lead: Any = "all", stage: Optional[str] = None, config: Any = None) -> List[Path]:
    """Run a rival's adapter for one lead or every lead with a row, check the frame, write the index table."""
    cfg = C.load_config(config)
    LY, H = load(cfg)
    run = H.Run(run_folder)
    registry = C.load_registry(cfg, run.package)
    products = C.load_products(cfg)
    rival = rival_of(registry, rival_id)
    if rival.get("runner"):
        refuse("rival %s is a method with a runner; it writes no index table (its predictions are made by tune and "
               "refit)" % rival_id)
    tiers = C.lead_tiers(rival)
    leads = [L for L in run.leads if tiers.get(L, {}).get("tier", C.TIER_NONE) != C.TIER_NONE] \
        if str(lead) == "all" else [int(lead)]
    stages = stages_of(rival)
    stage = stage or (C.STAGE_ALL if stages == (C.STAGE_ALL,) else C.STAGE_TRAIN)
    if stage not in stages:
        refuse("rival %s is written in stages %s, not %r (reads_target_in_test_window=%s)"
               % (rival_id, stages, stage, bool(rival.get("reads_target_in_test_window"))))
    token = None
    if stage == C.STAGE_TEST:
        from rivals_human import lockfile
        token = lockfile.verify_lock(C.board_dir(cfg, run.package, run.name))
    out_dir = C.index_rival_dir(cfg, run.package, run.name, rival_id)
    written = []
    with HumanCommand("adapt", out_dir.parent, cfg) as hctx:
        hctx.mkdir(out_dir)
        fn = load_adapter(rival["adapter"])
        for L in leads:
            if L not in run.cuts:
                refuse("lead %d is not a lead of the run %s" % (L, run.leads))
            tier = tiers.get(L, {}).get("tier", C.TIER_NONE)
            if tier == C.TIER_NONE:
                refuse("rival %s has no row at lead %d (%s)" % (rival_id, L, tiers.get(L, {}).get("reason")))
            sl = S.open_slim(cfg, run, L)
            actx = AdapterCtx(cfg, hctx, run, registry, products, rival, L, stage, sl, token)
            t0 = time.time()
            frame = fn(actx, dict(rival), L, stage)
            if not isinstance(frame, pd.DataFrame):
                refuse("adapter %s returned %s, not a DataFrame" % (rival["adapter"], type(frame).__name__))
            expected = actx.keys("stage")
            manifests = {pid: product_manifest(cfg, products, pid) for pid in actx.opened}
            rec = check_frame(frame, expected, rival, actx.timing, tier, run.legal, actx.opened, manifests,
                              "rival %s lead %d stage %s" % (rival_id, L, stage))
            files = index_files(cfg, run, rival_id, L)
            frame = frame[list(C.INDEX_FIXED_COLUMNS) + list(rival["stats"])].reset_index(drop=True)
            target = files[stage]
            man = read_index_manifest(cfg, run, rival_id, L) or {
                "format": C.FORMAT_INDEX, "rival": rival_id, "lead": L, "run_fingerprint": run.fingerprint,
                "stages": {}}
            if stage in (man.get("stages") or {}) and target.is_file():
                hctx.move_aside(target)
            hctx.write_parquet(target, frame)
            man["stages"][stage] = {"file": target.name, "sha256": S._sha_file(target), "rows": int(len(frame)),
                                    "check": rec, "opened": actx.opened, "adapter": rival["adapter"],
                                    "tool_code_sha256": tool_code_sha(), "slim_manifest_sha256": sl.manifest_sha,
                                    "timing": actx.timing.record(), "tier": tier, "seconds": time.time() - t0,
                                    "utc": H.utc_now()}
            hctx.replace_json(files["manifest"], man)
            hctx.log("adapt", rival_id, "lead %d" % L, time.time() - t0,
                     "stage %s: %d rows, %d covered (%s); T1 breaks %d, T2 breaks %d"
                     % (stage, rec["rows"], rec["covered"], tier, rec["t1_breaks"], rec["t2_breaks"]))
            written.append(target)
    return written


def check(run_folder: Any, rival_id: str, config: Any = None) -> Dict[str, Any]:
    """Re-check every written index table of a rival (spec 1.4 refusals and 1.5 timing), read-only."""
    cfg = C.load_config(config)
    LY, H = load(cfg)
    run = H.Run(run_folder)
    registry = C.load_registry(cfg, run.package)
    products = C.load_products(cfg)
    rival = rival_of(registry, rival_id)
    if rival.get("runner"):
        return {"rival": rival_id, "result": "a method with a runner: no index table (its outputs are checked at "
                                             "tune and refit)"}
    out: Dict[str, Any] = {"rival": rival_id, "leads": {}}
    for L, tr in sorted(C.lead_tiers(rival).items()):
        if tr["tier"] == C.TIER_NONE:
            out["leads"][str(L)] = "none: %s" % tr["reason"]
            continue
        man = read_index_manifest(cfg, run, rival_id, L)
        if man is None:
            out["leads"][str(L)] = "not written"
            continue
        sl = S.open_slim(cfg, run, L)
        timing = Timing(run, rival, L)
        rec = {}
        for st, srec in sorted((man.get("stages") or {}).items()):
            p = index_files(cfg, run, rival_id, L)[st]
            if S._sha_file(p) != srec["sha256"]:
                refuse("index %s changed after it was written" % p)
            frame = pq.read_table(str(p)).to_pandas()
            keys = sl.keys({C.STAGE_ALL: "all", C.STAGE_TRAIN: "train", C.STAGE_TEST: "test"}[st])
            manifests = {pid: product_manifest(cfg, products, pid) for pid in srec.get("opened") or {}}
            rec[st] = check_frame(frame, keys, rival, timing, tr["tier"], run.legal, srec.get("opened") or {},
                                  manifests, "rival %s lead %d stage %s" % (rival_id, L, st))
        out["leads"][str(L)] = rec
    eq = rival.get("equal_value_leads")
    if eq:
        frames = {}
        for L in eq:
            man = read_index_manifest(cfg, run, rival_id, int(L))
            if man is None or not man.get("stages"):
                frames = None                     # a lead not written yet: checked once every listed lead exists
                break
            frames[int(L)] = read_index(cfg, run, rival, int(L), stages=sorted(man["stages"]),
                                        lock_token=_check_token(cfg, run, man))
        out["equal_value_leads"] = ("not checked: a listed lead has no index table yet" if frames is None else
                                    check_equal_value_leads(frames, list(rival["stats"]),
                                                            "rival %s equal_value_leads %s" % (rival_id, list(eq))))
    return out


def _check_token(cfg: Any, run: Any, man: Mapping[str, Any]) -> Any:
    """`check` reads a test stage only when it is written, which happens only after the human lock (adapt verifies
    the lock); the same lock is verified here before the test stage is read."""
    if C.STAGE_TEST not in (man.get("stages") or {}):
        return None
    from rivals_human import lockfile
    return lockfile.verify_lock(C.board_dir(cfg, run.package, run.name))


def check_equal_value_leads(frames: Mapping[int, pd.DataFrame], stats: Sequence[str], what: str) -> Dict[str, Any]:
    """Registry `equal_value_leads` (SPEC_HUMAN 3: "`check` asserts equality per (unit, time)"): a rival whose value
    depends only on the unit and the target time writes the same numbers at every listed lead. Per (unit, time) key
    present at two listed leads, every stat must be equal (NaN equals NaN: not covered at both). A key present at
    one lead only is counted, never compared (lead sets may differ at the edges). Refuses on any difference."""
    leads = sorted(int(L) for L in frames)
    if len(leads) < 2:
        refuse("%s: needs at least two leads" % what)
    on = ["unit", "time"]
    base_L = leads[0]
    rec: Dict[str, Any] = {"leads": leads, "pairs": {}}
    b = frames[base_L][on + list(stats)].copy()
    b["unit"] = b["unit"].astype(str)
    if b.duplicated(subset=on).any():
        refuse("%s: lead %d names a (unit, time) twice" % (what, base_L))
    for L in leads[1:]:
        o = frames[L][on + list(stats)].copy()
        o["unit"] = o["unit"].astype(str)
        if o.duplicated(subset=on).any():
            refuse("%s: lead %d names a (unit, time) twice" % (what, L))
        j = b.merge(o, on=on, how="outer", suffixes=("__a", "__b"), indicator=True)
        both = (j["_merge"] == "both").to_numpy()
        if not both.any() and len(b) and len(o):
            refuse("%s: leads %d and %d share no (unit, time) key" % (what, base_L, L))
        diff = np.zeros(len(j), dtype=bool)
        for s in stats:
            xa = j[s + "__a"].to_numpy(np.float64)
            xb = j[s + "__b"].to_numpy(np.float64)
            same = (xa == xb) | (np.isnan(xa) & np.isnan(xb))
            diff |= both & ~same
        if diff.any():
            ex = j.loc[diff, on].head(3).to_dict("records")
            refuse("%s: %d (unit, time) keys differ between lead %d and lead %d (e.g. %s)"
                   % (what, int(diff.sum()), base_L, L, ex))
        rec["pairs"]["%d-%d" % (base_L, L)] = {"keys_compared": int(both.sum()),
                                               "only_lead_%d" % base_L: int((j["_merge"] == "left_only").sum()),
                                               "only_lead_%d" % L: int((j["_merge"] == "right_only").sum()),
                                               "result": "equal"}
    return rec


def prep(run_folder: Any, rival_id: str, config: Any = None, stage: str = C.STAGE_TRAIN) -> Any:
    """Run a rival's registry `prep` ("module:function"; fn(ctx, rival) with ctx at lead 0) under the heavy-job lock:
    an owner prep command (spec 8, e.g. O10, O11, O15). Stage train: no test feature, no label; stage test only with
    a valid human lock (the token is passed; spec A7). Outputs go under the rival's work folder (ctx.write_bytes);
    hash them afterwards with `manifest --product <id>`."""
    cfg = C.load_config(config)
    LY, H = load(cfg)
    run = H.Run(run_folder)
    registry = C.load_registry(cfg, run.package)
    products = C.load_products(cfg)
    rival = rival_of(registry, rival_id)
    if not rival.get("prep"):
        refuse("rival %s has no prep step in its registry entry" % rival_id)
    if stage not in (C.STAGE_TRAIN, C.STAGE_TEST):
        refuse("prep stage must be train or test, not %r" % stage)
    token = None
    if stage == C.STAGE_TEST:
        from rivals_human import lockfile
        token = lockfile.verify_lock(C.board_dir(cfg, run.package, run.name))
    out_dir = C.index_rival_dir(cfg, run.package, run.name, rival_id)
    with HumanCommand("prep", out_dir.parent, cfg) as hctx:
        hctx.mkdir(out_dir.parent)
        actx = AdapterCtx(cfg, hctx, run, registry, products, rival, 0, stage, S.open_slim(cfg, run, 0), token)
        t0 = time.time()
        res = load_adapter(rival["prep"])(actx, dict(rival))
        hctx.log("prep", rival_id, seconds=time.time() - t0, message="prep %s stage %s done" % (rival["prep"], stage))
        return res
