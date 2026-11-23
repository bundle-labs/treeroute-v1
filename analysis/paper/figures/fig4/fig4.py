"""Figure 5: (a) pooled MAE by lead; (b) MAE reduction of the final answer against its
reference by test year, 100 x (reference - final answer) / reference (K67 with the sign
reversed, so that above 0 favours the final answer, as in Figure 4 and Table 5). Round 5 (2026-11-11): tables renumbered (paper/draft/TABLE_NUMBERS.md). Round 4 (2026-11-11): figures renumbered by first citation: map (unnumbered) -> 1, 1 -> 2, 2 -> 3, 3 -> 4, 4 -> 5 (folders keep their names; paper/figures/FIGURE_NUMBERS.md).

Revised 2026-10-27 after two independent checks. Decision log: paper/draft/review_logs/figsupp_fig4_log.md.
Copies: paper/draft/_snapshots/20261027T1500Z_figsupp/fig4_pre_revise_attempt1/ (as built, before any
revision) and paper/draft/_snapshots/20261027T1500Z_figsupp/fig4/ (after the first, unlogged revision
attempt, before this one).
Fixes 2026-10-28 (critic items m1, m5; copy before them: paper/draft/_snapshots/20261028T0930Z_fixes1/figs/fig4/):
panel (b) legend "0 = level" -> "0 = same MAE" (wording rule RC10: "level" only for EQUIVALENT); CHECK_A fact
label of the PM2.5 12-month geometric normal -> "R6, M45, K33" (R6 now holds the value). The longer legend no
longer fitted the page when centred on the panel row, so the panel (b) legend is now centred on the page. No value
changed.

Brief: paper/draft/tables/fig_4_spec.md. Facts: paper/PAPER_FACTS.md (R3, R6, R7, R8,
R11, R16, R17, K63, K64, K67, K73, D22, D54).

Reads only (all read-only, small CSVs):
  D:/treeroute/runs/_headline_tables/headline_93b64854d1f9.csv            (PM2.5)
  D:/treeroute/runs/_headline_tables/ndvi/headline_9e5590eab94b.csv
  D:/treeroute/runs/_headline_tables/fire/headline_85a9134089e4.csv
  D:/treeroute/runs/_headline_tables/defo/headline_1571da960aa6.csv
  D:/treeroute/runs/_headline_tables/coral/headline_344838cf7de1.csv
  D:/treeroute/runs/_headline_tables/scores_long_e2064671e481.csv         (pinned arm at declined leads;
                                                                           also the geometric normal at 12 months)
  D:/treeroute/runs/_headline_tables/ndvi/scores_long_be44fcb279ae.csv
  D:/treeroute/runs/_headline_tables/fire/scores_long_e7f8ef64ffa7.csv    (also the arcsine-scale normal at 6, 12 months)
  D:/treeroute/runs/_headline_tables/coral/scores_long_57920b9d8983.csv
  D:/treeroute/runs/_headline_tables/per_year_bd2c0a61a5a8.csv            (PM2.5)
  D:/treeroute/runs/_headline_tables/ndvi/per_year_b537985b2ac7.csv
  D:/treeroute/runs/_headline_tables/fire/per_year_d657a6a40d37.csv
  D:/treeroute/runs/_headline_tables/defo/per_year_994462902c87.csv
  D:/treeroute/runs/_headline_tables/coral/per_year_7dde14b4e308.csv

Writes only into this script's folder: fig4_data.csv, fig4.pdf, fig4.png.
Every plotted value is checked against its fact-sheet value before drawing (fail loud).
No randomness anywhere.
"""
import sys

sys.dont_write_bytecode = True

import os
from decimal import Decimal

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
import pandas as pd

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
HT = "D:/treeroute/runs/_headline_tables/"

