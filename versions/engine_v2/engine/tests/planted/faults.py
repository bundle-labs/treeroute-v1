"""The planted-fault table: each fault breaks one rule of the clean package (build.make_clean_package) and names
the guard that must catch it. kind 'detection' means the guard finds the fault in the data; 'rule enforcement'
means the guard enforces a DECLARATION (a wrong but complete fact would pass). expect is 'refuse', or 'flag' for
a guard whose signed contract is report only. Package-level faults run through the check passes; validator-level
faults call the validator directly (the engine's own lookups cannot produce the fault). PLANTED_FAULTS.md lists
the same table; a test keeps the two equal.
"""

import numpy as np
import pandas as pd

from . import build as B

DEEP, QUICK, VALIDATOR = "deep", "quick", "validator"


def _f(fid, guard, mode, expect, kind, what, apply):
    return {"id": fid, "guard": guard, "mode": mode, "expect": expect, "kind": kind, "what": what, "apply": apply}


# ---------------------------------------------------------------------------------------------- package level
def pf_closed_undeclared_column(pkg):
    B.rewrite_drivers(pkg, lambda d: d.assign(x9=d["x1"] * 2.0),
                      ["unit_id", "step_year", "step_month", "x1", "g1", "x2", "s1", "frac", "x9"])


def pf_closed_unreviewed_unsigned(pkg):
    B.edit(pkg, "ban.yaml", "  frac: {verdict: keep, reason: reviewed, evidence: Part 1}",
           "  frac: {verdict: keep_unreviewed, reason: not reviewed yet}")
    B.edit_store(pkg, "    legal_range: [0.0, 1.0]\n    fact_status: verified",
                 "    legal_range: [0.0, 1.0]\n    fact_status: unverified")


def pf_closed_absent_column(pkg):
    B.edit(pkg, "catalog.yaml", "  s1: {role: driver}\n", "  s1: {role: driver}\n  ghost: {role: driver}\n")
    B.edit(pkg, "ban.yaml", "  s1: {verdict: keep, reason: reviewed, evidence: Part 1}\n",
           "  s1: {verdict: keep, reason: reviewed, evidence: Part 1}\n"
           "  ghost: {verdict: conditional, reason: no store holds it yet, evidence: Part 1}\n")


def pf_lag_unknown_window(pkg):
    B.edit_store(pkg, "    window: {length: 3, unit: month, align: centred}",
                 "    window: {align: unknown}")


def pf_epoch_content_epoch(pkg):
    # the kept STATIC s1 declares a content epoch after the cut (a post-window snapshot); snapshot and release dates
    # are never compared (plan 1.3), the content epoch is, on every cadence kind
    # (the clean s1 is a physical map, content_epoch timeless under ruling N2; the fault dates it after the cut)
    B.edit_store(pkg, "    content_epoch: timeless   # ruling N2: a physical static map\n",
                 "    content_epoch: '2010-06'\n")


def pf_epoch_post_cut_label(pkg):
    B.edit(pkg, "catalog.yaml", "    stamp: period_end\n  x1:", "    stamp: period_end\n    calibration_through: 2009\n  x1:")


def pf_epoch_target_outlasts_drivers(pkg):
    # labels 2011-2012 with no driver rows: R3 counts the JOINED rows, so Y_end stays 2010 and the train end 2006;
    # a target calibrated through 2008 is past it (the old 'last label year minus 4' estimate gave 2008 and passed)
    t, _ = B.frames()
    extra = t[t["step_year"] >= 2009].copy()
    extra["step_year"] += 2
    B.write_target(pkg, extra)
    B.edit(pkg, "catalog.yaml", "    stamp: period_end\n  x1:", "    stamp: period_end\n    calibration_through: 2008\n  x1:")


def pf_missing_year_file(pkg):
    # one driver YEAR file is gone (grp_a, 2009, inside the test window); no store fact declares it absent
    from pathlib import Path

    (Path(pkg) / "data" / "drivers" / "group=grp_a" / "year=2009" / "part-0.parquet").unlink()


def pf_lineage_coproduct(pkg):
    B.edit_store(pkg, "    legal_range: [0.0, 1.0]\n    fact_status: verified",
                 "    legal_range: [0.0, 1.0]\n    lineage: {assimilates: [y]}\n    fact_status: verified")


