"""The human board: init, tune, lock, refit, score, board, status (SPEC_HUMAN.txt 1.6, 1.9, 1.11; PROT H6-H17).

Plug and predict: every fact is read from the run (links, c, cuts, legal range, band, tolerance, decline target,
R14 blocks, strata), the slim copy, the index tables and the problem registry; no problem is named here.

Order (PROT H16, spec A2): init (human_board.json once) -> tune (candidates on tune rows, scored on inner rows, or a
forecast-only product on its lowest covered lead's guard rows) -> lock (picks + coverage masks + hashes, write-once,
before any test file) -> refit per lead (guard N2, refit, raw and guarded test predictions) -> refs -> score (the ONE
reader of test y) -> board.
"""
# Provenance: SPEC_HUMAN.txt 1.6 (maps, pick), 1.9 (rows, guard, coverage, verdicts), 1.11 (lock), 1.13 (commands);
# harness.py:1379-1487 init, :1554-1584 load_board, :1737-1792 tune, :1872-1881 _inner_comparator, :1884 _join,
# :1939-2012 lock, :2074 saved_test_keys, :2088 to_saved_order, :2100-2113 apply_guard, :2116-2266 refit, :2269-2294
# _guard_comparator, :2383-2413 _strata_tables, :2416-2451 check_ours_against_run, :2454-2530 score (verdict rows
# :2486-2514), :2533 _pooled, :2557-2585 board, :2612-2645 status.

import json
import math
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from rivals_human import config as C
from rivals_human import index as IX
from rivals_human import lockfile as LK
from rivals_human import maps as MP
from rivals_human import methods as ME
from rivals_human import slim as S
from rivals_human.common import (HumanCommand, check_common_board, load, refuse, tool_code_sha)


# ===================================================================================================== helpers
def _sha(p: Any) -> str:
    return S._sha_file(p)


def _canon(obj: Any) -> str:
    _, H = load()
    return H.dumps_canonical(obj)


def _hash(obj: Any) -> str:
    import hashlib
    return hashlib.sha256(_canon(obj).encode("ascii")).hexdigest()


def _registry_shas(cfg: Any, registry: Mapping[str, Any]) -> Dict[str, str]:
    rd = C.registry_dir(cfg)
    return {"registry": _sha(registry["_file"]), "schema": _sha(rd / C.SCHEMA_FILE),
            "products": _sha(cfg.path("on_disk_products"))}


def check_registry_against_run(registry: Mapping[str, Any], run: Any) -> None:
    """Every registry lead is a run lead and every run lead is named; links are R22 links; t1 columns are R8 entries;
    slim extra columns hold no label (review issue 3)."""
    r8 = (run.derived.get("R8") or {}).get("value") or {}
    is_table = "max_feature_end_minus_issue_day" in run.plan
    S.check_extra_columns(registry, run)
    for r in registry["rivals"]:
        tiers = C.lead_tiers(r)
        extra = sorted(set(tiers) - set(run.leads))
        missing = sorted(set(run.leads) - set(tiers))
        if extra or missing:
            refuse("registry rival %s names leads %s; the run's leads are %s (every run lead named, tier or 'none' "
                   "with a reason)" % (r["id"], sorted(tiers), run.leads))
        rl = r.get("links")
        if rl and rl != "all":
            bad = [l for l in rl if l not in run.links]
            if bad:
                refuse("registry rival %s names links %s outside the run's R22 links %s" % (r["id"], bad, run.links))
        if not is_table:
            bad = [c for c in r.get("t1_kind_columns") or [] if c not in r8]
            if bad:
                refuse("registry rival %s names t1_kind_columns %s that are not R8 entries" % (r["id"], bad))
        cov = r.get("coverage") or C.COVERAGE_X
        if not (cov in (C.COVERAGE_X, C.COVERAGE_ALL) or isinstance(cov, Mapping)):
            refuse("registry rival %s: coverage %r is not %s, %s or a rule mapping (issue_min, issue_max, time_min, "
                   "time_max, units_column_positive, units_column_true, function); put plain words in coverage_note"
                   % (r["id"], cov, C.COVERAGE_X, C.COVERAGE_ALL))
        eq = r.get("equal_value_leads")
        if eq:
            if r.get("runner"):
                refuse("registry rival %s: equal_value_leads needs an index table; a runner writes none" % r["id"])
            bad = [L for L in eq if int(L) not in run.leads or tiers.get(int(L), {}).get("tier") in (None, C.TIER_NONE)]
            if len(set(int(L) for L in eq)) < 2 or bad:
                refuse("registry rival %s: equal_value_leads %s must name two or more run leads with a row (bad %s)"
                       % (r["id"], list(eq), bad))
        label_free_needed = bool(r.get("runner")) or bool(r.get("reads_target_in_test_window"))
        if label_free_needed and cov == C.COVERAGE_X:
            refuse("registry rival %s reads labels or target observations in the test window (or is a runner), so its "
                   "coverage must be a label-free rule fixed before the lock (all_rows or a rule mapping), not %s"
                   % (r["id"], C.COVERAGE_X))


def no_rival_reason(registry: Mapping[str, Any], lead: int) -> Optional[str]:
    """The package's plain reason for a lead without a human rival (no_rival_leads or leads_without_rival)."""
    for key in ("no_rival_leads", "leads_without_rival"):
        m = registry.get(key) or {}
        v = m.get(lead, m.get(str(lead)))
        if v:
            return str(v)
    return None


TIER_PRINT_ORDER = {"P": 0.0, "L": 0.0, "X": 1.0, "A": 2.0}
PLACEBO_PRINT_ORDER = 1.5


def human_rival_order(registry: Mapping[str, Any], lead: int, ids: Sequence[str]) -> List[str]:
    """Print order of a lead's human rivals (PLAN 3.14): deciding tiers (P, L), then labelled extensions (X), then
    placebos, then advantaged rows (A), registry order inside a tier; a rival with `print_beside` is moved right
    after the rival it names (e.g. a same-month tier-A row beside its parity row; review B issue 5)."""
    by_id = rival_by_id(registry)
    pos = {r["id"]: i for i, r in enumerate(registry["rivals"])}
    ids = list(dict.fromkeys(str(i) for i in ids))

    def rank(rid):
        r = by_id.get(rid)
        if r is None:
            return (9.0, 10 ** 6)
        if r.get("placebo_of"):
            return (PLACEBO_PRINT_ORDER, pos[rid])
        return (TIER_PRINT_ORDER.get(C.lead_tiers(r).get(int(lead), {}).get("tier"), 3.0), pos[rid])

    base = sorted(ids, key=rank)
    parent = {rid: (by_id.get(rid) or {}).get("print_beside") for rid in base}
    out = [rid for rid in base if parent[rid] not in ids]
    for rid in base:
        par = parent[rid]
        if par in ids:
            k = out.index(par) + 1
            while k < len(out) and parent.get(out[k]) == par:
                k += 1
            out.insert(k, rid)
    return out


def joint_claim_line(jc: Mapping[str, Any], t: pd.DataFrame, registry: Mapping[str, Any], lead: int) -> Optional[str]:
    """The joint claim of several forms (Q14 a): YES only when ours BEATS every form; NO with each verdict printed;
    NOT DECIDABLE when a form with a row at this lead has no deciding row or was not calibratable (review B issue
    10). None when no form has a row at this lead."""
    by_id = rival_by_id(registry)
    forms = [rid for rid in jc["rivals"] if C.lead_tiers(by_id[rid]).get(int(lead), {}).get("tier", C.TIER_NONE)
             != C.TIER_NONE]
    if not forms:
        return None
    sub = t[(t["rival"].astype(str).isin(forms)) & (t["contrast"] == "guarded_vs_headline")] if len(t) else t
    have = set(sub["rival"].astype(str)) if len(sub) else set()
    missing = [rid for rid in forms if rid not in have]
    bad = sorted(set(str(v) for v in sub["verdict"]) - {"BEATS", "LOSES", "EQUIVALENT", "CANNOT TELL"}) if len(sub) \
        else []
    if missing or bad:
        why = []
        if missing:
            why.append("%s has no row" % ", ".join(missing))
        if bad:
            why.append("verdict %s" % ", ".join(bad))
        return "%s: NOT DECIDABLE (%s)" % (jc["name"], "; ".join(why))
    yes = bool((sub["verdict"] == "BEATS").all()) and len(sub) == len(forms)
    return "%s: %s" % (jc["name"], "YES" if yes else "NO (each form's verdict is printed above)")


def product_pin(cfg: Any, products: Mapping[str, Any], pid: str) -> Any:
    """What init pins of a product: its manifest sha256, or for a staged product the {file: sha256} it lists now
    (later stages may add files, never change one)."""
    if products[pid].get("staged"):
        m = IX.product_manifest(cfg, products, pid)
        return {"staged_files": {n: e["sha256"] for n, e in sorted(m["files"].items())}}
    return _sha(IX.product_manifest_path(cfg, products, pid))


def check_product_pin(cfg: Any, products: Mapping[str, Any], pid: str, pin: Any) -> None:
    if isinstance(pin, Mapping) and "staged_files" in pin:
        now = IX.product_manifest(cfg, products, pid)["files"]
        bad = sorted(n for n, sha in pin["staged_files"].items() if (now.get(n) or {}).get("sha256") != sha)
        if bad:
            refuse("staged product %s: files hashed at init changed or are gone: %s" % (pid, bad[:5]))
        return
    if _sha(IX.product_manifest_path(cfg, products, pid)) != pin:
        refuse("the product manifest of %s changed since init" % pid)