PROBLEMS = [
    # key, display name, sub-folder prefix, headline, scores_long, per_year, leads, lead labels,
    # test years, y scale for panel (a), panel (a) title
    dict(key="pm25", name="PM2.5", headline=HT + "headline_93b64854d1f9.csv",
         scores=HT + "scores_long_e2064671e481.csv", per_year=HT + "per_year_bd2c0a61a5a8.csv",
         leads=[0, 6, 12], lead_labels=["Nowcast", "6 mo", "12 mo"], years=[2020, 2021, 2022, 2023], lead_unit="months",
         scale=1.0, title_a="PM2.5\n(\u00b5g m$^{-3}$)", zero_heavy=False, grid_kind=True,
         off_scale_pz="R3"),
    dict(key="ndvi", name="NDVI", headline=HT + "ndvi/headline_9e5590eab94b.csv",
         scores=HT + "ndvi/scores_long_be44fcb279ae.csv", per_year=HT + "ndvi/per_year_b537985b2ac7.csv",
         leads=[0, 6, 12], lead_labels=["Nowcast", "6 mo", "12 mo"], years=[2020, 2021, 2022, 2023], lead_unit="months",
         scale=1.0, title_a="NDVI\n(index)", zero_heavy=False, grid_kind=True, off_scale_pz="R3"),
    dict(key="fire", name="Burned fraction", headline=HT + "fire/headline_85a9134089e4.csv",
         scores=HT + "fire/scores_long_e7f8ef64ffa7.csv", per_year=HT + "fire/per_year_d657a6a40d37.csv",
         leads=[0, 6, 12], lead_labels=["Nowcast", "6 mo", "12 mo"], years=[2019, 2020, 2021, 2022], lead_unit="months",
         scale=1e3, title_a="Burned fraction\n(fraction, units of 10$^{-3}$)", zero_heavy=True, grid_kind=True,
         off_scale_pz=None),
    dict(key="defo", name="Forest loss", headline=HT + "defo/headline_1571da960aa6.csv",
         scores=None, per_year=HT + "defo/per_year_994462902c87.csv",
         leads=[0, 1], lead_labels=["Nowcast", "1 yr"], years=[2020, 2021, 2022, 2023], lead_unit="years",
         scale=1e3, title_a="Forest loss\n(fraction, units of 10$^{-3}$)", zero_heavy=True, grid_kind=True,
         off_scale_pz=None),
    # coral is the neighbour kind: its skill guard's reference and decline target are both the training
    # median (K33), so no separate guard reference exists at its declined lead
    dict(key="coral", name="Coral bleaching", headline=HT + "coral/headline_344838cf7de1.csv",
         scores=HT + "coral/scores_long_57920b9d8983.csv", per_year=HT + "coral/per_year_7dde14b4e308.csv",
         leads=[0, 183, 365], lead_labels=["Nowcast", "183 d", "365 d"], years=[2016, 2017, 2018, 2019], lead_unit="days",
         scale=1.0, title_a="Coral bleaching\n(percentage points)", zero_heavy=True, grid_kind=False,
         off_scale_pz=None),
]
# panel (a) tick labels: categorical lead slots ("Now" = nowcast), so sideways offsets read as offsets
TICKS_A = {"pm25": ["Now", "6", "12"], "ndvi": ["Now", "6", "12"], "fire": ["Now", "6", "12"],
           "defo": ["Now", "1"], "coral": ["Now", "183", "365"]}