def pf_lineage_unsigned_exception(pkg):
    # the co-product of PF08 with an exceptions.yaml entry whose owner field is the packages' unsigned placeholder
    pf_lineage_coproduct(pkg)
    B.edit(pkg, "exceptions.yaml", "", "entries:\n  - kind: provenance_flag\n    column: frac\n"
           "    decision: disclose\n    reason: a co-product kept by a ruling\n"
           "    owner: 'UNSIGNED -- basis: a ruling'\n    date: '2026-10-06'\n")


def pf_lineage_sum_group(pkg):
    B.edit_store(pkg, "    scope: unit\n    stamp: period_end\n    fact_status: verified",
                 "    scope: unit\n    stamp: period_end\n    sum_group: share\n    fact_status: verified")
    B.edit_store(pkg, "    legal_range: [0.0, 1.0]\n    fact_status: verified",
                 "    legal_range: [0.0, 1.0]\n    sum_group: share\n    fact_status: verified")
    B.edit(pkg, "ban.yaml", "  s1: {verdict: keep, reason: reviewed, evidence: Part 1}",
           "  s1: {verdict: ban, reason: structural, evidence: Part 1}")


def pf_lineage_reconstruction(pkg):
    # frac_rest = 1 - frac, banned, while frac is kept: the banned member is the total minus the kept one
    B.rewrite_drivers(pkg, lambda d: d.assign(frac_rest=1.0 - d["frac"].astype("float32").astype("float64")),
                      ["unit_id", "step_year", "step_month", "x1", "g1", "x2", "s1", "frac", "frac_rest"])
    B.edit_store(pkg, "    legal_range: [0.0, 1.0]\n    fact_status: verified",
                 "    legal_range: [0.0, 1.0]\n    sum_group: share\n    fact_status: verified")
    B.add_store_column(pkg, "  frac_rest:\n    dtype: float32\n    units: '1'\n"
                            "    cadence: {kind: regular, length: 1, unit: month}\n    scope: unit\n"
                            "    stamp: period_end\n    window: {length: 1, unit: month, align: backward}\n"
                            "    legal_range: [0.0, 1.0]\n    sum_group: share\n    fact_status: verified\n")
    B.edit(pkg, "catalog.yaml", "  s1: {role: driver}\n",
           "  s1: {role: driver}\n  frac_rest: {role: driver, co_measured_with_target: false, "
           "co_measured_evidence: Part 1}\n")
    B.edit(pkg, "ban.yaml", "  s1: {verdict: keep, reason: reviewed, evidence: Part 1}\n",
           "  s1: {verdict: keep, reason: reviewed, evidence: Part 1}\n"
           "  frac_rest: {verdict: ban, reason: structural, evidence: Part 1}\n")


def pf_hist_declared(pkg):
    B.edit(pkg, "features/build.py", '"reads_target": False, "fact_status": "verified"},\n}',
           '"reads_target": True, "fact_status": "verified"},\n}')


def pf_hist_hidden_copy(pkg):
    # a store column that is the unit's own target one month earlier, declared as an ordinary driver
    y = B.target_by_key()

    def mutate(d):
        prev = d[["unit_id", "step_year", "step_month"]].copy()
        m = prev["step_month"] - 1
        prev["py"] = np.where(m == 0, prev["step_year"] - 1, prev["step_year"])
        prev["pm"] = np.where(m == 0, 12, m)
        idx = pd.MultiIndex.from_arrays([prev["unit_id"], prev["py"], prev["pm"]])
        return d.assign(x1=y.reindex(idx).to_numpy())
    B.rewrite_drivers(pkg, mutate)


def pf_hist_script_reads_target(pkg):
    # the feature script opens the target store and returns y(t) as 'x1_lag1' (still declared a lag of x1)
    B.edit(pkg, "features/build.py", "    return pd.DataFrame({\"ctx:m\": frame[month].astype(\"float32\"), \"x1_lag1\": lag}, index=frame.index)",
           "    import glob, os\n"
           "    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'target')\n"
           "    t = pd.concat([pd.read_parquet(p) for p in glob.glob(os.path.join(root, '*', '*', '*.parquet'))])\n"
           "    yy = t.set_index(['unit_id', 'step_year', 'step_month'])['y']\n"
           "    years = [c for c, part in keys['time'].items() if part == 'year'][0]\n"
           "    idx = pd.MultiIndex.from_arrays([frame[keys['unit']], frame[years], frame[month]])\n"
           "    lag = yy.reindex(idx).to_numpy()\n"
           "    return pd.DataFrame({\"ctx:m\": frame[month].astype(\"float32\"), \"x1_lag1\": lag}, index=frame.index)")


