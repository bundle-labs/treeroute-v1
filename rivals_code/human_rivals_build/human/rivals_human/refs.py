"""Reference rows at the nowcast (SPEC_HUMAN.txt 1.10; Q4, Q23; PLAN :76-77). Generic; run after the human lock.

Grids with a history block:
  persistence          = baseline_persistence(the float64 label at the T2 step) (MET:436); the export's hist_last_1
                         (float32) holds that label (LAD:880-893) and must equal it in float32 on every row.
  damped persistence   = baseline_damped_persistence (MET:534): normal_target = nfit__identity of the row,
                         normal_issue = the unit's fit-cut identity normal at the season key of the T2 step (from the
                         slim rows of the same unit and lead), phi = damped_persistence_phi (MET:461) on unit histories
                         of slim refit labels at or before the lead's fit cut, gap = lead + offset (1 + offset at the
                         nowcast), same_season_key = shares_season_key(gap, steps_per_year) (MET:447).
Tables:
  last visit at the site = the label of the latest earlier visit of the same package unit (the catalog's key_unit
                         column of the package's lead files, e.g. a site) strictly before the issue day, from
                         slim train labels and, for visits inside the test window, the saved test labels read
                         through the one reader (lockfile.open_test_labels).
PARITY PROOF FIRST: the same code at every lead >= 1 must reproduce the run's saved base__persistence (and
base__damped_persistence on grids) byte for byte; otherwise refuse and write no nowcast row.
"""
# Provenance: SPEC_HUMAN.txt 1.10; engine report/metrics.py:436 baseline_persistence, :447 shares_season_key, :461
# damped_persistence_phi, :534 baseline_damped_persistence; pipeline/ladder.py:878-897 (persistence inputs),
# :1012-1028 (normal at the persisted label's season key); pipeline/table_ladder.py:390-396, labels/rows.py:143-184
# (last label strictly before the issue day).

import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from rivals_human import config as C
from rivals_human import lockfile as LK
from rivals_human import slim as S
from rivals_human.board import load_board
from rivals_human.common import HumanCommand, refuse

HIST_LAST_1 = "x__hist_last_1"
COL_PERSIST = "base__human_persistence"
COL_DAMPED = "base__human_damped_persistence"
COL_LAST_VISIT = "base__human_last_visit"
SITE_SEPARATOR = "|"


def _bytes_equal(a: np.ndarray, b: np.ndarray) -> Tuple[bool, int]:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    na, nb = np.isnan(a), np.isnan(b)
    if a.shape != b.shape:
        return False, -1
    bad = (na != nb) | (~na & ~nb & (a.view(np.int64) != b.view(np.int64)))
    return (not bad.any()), int(bad.sum())


# ===================================================================================================== grids
def _histories(cfg: Any, run: Any, lead: int, units: List[str]) -> Dict[str, Any]:
    """Unit histories (duck-typed UnitHistory: unit_id, times, season_keys, y, cut) of the slim refit labels of every
    slimmed lead, at or before this lead's fit cut. Two leads naming one (unit, time) must agree on its label."""
    # the newest label READABLE at the fit cut is fit_cut - R17's start offset (the engine's ctx_fit.unit_history); with
    # an offset of 1 (NDVI) a history to fit_cut itself gave another phi on ~2/3 of the units (2026-10-25, Part 618)
    cut = int(run.cuts[int(lead)]["fit_cut"]) - S.run_offset(run)
    parts = []
    season = None
    for L in run.leads:
        sl = S.open_slim(cfg, run, L)
        season = sl.season
        s = sl.read_set("refit", extras=False)
        f = pd.DataFrame({"unit": s.keys["unit"].astype(str).to_numpy(), "time": s.keys["time"].to_numpy(np.int64),
                          "y": s.y})
        parts.append(f[f["time"] <= cut])
    f = pd.concat(parts, ignore_index=True)
    g = f.groupby(["unit", "time"])["y"].agg(["min", "max"])
    if (g["min"] != g["max"]).any():
        refuse("two slim leads hold different labels for %d (unit, time) pairs" % int((g["min"] != g["max"]).sum()))
    f = f.drop_duplicates(subset=["unit", "time"]).sort_values(["unit", "time"]).reset_index(drop=True)
    out = {}
    by = {u: d for u, d in f.groupby("unit", sort=True)}
    for u in units:
        d = by.get(u)
        t = d["time"].to_numpy(np.int64) if d is not None else np.zeros(0, dtype=np.int64)
        y = d["y"].to_numpy(np.float64) if d is not None else np.zeros(0)
        out[u] = SimpleNamespace(unit_id=u, times=t, season_keys=S.season_keys(t, season), y=y, cut=cut)
    return out