# ---------------------------------------------------------------------------------------------
# Fact-sheet check values (PAPER_FACTS.md). Each is compared at its printed precision.
# ---------------------------------------------------------------------------------------------
CHECK_A = {
    # (problem, lead, series): (printed value, fact ids)
    ("pm25", 0, "final_answer"): ("3.588", "R3"),
    ("pm25", 6, "final_answer"): ("3.846", "R6"),
    ("pm25", 12, "final_answer"): ("4.084", "R6"),
    ("pm25", 0, "decline_target"): ("4.032", "R3, K73"),
    ("pm25", 6, "decline_target"): ("4.054", "R6, K73"),
    ("pm25", 12, "decline_target"): ("4.084", "R6, K73"),
    ("pm25", 0, "reference"): ("3.853", "R3, R4"),
    ("pm25", 6, "reference"): ("3.879", "R6"),
    ("pm25", 6, "damped_persistence"): ("3.975", "R7"),
    ("pm25", 12, "damped_persistence"): ("3.835", "R7, R17"),
    ("pm25", 12, "pinned_arm_rejected"): ("3.840", "R6"),
    ("ndvi", 0, "final_answer"): ("0.03146", "R3"),
    ("ndvi", 6, "final_answer"): ("0.03957", "R6"),
    ("ndvi", 12, "final_answer"): ("0.03958", "R6"),
    ("ndvi", 0, "decline_target"): ("0.03941", "R3"),
    ("ndvi", 6, "decline_target"): ("0.03957", "R6, R17"),
    ("ndvi", 12, "decline_target"): ("0.03958", "R6, R17"),
    ("ndvi", 6, "damped_persistence"): ("0.03862", "R7, R17"),
    ("ndvi", 12, "damped_persistence"): ("0.03882", "R7, R17"),
    ("ndvi", 6, "pinned_arm_rejected"): ("0.0392", "R6"),
    ("ndvi", 12, "pinned_arm_rejected"): ("0.0400", "R6"),
    ("fire", 0, "final_answer"): ("0.004385", "R3"),
    ("fire", 6, "final_answer"): ("0.006312", "R7, R17"),
    ("fire", 12, "final_answer"): ("0.006311", "R17"),
    ("fire", 0, "decline_target"): ("0.006259", "R3"),
    ("fire", 6, "decline_target"): ("0.006312", "R7, R17"),
    ("fire", 12, "decline_target"): ("0.006311", "R17"),
    ("fire", 0, "reference"): ("0.004428", "R3, R4"),
    ("fire", 6, "guard_reference_declined"): ("0.00446", "R11, M45, K33"),
    ("fire", 12, "guard_reference_declined"): ("0.00446", "R11, M45, K33"),
    # PAPER_FACTS R6 (registered 2026-10-27 in the cross-check pass): 3.909 (3.908921; n 91,428), read from
    # scores_long_e2064671e481.csv (lead 12, table pooled, rows all, line pooled, rows_basis all, column
    # arm__log_c_trees_off_unweighted); the full-precision value is checked here
    ("pm25", 12, "guard_reference_declined"): ("3.908921", "R6, M45, K33"),
    ("fire", 0, "predict_zero"): ("0.004284", "R3"),
    ("fire", 6, "predict_zero"): ("0.004284", "R17"),
    ("fire", 12, "predict_zero"): ("0.004284", "R17"),
    ("fire", 6, "damped_persistence"): ("0.006299", "R7"),
    ("fire", 12, "damped_persistence"): ("0.006368", "K64"),
    ("fire", 6, "pinned_arm_rejected"): ("0.00452", "R6, R11"),
    ("fire", 12, "pinned_arm_rejected"): ("0.00450", "R6, R11"),
    ("defo", 0, "final_answer"): ("0.005416", "R3"),
    ("defo", 1, "final_answer"): ("0.005408", "R6"),
    ("defo", 0, "decline_target"): ("0.008405", "R3"),
    ("defo", 1, "decline_target"): ("0.008405", "R3, K63 (lead-1 baselines equal lead 0)"),
    ("defo", 0, "reference"): ("0.005715", "R3, R4"),
    ("defo", 1, "reference"): ("0.005715", "K63"),
    ("defo", 0, "predict_zero"): ("0.006120", "R3"),
    ("defo", 1, "predict_zero"): ("0.006120", "K73"),
    ("defo", 1, "damped_persistence"): ("0.008317", "K64"),
    ("coral", 0, "final_answer"): ("6.698", "R3"),
    ("coral", 183, "final_answer"): ("7.710", "R6"),
    ("coral", 365, "final_answer"): ("8.294", "R6"),
    ("coral", 0, "decline_target"): ("8.294", "R3"),
    ("coral", 183, "decline_target"): ("8.294", "R6"),
    ("coral", 365, "decline_target"): ("8.294", "R6, R17"),
    ("coral", 0, "predict_zero"): ("8.100", "R3"),
    ("coral", 183, "predict_zero"): ("8.100", "K73"),
    ("coral", 365, "predict_zero"): ("8.100", "R17"),
    ("coral", 365, "pinned_arm_rejected"): ("8.281", "R6"),
}
CHECK_DECLINED = {("pm25", 12), ("ndvi", 6), ("ndvi", 12), ("fire", 6), ("fire", 12), ("coral", 365)}  # R6
# declined leads at which the skill guard's reference differs from the decline target (M45, R11; PM2.5 12
# months re-read from source, see CHECK_A); NDVI's pinned arm is identity-link, coral's both are the median
CHECK_GUARD_REF = {("pm25", 12), ("fire", 6), ("fire", 12)}
CHECK_B = {
    # K67, 100 x (mae_adopted - mae_reference) / mae_reference, years in order
    ("pm25", 0): ["-10.78", "-7.75", "-5.16", "-4.03"],
    ("pm25", 6): ["-2.86", "-1.93", "0.0096", "1.29"],
    ("ndvi", 0): ["-23.27", "-19.37", "-21.40", "-16.67"],
    ("fire", 0): ["-0.12", "-1.60", "-0.72", "-1.54"],
    ("defo", 0): ["-3.90", "-6.69", "-6.58", "-4.81"],
    ("defo", 1): ["-4.60", "-6.08", "-6.25", "-5.17"],
    ("coral", 0): ["-26.27", "10.45", "-15.04", "3.86"],
    ("coral", 183): ["-11.13", "7.24", "-1.29", "7.99"],
}
# D54 (coral nowcast, per year: ours / training median / predict-zero) and D22 (fire 2021)
CHECK_MAE_YEAR = {
    ("coral", 0, 2016): ("12.41", "16.83", "17.08"), ("coral", 0, 2017): ("3.57", "3.23", "2.81"),
    ("coral", 0, 2018): ("1.28", "1.51", "0.84"), ("coral", 0, 2019): ("4.81", "4.63", "4.30"),
    ("fire", 0, 2021): ("0.004590", None, "0.004674"),
}
# Predict-zero beats the final answer (D22: fire 2019, 2020, 2022; D54, K67: coral 2017-2019 at both kept leads)
CHECK_PZ_BEATS = {("fire", 0): [2019, 2020, 2022], ("coral", 0): [2017, 2018, 2019],
                  ("coral", 183): [2017, 2018, 2019], ("defo", 0): [], ("defo", 1): []}


def agrees(value, printed):
    """True if value rounds to the printed fact value at the printed precision."""
    q = Decimal(printed)
    step = Decimal(1).scaleb(q.as_tuple().exponent)
    return abs(Decimal(repr(float(value))) - q) <= step / 2 + Decimal("1e-15")


def fail(msg):
    raise SystemExit("FIG4 CHECK FAILED: " + msg)


# ---------------------------------------------------------------------------------------------
# Panel (a) data
# ---------------------------------------------------------------------------------------------
rows_out = []
DODGE = 0.3  # panel (a), in lead slots: pinned-arm crosses right of their lead, damped persistence left
X_OFFSET = {"pinned_arm_rejected": DODGE, "damped_persistence": -DODGE}


def add(panel, p, lead, label, series, value, source, selector, facts="", state="", year=None,
        note=""):
    plotted = value * (p["scale"] if panel == "a" else 1.0)
    if series == "predict_zero_off_scale_not_drawn":
        plotted = None
    rows_out.append(dict(panel=panel, problem=p["name"], lead=lead, lead_label=label, test_year=year,
                         series=series, state=state, value=value, plotted_value=plotted,
                         x_offset_in_lead_slots=X_OFFSET.get(series, 0.0) if panel == "a" else 0.0,
                         plotted_unit=("MAE x %g" % p["scale"]) if panel == "a"
                         else "% MAE reduction vs reference (above 0 favours the series)",
                         source_file=source, source_selector=selector, fact_ids=facts, note=note))