def pf_keys_month_tree(pkg):
    B.edit(pkg, "catalog.yaml", "  'ctx:m': {role: router_context,", "  'ctx:m': {role: engineered,")


def pf_split_unknown_group(pkg):
    B.edit(pkg, "split.yaml", "excluded: {}\n", "excluded: {grp_q: no such group}\n")


def pf_support_presence_only(pkg):
    B.rewrite_target(pkg, lambda t: t[t["y"] > t["y"].median()])


def pf_support_cadence_gap(pkg):
    B.rewrite_target(pkg, lambda t: t[~((t["unit_id"] == "grp_b_1") & (t["step_year"] == 2004) & (t["step_month"] == 5))])


def pf_facts_unsigned(pkg):
    B.edit_store(pkg, "    window: {length: 3, unit: month, align: centred}\n    fact_status: verified",
                 "    window: {length: 3, unit: month, align: centred}\n    fact_status: assumed")


def pf_missing_vanishing_unreviewed(pkg):
    B.rewrite_drivers(pkg, lambda d: d.assign(frac=np.where(d["step_year"] == 2010, np.nan, d["frac"])))
    B.edit(pkg, "ban.yaml", "  frac: {verdict: keep, reason: reviewed, evidence: Part 1}",
           "  frac: {verdict: keep_unreviewed, reason: not reviewed yet}")


def pf_missing_group_year(pkg):
    B.rewrite_drivers(pkg, lambda d: d.assign(g1=np.where((d["group_id"] == "grp_c") & (d["step_year"] == 2003),
                                                          np.nan, d["g1"])))


def pf_cadence_fake_monthly(pkg):
    B.rewrite_drivers(pkg, lambda d: d.assign(frac=d.groupby(["unit_id", "step_year"])["frac"].transform("first")))


def pf_derived_wrong_lag(pkg):
    B.edit(pkg, "features/build.py", "LAG_K = 1", "LAG_K = 2")


def pf_derived_fits_model(pkg):
    B.edit(pkg, "features/build.py", "def build(frame, keys):\n",
           "def build(frame, keys):\n    from sklearn.linear_model import LinearRegression\n"
           "    LinearRegression().fit(frame[['x1']].fillna(0), frame['x1'].fillna(0))\n")


def pf_sentinel_undeclared_code(pkg):
    B.rewrite_drivers(pkg, lambda d: d.assign(frac=np.where((d["step_month"] == 3) & (d["step_year"] == 2002),
                                                            -9999.0, d["frac"])))


def pf_sentinel_target_fill(pkg):
    B.rewrite_target(pkg, lambda t: t.assign(y=np.where((t["step_month"] == 7) & (t["step_year"] == 2005), 9.96921e36,
                                                        t["y"])))


def pf_range_out_of_range(pkg):
    B.rewrite_drivers(pkg, lambda d: d.assign(frac=np.where(d["step_month"] == 1, 1.5, d["frac"])))


def pf_range_under_share(pkg):
    # one value out of range in 1,440 frac values: under 0.1%, so a flag with its count
    B.rewrite_drivers(pkg, lambda d: d.assign(frac=np.where((d["unit_id"] == "grp_a_0") & (d["step_year"] == 2002)
                                                            & (d["step_month"] == 2), 1.5, d["frac"])))


def pf_join_duplicated_rows(pkg):
    B.rewrite_drivers(pkg, lambda d: pd.concat([d, d[(d["unit_id"] == "grp_a_2") & (d["step_month"] == 4)]],
                                               ignore_index=True))


def pf_join_column_set(pkg):
    B.rewrite_drivers(pkg, lambda d: d, ["unit_id", "step_year", "step_month", "x1", "g1", "x2", "s1"])