def _normal_lookup(sl: S.SlimLead, token: Any) -> Dict[Tuple[str, int], float]:
    """(unit, season key) -> the lead's fit-cut identity normal, from the slim refit and test rows (nfit__identity)."""
    rows = []
    s = sl.read_set("refit", extras=False)
    rows.append(pd.DataFrame({"unit": s.keys["unit"].astype(str).to_numpy(),
                              "k": S.season_keys(s.keys["time"].to_numpy(np.int64), sl.season),
                              "n": s.normal["identity"]}))
    t = sl.read_set("test", lock=token, extras=False)
    rows.append(pd.DataFrame({"unit": t.keys["unit"].astype(str).to_numpy(),
                              "k": S.season_keys(t.keys["time"].to_numpy(np.int64), sl.season),
                              "n": t.normal["identity"]}))
    f = pd.concat(rows, ignore_index=True).dropna()
    g = f.groupby(["unit", "k"])["n"].agg(["min", "max"])
    if (g["min"] != g["max"]).any():
        refuse("lead %d: the fit-cut identity normal differs within %d (unit, season key) cells"
               % (sl.lead, int((g["min"] != g["max"]).sum())))
    return {(u, int(k)): float(v) for (u, k), v in g["min"].items()}


def grid_refs(eng: Any, cfg: Any, run: Any, lead: int, token: Any, saved_keys: pd.DataFrame,
              scored_units: List[str], labels: pd.DataFrame) -> Dict[str, Any]:
    """Persistence and damped persistence of a lead's saved test rows (saved order). The issue label is the float64
    label at the T2 step (labels: every label the tool may hold after the lock); the export's hist_last_1 (stored
    float32) must equal it cast to float32 on every row where that label exists, which proves the step."""
    M = eng.metrics
    sl = S.open_slim(cfg, run, lead)
    if HIST_LAST_1 not in sl.history:
        refuse("the run's history block has no hist_last_1; no persistence row can be built")
    t = sl.read_set("test", lock=token, extras=False)
    keys = t.keys.copy()
    keys["unit"] = keys["unit"].astype(str)
    from rivals_human.common import load
    _, H = load()
    pos = H.to_saved_order(saved_keys, keys, "the saved test rows (references)")
    hist1 = t.history[HIST_LAST_1].to_numpy(np.float64)[pos]
    units = keys["unit"].to_numpy()[pos]
    times = keys["time"].to_numpy(np.int64)[pos]
    offset = S.run_offset(run)
    gap = (1 if int(lead) == 0 else int(lead)) + offset
    label_step = times - gap
    lk = pd.DataFrame({"unit": units.astype(str), "time": label_step})
    lab = labels[["unit", "time", "y"]].copy()
    lab["unit"] = lab["unit"].astype(str)
    y_issue = lk.merge(lab, on=["unit", "time"], how="left", validate="many_to_one")["y"].to_numpy(np.float64)
    fy, fh = np.isfinite(y_issue), np.isfinite(hist1)
    # where the T2-step label is missing, the history block's hist_last_1 may hold an older label (its newest valid
    # one) while persistence stays NaN (MET:436); where it exists, hist_last_1 is that label in float32
    bad = (fy & ~fh) | (fy & fh & (y_issue.astype(np.float32).astype(np.float64) != hist1))
    if bad.any():
        refuse("lead %d: the label at the T2 step (time - %d) differs from the export's hist_last_1 on %d rows "
               "(the T2 step or the label source is wrong)" % (int(lead), gap, int(bad.sum())))
    per_year = int(sl.season.get("steps_per_year") or 1)
    same = bool(M.shares_season_key(gap, per_year))
    pers = M.baseline_persistence(y_issue, run.legal)
    hist = _histories(cfg, run, lead, scored_units)
    phi = M.damped_persistence_phi(hist, gap, same)
    lookup = _normal_lookup(sl, token)
    nt = t.normal["identity"][pos]
    keys_issue = S.season_keys(label_step, sl.season)
    ni = np.array([lookup.get((u, int(k)), np.nan) for u, k in zip(units.tolist(), keys_issue.tolist())])
    ph = np.array([phi.get(str(u), np.nan) for u in units.tolist()])
    ok = np.isfinite(nt) & np.isfinite(ni) & np.isfinite(ph)
    damped = np.full(units.size, np.nan)
    if ok.any():
        damped[ok] = M.baseline_damped_persistence(nt[ok], ni[ok], y_issue[ok], ph[ok], run.legal)
    return {"persistence": pers, "damped_persistence": damped, "gap": gap, "same_season_key": same,
            "rows_without_issue_normal": int((~np.isfinite(ni)).sum()), "rows_without_phi": int((~np.isfinite(ph)).sum()),
            "rows_with_issue_label": int(np.isfinite(y_issue).sum()),
            "phi_median": float(np.median(list(phi.values()))) if phi else None}