def check_a(p, lead, series, value):
    key = (p["key"], lead, series)
    if key in CHECK_A:
        printed, facts = CHECK_A[key]
        if not agrees(value, printed):
            fail(f"{key}: file {value!r} vs fact {printed}")
        return facts
    return "computed from source (no fact value)"


data_a = {}
DP_SHARE = {}  # damped persistence: scored rows / labelled test rows (caption "98.7-100%")
for p in PROBLEMS:
    h = pd.read_csv(p["headline"])
    h = h[(h["rows"] == "all") & (h["line"] == "pooled")].set_index("lead")
    if list(h.index) != p["leads"]:
        fail(f"{p['key']} leads {list(h.index)}")
    adopted_arm_lead0 = h.loc[0, "adopted"]
    sl = None
    if p["scores"] is not None:
        sl = pd.read_csv(p["scores"], usecols=["lead", "rows", "table", "rows_basis", "column", "line", "n", "mae"])
        sl = sl[(sl["rows"] == "all") & (sl["table"] == "pooled") & (sl["line"] == "pooled")
                & (sl["rows_basis"] == "all")]
    d = {}
    for lead, label in zip(p["leads"], p["lead_labels"]):
        r = h.loc[lead]
        declined = bool(r["declined"])
        if declined != ((p["key"], lead) in CHECK_DECLINED):
            fail(f"{p['key']} lead {lead}: declined={declined} disagrees with R6")
        sel = f"lead={lead}, rows=all, line=pooled"
        # final answer
        v = float(r["mae_adopted"])
        st = "declined (final answer = decline target)" if declined else "skill guard passed"
        add("a", p, lead, label, "final_answer", v, p["headline"], sel + ", column=mae_adopted",
            check_a(p, lead, "final_answer", v), st)
        d[(lead, "final_answer")] = (v, declined)
        # decline target: arithmetic normal on the grids, training median on coral (M44, K33)
        col = "mae_reference" if p["key"] == "coral" else "mae_guess_normal"
        v = float(r[col])
        add("a", p, lead, label, "decline_target", v, p["headline"], sel + f", column={col}",
            check_a(p, lead, "decline_target", v))
        d[(lead, "decline_target")] = v
        # the declined answer is the identity-link trees-off column; it equals base__guess_normal up to
        # the climatology identity's rounding (below 2e-8 relative here; M33, K60)
        if declined and abs(float(r["mae_adopted"]) - v) > 1e-6 * v:
            fail(f"{p['key']} lead {lead}: declined answer != decline target")
        # reference where it differs from the decline target (kept leads)
        if not declined:
            v = float(r["mae_reference"])
            if abs(v - d[(lead, "decline_target")]) > 1e-6 * v:
                add("a", p, lead, label, "reference", v, p["headline"], sel + ", column=mae_reference",
                    check_a(p, lead, "reference", v), "own-link trees-off fit (" + r["reference"] + ")")
                d[(lead, "reference")] = v
        # At a declined lead on the grid kinds, the skill guard's reference is the pinned arm's own-link
        # trees-off (K33, M45). It is drawn as its own marker wherever it differs from the decline target
        # (PM2.5 12 months: geometric normal; burned fraction 6 and 12 months: arcsine-scale normal).
        # The printed reference at a declined lead is the decline target itself (K46), so this is NOT
        # added to the "reference" series.
        if declined and p["grid_kind"]:
            rest = adopted_arm_lead0.split("__", 1)[1]
            links = [k for k in ("identity", "log_c", "arcsine") if rest.startswith(k + "_")]
            if len(links) != 1:
                fail(f"{p['key']}: cannot read the link of the pinned arm {adopted_arm_lead0}")
            gcol = f"arm__{links[0]}_trees_off_unweighted"
            m = sl[(sl["lead"] == lead) & (sl["column"] == gcol)]
            if len(m) != 1 or int(m["n"].iloc[0]) != int(r["n_adopted"]):
                fail(f"{p['key']} {gcol} row at lead {lead}")
            v = float(m["mae"].iloc[0])
            if abs(v - d[(lead, "decline_target")]) > 1e-6 * v:
                name = {"log_c": "geometric normal", "arcsine": "arcsine-scale normal"}[links[0]]
                add("a", p, lead, label, "guard_reference_declined", v, p["scores"],
                    f"lead={lead}, rows=all, table=pooled, line=pooled, rows_basis=all, column={gcol}",
                    check_a(p, lead, "guard_reference_declined", v),
                    f"{name}: the pinned arm's reference (the normal in its link), which the skill guard "
                    "compared against on the guard rows; not the printed reference (K46)")
                d[(lead, "guard_reference_declined")] = v
            elif links[0] != "identity":
                fail(f"{p['key']} lead {lead}: non-identity guard reference equals the decline target")
        # pinned arm at declined leads (what the skill guard rejected)
        if declined:
            m = sl[(sl["lead"] == lead) & (sl["column"] == adopted_arm_lead0)]
            if len(m) != 1 or int(m["n"].iloc[0]) != int(r["n_adopted"]):
                fail(f"{p['key']} pinned arm row at lead {lead}")
            v = float(m["mae"].iloc[0])
            add("a", p, lead, label, "pinned_arm_rejected", v, p["scores"],
                f"lead={lead}, rows=all, table=pooled, line=pooled, rows_basis=all, column={adopted_arm_lead0}",
                check_a(p, lead, "pinned_arm_rejected", v), "skill guard failed")
            d[(lead, "pinned_arm_rejected")] = v
        # damped persistence: leads >= 1, gridded problems only (coral is on a subset: R8, K64)
        if lead > 0 and p["key"] != "coral":
            v = float(r["mae_damped_persistence"])
            share = ""
            if sl is not None:
                m = sl[(sl["lead"] == lead) & (sl["column"] == "base__damped_persistence")]
                if len(m) != 1 or abs(float(m["mae"].iloc[0]) - v) > 1e-6 * v:
                    fail(f"{p['key']} lead {lead}: damped persistence differs between headline and scores_long")
                share = f"scored on {int(m['n'].iloc[0])} of {int(r['n_adopted'])} labelled test rows"
            else:  # defo: read the row count from its scores_long
                sld = pd.read_csv(HT + "defo/scores_long_726623e350c2.csv",
                                  usecols=["lead", "rows", "table", "rows_basis", "column", "line", "n"])
                m = sld[(sld["lead"] == lead) & (sld["rows"] == "all") & (sld["table"] == "pooled")
                        & (sld["line"] == "pooled") & (sld["rows_basis"] == "all")
                        & (sld["column"] == "base__damped_persistence")]
                share = (f"scored on {int(m['n'].iloc[0])} of {int(r['n_adopted'])} labelled test rows "
                         "(D:/treeroute/runs/_headline_tables/defo/scores_long_726623e350c2.csv)")
            add("a", p, lead, label, "damped_persistence", v, p["headline"],
                sel + ", column=mae_damped_persistence", check_a(p, lead, "damped_persistence", v),
                note=share)
            d[(lead, "damped_persistence")] = v
            DP_SHARE[(p["key"], lead)] = int(m["n"].iloc[0]) / int(r["n_adopted"])
        # predict-zero: zero-heavy problems only (off scale on PM2.5, NDVI)
        v = float(r["mae_predict_zero"])
        if p["zero_heavy"]:
            add("a", p, lead, label, "predict_zero", v, p["headline"], sel + ", column=mae_predict_zero",
                check_a(p, lead, "predict_zero", v))
            d[(lead, "predict_zero")] = v
        elif lead == 0:
            printed = {"pm25": "17.52", "ndvi": "0.4365"}[p["key"]]
            if not agrees(v, printed):
                fail(f"{p['key']} predict-zero {v} vs R3 {printed}")
            add("a", p, lead, label, "predict_zero_off_scale_not_drawn", v, p["headline"],
                sel + ", column=mae_predict_zero", "R3", note="off scale; stated in the caption, not drawn")
            d["pz_off_scale"] = v
    data_a[p["key"]] = d