def pf_missing_files(pkg):
    # the driver store moves to a new folder that holds no file for grp_c, and no store fact declares it absent
    from pathlib import Path

    _, d = B.frames()
    d = d[d["group_id"] != "grp_c"]
    base = Path(pkg) / "data" / "drivers2"
    for (group, year), sub in d.groupby(["group_id", "step_year"]):
        out = base / ("group=%s" % group) / ("year=%d" % year)
        out.mkdir(parents=True, exist_ok=True)
        frame = sub[["unit_id", "step_year", "step_month", "x1", "g1", "x2", "s1", "frac"]].copy()
        for c in ("x1", "g1", "x2", "s1", "frac"):
            frame[c] = frame[c].astype("float32")
        frame.to_parquet(out / "part-0.parquet", index=False)
    B.edit(pkg, "dataset.yaml", "data/drivers/group=", "data/drivers2/group=")


# --------------------------------------------------------------------------------------------- validator level
def vf_calendar_row_shift():
    """A row-shift lag over a series with a missing step reads 2 steps back where 1 was meant."""
    from treeroute.check import guards as G

    unit = np.array([0, 0, 0, 0, 1, 1, 1], dtype=np.int64)
    step = np.array([10, 11, 13, 14, 10, 11, 12], dtype=np.int64)          # unit 0 has no step 12
    read = np.arange(len(unit)) - 1                                        # row shift: the previous row
    rows = np.arange(1, len(unit))
    return G.check_g_calendar(unit[read[rows]], step[read[rows]], unit[rows], step[rows], 1, False)


def vf_lag_typed():
    """A lag map whose lag differs from R8's recomputation (a typed lag)."""
    from types import SimpleNamespace

    from treeroute.check import guards as G
    from treeroute.timing import Lag

    month = SimpleNamespace(kind="regular", length=1, unit="month")
    col = SimpleNamespace(name="g1", cadence=month, stamp="period_centre", fact_status="verified",
                          window=SimpleNamespace(length=3, unit="month", align="centred", max_length=None,
                                                 reach_after_max=None, reach_before_max=None),
                          co_measured_with_target=False)
    target = SimpleNamespace(name="y", stamp="period_end", computed_from=(),
                             window=SimpleNamespace(length=1, unit="month", align="backward", max_length=None,
                                                    reach_after_max=None, reach_before_max=None))
    lags = {"g1": Lag(column="g1", steps=0, column_cadence=month, floor_reason=None)}
    return G.check_g_lag({"g1": col}, target, month, lags)