# ===================================================================================================== tables
def site_of(unit: str) -> str:
    return str(unit).split(SITE_SEPARATOR, 1)[0]


def package_units(run: Any, slim0: S.SlimLead) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """{row id: package unit} of a table package, read from the package's own lead files (the catalog's key_row and
    key_unit columns only; the label column is never read), through the engine's loader (package/load.py:259
    load_package, package/table.py:126 table_spec, :217 lead_files). The package folder and fingerprint are the
    export's (kept in the slim copy)."""
    from treeroute.package.load import load_package
    from treeroute.package import table as TB
    import pyarrow.parquet as pq
    em = slim0.export_manifest()
    folder = (em.get("package") or {}).get("folder")
    if not folder:
        refuse("the kept export manifest names no package folder; the package unit of a table row is unknown")
    pkg = load_package(folder)
    if pkg.fingerprint != em["package"]["fingerprint"]:
        refuse("the package %s now has fingerprint %s; the export was made from %s" % (folder, pkg.fingerprint[:16],
                                                                                   em["package"]["fingerprint"][:16]))
    spec = TB.table_spec(pkg)
    files = TB.lead_files(pkg, run.leads)
    out: Dict[str, str] = {}
    for L, path in sorted(files.items()):
        t = pq.read_table(path, columns=[spec.row_col, spec.package_unit_col]).to_pandas()
        for r, u in zip(t[spec.row_col].astype(str).tolist(), t[spec.package_unit_col].astype(str).tolist()):
            if out.setdefault(r, u) != u:
                refuse("row %s names package units %s and %s in two lead files" % (r, out[r], u))
    return out, {"package_folder": folder, "row_column": spec.row_col, "unit_column": spec.package_unit_col,
                 "rows": len(out), "files": {str(L): p for L, p in sorted(files.items())}}