guard_drawn = {(p["key"], l) for p in PROBLEMS for l in p["leads"]
               if (l, "guard_reference_declined") in data_a[p["key"]]}
if guard_drawn != CHECK_GUARD_REF:
    fail(f"skill guard's reference drawn at {sorted(guard_drawn)}, expected {sorted(CHECK_GUARD_REF)}")
if not (agrees(100 * min(DP_SHARE.values()), "98.7") and agrees(100 * max(DP_SHARE.values()), "100")):
    fail(f"damped persistence coverage {DP_SHARE}")

# R17: at every declined lead a naive baseline beat the decline answer
for p in PROBLEMS:
    d = data_a[p["key"]]
    for lead in p["leads"]:
        fa, declined = d[(lead, "final_answer")]
        if declined:
            naive = [d.get((lead, s)) for s in ("damped_persistence", "predict_zero")]
            if not any(x is not None and x < fa for x in naive):
                fail(f"R17 not reproduced at {p['key']} lead {lead}")

# ---------------------------------------------------------------------------------------------
# Panel (b) data: kept leads only
# ---------------------------------------------------------------------------------------------
data_b = {}
for p in PROBLEMS:
    y = pd.read_csv(p["per_year"])
    y = y[y["rows"] == "all"]
    for lead, label in zip(p["leads"], p["lead_labels"]):
        if (p["key"], lead) in CHECK_DECLINED:
            continue
        s = y[y["lead"] == lead].sort_values("year")
        if list(s["year"]) != p["years"]:
            fail(f"{p['key']} lead {lead} years {list(s['year'])}")
        k67 = 100.0 * (s["mae_adopted"] - s["mae_reference"]) / s["mae_reference"]  # K67's sign
        for yr, v, printed in zip(p["years"], k67, CHECK_B[(p["key"], lead)]):
            if not agrees(v, printed):
                fail(f"K67 {p['key']} lead {lead} {yr}: {v} vs {printed}")
        pct = -k67  # plotted: MAE reduction, 100 x (reference - final answer) / reference; above 0 = better
        for yr, a_, r_, z_ in zip(s["year"], s["mae_adopted"], s["mae_reference"], s["mae_predict_zero"]):
            c = CHECK_MAE_YEAR.get((p["key"], lead, int(yr)))
            if c:
                if not agrees(a_, c[0]) or (c[1] and not agrees(r_, c[1])) or not agrees(z_, c[2]):
                    fail(f"D54/D22 {p['key']} {yr}")
        sel = f"lead={lead}, rows=all; 100*(mae_reference-mae_adopted)/mae_reference"
        for yr, v in zip(p["years"], pct):
            add("b", p, lead, label, "final_answer_reduction_vs_reference", float(v), p["per_year"],
                sel + f", year={yr}", "K67 (sign reversed), R16", "kept lead", year=yr)
        data_b[(p["key"], lead)] = list(pct)
        if p["zero_heavy"]:
            pz = 100.0 * (s["mae_reference"] - s["mae_predict_zero"]) / s["mae_reference"]
            beats = [int(yr) for yr, a_, z_ in zip(s["year"], s["mae_adopted"], s["mae_predict_zero"]) if z_ < a_]
            if beats != CHECK_PZ_BEATS[(p["key"], lead)]:
                fail(f"predict-zero years {p['key']} lead {lead}: {beats}")
            for yr, v in zip(p["years"], pz):
                add("b", p, lead, label, "predict_zero_reduction_vs_reference", float(v), p["per_year"],
                    f"lead={lead}, rows=all; 100*(mae_reference-mae_predict_zero)/mae_reference, year={yr}",
                    "computed from source (signs: D22, D54, K67)", year=yr)
            data_b[(p["key"], lead, "pz")] = list(pz)