FAULTS = (
    _f("PF01", "G-CLOSED", QUICK, "refuse", "detection", "a column in the data with no catalog row and no verdict",
       pf_closed_undeclared_column),
    _f("PF02", "G-CLOSED", QUICK, "refuse", "rule enforcement", "keep_unreviewed on a column whose timing facts are "
       "unverified", pf_closed_unreviewed_unsigned),
    _f("PF03", "G-CLOSED", QUICK, "refuse", "detection", "a catalog row and verdict for a column no store holds",
       pf_closed_absent_column),
    _f("PF04", "G-LAG", QUICK, "refuse", "rule enforcement", "a lag fact that cannot be computed: an unknown window "
       "with no signed bound on a kept column (a wrong but complete window passes)", pf_lag_unknown_window),
    _f("PF05", "G-LAG", VALIDATOR, "refuse", "rule enforcement", "a typed lag: the lag map differs from R8's "
       "recomputation", vf_lag_typed),
    _f("PF06", "G-EPOCH", DEEP, "refuse", "rule enforcement", "a kept static column whose content epoch lies after "
       "the cut (a post-window snapshot), without a 'freeze' verdict", pf_epoch_content_epoch),
    _f("PF07", "G-EPOCH", DEEP, "refuse", "rule enforcement", "a post-cut label: the target calibrated past the donor "
       "train end, not disclosed", pf_epoch_post_cut_label),
    _f("PF08", "G-LINEAGE", QUICK, "refuse", "rule enforcement", "a kept co-product (lineage assimilates the target) "
       "without a signed exception", pf_lineage_coproduct),
    _f("PF09", "G-LINEAGE", QUICK, "refuse", "rule enforcement", "a sum group with mixed verdicts", pf_lineage_sum_group),
    _f("PF10", "G-LINEAGE (deep)", DEEP, "flag", "detection", "a banned sum-group member rebuilt as the total minus a "
       "kept member (report only by contract)", pf_lineage_reconstruction),
    _f("PF11", "G-HIST", QUICK, "refuse", "rule enforcement", "a feature output declared as reading the target "
       "(a lag of the own target)", pf_hist_declared),
    _f("PF12", "G-HIST (sample)", DEEP, "refuse", "detection", "a store column that is the own target one step "
       "earlier, declared as an ordinary driver", pf_hist_hidden_copy),
    _f("PF13", "G-HIST (sample)", DEEP, "refuse", "detection", "a feature script that reads the target at t "
       "(declared as a lag of a driver)", pf_hist_script_reads_target),
    _f("PF14", "G-KEYS", QUICK, "refuse", "rule enforcement", "a column derived from a key (the calendar month) "
       "entering the trees", pf_keys_month_tree),
    _f("PF15", "G-SPLIT", QUICK, "refuse", "detection", "split.yaml excludes a group the data do not hold",
       pf_split_unknown_group),
    _f("PF16", "G-SUPPORT (deep)", DEEP, "refuse", "detection", "the presence-only refusal: only rows with a large "
       "label are stored", pf_support_presence_only),
    _f("PF17", "G-SUPPORT (deep)", DEEP, "refuse", "detection", "a cadence gap: one unit misses one month inside "
       "the record", pf_support_cadence_gap),
    _f("PF18", "G-FACTS", QUICK, "refuse", "rule enforcement", "an unsigned fact: 'assumed' timing facts with no "
       "reviewer on a kept column", pf_facts_unsigned),
    _f("PF19", "G-MISSING", DEEP, "refuse", "rule enforcement", "a kept column vanishing in a test year (R30) with "
       "only a keep_unreviewed verdict", pf_missing_vanishing_unreviewed),
    _f("PF20", "G-MISSING (deep)", DEEP, "flag", "detection", "a column all missing in one group-year inside files "
       "that exist (report only by contract)", pf_missing_group_year),
    _f("PF21", "G-CADENCE", DEEP, "refuse", "detection", "a fake-monthly column: declared monthly, constant within "
       "every unit-year", pf_cadence_fake_monthly),
    _f("PF22", "G-CALENDAR", VALIDATOR, "refuse", "detection", "a row-shift lag across a missing step",
       vf_calendar_row_shift),
    _f("PF23", "G-DERIVED (recompute)", DEEP, "refuse", "detection", "the feature script computes lag 2 while "
       "declaring lag 1", pf_derived_wrong_lag),
    _f("PF24", "G-DERIVED", QUICK, "refuse", "detection", "a feature script that fits a model (.fit)",
       pf_derived_fits_model),
    _f("PF25", "G-SENTINEL (deep)", DEEP, "flag", "detection", "an undeclared fill code (-9999) left in a driver "
       "(report only by contract)", pf_sentinel_undeclared_code),
    _f("PF26", "G-SENTINEL (deep)", DEEP, "refuse", "detection", "a sentinel value left in the target (the read "
       "refuses it, D30)", pf_sentinel_target_fill),
    _f("PF27", "G-RANGE", DEEP, "refuse", "detection", "an out-of-range share: a fraction above 1 in 1 of 12 months",
       pf_range_out_of_range),
    _f("PF28", "G-RANGE", DEEP, "flag", "detection", "one value out of range, under 0.1% of the column: flagged with "
       "its count", pf_range_under_share),
    _f("PF29", "G-JOIN", DEEP, "refuse", "detection", "a join that duplicates rows: a store file repeats unit x step "
       "keys", pf_join_duplicated_rows),
    _f("PF30", "G-JOIN", DEEP, "refuse", "detection", "a store's column set differs from its catalog (a declared "
       "column missing from the files)", pf_join_column_set),
    _f("PF31", "G-MISSING (files)", DEEP, "refuse", "detection", "a driver store holds no file for one group, which "
       "no store fact declares absent", pf_missing_files),
    _f("PF32", "G-LINEAGE", QUICK, "refuse", "rule enforcement", "the PF08 co-product with an exceptions.yaml entry "
       "whose owner reads 'UNSIGNED -- basis: ...' (a disclosure, not a signature)", pf_lineage_unsigned_exception),
    _f("PF33", "G-EPOCH", DEEP, "refuse", "detection", "the target outlasts the drivers by 2 years and is calibrated "
       "through 2008: R3 on the joined rows puts the train end at 2006", pf_epoch_target_outlasts_drivers),
    _f("PF34", "G-MISSING (files)", DEEP, "refuse", "detection", "one driver YEAR file is missing inside the store's "
       "record (one group, one test year), which no store fact declares absent", pf_missing_year_file),
)

__all__ = ["FAULTS", "DEEP", "QUICK", "VALIDATOR"]