def table_last_visit(labels: pd.DataFrame, units: np.ndarray, issue: np.ndarray,
                     unit_of: Mapping[str, str]) -> np.ndarray:
    """The label of the latest visit of the same package unit strictly before the issue day (labels/rows.py:143-184;
    ties on a day: the last in (unit, day, row id) order), NaN when none. unit_of maps a row id to its package unit."""
    def site(u):
        v = unit_of.get(str(u))
        if v is None:
            refuse("row %s has no package unit in the package's lead files" % u)
        return v
    f = labels.assign(site=labels["unit"].astype(str).map(site)).sort_values(["site", "time", "unit"],
                                                                            kind="mergesort")
    by = {s: (d["time"].to_numpy(np.int64), d["y"].to_numpy(np.float64)) for s, d in f.groupby("site", sort=True)}
    out = np.full(len(units), np.nan)
    for i, (u, d) in enumerate(zip(units.tolist(), issue.tolist())):
        rec = by.get(site(u))
        if rec is None:
            continue
        j = int(np.searchsorted(rec[0], int(d), side="left")) - 1
        if j >= 0:
            out[i] = rec[1][j]
    return out


def all_labels(cfg: Any, run: Any, ctx: Any, store: Optional[Mapping[str, Any]] = None) -> pd.DataFrame:
    """Every label the tool may hold after the lock: slim train labels of every lead and the saved lead-0 test
    labels (the one reader). One label per (unit, time); two sources naming one must agree."""
    parts = []
    for L in run.leads:
        sl = S.open_slim(cfg, run, L)
        for s in ("refit",) + (("tune", "inner") if L == 0 else ("guardfit", "guard")):
            try:
                st = sl.read_set(s, extras=False)
            except Exception as exc:          # a lead without that set (e.g. no guard rows) has nothing to add
                if "holds no" not in str(exc):
                    raise
                continue
            parts.append(pd.DataFrame({"unit": st.keys["unit"].astype(str).to_numpy(),
                                       "time": st.keys["time"].to_numpy(np.int64), "y": st.y}))
    opened = LK.open_test_labels(ctx, run, 0)
    tf = opened["frame"]
    yy = tf["y"].to_numpy(np.float64)
    ok = np.isfinite(yy)
    parts.append(pd.DataFrame({"unit": tf.loc[ok, "unit"].astype(str).to_numpy(),
                               "time": tf.loc[ok, "time"].to_numpy(np.int64), "y": yy[ok]}))
    f = pd.concat(parts, ignore_index=True)
    g = f.groupby(["unit", "time"])["y"].agg(["min", "max"])
    if (g["min"] != g["max"]).any():
        refuse("label sources disagree on %d (unit, time) pairs" % int((g["min"] != g["max"]).sum()))
    f = f.drop_duplicates(subset=["unit", "time"]).reset_index(drop=True)
    if store is not None:
        f = pd.concat([f, store_labels(cfg, run, store, f)], ignore_index=True)
    return f