# Predict-zero against the reference is the same series at both kept leads where the reference is
# the same (forest loss, coral); draw it once per problem, and fail loud if it is not identical.
for k in ("defo", "coral"):
    leads = [l for l in [x["leads"] for x in PROBLEMS if x["key"] == k][0] if (k, l) not in CHECK_DECLINED]
    a0, a1 = data_b[(k, leads[0], "pz")], data_b[(k, leads[1], "pz")]
    if max(abs(u - v) for u, v in zip(a0, a1)) > 1e-9:
        fail(f"{k}: predict-zero vs reference differs between kept leads")

pd.DataFrame(rows_out).to_csv(os.path.join(OUT_DIR, "fig4_data.csv"), index=False)

# ---------------------------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------------------------
MM = 1 / 25.4
# Superscripts (the exponents in "ug m^-3" and "10^-3" in the panel titles) are set at 7 pt, not mathtext's
# default 0.7 x 7.5 = 5.25 pt, so that no text in the figure is below 7 pt at print size. Arial has no
# superscript-minus glyph, so mathtext is needed; its script scale is a module constant (matplotlib 3.11).
import matplotlib._mathtext as _mt
_mt.SHRINK_FACTOR = 7.0 / 7.5
plt.rcParams.update({
    "font.family": "Arial", "font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7.5,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5, "pdf.fonttype": 42, "ps.fonttype": 42,
    "svg.fonttype": "none", "mathtext.fontset": "custom", "mathtext.rm": "Arial",
    "mathtext.it": "Arial:italic", "mathtext.bf": "Arial:bold", "mathtext.default": "regular",
"axes.edgecolor": "#52514e", "xtick.color": "#0b0b0b", "ytick.color": "#0b0b0b",
    "axes.labelcolor": "#0b0b0b", "text.color": "#0b0b0b",
})
# Colours (validated with a Python port of the dataviz validator: CVD dE >= 9.8 and normal dE >= 15
# for every pair that shares a panel; greyscale is carried by marker and line style as well)
C_FINAL = "#2a78d6"      # final answer (blue, slot 1)
C_LEAD = "#104281"       # final answer at the kept forecast lead, panel (b) (darker blue step)
C_DP = "#eb6834"         # damped persistence (orange, slot 2)
C_PZ = "#898781"         # predict-zero (grey)
C_DECL = "#0b0b0b"       # decline target (ink)
C_REF = "#52514e"        # reference (secondary ink)
C_BAND = "#e3e1da"       # declined lead band (darkened 2026-10-27 so it survives print and photocopy)
C_GRID = "#e1e0d9"

fig = plt.figure(figsize=(175 * MM, 140 * MM))
gs = fig.add_gridspec(4, 5, height_ratios=[1.0, 0.44, 1.0, 0.10], hspace=0.55, wspace=0.62,
                      left=0.085, right=0.99, top=0.92, bottom=0.03)


def style_axis(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=C_GRID, lw=0.4, zorder=0)
    ax.set_axisbelow(True)