def rival_by_id(registry: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {r["id"]: r for r in registry["rivals"]}


def pick_lead(rival: Mapping[str, Any]) -> int:
    tiers = C.lead_tiers(rival)
    if (rival.get("pick") or C.PICK_NOWCAST) == C.PICK_NOWCAST:
        return 0
    covered = sorted(L for L, t in tiers.items() if t["tier"] != C.TIER_NONE)
    if not covered:
        refuse("rival %s has no lead with a row" % rival["id"])
    return covered[0]


def pick_sets(rival: Mapping[str, Any]) -> Tuple[int, str, str]:
    L = pick_lead(rival)
    return (L, "tune", "inner") if L == 0 else (L, "guardfit", "guard")


def keys_frame(keys: pd.DataFrame, season: Mapping[str, Any]) -> pd.DataFrame:
    k = keys[list(C.KEYS)].reset_index(drop=True).copy()
    k["unit"] = k["unit"].astype(str)
    k["group"] = k["group"].astype(str)
    k[C.SEASON_KEY] = S.season_keys(k["time"].to_numpy(np.int64), season)
    return k


def join_index(keys: pd.DataFrame, idx: pd.DataFrame, cols: Sequence[str], what: str) -> pd.DataFrame:
    """The index columns for the given keys (left order), one to one; a missing key refuses."""
    on = list(C.JOIN_KEYS)
    lk = keys[on].copy()
    lk["unit"] = lk["unit"].astype(str)
    r = idx[on + list(cols)].copy()
    r["unit"] = r["unit"].astype(str)
    if r.duplicated(subset=on).any():
        refuse("%s: the index names a key twice" % what)
    j = lk.merge(r, on=on, how="left", indicator=True, validate="one_to_one")
    miss = int((j["_merge"] != "both").sum())
    if miss:
        refuse("%s: %d keys have no index row" % (what, miss))
    return j[list(cols)].reset_index(drop=True)


def zero_share_lead0(sl0: S.SlimLead) -> float:
    s = sl0.read_set("refit", extras=False)
    return float(np.mean(s.y == 0.0))


def coverage_rule_mask(rule: Any, keys: pd.DataFrame, units: pd.DataFrame, what: str, actx: Any = None) -> np.ndarray:
    """A label-free coverage rule (registry `coverage`): all_rows, or a mapping whose conditions are ANDed:
    issue_min / issue_max and time_min / time_max (step or day; time = the target time, a key, never a label),
    units_column_positive / units_column_true (a units.parquet column), function ("module:function";
    fn(ctx, rival, lead, keys) -> bool per key; ctx at stage train: no test feature, no label)."""
    n = len(keys)
    if rule == C.COVERAGE_ALL:
        return np.ones(n, dtype=bool)
    if not isinstance(rule, Mapping):
        refuse("%s: coverage rule %r is not all_rows or a mapping" % (what, rule))
    known = {"issue_min", "issue_max", "time_min", "time_max", "units_column_positive", "units_column_true",
             "function"}
    if set(rule) - known:
        refuse("%s: unknown coverage condition(s) %s (known %s)" % (what, sorted(set(rule) - known), sorted(known)))
    m = np.ones(n, dtype=bool)
    iss = keys["issue"].to_numpy(np.int64)
    tim = keys["time"].to_numpy(np.int64)
    if "issue_min" in rule:
        m &= iss >= int(rule["issue_min"])
    if "issue_max" in rule:
        m &= iss <= int(rule["issue_max"])
    if "time_min" in rule:
        m &= tim >= int(rule["time_min"])
    if "time_max" in rule:
        m &= tim <= int(rule["time_max"])
    for cond in ("units_column_positive", "units_column_true"):
        if cond in rule:
            col = str(rule[cond])
            if col not in units.columns:
                refuse("%s: units.parquet has no column %r (coverage rule)" % (what, col))
            u = units[["unit", col]].copy()
            u["unit"] = u["unit"].astype(str)
            v = keys[["unit"]].astype(str).merge(u, on="unit", how="left")[col]
            if v.isna().any():
                refuse("%s: %d rows' units have no %s value" % (what, int(v.isna().sum()), col))
            m &= (v.to_numpy(np.float64) > 0) if cond == "units_column_positive" else v.astype(bool).to_numpy()
    if "function" in rule:
        if actx is None:
            refuse("%s: a coverage function needs the adapter context" % what)
        fn = IX.load_adapter(rule["function"])
        got = np.asarray(fn(actx, dict(actx.rival), int(actx.lead), keys.copy()))
        if got.shape != (n,) or got.dtype != bool:
            refuse("%s: coverage function %s returned %s %s, not one bool per key" % (what, rule["function"],
                                                                                     got.dtype, got.shape))
        m &= got
    return m


# ===================================================================================================== init
def init(run_folder: Any, config: Any = None, dry: bool = False, allow_waiting: bool = False) -> Path:
    """Write human_board.json once (spec 1.11): run facts, the common board's path and sha, every code / registry /
    slim / product / index sha, constants, library versions and thread state. Rivals that cannot run yet are
    listed as waiting (with the plain line).
    The board is write-once, so a waiting rival stays waiting for the board's life: init refuses while a
    non-optional rival with a tier-P row is waiting, unless allow_waiting (the owner then locks without it by a
    recorded decision; review B issue 9). dry: a DRY board (tune-only dry pass) that refit, refs and score refuse."""
    cfg = C.load_config(config)
    LY, H = load(cfg)
    run = H.Run(run_folder)
    out = C.board_dir(cfg, run.package, run.name)
    with HumanCommand("init", out, cfg) as ctx:
        registry = C.load_registry(cfg, run.package)
        products = C.load_products(cfg)
        check_registry_against_run(registry, run)
        cb = check_common_board(H, cfg, run.package, run.name, required=True)
        cbb = cb["board"]
        if cbb["run"]["fingerprint"] != run.fingerprint:
            refuse("the common board is of run fingerprint %s, not %s" % (cbb["run"]["fingerprint"][:16],
                                                                         run.fingerprint[:16]))
        if float(cbb["run"]["band"]) != float(run.band):
            refuse("the common board band %r differs from the run's %r" % (cbb["run"]["band"], run.band))
        live = H.engine_file_sha()
        if live != cbb["engine"]["live_file_sha"]:
            refuse("the LIVE engine (%s) differs from the common board's (%s)" % (live[:8],
                                                                                 cbb["engine"]["live_file_sha"][:8]))
        slims = {}
        for L in run.leads:
            sl = S.open_slim(cfg, run, L)
            slims[str(L)] = {"dir": str(sl.dir), "manifest_sha256": sl.manifest_sha,
                             "source_export_content_sha256": sl.manifest["source_export_content_sha256"],
                             "counts": sl.manifest.get("counts")}
        sl0 = S.open_slim(cfg, run, 0)
        zero_share = zero_share_lead0(sl0)
        rivals = {}
        for r in registry["rivals"]:
            st = {"status": "ready", "waiting": [], "index": {}, "products": {}}
            for pid in r.get("products") or []:
                ok, line = IX.product_status(cfg, products, pid)
                if ok:
                    st["products"][pid] = product_pin(cfg, products, pid)
                else:
                    st["waiting"].append(line)
            if r.get("availability"):
                actx = IX.AdapterCtx(cfg, ctx, run, registry, products, r, 0, C.STAGE_TRAIN, sl0)
                ok, line = IX.load_adapter(r["availability"])(actx, dict(r))
                if not ok:
                    st["waiting"].append(str(line))
            if not r.get("runner"):
                for L, t in sorted(C.lead_tiers(r).items()):
                    if t["tier"] == C.TIER_NONE:
                        continue
                    stages = IX.stages_of(r)
                    pre = [s for s in stages if s != C.STAGE_TEST]
                    shas = IX.index_shas(cfg, run, r["id"], L, pre)
                    st["index"][str(L)] = shas
                    if any(v is None for v in shas.values()):
                        st["waiting"].append("index table of lead %d (stage %s) is not written: py -3.9 -B -m "
                                             "rivals_human.cli adapt --run <run> --rival %s --lead %d"
                                             % (L, "/".join(pre), r["id"], L))
            if st["waiting"]:
                st["status"] = "waiting"
            rivals[r["id"]] = st
        blocking = [r["id"] for r in registry["rivals"] if rivals[r["id"]]["status"] == "waiting"
                    and not r.get("optional") and not r.get("placebo_of")
                    and any(t["tier"] == "P" for t in C.lead_tiers(r).values())]
        if blocking and not allow_waiting:
            refuse("non-optional parity rival(s) %s are waiting (%s); human_board.json is written once, so they would "
                   "stay waiting for this board's life" % (blocking, " | ".join(
                       w for rid in blocking for w in rivals[rid]["waiting"])),
                   fix="put the product on disk (and adapt) first, or record the owner decision and pass "
                       "--allow-waiting, then lock --without <ids> --decision '<the decision>'")
        board = {
            "format": C.FORMAT_BOARD,
            "dry": bool(dry),
            "allow_waiting": bool(allow_waiting),
            "run": {"folder": str(run.folder), "name": run.name, "fingerprint": run.fingerprint,
                    "package": run.package, "kind": run.kind, "router_kind": run.router_kind, "links": run.links,
                    "leads": run.leads, "cuts": {str(k): v for k, v in run.cuts.items()},
                    "c": {str(L): run.c(L) for L in run.leads}, "legal": list(run.legal), "ub": run.ub,
                    "band": run.band, "hit_tolerance": run.tol, "measurement_error_floor": run.floor,
                    "decline_target": run.decline_target, "v1_donor_median_guard": run.v1,
                    "offset_steps": S.run_offset(run), "season": S.run_season(run),
                    "is_table": "max_feature_end_minus_issue_day" in run.plan,
                    "file_sha256": H.run_file_shas(run)},
            "common_board": {"path": cb["path"], "sha256": cb["sha256"],
                             "harness_code_sha256": cbb["harness_code_sha256"],
                             "harness_accepted_as": cb["harness_accepted_as"]},
            "engine": {"live_file_sha": live},
            "common_harness_sha256": H.harness_code_sha(),
            "tool_code_sha256": tool_code_sha(),
            "registry": dict(_registry_shas(cfg, registry), file=registry["_file"]),
            "slim": slims,
            "rivals": rivals,
            "data_rules": {"legal_min": run.legal[0], "refit_y_zero_share_lead0": zero_share,
                           "l1_print": bool(float(run.legal[0]) == 0.0 and zero_share >= H.TWEEDIE_ZERO_SHARE),
                           "tweedie_zero_share": H.TWEEDIE_ZERO_SHARE},
            "constants": {"shrink_k": C.SHRINK_K, "min_fit_rows": C.MIN_FIT_ROWS, "min_fit_groups": C.MIN_FIT_GROUPS,
                          "min_unit_rows": C.MIN_UNIT_ROWS, "min_group_test_rows": C.MIN_GROUP_TEST_ROWS,
                          "max_stats": C.MAX_STATS, "l1_max_blocks": C.L1_MAX_BLOCKS, "threads": C.THREADS,
                          "families": C.FAMILY_ORDER},
            "versions": H.library_versions(), "threadpool_info": H.thread_state(),
            "config": cfg.as_dict(),
        }
        bp = out / C.BOARD_FILE
        text = H.dumps_pretty(board)
        if bp.is_file():
            old = C.read_json(bp)
            if H.dumps_pretty(old) != text:
                refuse("%s exists and differs from this init" % bp,
                       fix="init writes human_board.json once; move the board folder aside to start again")
            ctx.log("init", message="human_board.json exists and is identical; nothing written")
            return out
        ctx.mkdir(out)
        ctx.write_once_json(bp, board)
        for rid, st in rivals.items():
            ctx.log("init", rid, message="%s%s" % (st["status"], (": " + " | ".join(st["waiting"])) if st["waiting"]
                                                  else ""))
        return out


def load_board(ctx: Any) -> Tuple[Dict[str, Any], Any, Dict[str, Any]]:
    """(board, run, registry) with every pinned sha re-checked (H:1554-1584 on the human files)."""
    H = ctx.H
    cfg = ctx.hcfg
    bp = ctx.out / C.BOARD_FILE
    board = C.read_json(bp)
    if board.get("format") != C.FORMAT_BOARD:
        refuse("%s is not a %s file" % (bp, C.FORMAT_BOARD))
    run = H.Run(board["run"]["folder"])
    if run.fingerprint != board["run"]["fingerprint"]:
        refuse("the run fingerprint %s differs from the human board's %s" % (run.fingerprint[:16],
                                                                            board["run"]["fingerprint"][:16]))
    if tool_code_sha() != board["tool_code_sha256"]:
        refuse("the human tool code changed since init (%s vs %s)" % (tool_code_sha()[:16],
                                                                      board["tool_code_sha256"][:16]),
               fix="a board runs under one tool code; init a new board")
    if H.harness_code_sha() != board["common_harness_sha256"]:
        refuse("the common harness changed since init")
    if H.library_versions() != board["versions"]:
        refuse("library versions changed since init: %s vs %s" % (H.library_versions(), board["versions"]))
    th = H.thread_state()
    if th != board["threadpool_info"]:
        refuse("the thread pools differ from init (%s vs %s)" % (th, board["threadpool_info"]))
    if cfg.as_dict() != board["config"]:
        refuse("the config differs from the human board's (%s)" % cfg.source)
    if H.engine_file_sha() != board["engine"]["live_file_sha"]:
        refuse("the LIVE engine changed since init")
    if H.run_file_shas(run) != board["run"]["file_sha256"]:
        refuse("run files changed since init", fix="the run folder is read-only; restore it")
    cbp = Path(board["common_board"]["path"])
    if not cbp.is_file() or _sha(cbp) != board["common_board"]["sha256"]:
        refuse("the common board %s changed or is missing since init" % cbp)
    registry = C.load_registry(cfg, run.package)
    if _registry_shas(cfg, registry) != {k: v for k, v in board["registry"].items() if k != "file"}:
        refuse("the registry, its schema or the product registry changed since init")
    for L, rec in board["slim"].items():
        sl = S.open_slim(cfg, run, int(L))
        if sl.manifest_sha != rec["manifest_sha256"]:
            refuse("the slim copy of lead %s changed since init" % L)
    products = C.load_products(cfg)
    by_id = rival_by_id(registry)
    for rid, st in board["rivals"].items():
        if st["status"] != "ready":
            continue
        for pid, pin in st["products"].items():
            check_product_pin(cfg, products, pid, pin)
        for L, shas in st["index"].items():
            now = IX.index_shas(cfg, run, rid, int(L), list(shas))
            if now != shas:
                refuse("the index table of %s lead %s changed since init (%s vs %s)" % (rid, L, now, shas))
        if rid not in by_id:
            refuse("rival %s of the board is not in the registry" % rid)
    return board, run, registry


def ready_rivals(board: Mapping[str, Any], registry: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return [r for r in registry["rivals"] if board["rivals"][r["id"]]["status"] == "ready"]


# ===================================================================================================== sets
class SetData(object):
    """One set of one lead joined with a rival's index columns: keys (+ season key), y, normals, x by stat."""

    def __init__(self, keys, y, normal, x):
        self.keys, self.y, self.normal, self.x = keys, y, normal, x

    def subset(self, mask: np.ndarray) -> "SetData":
        m = np.asarray(mask, dtype=bool)
        return SetData(self.keys.loc[m].reset_index(drop=True), None if self.y is None else self.y[m],
                       {l: v[m] for l, v in self.normal.items()},
                       self.x.loc[m].reset_index(drop=True) if self.x is not None else None)


def set_data(cfg: Any, run: Any, rival: Mapping[str, Any], lead: int, set_name: str, idx: Optional[pd.DataFrame],
             token: Any = None) -> SetData:
    sl = S.open_slim(cfg, run, lead)
    s = sl.read_set(set_name, lock=token, extras=False)
    k = keys_frame(s.keys, sl.season)
    x = join_index(k, idx, rival["stats"], "rival %s lead %d set %s" % (rival["id"], lead, set_name)) \
        if idx is not None else None
    return SetData(k, s.y, s.normal, x)


def predict_candidate(model: MP.MapModel, cand: Mapping[str, Any], sd: SetData, run: Any, lead: int,
                      eng: Any, H: Any) -> Tuple[np.ndarray, np.ndarray]:
    """(pre, clipped) of a fitted candidate on a set's rows (link_inverse, no smearing; clip_to_legal)."""
    link = cand["link"] or "identity"
    z0 = sd.normal[link]
    x = sd.x[cand["stat"]].to_numpy(np.float64)
    z = model.predict(x, z0, sd.keys["unit"].to_numpy(), sd.keys)
    pre = MP.link_inverse(z, link, run.c(lead), run.ub) if cand["family"] != "F0" else np.asarray(z, np.float64)
    return pre, H.clip(eng, pre, run.legal)


def fit_candidate(cand: Mapping[str, Any], sd: SetData, run: Any, lead: int, l1: bool = False) -> MP.MapModel:
    link = cand["link"] or "identity"
    x = sd.x[cand["stat"]].to_numpy(np.float64)
    ok = np.isfinite(x) & np.isfinite(sd.y)
    f = sd.subset(ok)
    args = (f.x[cand["stat"]].to_numpy(np.float64), f.y, f.normal[link], cand["link"], run.c(lead), run.ub,
            f.keys["unit"].to_numpy(), f.keys)
    if l1:
        return MP.fit_l1(cand["family"], *args)
    return MP.fit(cand["family"], *args)


# ===================================================================================================== tune
def _trial_paths(out: Path, rival_id: str, cand_id: str) -> Tuple[Path, Path, Path]:
    d = out / C.TRIALS_DIR / rival_id
    return d / (cand_id + ".json"), d / (cand_id + ".parquet"), d / (cand_id + ".map.json")


def _trial_hash(board, rival, cand, lead, fit_set, score_set) -> str:
    return _hash({"rival": rival, "candidate": cand, "lead": lead, "fit": fit_set, "score": score_set,
                  "index": board["rivals"][rival["id"]]["index"], "slim": board["slim"][str(lead)],
                  "tool": board["tool_code_sha256"], "c": board["run"]["c"].get(str(lead)),
                  "ub": board["run"]["ub"], "legal": board["run"]["legal"]})


def _adapter_ctx(ctx: Any, run: Any, registry: Mapping[str, Any], rival: Mapping[str, Any], lead: int,
                 stage: str, token: Any = None) -> IX.AdapterCtx:
    cfg = ctx.hcfg
    return IX.AdapterCtx(cfg, ctx, run, registry, C.load_products(cfg), rival, lead, stage, S.open_slim(cfg, run, lead),
                         token)


def tune(out: Any, resume: bool = False, config: Any = None) -> Path:
    """Fit every candidate of every ready rival on its pick set, score it on the covered pick rows (spec 1.6)."""
    cfg = C.load_config(config)
    with HumanCommand("tune", out, cfg, need_file=C.BOARD_FILE) as ctx:
        board, run, registry = load_board(ctx)
        if (ctx.out / C.PICKS_LOCK).is_file():
            refuse("the human picks are locked; tuning never runs again after the lock")
        traces = LK.test_side_files(ctx.out)
        if traces:
            refuse("this board already holds test-side files (%s)" % [str(p) for p in traces[:3]])
        tdir = ctx.out / C.TRIALS_DIR
        if tdir.is_dir() and any(tdir.iterdir()) and not resume:
            refuse("%s already holds trials" % tdir, fix="pass --resume")
        for rival in ready_rivals(board, registry):
            if rival.get("placebo_of"):
                ctx.log("tune", rival["id"], message="placebo of %s: takes its parent's pick (never tuned)"
                        % rival["placebo_of"])
                continue
            if rival.get("runner"):
                _tune_runner(ctx, board, run, registry, rival)
            else:
                _tune_index(ctx, board, run, rival)
        write_trials_csv(ctx, board, registry)
        return ctx.out


def _tune_index(ctx, board, run, rival) -> None:
    H, eng, cfg = ctx.H, ctx.eng, ctx.hcfg
    L, fit_set, score_set = pick_sets(rival)
    idx = IX.read_index(cfg, run, rival, L, stages=[s for s in IX.stages_of(rival) if s != C.STAGE_TEST])
    fit = set_data(cfg, run, rival, L, fit_set, idx)
    sc = set_data(cfg, run, rival, L, score_set, idx)
    cover = np.isfinite(sc.x[list(rival["stats"])].to_numpy(np.float64)).all(axis=1)
    scc = sc.subset(cover)
    cands = MP.candidates(rival, run.links)
    ctx.log("tune", rival["id"], message="%d candidates at lead %d (%s -> %s); %d of %d %s rows covered by every stat"
            % (len(cands), L, fit_set, score_set, int(cover.sum()), cover.size, score_set))
    for k, cand in enumerate(cands):
        jp, pp, mp_ = _trial_paths(ctx.out, rival["id"], cand["id"])
        h = _trial_hash(board, rival, cand, L, fit_set, score_set)
        if jp.is_file():
            rec = C.read_json(jp)
            ok = rec.get("config_hash") == h and (rec.get("status") != "ok" or (
                pp.is_file() and _sha(pp) == rec.get("preds_sha256")))
            if ok:
                continue
            for p in (jp, pp, mp_):
                ctx.move_aside(p)
        t0 = time.time()
        rec = {"rival": rival["id"], "candidate": cand["id"], "stat": cand["stat"], "family": cand["family"],
               "link": cand["link"], "order": cand["order"], "lead": L, "fit_set": fit_set, "score_set": score_set,
               "config_hash": h, "rows_score": int(scc.y.size)}
        try:
            if not scc.y.size:
                raise MP.NotCalibratable("no %s row is covered by every stat" % score_set)
            model = fit_candidate(cand, fit, run, L)
        except MP.NotCalibratable as exc:
            rec.update(status="not_calibratable", reason=str(exc))
            ctx.mkdir(jp.parent)
            ctx.write_once_json(jp, rec)
            ctx.log("trial", rival["id"], cand["id"], time.time() - t0, "not calibratable: %s" % exc)
            continue
        pre, pred = predict_candidate(model, cand, scc, run, L, eng, H)
        met = H.inner_metrics(eng, scc.y, pred, run.legal)
        frame = scc.keys[list(C.KEYS)].copy()
        frame["x"] = scc.x[cand["stat"]].to_numpy(np.float64)
        frame["pre"] = pre
        frame["pred"] = pred
        ctx.mkdir(jp.parent)
        ctx.write_parquet(pp, frame)
        ctx.replace_json(mp_, model.to_json())
        rec.update(status="ok", pick_mae=met["mae"], metrics=met, rows_fit=int(model.info.get("rows", 0)),
                   preds_sha256=_sha(pp), map_sha256=_sha(mp_), seconds=time.time() - t0)
        ctx.write_once_json(jp, rec)
        ctx.log("trial", rival["id"], "%d/%d %s" % (k + 1, len(cands), cand["id"]), time.time() - t0,
                "%s MAE %r (corr2 %.4g, predict-zero MAE %.6g)" % (score_set, met["mae"], met["corr2"],
                                                                   met["predict_zero_mae"]))


def _tune_runner(ctx, board, run, registry, rival) -> None:
    H, eng = ctx.H, ctx.eng
    L, fit_set, score_set = pick_sets(rival)
    cand = {"id": "method", "stat": None, "family": None, "link": None, "order": [0, 0, 0]}
    jp, pp, mp_ = _trial_paths(ctx.out, rival["id"], cand["id"])
    h = _trial_hash(board, rival, cand, L, fit_set, score_set)
    if jp.is_file():
        rec = C.read_json(jp)
        if rec.get("config_hash") == h and pp.is_file() and _sha(pp) == rec.get("preds_sha256"):
            return
        for p in (jp, pp, mp_):
            ctx.move_aside(p)
    t0 = time.time()
    runner = ME.load_runner(rival)
    actx = _adapter_ctx(ctx, run, registry, rival, L, C.STAGE_TRAIN)
    params = ME.run_fit(runner, actx, rival, L, fit_set)
    sl = S.open_slim(ctx.hcfg, run, L)
    sc = sl.read_set(score_set, extras=False)
    tier = C.lead_tiers(rival)[L]["tier"]
    pf, prec = ME.run_predict(runner, actx, rival, L, params, score_set, sc.keys, tier)
    pre = pf["pre"].to_numpy(np.float64)
    ok = np.isfinite(pre)
    pred = H.clip(eng, pre[ok], run.legal)
    met = H.inner_metrics(eng, sc.y[ok], pred, run.legal)
    frame = pf.loc[ok, list(C.KEYS)].reset_index(drop=True)
    frame["pre"] = pre[ok]
    frame["pred"] = pred
    ctx.mkdir(jp.parent)
    ctx.write_parquet(pp, frame)
    ctx.replace_json(mp_, {"family": None, "method": rival["runner"], "params": params})
    rec = {"rival": rival["id"], "candidate": "method", "stat": None, "family": None, "link": None,
           "order": cand["order"], "lead": L, "fit_set": fit_set, "score_set": score_set, "config_hash": h,
           "status": "ok", "pick_mae": met["mae"], "metrics": met, "rows_score": int(ok.sum()),
           "rows_not_predicted": int((~ok).sum()), "runner_check": prec, "preds_sha256": _sha(pp),
           "map_sha256": _sha(mp_), "seconds": time.time() - t0}
    ctx.write_once_json(jp, rec)
    ctx.log("trial", rival["id"], "method", time.time() - t0, "%s MAE %r on %d rows (%d not predicted)"
            % (score_set, met["mae"], int(ok.sum()), int((~ok).sum())))


def trial_records(out: Path, rival_id: str) -> List[Dict[str, Any]]:
    d = Path(out) / C.TRIALS_DIR / rival_id
    if not d.is_dir():
        return []
    return [C.read_json(p) for p in sorted(d.glob("*.json")) if not p.name.endswith(".map.json")]


def write_trials_csv(ctx: Any, board: Mapping[str, Any], registry: Mapping[str, Any]) -> None:
    rows = []
    for r in registry["rivals"]:
        for rec in trial_records(ctx.out, r["id"]):
            m = rec.get("metrics") or {}
            rows.append({"rival": r["id"], "candidate": rec["candidate"], "status": rec["status"],
                         "stat": rec.get("stat") or "", "family": rec.get("family") or "", "link": rec.get("link") or "",
                         "lead": rec["lead"], "score_set": rec["score_set"], "rows_score": rec.get("rows_score"),
                         "mae": m.get("mae"), "corr2": m.get("corr2"), "calibration_ratio": m.get("calibration_ratio"),
                         "predict_zero_mae": m.get("predict_zero_mae"), "reason": rec.get("reason", "")})
    frame = pd.DataFrame(rows)
    ctx.replace_bytes(ctx.out / C.TRIALS_CSV, frame.to_csv(index=False, lineterminator="\n").encode("utf-8"))


def pick_of(records: Sequence[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    """The lowest pick-set MAE over the calibratable candidates; ties by the fixed order (stat, family, link)."""
    best = None
    for r in sorted(records, key=lambda r: tuple(r["order"])):
        if r["status"] != "ok":
            continue
        v = float(r["pick_mae"])
        if not math.isfinite(v):
            refuse("candidate %s has a non-finite pick MAE" % r["candidate"])
        if best is None or v < float(best["pick_mae"]):
            best = r
    return best


# ===================================================================================================== lock
def lock(out: Any, config: Any = None, without: Sequence[str] = (), decision: str = "") -> Path:
    """Lock the picks, the coverage masks of every lead and every hash, before any test file (spec 1.11)."""
    cfg = C.load_config(config)
    with HumanCommand("lock", out, cfg, need_file=C.BOARD_FILE) as ctx:
        H, eng = ctx.H, ctx.eng
        board, run, registry = load_board(ctx)
        traces = LK.test_side_files(ctx.out)
        if traces:
            refuse("this board already holds test-side files (%s); picks are never locked after a test row was "
                   "touched" % [str(p) for p in traces[:3]])
        if (ctx.out / C.PICKS_LOCK).is_file():
            refuse("the human picks are already locked; picks are written once")
        if (ctx.out / C.PICKS_FILE).is_file():
            ctx.log("lock", message="human_picks.json without its lock (a killed lock): moved aside, locking again")
            ctx.move_aside(ctx.out / C.PICKS_FILE)
        if without and not decision.strip():
            refuse("--without needs --decision '<the owner decision recorded in the Part>'")
        write_trials_csv(ctx, board, registry)
        picks: Dict[str, Any] = {}
        by_id = rival_by_id(registry)
        for r in registry["rivals"]:
            rid = r["id"]
            st = board["rivals"][rid]
            if st["status"] != "ready":
                if rid in without:
                    picks[rid] = {"status": "dropped_by_owner_decision", "decision": decision, "waiting": st["waiting"]}
                    continue
                refuse("rival %s is waiting (%s); the board is locked without it only by an owner decision"
                       % (rid, " | ".join(st["waiting"])),
                       fix="lock --without %s --decision '<the owner decision, recorded in the Part>'" % rid)
            if r.get("placebo_of"):
                continue
            picks[rid] = _lock_one(ctx, board, run, r)
        for r in registry["rivals"]:
            if r.get("placebo_of") and board["rivals"][r["id"]]["status"] == "ready":
                parent = picks.get(r["placebo_of"]) or {}
                if parent.get("status") != "ok":
                    picks[r["id"]] = {"status": "parent_not_picked", "parent": r["placebo_of"]}
                    continue
                if parent.get("stat") not in r["stats"]:
                    refuse("placebo %s does not hold its parent's picked stat %s" % (r["id"], parent.get("stat")))
                rec = {k: parent[k] for k in ("stat", "family", "link", "form", "candidate")}
                rec.update(status="ok", placebo_of=r["placebo_of"], pick_mae=None)
                picks[r["id"]] = rec
        # coverage masks and timing per lead (label-free; saved test keys hold no y)
        for r in registry["rivals"]:
            rec = picks.get(r["id"])
            if not rec or rec.get("status") != "ok":
                continue
            rec["leads"] = {}
            cov_shas = {}
            for L, t in sorted(C.lead_tiers(r).items()):
                if t["tier"] == C.TIER_NONE:
                    rec["leads"][str(L)] = {"tier": C.TIER_NONE, "reason": t["reason"]}
                    continue
                mask_rec = _coverage_mask(ctx, board, run, r, rec, L)
                cov_shas[str(L)] = mask_rec["sha256"]
                rec["leads"][str(L)] = {"tier": t["tier"], "decides": t["decides"], "label": t["label"],
                                        "score_without_net": int(L) in [int(x) for x in r.get("score_without_net") or []],
                                        "timing": IX.Timing(run, r, L).record(), "coverage": mask_rec}
            rec["coverage_sha256"] = cov_shas
        doc = {"format": C.FORMAT_PICKS, "run_fingerprint": run.fingerprint, "picks": picks,
               "trials_csv_sha256": _sha(ctx.out / C.TRIALS_CSV), "board_json_sha256": _sha(ctx.out / C.BOARD_FILE),
               "common_harness_sha256": board["common_harness_sha256"], "tool_code_sha256": board["tool_code_sha256"],
               "slim": board["slim"], "index": {rid: st["index"] for rid, st in board["rivals"].items()},
               "owner_decision": {"without": list(without), "decision": decision} if without else None,
               "utc": H.utc_now()}
        LK.write_lock(ctx, doc)
        for rid, p in sorted(picks.items()):
            ctx.log("pick", rid, message="%s: %s" % (p.get("status"), ", ".join(
                "%s=%s" % (k, p.get(k)) for k in ("stat", "family", "link", "pick_mae") if k in p)))
        ctx.log("locked", message="human_picks.json sha %s" % _sha(ctx.out / C.PICKS_FILE))
        return ctx.out


def _lock_one(ctx, board, run, r) -> Dict[str, Any]:
    H, eng = ctx.H, ctx.eng
    recs = trial_records(ctx.out, r["id"])
    L, fit_set, score_set = pick_sets(r)
    if r.get("runner"):
        want = 1
    else:
        want = len(MP.candidates(r, run.links))
    if len(recs) != want:
        refuse("rival %s holds %d finished trials of %d" % (r["id"], len(recs), want), fix="tune --resume")
    for rec in recs:
        cand = {"id": rec["candidate"], "stat": rec["stat"], "family": rec["family"], "link": rec["link"],
                "order": rec["order"]}
        if rec.get("config_hash") != _trial_hash(board, r, cand, L, fit_set, score_set):
            refuse("trial %s/%s is stale (config hash)" % (r["id"], rec["candidate"]), fix="tune --resume")
    best = pick_of(recs)
    if best is None:
        return {"status": "not_calibratable", "reason": "; ".join(sorted(set(x.get("reason", "") for x in recs))),
                "lead": L}
    _, pp, mp_ = _trial_paths(ctx.out, r["id"], best["candidate"])
    if _sha(pp) != best["preds_sha256"]:
        refuse("trial %s/%s predictions changed" % (r["id"], best["candidate"]))
    rec = {"status": "ok", "candidate": best["candidate"], "stat": best["stat"], "family": best["family"],
           "link": best["link"], "form": "method" if r.get("runner") else ("as shipped" if best["family"] == "F0"
                                                                           else "calibrated"),
           "pick_lead": L, "pick_set": score_set, "pick_mae": best["pick_mae"], "pick_rows": best["rows_score"],
           "trial_preds_sha256": best["preds_sha256"], "map_sha256": best["map_sha256"]}
    if L == 0:
        ip = pq.read_table(str(pp)).to_pandas()
        sl = S.open_slim(ctx.hcfg, run, 0)
        inner = sl.read_set("inner", extras=False)
        k = keys_frame(inner.keys, sl.season)
        j = ip[["unit", "time", "issue", "pred"]].copy()
        j["unit"] = j["unit"].astype(str)
        jj = j.merge(k.assign(_y=inner.y)[["unit", "time", "issue", "_y"]], on=["unit", "time", "issue"], how="left",
                     validate="one_to_one")
        y = jj["_y"].to_numpy(np.float64)
        comp_name, comp = H._inner_comparator(ctx, run, "human", best["link"] or "identity",
                                              ip[["unit", "time"]], y)
        rmae, cmae = eng.metrics.mae(y, jj["pred"].to_numpy(np.float64)), eng.metrics.mae(y, comp)
        if rmae != float(best["pick_mae"]):
            refuse("rival %s: the saved inner MAE does not reproduce" % r["id"])
        rec["n2_lead_0"] = {"comparator": comp_name, "comparator_mae": cmae, "rival_mae": rmae,
                            "eligible": bool(eng.decide.n2_eligible(rmae, cmae)), "rows": int(y.size)}
    else:
        rec["n2_lead_0"] = "forecast-only: picked on lead-%d guard rows; its guard runs at refit" % L
    return rec


def _coverage_mask(ctx, board, run, r, pick, L) -> Dict[str, Any]:
    """The test rows of lead L the pick covers, from the index or the registry's label-free rule (no label read).
    Written to lead_<L>/coverage_<rival>.parquet in the saved order; its sha goes into the lock."""
    H, cfg = ctx.H, ctx.hcfg
    col, saved = H.saved_test_keys(run, L)
    keys = saved[["unit", "group", "time", "issue", "lead"]].reset_index(drop=True).copy()
    keys["unit"] = keys["unit"].astype(str)
    rule = r.get("coverage") or C.COVERAGE_X
    if rule == C.COVERAGE_X:
        idx = IX.read_index(cfg, run, r, L, stages=[C.STAGE_ALL])
        x = join_index(keys, idx, [pick["stat"]], "coverage of %s lead %d" % (r["id"], L))
        mask = np.isfinite(x[pick["stat"]].to_numpy(np.float64))
        how = "finite %s in the index" % pick["stat"]
    else:
        sl = S.open_slim(cfg, run, L)
        actx = IX.AdapterCtx(cfg, ctx, run, C.load_registry(cfg, run.package), C.load_products(cfg), r, L,
                             C.STAGE_TRAIN, sl)
        mask = coverage_rule_mask(rule, keys, sl.units(), "rival %s lead %d" % (r["id"], L), actx)
        how = "registry rule %s" % json.dumps(rule, sort_keys=True)
    frame = keys.copy()
    frame["covered"] = mask
    d = ctx.mkdir(ctx.out / (C.LEAD_DIR % L))
    p = d / (C.COVERAGE_FILE % r["id"])
    if p.is_file():
        ctx.move_aside(p)
    ctx.write_parquet(p, frame)
    g = frame.loc[mask].groupby("group").size()
    return {"file": str(p.relative_to(ctx.out)).replace("\\", "/"), "sha256": _sha(p), "rule": how,
            "rows": int(mask.sum()), "rows_total": int(mask.size), "groups": int(len(g)),
            "groups_total": int(frame["group"].nunique()),
            "groups_with_min_rows": int((g >= C.MIN_GROUP_TEST_ROWS).sum())}


def read_coverage(out: Path, pick: Mapping[str, Any], rival_id: str, lead: int) -> pd.DataFrame:
    rec = pick["leads"][str(lead)]["coverage"]
    p = Path(out) / rec["file"]
    if _sha(p) != rec["sha256"]:
        refuse("the coverage mask %s changed after the lock" % p)
    return pq.read_table(str(p)).to_pandas()


# ===================================================================================================== refit
def refit(out: Any, lead: int, resume: bool = False, config: Any = None) -> Path:
    """Per rival with a row at the lead: guard (N2), refit at the fit cut, raw and guarded test predictions."""
    cfg = C.load_config(config)
    lead = int(lead)
    with HumanCommand("refit", out, cfg, need_file=C.BOARD_FILE) as ctx:
        board, run, registry = load_board(ctx)
        token = LK.verify_lock(ctx.out)
        if lead not in run.leads:
            refuse("lead %d is not a lead of the run (%s)" % (lead, run.leads))
        picks = token.doc["picks"]
        ldir = ctx.mkdir(ctx.out / (C.LEAD_DIR % lead))
        fb_name, saved = ctx.H.saved_test_keys(run, lead)
        for r in registry["rivals"]:
            p = picks.get(r["id"])
            if not p or p.get("status") != "ok":
                continue
            lrec = p["leads"].get(str(lead))
            if not lrec or lrec["tier"] == C.TIER_NONE:
                continue
            done_p = ldir / (C.DONE_FILE % r["id"])
            h = _hash({"lead": lead, "pick": p, "tool": board["tool_code_sha256"], "picks": token.picks_sha256})
            if done_p.is_file():
                rec = C.read_json(done_p)
                if rec.get("hash") == h and resume:
                    ctx.log("refit", r["id"], message="skipped (finished, same hash)")
                    continue
                if rec.get("hash") == h:
                    refuse("lead %d %s is already refit" % (lead, r["id"]), fix="pass --resume")
                ctx.move_aside(done_p)
            for name in (C.PREDS_FILE, C.GUARD_FILE, C.MAP_FILE):
                ctx.move_aside(ldir / (name % r["id"]))
            _refit_one(ctx, board, run, registry, r, p, lead, token, saved, fb_name, ldir, done_p, h)
        return ctx.out


def _parent(registry, r):
    if r.get("placebo_of"):
        return rival_by_id(registry)[r["placebo_of"]]
    return r


def _refit_one(ctx, board, run, registry, r, p, lead, token, saved, fb_name, ldir, done_p, h) -> None:
    H, eng, cfg = ctx.H, ctx.eng, ctx.hcfg
    t0 = time.time()
    lrec = p["leads"][str(lead)]
    cov = read_coverage(ctx.out, p, r["id"], lead)
    skeys = saved[["unit", "group", "time", "issue", "lead"]].reset_index(drop=True).copy()
    skeys["unit"] = skeys["unit"].astype(str)
    if not (cov["unit"].astype(str).to_numpy() == skeys["unit"].to_numpy()).all() or \
            not np.array_equal(cov["time"].to_numpy(np.int64), skeys["time"].to_numpy(np.int64)):
        refuse("the coverage mask of %s lead %d is not in the saved test order" % (r["id"], lead))
    mask = cov["covered"].to_numpy(bool)
    no_net = bool(lrec.get("score_without_net"))
    fb = saved[fb_name].to_numpy(np.float64)
    sl = S.open_slim(cfg, run, lead)
    status = "ok"
    info: Dict[str, Any] = {}
    product_cell = np.array([""] * len(skeys), dtype=object)
    l1_pre = None
    if r.get("runner"):
        runner = ME.load_runner(r)
        actx = _adapter_ctx(ctx, run, registry, r, lead, C.STAGE_ALL, token)
        # guard
        if lead == pick_lead(r):
            gp = pq.read_table(str(_trial_paths(ctx.out, r["id"], "method")[1])).to_pandas()
            gkeys = gp[list(C.KEYS)]
            g_pred = gp["pred"].to_numpy(np.float64)
            g_pre = gp["pre"].to_numpy(np.float64)
            gset = "inner" if lead == 0 else "guard"
            guard_source = "the tuning run's %s predictions" % gset
        else:
            params_g = ME.run_fit(runner, actx, r, lead, "guardfit")
            gs = sl.read_set("guard", extras=False)
            gpf, _ = ME.run_predict(runner, actx, r, lead, params_g, "guard", gs.keys, lrec["tier"])
            ok = np.isfinite(gpf["pre"].to_numpy(np.float64))
            gkeys = gpf.loc[ok, list(C.KEYS)].reset_index(drop=True)
            g_pre = gpf["pre"].to_numpy(np.float64)[ok]
            g_pred = H.clip(eng, g_pre, run.legal)
            gset = "guard"
            guard_source = "a fit on the guard-fit rows, scored on the guard rows"
        gy, comp_name, comp = _guard_labels_and_comparator(ctx, run, lead, gset, gkeys, None, sl)
        # refit
        params = ME.run_fit(runner, actx, r, lead, "refit")
        tset = sl.keys("test")
        tpf, trec = ME.run_predict(runner, actx, r, lead, params, "test", tset, lrec["tier"])
        pos = H.to_saved_order(saved, tpf, "the saved test rows (%s)" % r["id"])
        t_pre_all = tpf["pre"].to_numpy(np.float64)[pos]
        bad = mask & ~np.isfinite(t_pre_all)
        if bad.any():
            refuse("rival %s lead %d: the runner predicts no value on %d rows of its locked coverage" %
                   (r["id"], lead, int(bad.sum())))
        t_pre = np.where(mask, t_pre_all, np.nan)
        info = {"runner_check": trec, "params_file": (C.MAP_FILE % r["id"])}
        ctx.replace_json(ldir / (C.MAP_FILE % r["id"]), {"method": r["runner"], "params": params,
                                                          "guard_params": None})
    else:
        base = _parent(registry, r)
        cand = {"id": p["candidate"], "stat": p["stat"], "family": p["family"], "link": p["link"]}
        stages_train = [s for s in IX.stages_of(r) if s != C.STAGE_TEST]
        idx_train = IX.read_index(cfg, run, r, lead, stages=stages_train)
        # guard
        fset, gset = ("tune", "inner") if lead == 0 else ("guardfit", "guard")
        gfit = set_data(cfg, run, r, lead, fset, idx_train)
        gsc = set_data(cfg, run, r, lead, gset, idx_train)
        gcov = np.isfinite(gsc.x[cand["stat"]].to_numpy(np.float64))
        gsc_c = gsc.subset(gcov)
        guard_ok = True
        try:
            gmodel = fit_candidate(cand, gfit, run, lead)
        except MP.NotCalibratable as exc:
            gmodel = None
            if no_net:
                # Q12 b: a lead scored WITHOUT the safety net keeps its row when the guard cannot be fitted (too few
                # guard-fit rows); guarded = raw, flagged (review issue 6)
                guard_ok = False
                info["guard_not_run"] = ("guard fit (%s) not calibratable: %s; no safety net at this lead (Q12 b), "
                                         "guarded = raw" % (fset, exc))
            else:
                status = "not_calibratable"
                info["reason"] = "guard fit (%s): %s" % (fset, exc)
        if status == "ok":
            # refit at the fit cut
            rfit = set_data(cfg, run, r, lead, "refit", idx_train)
            try:
                model = fit_candidate(cand, rfit, run, lead)
            except MP.NotCalibratable as exc:
                status = "not_calibratable"
                info["reason"] = "refit: %s" % exc
                model = None
        if status == "ok":
            if guard_ok:
                g_pre, g_pred = predict_candidate(gmodel, cand, gsc_c, run, lead, eng, H)
                gkeys = gsc_c.keys[list(C.KEYS)]
                gy, comp_name, comp = _guard_labels_and_comparator(ctx, run, lead, gset, gkeys, gsc_c, sl,
                                                                   cand["link"])
                if not np.array_equal(gy, gsc_c.y):
                    refuse("internal: the guard labels differ from the slim labels")
                guard_source = "the pick fitted on the %s rows, scored on the covered %s rows" % (fset, gset)
                if lead == 0 and not r.get("placebo_of") and pick_lead(r) == 0:
                    _check_trial_reproduces(ctx, r, p, gsc_c, g_pred)
            else:
                gkeys, gy, g_pre, g_pred, comp_name, comp = None, None, None, None, None, None
                guard_source = "not run: %s" % info["guard_not_run"]
            # test rows (after the lock): the index's test rows (one go, or the test stage) and the slim test normals
            idx_test = IX.read_index(cfg, run, r, lead, stages=[s for s in IX.stages_of(r)], lock_token=token)
            ts = set_data(cfg, run, r, lead, "test", idx_test, token=token)
            pos = H.to_saved_order(saved, ts.keys, "the saved test rows (%s)" % r["id"])
            ts = SetData(ts.keys.iloc[pos].reset_index(drop=True), None, {l: v[pos] for l, v in ts.normal.items()},
                         ts.x.iloc[pos].reset_index(drop=True))
            xs = ts.x[cand["stat"]].to_numpy(np.float64)
            if (r.get("coverage") or C.COVERAGE_X) == C.COVERAGE_X or IX.stages_of(r) != (C.STAGE_ALL,):
                now = np.isfinite(xs)
                if (r.get("coverage") or C.COVERAGE_X) == C.COVERAGE_X and not np.array_equal(now, mask):
                    refuse("rival %s lead %d: the index's test coverage differs from the locked mask" % (r["id"], lead))
                if (r.get("coverage") or C.COVERAGE_X) != C.COVERAGE_X and (mask & ~now).any():
                    refuse("rival %s lead %d: the test-stage index misses %d rows of the locked coverage (rule %s)"
                           % (r["id"], lead, int((mask & ~now).sum()), r.get("coverage")))
            tc = ts.subset(mask)
            t_pre_c, _ = predict_candidate(model, cand, tc, run, lead, eng, H)
            t_pre = np.full(len(skeys), np.nan)
            t_pre[mask] = t_pre_c
            pc = join_index(ts.keys, idx_test, [C.COL_PRODUCT_CELL], "product cells of %s" % r["id"])
            product_cell = pc[C.COL_PRODUCT_CELL].astype(str).to_numpy()
            ctx.replace_json(ldir / (C.MAP_FILE % r["id"]), {"refit": model.to_json(),
                                                             "guard": gmodel.to_json() if gmodel is not None else None,
                                                             "candidate": cand})
            if board["data_rules"]["l1_print"]:
                try:
                    l1 = fit_candidate(cand, rfit, run, lead, l1=True)
                    l1_pre = np.full(len(skeys), np.nan)
                    zl1 = l1.predict(tc.x[cand["stat"]].to_numpy(np.float64), tc.normal[l1.link or "identity"],
                                     tc.keys["unit"].to_numpy(), tc.keys)
                    l1_pre[mask] = MP.link_inverse(zl1, l1.link or "identity", run.c(lead), run.ub)
                    info["l1"] = {"family": l1.family, "of": cand["family"]}
                except MP.NotCalibratable as exc:
                    info["l1"] = {"not_calibratable": str(exc)}
    if status != "ok":
        done = {"hash": h, "lead": lead, "rival": r["id"], "status": status, "info": info, "utc": H.utc_now()}
        ctx.write_once_json(done_p, done)
        ctx.log("refit", r["id"], message="lead %d: NOT calibratable (%s): no row, disclosed" % (lead, info["reason"]))
        return
    m = eng.metrics
    guard_run = gy is not None
    if guard_run:
        g_mae, c_mae = m.mae(gy, g_pred), m.mae(gy, comp)
        passed = bool(eng.decide.n2_eligible(g_mae, c_mae))
        gframe = gkeys.reset_index(drop=True).copy()
        gframe["y"] = gy
        gframe["pre"] = g_pre
        gframe["pred"] = g_pred
        gframe["comparator"] = comp
        gframe["guard_passed"] = passed
        ctx.write_parquet(ldir / (C.GUARD_FILE % r["id"]), gframe)
    else:                                            # only on a no-net lead (Q12 b): nothing to guard with
        if not no_net:
            refuse("internal: the guard did not run on a lead with a safety net")
        g_mae, c_mae, passed = None, None, False
    t_raw = np.full(len(skeys), np.nan)
    t_raw[mask] = H.clip(eng, t_pre[mask], run.legal)
    if no_net:
        guarded = t_raw.copy()
    else:
        guarded = np.where(mask, t_raw if passed else fb, np.nan)
    filled = np.where(mask, guarded, fb)
    pframe = skeys.copy()
    if not r.get("runner"):
        xs_saved = np.full(len(skeys), np.nan)
        xs_saved[mask] = tc.x[cand["stat"]].to_numpy(np.float64)
        pframe["x"] = xs_saved
    pframe["covered"] = mask
    pframe["pre"] = t_pre
    pframe["raw"] = t_raw
    pframe["guarded"] = guarded
    pframe["filled"] = filled
    pframe["guard_passed"] = passed
    pframe["guard_run"] = guard_run
    pframe["no_safety_net"] = no_net
    pframe[C.COL_PRODUCT_CELL] = product_cell
    if l1_pre is not None:
        pframe["l1_pre"] = l1_pre
        pframe["l1_raw"] = np.where(mask, H.clip(eng, np.nan_to_num(l1_pre), run.legal), np.nan)
    ctx.write_parquet(ldir / (C.PREDS_FILE % r["id"]), pframe)
    done = {"hash": h, "lead": lead, "rival": r["id"], "status": "ok", "tier": lrec["tier"],
            "guard": {"rows": int(gy.size) if guard_run else 0, "rival_mae": g_mae, "comparator": comp_name,
                      "comparator_mae": c_mae, "passed": passed if guard_run else None, "run": guard_run,
                      "source": guard_source, "score_without_net": no_net},
            "fallback": fb_name, "covered_rows": int(mask.sum()), "test_rows": int(mask.size), "info": info,
            "preds_sha256": _sha(ldir / (C.PREDS_FILE % r["id"])), "seconds": time.time() - t0, "utc": H.utc_now()}
    ctx.write_once_json(done_p, done)
    ctx.log("refit", r["id"], seconds=time.time() - t0,
            message="lead %d: covered %d of %d test rows; guard %s%s" % (
                lead, int(mask.sum()), mask.size,
                ("%r vs %s %r: %s" % (g_mae, comp_name, c_mae, "passed" if passed else "failed")) if guard_run
                else "NOT RUN (%s)" % info.get("guard_not_run"),
                "; NO SAFETY NET (guarded = raw)" if no_net else ""))


def _guard_labels_and_comparator(ctx, run, lead, gset, gkeys, gsc_c, sl, link=None):
    """Labels of the covered guard rows (slim, checked against the run's saved file byte for byte by the harness
    helpers) and the N2 comparator: lead 0 inner_preds (H._inner_comparator), lead L guard_preds
    (H._guard_comparator); learner 'human', the pick's link (F0 and M: identity)."""
    H = ctx.H
    s = sl.read_set(gset, extras=False)
    k = s.keys[["unit", "time", "issue"]].copy()
    k["unit"] = k["unit"].astype(str)
    k["_y"] = s.y
    for l in run.links:
        k["_n_" + l] = s.normal[l]
    g = gkeys[["unit", "time", "issue"]].copy()
    g["unit"] = g["unit"].astype(str)
    j = g.merge(k, on=["unit", "time", "issue"], how="left", validate="one_to_one")
    if j["_y"].isna().any():
        refuse("internal: %d guard rows have no slim label" % int(j["_y"].isna().sum()))
    gy = j["_y"].to_numpy(np.float64)
    lk = link or "identity"
    if gset == "inner":
        name, comp = H._inner_comparator(ctx, run, "human", lk, g[["unit", "time"]], gy)
    else:
        sd = SimpleNamespace(normal={l: j["_n_" + l].to_numpy(np.float64) for l in run.links})
        name, comp = H._guard_comparator(ctx, run, lead, "human", lk, sd, g, gy,
                                         {"c": run.c(lead), "ub": run.ub})
    return gy, name, np.asarray(comp, dtype=np.float64)


def _check_trial_reproduces(ctx, r, p, gsc_c, g_pred) -> None:
    """Lead 0: the pick refit on the tune rows reproduces its tuning predictions byte for byte on the rows every
    stat covers (determinism)."""
    _, pp, _ = _trial_paths(ctx.out, r["id"], p["candidate"])
    tp = pq.read_table(str(pp)).to_pandas()
    a = gsc_c.keys[["unit", "time", "issue"]].copy()
    a["_p"] = g_pred
    tp["unit"] = tp["unit"].astype(str)
    j = tp[["unit", "time", "issue", "pred"]].merge(a, on=["unit", "time", "issue"], how="left")
    if j["_p"].isna().any() or j["_p"].to_numpy(np.float64).tobytes() != j["pred"].to_numpy(np.float64).tobytes():
        refuse("determinism check failed: rival %s's pick refit on the tune rows does not reproduce its tuning "
               "predictions byte for byte" % r["id"])


# ===================================================================================================== score
def _ours_frame(run: Any, lead: int, saved: pd.DataFrame) -> pd.DataFrame:
    keep = [c for c in ("unit", "group", "time", "year", "lead", "issue", "y", "normal", "legal_min", "legal_max")
            if c in saved.columns]
    frame = saved[keep].copy()
    for c in saved.columns:
        if c.startswith("base__"):
            frame[c] = saved[c]
    headline, raw = run.ours(lead)
    for name, col in (("ours", headline), ("ours_raw", raw)):
        if col not in saved.columns:
            refuse("lead %d: our column %s is not in the saved test rows" % (lead, col))
        frame["arm__" + name] = saved[col].to_numpy(np.float64)
        pre = "pre__" + col[len("arm__"):] if col.startswith("arm__") else None
        if pre and pre in saved.columns:
            frame["pre__" + name] = saved[pre].to_numpy(np.float64)
    return frame


def _contrast(eng, H, run, gt, pt, rcol, ocol, what, rows_basis="all"):
    m = eng.metrics
    rmap = m.metric_by_key(gt, rcol, "mae", "group", rows_basis=rows_basis)
    omap = m.metric_by_key(gt, ocol, "mae", "group", rows_basis=rows_basis)
    groups, d = m._paired_contrast(rmap, omap, what)
    tag, jk = m.contrast_tag(d, run.band)
    bj = m.blocked_jackknife(dict(zip(groups, d.tolist())), run.block_of_group) if run.block_of_group else None

    def pooled(col):
        sel = pt[(pt["line"] == "pooled") & (pt["column"] == col) & (pt["rows_basis"] == rows_basis)]
        if len(sel) != 1:
            refuse("the pooled table has %d lines for %s on %s" % (len(sel), col, rows_basis))
        rr = sel.iloc[0]
        return {k: float(rr[k]) for k in ("mae", "corr2", "calibration_ratio", "hit", "anom_r2")}

    pr, po = pooled(rcol), pooled(ocol)
    timid = bool(pr["mae"] < po["mae"] and (
        (math.isfinite(pr["calibration_ratio"]) and pr["calibration_ratio"] < 0.5)
        or (math.isfinite(pr["corr2"]) and math.isfinite(po["corr2"]) and pr["corr2"] < 0.5 * po["corr2"])))
    return {"verdict": H.VERDICT_WORDS[tag.value], "tag": tag.value, "d_mean": jk.mean, "d_se": jk.se,
            "d_low": jk.low, "d_high": jk.high, "n_groups": jk.n_groups,
            "blocked_mean": None if bj is None else bj.mean, "blocked_se": None if bj is None else bj.se,
            "rival_mae": pr["mae"], "ours_mae_same_rows": po["mae"], "anomaly_r2": pr["anom_r2"],
            "corr2": pr["corr2"], "hit": pr["hit"], "calibration_ratio": pr["calibration_ratio"],
            "ours_corr2": po["corr2"], "timid_win": timid}


def score(out: Any, lead: int, config: Any = None) -> Path:
    """Score every human rival of the lead with the engine's own functions (spec 1.9). The ONE reader of test y."""
    cfg = C.load_config(config)
    lead = int(lead)
    with HumanCommand("score", out, cfg, need_file=C.BOARD_FILE) as ctx:
        H, eng = ctx.H, ctx.eng
        board, run, registry = load_board(ctx)
        token = LK.verify_lock(ctx.out)
        picks = token.doc["picks"]
        ldir = ctx.out / (C.LEAD_DIR % lead)
        rivals = []
        need = []
        for r in registry["rivals"]:
            p = picks.get(r["id"])
            if not p or p.get("status") != "ok":
                continue
            lrec = p["leads"].get(str(lead))
            if not lrec or lrec["tier"] == C.TIER_NONE:
                continue
            need.append(ldir / (C.DONE_FILE % r["id"]))
            rivals.append((r, p, lrec))
        refs_json = ldir / C.REFS_JSON
        if lead == 0:
            need.append(refs_json)
        opened = LK.open_test_labels(ctx, run, lead, need)
        saved = opened["frame"]
        frame = _ours_frame(run, lead, saved)
        refs_cols: List[str] = []
        if (ldir / C.REFS_FILE).is_file():
            rf = pq.read_table(str(ldir / C.REFS_FILE)).to_pandas()
            j = H._join(saved[["unit", "time", "lead"]], rf, ["unit", "time", "lead"], C.REFS_FILE)
            for c in rf.columns:
                if c.startswith("base__"):
                    frame[c] = j[c].to_numpy(np.float64)
                    refs_cols.append(c)
        m = eng.metrics
        tol, floor, kind = run.tol, run.floor, run.kind
        sdir = ctx.mkdir(ctx.out / C.SCORES_DIR)
        t_all = {"group": m.score_table(frame, ("group",), tol, floor, kind),
                 "pooled": m.score_table(frame, (), tol, floor, kind)}
        if "year" in frame.columns:
            t_all["year"] = m.score_table(frame, ("year",), tol, floor, kind)
        ours_check = H.check_ours_against_run(run, lead, t_all["group"], t_all["pooled"])
        ctx.log("ours", message="our columns vs the run's own scores (all rows): %s" % ours_check["result"])
        for name, t in t_all.items():
            ctx.replace_bytes(sdir / ("lead_%d_all_%s.csv" % (lead, name)),
                              t.to_csv(index=False, lineterminator="\n").encode("utf-8"))
        ctx.replace_json(sdir / ("lead_%d_ours_check.json" % lead), ours_check)
        ours_all = H._pooled(t_all["pooled"], "arm__ours")["mae"]
        units = S.open_slim(cfg, run, lead).units()
        rows: List[Dict[str, Any]] = []
        for r, p, lrec in rivals:
            done = C.read_json(ldir / (C.DONE_FILE % r["id"]))
            if done["status"] != "ok":
                rows.append(_row(run, lead, r, lrec, "guarded_vs_headline", {"verdict": "NOT CALIBRATABLE"},
                                 flags=["not calibratable: %s" % done["info"].get("reason")]))
                continue
            pp = ldir / (C.PREDS_FILE % r["id"])
            if _sha(pp) != done["preds_sha256"]:
                refuse("%s changed after refit" % pp)
            pf = pq.read_table(str(pp)).to_pandas()
            j = H._join(saved[["unit", "time", "lead"]], pf, ["unit", "time", "lead"], pp.name)
            cov = j["covered"].to_numpy(bool)
            f = frame.copy()
            f["arm__rival"] = j["guarded"].to_numpy(np.float64)
            f["arm__rival_raw"] = j["raw"].to_numpy(np.float64)
            f["pre__rival_raw"] = j["pre"].to_numpy(np.float64)
            f["arm__rival_filled"] = j["filled"].to_numpy(np.float64)
            if "l1_raw" in j.columns:
                f["arm__rival_l1_raw"] = j["l1_raw"].to_numpy(np.float64)
            fc = f.loc[cov].reset_index(drop=True)
            gcount = fc.groupby("group").size()
            dec_groups = sorted(gcount.index[gcount >= C.MIN_GROUP_TEST_ROWS].astype(str).tolist())
            fd = fc[fc["group"].astype(str).isin(dec_groups)].reset_index(drop=True)
            filled_cols = [c for c in f.columns if not c.startswith(("arm__rival", "pre__rival"))] + ["arm__rival_filled"]
            ff = f[filled_cols].rename(columns={"arm__rival_filled": "arm__rival_filled_all_rows"})
            t_fill = m.score_table(ff, (), tol, floor, kind)
            years = sorted(set(fc["year"].astype(int).tolist())) if "year" in fc.columns else []
            base_flags = []
            if lrec.get("score_without_net"):
                base_flags.append(C.NO_SAFETY_NET)
            if done["guard"].get("run") is False:
                base_flags.append("guard not run (too few guard-fit rows; guarded = raw)")
            if lrec["tier"] == "X" and not r.get("placebo_of"):
                base_flags.append("extension")
            if not cov.all():
                base_flags.append("coverage %d of %d rows" % (int(cov.sum()), cov.size))
            if r.get("placebo_of"):
                base_flags.append("placebo of %s (a check: the guard should decline it; printed only)" % r["placebo_of"])
            common = {"rows": int(len(fd)), "rows_covered": int(cov.sum()), "rows_total": int(cov.size),
                      "groups": len(dec_groups), "groups_covered": int(len(gcount)),
                      "groups_total": int(frame["group"].nunique()), "years": years,
                      "ours_mae_all_rows": ours_all, "guard_passed": done["guard"]["passed"],
                      "filled_mae_all_rows": H._pooled(t_fill, "arm__rival_filled_all_rows")["mae"],
                      "rival_kind": r["kind"]}
            if not len(fd):
                rows.append(_row(run, lead, r, lrec, "guarded_vs_headline",
                                 dict(common, verdict="CANNOT TELL", note="no group has >= %d covered test rows"
                                      % C.MIN_GROUP_TEST_ROWS), flags=base_flags))
                continue
            tabs = {"group": m.score_table(fd, ("group",), tol, floor, kind),
                    "pooled": m.score_table(fd, (), tol, floor, kind),
                    "pooled_all_covered": m.score_table(fc, (), tol, floor, kind), "filled_all_rows": t_fill}
            if "year" in fd.columns:
                tabs["year"] = m.score_table(fd, ("year",), tol, floor, kind)
            tabs.update(H._strata_tables(ctx, board, run, units, fd, tol, floor, kind))
            if "seen_during_design" in units.columns and units["seen_during_design"].astype(bool).any():
                seen = set(units.loc[units["seen_during_design"].astype(bool), "unit"].astype(str))
                f2 = fd[~fd["unit"].astype(str).isin(seen)].reset_index(drop=True)
                if len(f2):
                    tabs["pooled_unseen"] = m.score_table(f2, (), tol, floor, kind)
            if r.get("resolution_matched"):
                pc_cov = j.loc[cov, C.COL_PRODUCT_CELL].astype(str).to_numpy()
                pc_dec = pc_cov[fc["group"].astype(str).isin(dec_groups).to_numpy()]
                tabs.update(_resolution_matched(m, fd, pc_dec, tol, floor, kind))
            for name, t in tabs.items():
                ctx.replace_bytes(sdir / ("lead_%d_%s_%s.csv" % (lead, r["id"], name)),
                                  t.to_csv(index=False, lineterminator="\n").encode("utf-8"))
            gt, pt = tabs["group"], tabs["pooled"]
            normal_col = "base__guess_normal" if "base__guess_normal" in fd.columns else (
                run.decline_target if run.decline_target in fd.columns else None)
            nmae = H._pooled(pt, normal_col)["mae"] if normal_col else None
            for cname, rcol, ocol in (("guarded_vs_headline", "arm__rival", "arm__ours"),
                                      ("raw_vs_raw", "arm__rival_raw", "arm__ours_raw")):
                res = _contrast(eng, H, run, gt, pt, rcol, ocol, "%s %s" % (r["id"], cname))
                rows.append(_row(run, lead, r, lrec, cname, dict(common, normal_mae_same_rows=nmae, **res),
                                 flags=list(base_flags)))
            if "arm__rival_l1_raw" in fd.columns:
                res = _contrast(eng, H, run, gt, pt, "arm__rival_l1_raw", "arm__ours_raw", "%s l1" % r["id"])
                l1_words = ("L1 isotonic calibration of the as-shipped index (the pick is F0; printed beside, Q13; "
                            "never decides)" if p.get("family") == "F0" else
                            "L1 map printed beside (Q13), never decides")
                rows.append(_row(run, lead, r, lrec, "l1_raw_vs_raw", dict(common, normal_mae_same_rows=nmae, **res),
                                 flags=list(base_flags) + [l1_words], force_no_decide=True))
        # reference rows (all rows; a reference column missing on some rows is read on its own basis)
        for rc in refs_cols + [c for c in frame.columns if c.startswith("base__") and c not in refs_cols]:
            gt_all = t_all["group"]
            basis = rc if (gt_all["rows_basis"] == rc).any() else "all"
            try:
                res = _contrast(eng, H, run, gt_all, t_all["pooled"], rc, "arm__ours", "reference %s" % rc,
                                rows_basis=basis)
            except Exception as exc:                         # a reference column the engine cannot pair: printed
                if not isinstance(exc, ctx.H.HarnessRefusal) and "R34" not in str(exc) and "G-DECIDE" not in str(exc):
                    raise
                rows.append({"lead": lead, "rival": rc, "rival_type": "reference", "contrast": "reference_vs_headline",
                             "verdict": "NOT PAIRED", "note": str(exc)[:200], "decides": False})
                continue
            bl_note = registry.get("nowcast_baseline_note")      # a package field, set where a ruling says so
            rows.append({"lead": lead, "rival": rc, "rival_type": "reference", "kind": "-", "tier": "-",
                         "contrast": "reference_vs_headline", "decides": False, "rows_basis": basis,
                         "ours_mae_all_rows": ours_all, **res,
                         "flags": str(bl_note) if (bl_note and lead == 0 and rc.startswith("base__human_")
                                                   and rc.endswith("persistence")) else ""})
        bl = pd.DataFrame(rows)
        ctx.replace_bytes(ctx.out / (C.BOARD_LEAD_CSV % lead), bl.to_csv(index=False, lineterminator="\n").encode("utf-8"))
        for r_ in rows:
            if r_.get("decides"):
                ctx.log("verdict", r_["rival"], message="ours vs %s (guarded, %s): %s; d = %s"
                        % (r_["rival"], r_.get("tier"), r_.get("verdict"), r_.get("d_mean")))
        return ctx.out


def _row(run, lead, r, lrec, contrast, res, flags=(), force_no_decide=False) -> Dict[str, Any]:
    decides = bool(lrec["decides"]) and contrast == "guarded_vs_headline" and not r.get("placebo_of") \
        and not force_no_decide
    out = {"lead": lead, "rival": r["id"], "rival_type": "human", "kind": r["kind"], "tier": lrec["tier"],
           "decides": decides, "rows_basis": "covered", "contrast": contrast, "band": run.band,
           "label": lrec.get("label") or "", "flags": "; ".join(flags)}
    out.update(res)
    return out


def _resolution_matched(m, fd, product_cell, tol, floor, kind) -> Dict[str, pd.DataFrame]:
    """PROT H15: y, ours and the rival averaged by (group, product_cell, time), scored the same way (printed only)."""
    f = fd.copy()
    f["product_cell"] = np.asarray(product_cell).astype(str)
    cols = [c for c in ("y", "normal", "arm__ours", "arm__ours_raw", "arm__rival", "arm__rival_raw") if c in f.columns]
    agg = f.groupby(["group", "product_cell", "time"], sort=True)[cols].mean().reset_index()
    agg["unit"] = agg["product_cell"]
    return {"resolution_matched_pooled": m.score_table(agg, (), tol, floor, kind),
            "resolution_matched_group": m.score_table(agg, ("group",), tol, floor, kind)}


# ===================================================================================================== board
READING_RULES = [
    "\"ours beats rival X\" is claimed only from a guarded_vs_headline row with tier P or L (decides = True).",
    "On a covered-rows row the claim is \"on the k%% of rows the product covers\" (k = rows covered / all rows); the "
    "deciding rows are the covered rows of groups with enough covered rows; coverage, our all-row MAE and the filled "
    "line are printed beside and never decide.",
    "A tier-A row reads as \"what that extra observation is worth\"; a tier-X row that is not a placebo is a labelled "
    "statistical extension; neither decides.",
    "A placebo row (flag \"placebo of ...\") is the parent's pick fed a time-shifted product: a check that the guard "
    "declines it, never a rival and never a verdict.",
    "A timid win is printed with its flag; verdicts are not changed.",
    "A tier-L row's BEATS is worded with its label (e.g. \"beats the nowcast rule fed old inputs\"), never as a win "
    "over the product itself.",
]


def board_md(out: Any, config: Any = None) -> Path:
    """human_board.md from every scored lead, with the registry's "no human rival" lines and joint claims."""
    cfg = C.load_config(config)
    with HumanCommand("board", out, cfg, need_file=C.BOARD_FILE) as ctx:
        bd, run, registry = load_board(ctx)
        files = sorted(ctx.out.glob(C.BOARD_LEAD_GLOB), key=lambda p: int(p.stem.split("_")[-1]))
        if not files:
            refuse("no %s yet" % C.BOARD_LEAD_GLOB, fix="score a lead first")
        lines = ["# Human rivals board", "",
                 "Run: %s (fingerprint %s). Band %r (the nowcast band at every lead). d = rival MAE - our MAE per group "
                 "on the covered rows of groups with >= %d covered rows; d > 0 means ours is better. BEATS = ours "
                 "beats the rival." % (run.name, run.fingerprint[:8], run.band, C.MIN_GROUP_TEST_ROWS), ""]
        scored = {int(p.stem.split("_")[-1]): pd.read_csv(p) for p in files}
        for L in run.leads:
            lines.append("## Lead %d" % L)
            if L not in scored:
                lines.append("not scored yet")
                lines.append("")
                continue
            t = scored[L]
            human = t[t["rival_type"] == "human"] if len(t) else t
            pkg = no_rival_reason(registry, L)
            if not len(human):
                reasons = sorted(set(C.lead_tiers(r)[L]["reason"] for r in registry["rivals"]
                                     if C.lead_tiers(r).get(L, {}).get("tier") == C.TIER_NONE))
                lines.append("no human rival: %s" % (pkg or "; ".join(reasons) or "none listed"))
            elif pkg:                                    # Q1, Q8 a: printed even when the lead has (A / L / X) rows
                lines.append("no published forecast at this lead: %s" % pkg)
            if len(human):
                order = human_rival_order(registry, L, human["rival"].astype(str).tolist())
                rank = {rid: i for i, rid in enumerate(order)}
                hs = human.assign(_o=human["rival"].astype(str).map(rank), _k=np.arange(len(human)))
                hs = hs.sort_values(["_o", "_k"], kind="mergesort").drop(columns=["_o", "_k"])
                t = pd.concat([hs, t[t["rival_type"] != "human"]], ignore_index=True)
            lines.append("")
            lines.append("| rival | type | tier | label | decides | contrast | ours vs rival | d mean | d low | d high | "
                         "rival MAE | our MAE (same rows) | rows covered (of all) | deciding rows | groups | guard | "
                         "timid | flags |")
            lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
            for _, rr in t.iterrows():
                def g(k, fmt="%.6g"):
                    v = rr.get(k)
                    try:
                        return fmt % float(v) if v is not None and str(v) != "nan" else ""
                    except (TypeError, ValueError):
                        return str(v)
                lab = rr.get("label") if isinstance(rr.get("label"), str) else ""
                lines.append("| %s | %s | %s | %s | %s | %s | %s%s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s "
                             "| %s |" % (
                                 rr.get("rival"), rr.get("rival_type"), rr.get("tier", ""), lab, rr.get("decides"),
                                 rr.get("contrast"), rr.get("verdict"),
                                 (" (%s)" % lab) if lab and str(rr.get("verdict")) == "BEATS" else "",
                                 g("d_mean"), g("d_low"), g("d_high"), g("rival_mae"), g("ours_mae_same_rows"),
                                 ("%s of %s" % (g("rows_covered", "%d"), g("rows_total", "%d")))
                                 if g("rows_covered", "%d") else "", g("rows", "%d"), g("groups", "%d"),
                                 rr.get("guard_passed", ""), rr.get("timid_win", ""),
                                 rr.get("flags", "") if isinstance(rr.get("flags"), str) else ""))
            for jc in registry.get("joint_claims") or []:
                line = joint_claim_line(jc, t, registry, L)
                if line:
                    lines.append("")
                    lines.append(line)
            lines.append("")
        lines.append("Reading rules:")
        lines.extend("- " + x.replace("%%", "%") for x in READING_RULES)
        ctx.replace_bytes(ctx.out / C.BOARD_MD, ("\n".join(lines) + "\n").encode("utf-8"))
        ctx.log("board", message="%d lead table(s)" % len(files))
        return ctx.out


def status(out: Any) -> str:
    """Plain progress of a human board (read-only, takes no lock)."""
    import psutil
    out = Path(out)
    lines = ["human board: %s" % out]
    sp = out / C.STATUS_FILE
    if sp.is_file():
        st = C.read_json(sp)
        alive = False
        try:
            alive = psutil.pid_exists(int(st.get("pid")))
        except (TypeError, ValueError):
            pass
        lines.append("last status: %s %s %s %s at %s (pid %s: %s)" % (
            st.get("command"), st.get("stage"), st.get("rival") or "", st.get("trial") or "", st.get("utc"),
            st.get("pid"), "RUNNING" if alive else "not running"))
    bp = out / C.BOARD_FILE
    if bp.is_file():
        b = C.read_json(bp)
        for rid, st in sorted(b.get("rivals", {}).items()):
            lines.append("rival %s: %s%s" % (rid, st["status"], (" (" + " | ".join(st["waiting"]) + ")")
                                             if st.get("waiting") else ""))
    td = out / C.TRIALS_DIR
    if td.is_dir():
        lines.append("finished trials: %d" % len([p for p in td.glob("*/*.json") if not p.name.endswith(".map.json")]))
    lines.append("picks locked: %s" % ("yes" if (out / C.PICKS_LOCK).is_file() else "no"))
    for ld in sorted(out.glob("lead_*")):
        lines.append("%s: refit done for %s; refs: %s; scored: %s" % (
            ld.name, sorted(p.stem[len("done_"):] for p in ld.glob("done_*.json")) or "none",
            "yes" if (ld / C.REFS_JSON).is_file() else "no",
            "yes" if (out / (C.BOARD_LEAD_CSV % int(ld.name.split("_")[1]))).is_file() else "no"))
    lp = out / C.LOG_FILE
    if lp.is_file():
        tail = lp.read_text(encoding="utf-8").splitlines()[-5:]
        lines.append("last log lines:")
        lines.extend("  " + t for t in tail)
    return "\n".join(lines)