def store_labels(cfg: Any, run: Any, store: Mapping[str, Any], held: pd.DataFrame) -> pd.DataFrame:
    """Training-period labels the slim sets do not hold, read from the package's target store (registry
    refs_label_store; Part 618). With an R17 start offset the export's training rows stop one step before the fit
    cut, yet the engine's persistence reads the label AT the lead-0 fit cut. Only steps in (newest held training step,
    lead-0 fit cut] are added (never a test step); every store row the tool already holds must equal it byte for byte
    (float64 of the store dtype), else refuse. Files are sha-checked against the product manifest."""
    from rivals_human import index as IX
    products = C.load_products(cfg)
    pid = str(store["product"])
    man = IX.product_manifest(cfg, products, pid)
    root = IX.product_root(cfg, products, pid)
    cut0 = int(run.cuts[0]["fit_cut"])
    train = held[held["time"] <= cut0]
    lo = int(train["time"].max())
    if lo >= cut0:
        return held.iloc[0:0][["unit", "time", "y"]]
    sl0 = S.open_slim(cfg, run, 0)
    units_tab = sl0.units()
    scored = units_tab.loc[units_tab["is_scored"].astype(bool), ["unit", "group"]].astype(str)
    want = set(scored["unit"])
    spy = int(sl0.season.get("steps_per_year") or 0)
    if spy != 12:
        refuse("refs label store: steps per year %r; the store's year x month time rule needs a monthly grid" % spy)
    years = sorted({(t - 1) // spy for t in range(lo, cut0 + 1)})          # the years holding (lo, cut0] and lo itself
    rows = []
    for grp in sorted(set(scored["group"])):
        for yr in years:
            name = str(store["file_pattern"]).format(group=grp, year=yr)
            e = man["files"].get(name)
            if e is None:
                refuse("refs label store %s lists no %s" % (pid, name))
            path = root / name
            IX.verify_product_file(path, str(e["sha256"]))
            cols = [store["unit_column"], store["year_column"], store["month_column"], store["label_column"]]
            t = pq.read_table(str(path), columns=cols).to_pandas()
            t = t[t[store["unit_column"]].astype(str).isin(want)]
            y = t[store["label_column"]].to_numpy().astype(str(store["dtype"])).astype(np.float64)
            rows.append(pd.DataFrame({"unit": t[store["unit_column"]].astype(str).to_numpy(),
                                      "time": (t[store["year_column"]].astype(np.int64) * spy
                                               + t[store["month_column"]].astype(np.int64)).to_numpy(np.int64), "y": y}))
    st = pd.concat(rows, ignore_index=True)
    st = st[np.isfinite(st["y"]) & (st["time"] <= cut0)]
    hk = held.assign(unit=held["unit"].astype(str))
    both = st.merge(hk, on=["unit", "time"], how="inner", suffixes=("_s", "_h"))
    if not len(both):
        refuse("refs label store %s overlaps no held label: the byte check cannot run" % pid)
    eq = both["y_s"].to_numpy(np.float64).view(np.int64) == both["y_h"].to_numpy(np.float64).view(np.int64)
    if not eq.all():
        refuse("refs label store %s differs from the held labels on %d of %d overlapping rows"
               % (pid, int((~eq).sum()), int(eq.size)))
    add = st[(st["time"] > lo) & (st["time"] <= cut0)]
    add = add.merge(hk[["unit", "time"]], on=["unit", "time"], how="left", indicator=True)
    add = add[add["_merge"] == "left_only"][["unit", "time", "y"]].reset_index(drop=True)
    return add


# ===================================================================================================== command
def refs(out: Any, lead: int, config: Any = None) -> Path:
    """Parity proof at every slimmed lead >= 1, then (lead 0) the nowcast reference rows (spec 1.10)."""
    cfg = C.load_config(config)
    lead = int(lead)
    with HumanCommand("refs", out, cfg, need_file=C.BOARD_FILE) as ctx:
        H, eng = ctx.H, ctx.eng
        board, run, registry = load_board(ctx)
        token = LK.verify_lock(ctx.out)
        ldir = ctx.mkdir(ctx.out / (C.LEAD_DIR % lead))
        is_table = bool(board["run"]["is_table"])
        hist = S.history_columns(run)
        rec: Dict[str, Any] = {"lead": lead, "utc": H.utc_now(), "parity": {}}
        leads_proof = [L for L in run.leads if L >= 1] if lead == 0 else [lead]
        t0 = time.time()
        if is_table:
            labels = all_labels(cfg, run, ctx)
            unit_of, rec["package_units"] = package_units(run, S.open_slim(cfg, run, 0))
            for L in leads_proof:
                col, saved = H.saved_test_keys(run, L)
                sv = H.read_columns(run.test_preds_path(L), ["unit", "time", "issue", "lead", "base__persistence"])
                got = table_last_visit(labels, sv["unit"].astype(str).to_numpy(), sv["issue"].to_numpy(np.int64),
                                       unit_of)
                want = eng.metrics.baseline_persistence(got, run.legal)
                ok, nbad = _bytes_equal(want, sv["base__persistence"].to_numpy(np.float64))
                rec["parity"][str(L)] = {"base__persistence": "equal" if ok else "DIFFERS on %d rows" % nbad,
                                         "rows": int(len(sv))}
                if not ok:
                    ctx.replace_json(ldir / C.REFS_JSON, dict(rec, result="REFUSED: parity proof failed"))
                    refuse("parity proof failed at lead %d: the last-visit rule differs from the run's saved "
                           "base__persistence on %d rows; no nowcast row is written" % (L, nbad))
            if lead == 0:
                col, saved = H.saved_test_keys(run, 0)
                lv = table_last_visit(labels, saved["unit"].astype(str).to_numpy(),
                                      saved["issue"].to_numpy(np.int64), unit_of)
                v = eng.metrics.baseline_persistence(lv, run.legal)
                frame = saved[["unit", "group", "time", "issue", "lead"]].reset_index(drop=True).copy()
                frame[COL_LAST_VISIT] = v
                ctx.write_parquet(ldir / C.REFS_FILE, frame)
                rec.update(rows=int(len(frame)), rows_with_last_visit=int(np.isfinite(v).sum()),
                           columns=[COL_LAST_VISIT], rule="last visit of the same package unit strictly before the "
                                                           "issue day")
        elif HIST_LAST_1 in hist:
            labels = all_labels(cfg, run, ctx, registry.get("refs_label_store"))
            units_tab = S.open_slim(cfg, run, 0).units()
            scored = sorted(units_tab.loc[units_tab["is_scored"].astype(bool), "unit"].astype(str).tolist()) \
                if "is_scored" in units_tab.columns else sorted(units_tab["unit"].astype(str).tolist())
            for L in leads_proof:
                col, saved = H.saved_test_keys(run, L)
                sv = H.read_columns(run.test_preds_path(L), ["unit", "time", "lead", "base__persistence",
                                                             "base__damped_persistence"])
                got = grid_refs(eng, cfg, run, L, token, saved, scored, labels)
                r1, n1 = _bytes_equal(got["persistence"], sv["base__persistence"].to_numpy(np.float64))
                r2, n2 = _bytes_equal(got["damped_persistence"], sv["base__damped_persistence"].to_numpy(np.float64))
                rec["parity"][str(L)] = {"base__persistence": "equal" if r1 else "DIFFERS on %d rows" % n1,
                                         "base__damped_persistence": "equal" if r2 else "DIFFERS on %d rows" % n2,
                                         **{k: v for k, v in got.items() if k not in ("persistence",
                                                                                     "damped_persistence")}}
                if not (r1 and r2):
                    ctx.replace_json(ldir / C.REFS_JSON, dict(rec, result="REFUSED: parity proof failed"))
                    refuse("parity proof failed at lead %d (persistence %s, damped %s); no nowcast row is written"
                           % (L, rec["parity"][str(L)]["base__persistence"],
                              rec["parity"][str(L)]["base__damped_persistence"]))
            if lead == 0:
                col, saved = H.saved_test_keys(run, 0)
                got = grid_refs(eng, cfg, run, 0, token, saved, scored, labels)
                frame = saved[["unit", "group", "time", "issue", "lead"]].reset_index(drop=True).copy()
                frame[COL_PERSIST] = got["persistence"]
                frame[COL_DAMPED] = got["damped_persistence"]
                ctx.write_parquet(ldir / C.REFS_FILE, frame)
                rec.update(rows=int(len(frame)), columns=[COL_PERSIST, COL_DAMPED],
                           **{k: v for k, v in got.items() if k not in ("persistence", "damped_persistence")})
        else:
            rec["result"] = "no history block and not a table package: no persistence reference row"
        rec.setdefault("result", "parity proof passed at leads %s" % leads_proof if leads_proof else
                       "no lead >= 1 to prove against")
        ctx.replace_json(ldir / C.REFS_JSON, rec)
        ctx.log("refs", seconds=time.time() - t0, message="lead %d: %s" % (lead, rec["result"]))
        return ctx.out