axes_a = []
for i, p in enumerate(PROBLEMS):
    ax = fig.add_subplot(gs[0, i])
    axes_a.append(ax)
    style_axis(ax)
    d = data_a[p["key"]]
    sc = p["scale"]
    xs = list(range(len(p["leads"])))
    allv = []
    for x, lead in zip(xs, p["leads"]):
        if d[(lead, "final_answer")][1]:
            ax.axvspan(x - 0.5, x + 0.5, color=C_BAND, lw=0, zorder=0.5)
    # decline target
    v = [d[(l, "decline_target")] * sc for l in p["leads"]]
    allv += v
    ax.plot(xs, v, color=C_DECL, lw=0.9, ls=(0, (4, 2)), zorder=2)
    # reference at kept leads (where it differs from the decline target): dotted, small filled diamonds
    rx = [x for x, l in zip(xs, p["leads"]) if (l, "reference") in d]
    if rx:
        rv = [d[(p["leads"][x], "reference")] * sc for x in rx]
        allv += rv
        ax.plot(rx, rv, color=C_REF, lw=1.2, ls=(0, (1, 1.4)), zorder=2.2, marker="D", ms=2.6,
                mfc=C_REF, mec=C_REF, mew=0)
        if len(rx) == 1:
            # a lone reference point (burned fraction's nowcast, 0.004428 against 0.004385) sits under the
            # final answer's circle: draw its level as a short dotted bar so it stays visible
            ax.plot([rx[0] - 0.36, rx[0] + 0.36], rv * 2, color=C_REF, lw=1.2, ls=(0, (1, 1.4)), zorder=2.2)
    # skill guard's reference at a declined lead (pinned arm's link): open diamond, no line
    for x, l in zip(xs, p["leads"]):
        if (l, "guard_reference_declined") in d:
            gv = d[(l, "guard_reference_declined")] * sc
            allv.append(gv)
            ax.plot([x], [gv], "D", ms=3.8, mfc="white", mec=C_REF, mew=0.9, zorder=2.6)
    # predict-zero
    if p["zero_heavy"]:
        v = [d[(l, "predict_zero")] * sc for l in p["leads"]]
        allv += v
        ax.plot(xs, v, color=C_PZ, lw=0.8, ls=(0, (5, 1.5, 1, 1.5)), marker="s", ms=3.6,
                mfc="white", mec=C_PZ, mew=0.9, zorder=2.5)
    # damped persistence
    dx = [x for x, l in zip(xs, p["leads"]) if (l, "damped_persistence") in d]
    if dx:
        v = [d[(p["leads"][x], "damped_persistence")] * sc for x in dx]
        allv += v
        # markers only: a connecting line between offset slots would suggest values between leads
        ax.plot([x - DODGE for x in dx], v, color=C_DP, lw=0, marker="^", ms=4.4, mfc=C_DP, mec="white",
                mew=0.5, zorder=3)
    # final answer: the solid line joins the kept leads only (always a prefix: the nowcast is kept on all
    # five problems). It stops at the last kept lead, because the open circle at a declined lead is the
    # decline target, a different forecast, and sits on the dashed decline-target line.
    v = [d[(l, "final_answer")][0] * sc for l in p["leads"]]
    allv += v
    kept_x = [x for x, l in zip(xs, p["leads"]) if not d[(l, "final_answer")][1]]
    if kept_x != xs[:len(kept_x)] or not kept_x:
        fail(f"{p['key']}: kept leads are not a prefix of the leads")
    if len(kept_x) > 1:
        ax.plot(kept_x, v[:len(kept_x)], color=C_FINAL, lw=1.2, zorder=4)
    for x, l in zip(xs, p["leads"]):
        fa, declined = d[(l, "final_answer")]
        if declined:
            ax.plot([x], [fa * sc], "o", ms=5.0, mfc="white", mec=C_FINAL, mew=1.1, zorder=5)
        else:
            ax.plot([x], [fa * sc], "o", ms=5.0, mfc=C_FINAL, mec="white", mew=0.6, zorder=5)
        if (l, "pinned_arm_rejected") in d:
            pv = d[(l, "pinned_arm_rejected")] * sc
            allv.append(pv)
            ax.plot([x + DODGE], [pv], "x", ms=4.6, mec=C_FINAL, mew=1.1, zorder=6)
    lo, hi = min(allv), max(allv)
    pad = 0.08 * (hi - lo)
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_xlim(-0.5, len(xs) - 0.5)
    ax.set_xticks(xs)
    ax.set_xticklabels(TICKS_A[p["key"]])
    ax.tick_params(axis="x", length=2, pad=2)
    ax.set_xlabel("Lead (%s)" % p["lead_unit"], labelpad=2)
    ax.set_title(p["title_a"], loc="left", fontsize=7.5, pad=4, linespacing=1.1)
    # predict-zero on PM2.5 and NDVI is off scale (17.52, 0.4365; R3): stated in the caption, not drawn
axes_a[0].set_ylabel("Pooled test MAE")

# legend for (a)
lax = fig.add_subplot(gs[1, :])
lax.axis("off")
handles_a = [
    Line2D([], [], color=C_FINAL, lw=1.2, marker="o", ms=5, mfc=C_FINAL, mec="white",
           label="Final answer, skill guard passed"),
    Line2D([], [], color=C_FINAL, lw=0, marker="o", ms=5, mfc="white", mec=C_FINAL, mew=1.1,
           label="Final answer at a declined lead (= decline target)"),
    Line2D([], [], color=C_FINAL, lw=0, marker="x", ms=4.6, mew=1.1,
           label="Pinned arm rejected by the skill guard"),
    Patch(facecolor=C_BAND, edgecolor="none", label="Declined lead"),
    Line2D([], [], lw=0, label=" "),  # spacer: left column = our answers, right column = normals, baselines
    Line2D([], [], color=C_DECL, lw=0.9, ls=(0, (4, 2)),
           label="Decline target (arithmetic normal; on coral the training median)"),
    Line2D([], [], color=C_REF, lw=1.2, ls=(0, (1, 1.4)), marker="D", ms=2.6, mfc=C_REF, mew=0,
           label="Reference at kept leads, where it differs from the decline target"),
    Line2D([], [], lw=0, marker="D", ms=3.8, mfc="white", mec=C_REF, mew=0.9,
           label="Pinned arm's reference at a declined lead (normal in its link)"),
    Line2D([], [], color=C_DP, lw=0, marker="^", ms=4.4, mec="white", mew=0.5, label="Damped persistence"),
    Line2D([], [], color=C_PZ, lw=0.8, ls=(0, (5, 1.5, 1, 1.5)), marker="s", ms=3.6, mfc="white",
           mec=C_PZ, mew=0.9, label="Predict-zero"),
]
lax.legend(handles=handles_a, loc="center", ncol=2, frameon=False, handlelength=2.6, columnspacing=3.0,
           handletextpad=0.6, borderaxespad=0, fontsize=7)

# (b)
axes_b = []
for i, p in enumerate(PROBLEMS):
    ax = fig.add_subplot(gs[2, i])
    axes_b.append(ax)
    style_axis(ax)
    xs = list(range(4))
    ax.axhline(0, color=C_DECL, lw=0.8, zorder=1.5)
    allv = [0.0]
    kept = [l for l in p["leads"] if (p["key"], l) not in CHECK_DECLINED]
    pz_done = False
    for j, lead in enumerate(kept):
        if p["zero_heavy"] and not pz_done:
            v = data_b[(p["key"], lead, "pz")]
            allv += v
            ax.plot(xs, v, color=C_PZ, lw=0.8, ls=(0, (5, 1.5, 1, 1.5)), marker="s", ms=3.6, mfc="white",
                    mec=C_PZ, mew=0.9, zorder=2.5)
            pz_done = True
        v = data_b[(p["key"], lead)]
        allv += v
        if j == 0:
            ax.plot(xs, v, color=C_FINAL, lw=1.2, marker="o", ms=4.4, mfc=C_FINAL, mec="white", mew=0.6,
                    zorder=4)
        else:
            # kept forecast lead: own marker (down-triangle) as well as a darker blue and a dashed line, so it
            # separates from the nowcast in greyscale where the two lines are close (forest loss)
            ax.plot(xs, v, color=C_LEAD, lw=1.2, ls=(0, (3.5, 1.5)), marker="v", ms=4.8, mfc=C_LEAD,
                    mec="white", mew=0.6, zorder=3.5)
    lo, hi = min(allv), max(allv)
    pad = 0.10 * (hi - lo)
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_xlim(-0.4, 3.4)
    ax.set_xticks(xs)
    yrs = p["years"]
    ax.set_xticklabels([str(yrs[0])] + ["\u2019%02d" % (yy % 100) for yy in yrs[1:]])
    ax.tick_params(axis="x", length=2, pad=2)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))
    lead_txt = ", ".join(p["lead_labels"][p["leads"].index(l)].replace("Nowcast", "nowcast") for l in kept)
    ax.set_title(p["name"] + "\n(" + lead_txt + ")", loc="left", fontsize=7.5, pad=4, linespacing=1.1)
axes_b[0].set_ylabel("MAE reduction against\nthe reference (%)", labelpad=2)
for ax in axes_b:
    ax.set_xlabel("Test year", labelpad=2)

lbx = fig.add_subplot(gs[3, :])
lbx.axis("off")
handles_b = [
    Line2D([], [], color=C_FINAL, lw=1.2, marker="o", ms=4.4, mec="white", mew=0.6,
           label="Final answer, nowcast"),
    Line2D([], [], color=C_LEAD, lw=1.2, ls=(0, (3.5, 1.5)), marker="v", ms=4.8, mec="white", mew=0.6,
           label="Final answer, kept forecast lead"),
    Line2D([], [], color=C_PZ, lw=0.8, ls=(0, (5, 1.5, 1, 1.5)), marker="s", ms=3.6, mfc="white", mec=C_PZ,
           mew=0.9, label="Predict-zero"),
    Line2D([], [], color=C_DECL, lw=0.8, label="Reference (0 = same MAE; above 0 = better)"),
]
# centred on the page, not on the panel row (which is offset right by the y-label margin): with "0 = same MAE"
# the one-row legend is too wide to stay on the page when centred on the panel row (2026-10-28)
_lbx_pos = lbx.get_position()
lbx.legend(handles=handles_b, loc="center", bbox_to_anchor=((0.5 - _lbx_pos.x0) / _lbx_pos.width, 0.5), ncol=4,
           frameon=False, handlelength=2.2, columnspacing=1.3, handletextpad=0.6, borderaxespad=0, fontsize=7)

for row_axes, letter in ((axes_a, "a"), (axes_b, "b")):
    top = row_axes[0].get_position().y1
    fig.text(0.008, top + 0.045, letter, fontsize=9, fontweight="bold", va="bottom")

# fail loud if any text or legend runs off the page (the coral title and the legends are the widest)
fig.canvas.draw()
_r = fig.canvas.get_renderer()
_W, _H = fig.bbox.width, fig.bbox.height
for _t in [a.title for a in axes_a + axes_b] + fig.texts + [lax.get_legend(), lbx.get_legend()]:
    _b = _t.get_window_extent(_r)
    if _b.x0 < 0 or _b.y0 < 0 or _b.x1 > _W or _b.y1 > _H:
        fail(f"text off the page: {_b}")

fig.savefig(os.path.join(OUT_DIR, "fig4.pdf"))
fig.savefig(os.path.join(OUT_DIR, "fig4.png"), dpi=300)
print("ok:", len(rows_out), "values written to fig4_data.csv")
