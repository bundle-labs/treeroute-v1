"""Figure 3: windows, cuts and locks of the five runs (drawing brief: fig2_spec.md, same folder). Round 4 (2026-11-11): figures renumbered by first citation: map (unnumbered) -> 1, 1 -> 2, 2 -> 3, 3 -> 4, 4 -> 5 (folders keep their names; paper/figures/FIGURE_NUMBERS.md).

Reads, read-only, each headline run's derived.json (rules R4, R5, R7, R10, R11), its adoption*.json.lock.json and
test_labels_opened_lead_*.json files, and ruling V3 in engine/OWNER_RULINGS_2026-10-06.md, and checks every value
against the values transcribed from paper/PAPER_FACTS.md (fact IDs beside each). Any mismatch raises; nothing is
drawn then. Writes fig2.pdf, fig2.png (300 dpi) and fig2_data.csv (every plotted value with its source, plus the
check rows behind the caption) next to this script. No engine code is imported. Run: python fig2.py

Revision 2026-10-27 (review log: paper/draft/review_logs/figsupp_fig2_log.md; pre-revision copy in
paper/draft/_snapshots/20261027T1500Z_figsupp/fig2/).
Fixes 2026-10-28 (critic item m5; copy before them: paper/draft/_snapshots/20261028T0930Z_fixes1/figs/fig2/):
the fact labels written into fig2_data.csv now name the final IDs K84, K85 and M6 (iv), which PAPER_FACTS.md
holds since the cross-check pass of 2026-10-27. No value or drawing changed.
"""
import sys

sys.dont_write_bytecode = True

import csv  # noqa: E402
import datetime as dt  # noqa: E402
import glob  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib._mathtext as _mathtext  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402
from matplotlib.path import Path  # noqa: E402

OUT = r"C:/Users/<user>/Desktop/data set for reserch paper/paper/figures/fig2"
RUN_ROOT = r"D:/treeroute/runs"
PREREG = r"C:/Users/<user>/Desktop/data set for reserch paper/engine/PREREGISTRATION_DRAFT.md"
RULINGS = r"C:/Users/<user>/Desktop/data set for reserch paper/engine/OWNER_RULINGS_2026-10-06.md"
TABLE_LADDER = (r"C:/Users/<user>/Desktop/data set for reserch paper/engine/treeroute/pipeline/"
                r"table_ladder.py")

# ---- values transcribed from PAPER_FACTS.md (checked against the run folders below) ----------------------------
# M3 run folders; M7 windows; M9 leads; R4 (derived.json) first year of the lagged driver stores and Y0 (D42: Y0
# 2004 on forest loss); M6 coral window by hand; P23/P28 and Table 1 test-exposed choices (phrases, no numbers);
# M1 run-lock stamps.
PROBLEMS = [
    dict(key="pm25", name="PM2.5", run="pm25/headline/20261007_74e67609", cadence="month",
         inner_fit=(2003, 2016), inner_score=(2017, 2019), test=(2020, 2023), target_first=2002, lag_first=2002,
         y0=2003, leads=[6, 12], lead=12, lead_text="L = 12 months", extra=[],
         exposed=["burned-area driver block"],
         exposed_src="P23 (PM2.5's GFED burn block, through a 2020-23 screen); Table 1; " + PREREG + " Appendix B",
         facts_win="M7", freeze="FREEZE_20261006T203115Z"),
    dict(key="ndvi", name="NDVI", run="ndvi/headline/20261016_d1de3158", cadence="month",
         inner_fit=(2003, 2016), inner_score=(2017, 2019), test=(2020, 2023), target_first=2002, lag_first=2002,
         y0=2003, leads=[6, 12], lead=12, lead_text="L = 12 months", extra=[],
         exposed=["architecture;", "five router-context drivers"],
         exposed_src="P23, P28 (NDVI architecture chosen on 2020-2023; top-5 context list), M6, K12; Table 1; S1 DE1, DE2",
         facts_win="M7", freeze="FREEZE_20261016T090651Z"),
    dict(key="fire", name="Burned fraction", run="fire/headline/20261017_869d1f38", cadence="month",
         inner_fit=(2003, 2015), inner_score=(2016, 2018), test=(2019, 2022), target_first=2002, lag_first=2002,
         y0=2003, leads=[6, 12], lead=12, lead_text="L = 12 months", extra=["assembled record ends 2022"],
         exposed=["last training year,", "hence test window"],
         exposed_src="P23 (fire's <= 2018 cut, chosen knowing earlier results), C8; Table 1; S1 TW2",
         facts_win="M7, D20, C1", freeze="FREEZE_20261016T091126Z"),
    dict(key="defo", name="Forest loss", run="defo/headline/20261017_d71c61f4", cadence="year",
         inner_fit=(2004, 2016), inner_score=(2017, 2019), test=(2020, 2023), target_first=2001, lag_first=2002,
         y0=2004, leads=[1], lead=1, lead_text="L = 1 year", extra=[],
         exposed=["region penalty centre; row budget"],
         exposed_src="P23 (lambda 100; 60,000-row budget), M21, M24, M27; Table 1; S1 DE5, DE6; " + PREREG
                     + " Appendix B (engine constants; the budget's exposure is recorded there as unknown)",
         facts_win="M7", freeze="FREEZE_20261017T105545Z"),
    dict(key="coral", name="Coral bleaching", run="coral/headline/20261020_f3b8e3da", cadence="day",
         inner_fit=(1994, 2012), inner_score=(2013, 2015), test=(2016, 2019), target_first=None, lag_first=None,
         y0=1994, leads=[183, 365], lead=365, lead_text="L = 365 days", extra=[],
         exposed=["tree inputs, links, pool design;", "test window set by hand"],
         exposed_src="P23 (coral's columns, links and pool design), P28, M6 (window signed after yearly counts); "
                     "Table 1; S1 DE3, TW3",
         facts_win="M7, M6", freeze="FREEZE_20261020T100907Z"),
]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
V3_TEXT = "2016-2019, by leaving out the 38 visits of 2020"  # ruling V3 row, read and checked below


class FigureCheckError(RuntimeError):
    pass


def need(cond, msg):
    if not cond:
        raise FigureCheckError(msg)


# ---- step and day positions (x = fractional calendar year at the END of the cut step) -------------------------
def step_end_x(step, cadence):
    if cadence == "month":  # timing/cuts.py year_last_step: monthly step = year x 12 + month
        year, m0 = divmod(step - 1, 12)
        return year + (m0 + 1) / 12.0, "end of %s %d" % (MONTHS[m0], year)
    if cadence == "year":
        return step + 1.0, "end of %d" % step
    if cadence == "day":  # derived.json R9/R11 days are proleptic ordinals (date.fromordinal)
        d = dt.date.fromordinal(step)
        ndays = 366 if (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0)) else 365
        return d.year + d.timetuple().tm_yday / float(ndays), "end of %d %s %d" % (d.day, MONTHS[d.month - 1],
                                                                                   d.year)
    raise FigureCheckError("unknown cadence %r" % cadence)


def expected_cuts(p, lead):
    """K21 recomputed from the windows: the check that derived.json R11 follows the stated rule."""
    train_end, inner_fit_end = p["test"][0] - 1, p["inner_fit"][1]
    if p["cadence"] == "month":
        tes, ies = train_end * 12 + 12, inner_fit_end * 12 + 12
        return min(tes, tes - (lead - 1)), min(ies, ies - (lead - 1))
    if p["cadence"] == "year":
        return min(train_end, train_end - (lead - 1)), min(inner_fit_end, inner_fit_end - (lead - 1))
    if lead == 0:
        return dt.date(train_end, 12, 31).toordinal(), dt.date(inner_fit_end, 12, 31).toordinal()
    return (dt.date(p["test"][0], 1, 1).toordinal() - lead,
            dt.date(p["inner_score"][0], 1, 1).toordinal() - lead)


def read_run(p):
    path = os.path.join(RUN_ROOT, p["run"], "derived.json").replace("\\", "/")
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    r7 = d["R7"]["value"]
    need(tuple(r7["inner_fit"]) == p["inner_fit"], "%s inner fit %r != M7" % (p["key"], r7["inner_fit"]))
    need((r7["inner_score"][0], r7["inner_score"][-1]) == p["inner_score"] and len(r7["inner_score"]) == 3,
         "%s inner score %r != M7" % (p["key"], r7["inner_score"]))
    need((r7["test_years"][0], r7["test_years"][-1]) == p["test"] and len(r7["test_years"]) == 4,
         "%s test %r != M7" % (p["key"], r7["test_years"]))
    need(r7["train_end"] == p["test"][0] - 1, "%s train end" % p["key"])
    need(d["R5"]["inputs"]["y_end"] == p["test"][1], "%s R5 y_end != last test year" % p["key"])
    r4 = d["R4"]
    lag = r4["inputs"]["largest_lag_years"]
    need(r4["value"] == p["y0"] and r7["y0"] == p["y0"], "%s Y0" % p["key"])
    if p["lag_first"] is None:  # coral: no engine-lagged source (R4 flag no_lag_sources), Y0 = first data year
        need("no_lag_sources" in r4["flags"] and lag == 0 and r4["inputs"]["first_data_year"] == p["y0"],
             "%s expected no lag sources" % p["key"])
    else:
        ds = r4["inputs"]["driver_stores"]
        need(ds["first_data_year"] == p["lag_first"] and r4["inputs"]["first_data_year"] == p["lag_first"],
             "%s first year of the lagged driver stores" % p["key"])
        need(ds["target_first_year"] == p["target_first"], "%s target first year" % p["key"])
        need(r4["value"] == ds["first_data_year"] + lag, "%s Y0 is not lagged-store first year + largest lag"
             % p["key"])
    r10 = d["R10"]["value"]
    need(list(r10["leads"]) == p["leads"], "%s leads %r != M9" % (p["key"], r10["leads"]))
    r11 = d["R11"]["value"]
    cuts = {}
    for lead in [0] + p["leads"]:
        got = (r11[str(lead)]["fit_cut"], r11[str(lead)]["guard_cut"])
        need(got == expected_cuts(p, lead), "%s lead %d cuts %r break K21 (expected %r)"
             % (p["key"], lead, got, expected_cuts(p, lead)))
        cuts[lead] = got
    return path, cuts, lag


def read_locks(p):
    """P17 re-read: every lead's adoption lock and test-label opening share one recorded second (lock first)."""
    folder = os.path.join(RUN_ROOT, p["run"]).replace("\\", "/")
    locks = sorted(glob.glob(folder + "/adoption*.json.lock.json"))
    need(len(locks) == 1 + len(p["leads"]), "%s expected %d lock files" % (p["key"], 1 + len(p["leads"])))
    out = {}
    for f in locks:
        with open(f, encoding="utf-8") as fh:
            j = json.load(fh)
        lead = j["lead"]
        with open(folder + "/test_labels_opened_lead_%d.json" % lead, encoding="utf-8") as fh:
            o = json.load(fh)
        need(o["opened_at"] == j["locked_at"], "%s lead %d: lock and opening not in one second" % (p["key"], lead))
        need(o["adoption_sha256"] == j["sha256"], "%s lead %d: opened with another adoption hash" % (p["key"], lead))
        out[lead] = dict(epoch=j["locked_at_epoch"], pre=j.get("pre_lock_test_window_reads"), file=f.replace("\\", "/"))
    need(set(out) == set([0] + p["leads"]), "%s lock leads" % p["key"])
    return out


def freeze_epoch(stamp):
    t = dt.datetime.strptime(stamp, "FREEZE_%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
    return t.timestamp()


# ---- style --------------------------------------------------------------------------------------------------
# Window colours, checked with a Python port of the dataviz skill's validate_palette.js (node is not installed;
# Machado 2009 CVD at severity 1, OKLab dE x100, all pairs, white surface): normal >= 28.8, protan/deutan >= 22.9;
# OKLCH L 0.76 / 0.48 / 0.62 so the three windows stay apart in greyscale; ink on orange 5.1:1, white on blue 6.6:1.
FIT, SCORE, TEST = "#86b6ef", "#1c5cab", "#d95926"
INK, INK2, MUTED, GRID, BOXFACE, BOXEDGE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#f4f3ef", "#c3c2b7"
# Greek letters: Arial's italic tau reads as an italic capital T (the glossary's T_k), so math italics come from
# DejaVu Sans (bundled with matplotlib); upright math text and digits stay Arial.
plt.rcParams.update({
    "font.family": "Arial", "font.size": 7, "mathtext.fontset": "custom", "mathtext.rm": "Arial",
    "mathtext.it": "DejaVu Sans:italic", "mathtext.bf": "Arial:bold", "pdf.fonttype": 42, "ps.fonttype": 42,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "xtick.minor.width": 0.4, "xtick.major.size": 2.5,
    "xtick.minor.size": 1.5, "xtick.color": INK2, "xtick.labelcolor": INK, "axes.edgecolor": MUTED,
})
# Cut symbols are set at SYM_PT; mathtext shrinks sub- and superscripts by its module constant SHRINK_FACTOR (0.7 by
# default, i.e. 6.0 pt here). It is raised so that every script is at least 7 pt at print size. Private constant:
# checked loudly so a matplotlib change cannot silently undo it.
SYM_PT, MIN_PT = 8.5, 7.0
need(hasattr(_mathtext, "SHRINK_FACTOR") and abs(_mathtext.SHRINK_FACTOR - 0.7) < 1e-12,
     "matplotlib._mathtext.SHRINK_FACTOR changed (%r); re-check the script-size fix" % getattr(_mathtext,
                                                                                            "SHRINK_FACTOR", None))
_mathtext.SHRINK_FACTOR = 0.824
need(SYM_PT * _mathtext.SHRINK_FACTOR >= MIN_PT, "script size below %.1f pt" % MIN_PT)


def padlock():
    """A padlock as one closed marker path: a U-shaped shackle (a ring with straight legs) over a body."""
    import math
    n = 24
    verts = [(0.28, 0.02), (0.28, 0.22)]
    verts += [(0.28 * math.cos(math.pi * i / n), 0.22 + 0.28 * math.sin(math.pi * i / n)) for i in range(1, n + 1)]
    verts += [(-0.28, 0.02), (-0.16, 0.02), (-0.16, 0.22)]
    verts += [(0.16 * math.cos(math.pi * (n - i) / n), 0.22 + 0.16 * math.sin(math.pi * (n - i) / n))
              for i in range(1, n + 1)]
    verts += [(0.16, 0.02), (0.28, 0.02)]
    codes = [Path.MOVETO] + [Path.LINETO] * (len(verts) - 2) + [Path.CLOSEPOLY]
    body = [(-0.40, -0.50), (0.40, -0.50), (0.40, 0.04), (-0.40, 0.04), (-0.40, -0.50)]
    verts += body
    codes += [Path.MOVETO, Path.LINETO, Path.LINETO, Path.LINETO, Path.CLOSEPOLY]
    return Path(verts, codes)


PADLOCK = padlock()
TAU_IN, TAU = r"$\tau_{\mathrm{in}}$", r"$\tau$"


def main():
    rows = []  # the data CSV

    def rec(problem, element, value, x0, x1, label, src, key, facts):
        rows.append(dict(problem=problem, element=element, value=value,
                         x_start="" if x0 is None else "%.6f" % x0, x_end="" if x1 is None else "%.6f" % x1,
                         label=label, source_file=src, source_key=key, fact_ids=facts))

    runs, locks = {}, {}
    for p in PROBLEMS:
        runs[p["key"]] = read_run(p)
        locks[p["key"]] = read_locks(p)

    # ruling V3: coral's window was made by leaving out the 2020 survey visits (S1 TW3)
    with open(RULINGS, encoding="utf-8") as fh:
        need(V3_TEXT in fh.read(), "ruling V3 text not found in %s" % RULINGS)

    W, H = 175.0, 147.0  # mm
    fig = plt.figure(figsize=(W / 25.4, H / 25.4))
    AX_L, AX_B, AX_W, AX_H = 47.0, 55.0, 125.0, 73.0
    ax = fig.add_axes([AX_L / W, AX_B / H, AX_W / W, AX_H / H])
    ov = fig.add_axes([0, 0, 1, 1], zorder=5)
    ov.set_xlim(0, W)
    ov.set_ylim(0, H)
    ov.axis("off")
    ov.patch.set_alpha(0)
    texts_a, texts_left, box_texts = [], [], []  # for the layout checks after drawing

    X0, X1, YLO, YHI = 1993.0, 2024.6, -0.78, 4.50
    ax.set_xlim(X0, X1)
    ax.set_ylim(YLO, YHI)
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    ax.set_yticks([])
    ax.set_xticks(range(1995, 2021, 5))
    ax.set_xticks(range(1994, 2025), minor=True)
    ax.set_xlabel("Calendar year (ticks at 1 January)", color=INK, labelpad=2)
    for xv in range(1995, 2021, 5):
        ax.axvline(xv, color=GRID, lw=0.5, zorder=0)

    def ymm(y):
        return AX_B + (y - YLO) / (YHI - YLO) * AX_H

    BH = 0.36  # bar height (data units)
    for i, p in enumerate(PROBLEMS):
        y = 4 - i
        path, cuts, lag = runs[p["key"]]
        key = p["key"]
        nm = p["name"]
        segs = [("inner_fit_window", p["inner_fit"], FIT, INK),
                ("inner_score_window", p["inner_score"], SCORE, "white"),
                ("test_window", p["test"], TEST, INK)]
        for el, (a, b), col, tcol in segs:
            ax.add_patch(Rectangle((a, y - BH / 2), b + 1 - a, BH, facecolor=col, edgecolor="none", zorder=2))
            lab = "%d\u2013%s" % (a, str(b)[2:] if str(a)[:2] == str(b)[:2] else b)
            ax.text((a + b + 1) / 2.0, y, lab, ha="center", va="center", color=tcol, fontsize=7, zorder=4)
            rec(nm, el, "%d-%d" % (a, b), a, b + 1.0, lab, path, "R7.value", p["facts_win"])
        if p["lag_first"] is not None and p["lag_first"] < p["y0"]:
            ax.plot([p["lag_first"], p["y0"]], [y, y], color=MUTED, lw=1.0, solid_capstyle="butt", zorder=1)
            rec(nm, "driver_lag_years_before_first_fit_year",
                "lagged driver stores from %d + largest lag %d y = Y0 %d (target record from %d)"
                % (p["lag_first"], lag, p["y0"], p["target_first"]),
                p["lag_first"], float(p["y0"]), "", path,
                "R4.inputs.driver_stores.first_data_year, .target_first_year; R4.inputs.largest_lag_years; R4.value",
                "M7%s; R4, K84" % (", D42" if key == "defo" else ""))
        elif p["lag_first"] is None:
            rec(nm, "driver_lag_years_before_first_fit_year", "none: R4 flag no_lag_sources, Y0 %d" % p["y0"],
                None, None, "", path, "R4.flags; R4.value", "M7; R4, K84; S8.5")
        if key == "coral":  # the 2020 survey visits left out by hand (ruling V3; S1 TW3); no count drawn
            x2020 = p["test"][1] + 1.0
            ax.add_patch(Rectangle((x2020, y - BH / 2), 1.0, BH, facecolor="white", edgecolor=MUTED, lw=0.5,
                                   hatch="//////", zorder=2))
            t = ax.text(x2020 + 0.5, y - BH / 2 - 0.10, "2020 visits left out", ha="center", va="top", fontsize=7,
                        color=INK2, zorder=4)
            texts_a.append(t)
            rec(nm, "survey_visits_left_out", "2020 (count not drawn)", x2020, x2020 + 1.0, "2020 visits left out",
                RULINGS, "V3 row: '%s'" % V3_TEXT, "M6 (iv), M7; S1 TW3")
        # nowcast cuts
        fit0, guard0 = cuts[0]
        xt, lt = step_end_x(fit0, p["cadence"])
        xi, li = step_end_x(guard0, p["cadence"])
        need(abs(xt - p["test"][0]) < 1e-9 and abs(xi - (p["inner_fit"][1] + 1)) < 1e-9,
             "%s nowcast cuts are not at the window edges" % key)
        for xv, lab, el, k2 in ((xi, TAU_IN, "inner_cut_tau_in", "guard_cut"),
                                (xt, TAU, "training_cut_tau", "fit_cut")):
            ax.plot([xv, xv], [y - BH / 2 - 0.07, y + BH / 2 + 0.07], color=INK, lw=0.9, zorder=5,
                    solid_capstyle="butt")
            t = ax.text(xv, y + BH / 2 + 0.09, lab, ha="center", va="bottom", fontsize=SYM_PT, color=INK, zorder=5)
            texts_a.append(t)
            rec(nm, el, "%s %d = %s" % ("day" if p["cadence"] == "day" else "step",
                                         fit0 if k2 == "fit_cut" else guard0, lt if k2 == "fit_cut" else li),
                None, xv, lab, path, "R11.value.0.%s" % k2, "K21, M7")
        # lock marker (P17): right of the training-cut label, over the start of the test window
        ax.plot([xt + 0.70], [y + BH / 2 + 0.21], marker=PADLOCK, ms=7.0, color=INK, ls="none", zorder=6)
        lk = locks[key]
        rec(nm, "lock_marker", "every lead (%s): adoption locked and test labels opened for scoring in one recorded "
            "second (re-read here)" % ", ".join(str(v) for v in sorted(lk)), None, xt, "padlock",
            "; ".join(lk[v]["file"] for v in sorted(lk)) + "; test_labels_opened_lead_*.json",
            "locked_at = opened_at; sha256 = adoption_sha256", "P17, M38, K37")
        pre = lk[0]["pre"]
        need(pre is not None, "%s: nowcast lock has no pre-lock read record" % key)
        if key == "coral":
            need(pre["rows_before_any_lock"] == 0, "coral: pre-lock test-window reads expected 0")
        else:
            need(pre["rows_before_any_lock"] > 0, "%s: pre-lock test-window reads expected > 0" % key)
        rec(nm, "pre_lock_test_window_reads_nowcast", "rows_before_any_lock %d (reads %d)"
            % (pre["rows_before_any_lock"], pre["reads"]), None, None, "caption and panel b note (no number drawn)",
            lk[0]["file"], "pre_lock_test_window_reads", "M10, D54 (a); S7.6")
        # example lead strip
        L = p["lead"]
        fitL, guardL = cuts[L]
        xf, lf = step_end_x(fitL, p["cadence"])
        xg, lg = step_end_x(guardL, p["cadence"])
        ys = y - BH / 2 - 0.19
        if key == "coral":
            ys = y - BH / 2 - 0.19
        # dotted drop line from the inner cut to the strip: the guard rows start after tau_in
        ax.plot([xi, xi], [y - BH / 2 - 0.07, ys], color=INK2, lw=0.6, ls=(0, (1.0, 1.2)), zorder=3)
        ax.plot([xi, xf], [ys, ys], color=INK2, lw=1.6, solid_capstyle="butt", zorder=3)
        ax.plot([xg], [ys], marker="o", ms=4.2, mfc="white", mec=INK, mew=0.8, ls="none", zorder=6)
        ax.plot([xf], [ys], marker="o", ms=4.2, mfc=INK, mec=INK, mew=0.8, ls="none", zorder=6)
        same = (fitL, guardL) == (fit0, guard0)
        lg_lab = r"$\tau^{g}_{%d}$" % L + (r" = $\tau_{\mathrm{in}}$" if same else "")
        lf_lab = r"$\tau_{%d}$" % L + (r" = $\tau$" if same else "")
        texts_a.append(ax.text(xg - 0.32, ys, lg_lab, ha="right", va="center", fontsize=SYM_PT, color=INK, zorder=6))
        texts_a.append(ax.text(xf + 0.32, ys, lf_lab, ha="left", va="center", fontsize=SYM_PT, color=INK, zorder=6))
        unit = {"month": "months", "year": "year", "day": "days"}[p["cadence"]]
        rec(nm, "example_lead", "%d %s (leads %s)" % (L, unit, ", ".join(str(v) for v in p["leads"])), None, None,
            p["lead_text"], path, "R10.value.leads", "M9")
        rec(nm, "fit_cut_tau_L", "lead %d: %s %d = %s" % (L, "day" if p["cadence"] == "day" else "step", fitL, lf),
            None, xf, lf_lab, path, "R11.value.%d.fit_cut" % L, "K21, M47")
        rec(nm, "guard_cut_tau_g_L", "lead %d: %s %d = %s" % (L, "day" if p["cadence"] == "day" else "step",
                                                               guardL, lg),
            None, xg, lg_lab, path, "R11.value.%d.guard_cut" % L, "K21, M19")
        rec(nm, "guard_rows_L", "(tau_in, tau_L] at lead %d" % L, xi, xf, "",
            path + ("; " + TABLE_LADDER + " docstring step 4" if key == "coral" else ""),
            "R11.value.0.guard_cut, R11.value.%d.fit_cut" % L, "K23, M47")
        for Lo in p["leads"]:  # the other lead's cuts: not drawn, checked against K21 (fact K84)
            if Lo == L:
                continue
            fo, go = cuts[Lo]
            rec(nm, "cuts_other_lead_not_drawn", "lead %d: fit cut %s, guard cut %s"
                % (Lo, step_end_x(fo, p["cadence"])[1], step_end_x(go, p["cadence"])[1]), None, None, "",
                path, "R11.value.%d" % Lo, "K21, M9, K84")

        # left column: name (+ example lead), notes, test-exposed phrase
        ym = ymm(y)
        lines = [("NAME", "bold", INK, False, False)]
        lines += [(t, "normal", INK2, False, False) for t in p["extra"]]
        lines += [(t, "normal", INK, j == 0, True) for j, t in enumerate(p["exposed"])]
        top = ym + 1.45 * (len(lines) - 1)
        for j, (t, wt, col, dia, indent) in enumerate(lines):
            yy = top - 2.9 * j
            if t == "NAME":
                tn = ov.text(3.0, yy, p["name"], ha="left", va="center", fontsize=7.5, fontweight="bold", color=INK)
                tl = ov.annotate("   " + p["lead_text"], xy=(1.0, 0.5), xycoords=tn, va="center", ha="left",
                                 fontsize=7, color=INK2)
                texts_left += [tn, tl]
                continue
            texts_left.append(ov.text(5.6 if indent else 3.0, yy, t, ha="left", va="center", fontsize=7,
                                      fontweight=wt, color=col))
            if dia:
                ov.plot([3.8], [yy], marker="D", ms=3.3, color=INK, ls="none")
        rec(nm, "test_exposed_mark", " ".join(p["exposed"]), None, None, "diamond", p["exposed_src"], "",
            "P23, P28; Table 1")

    # ---- run order (caption): each later run was locked after PM2.5's test labels had been opened -------------
    first_open = max(v["epoch"] for v in locks["pm25"].values())
    grid_open = max(v["epoch"] for k in ("pm25", "ndvi", "fire", "defo") for v in locks[k].values())
    for p in PROBLEMS[1:]:
        need(freeze_epoch(p["freeze"]) > first_open, "%s run lock is not after PM2.5's last opening" % p["key"])
    need(freeze_epoch(PROBLEMS[4]["freeze"]) > grid_open, "coral run lock is not after the grids' openings")
    for p in PROBLEMS:
        lk = locks[p["key"]]
        rec(p["name"], "run_lock_and_openings_utc", "run lock %s; adoption locks/openings %s" % (
            p["freeze"], ", ".join("lead %d %s" % (v, dt.datetime.fromtimestamp(lk[v]["epoch"], dt.timezone.utc)
                                                  .strftime("%Y-%m-%dT%H:%M:%SZ")) for v in sorted(lk))),
            None, None, "caption (order only; no date drawn)",
            "M1 stamps; " + "; ".join(lk[v]["file"] for v in sorted(lk)), "locked_at_epoch",
            "M1, P17, K85; Supplement S4 Table S4.4")

    # ---- legend band (above panel a): symbols at SYM_PT, words at 7 pt --------------------------------------
    ov.text(2.0, H - 3.4, "a", fontsize=9, fontweight="bold", va="center", ha="left", color=INK)
    LY = [H - 3.4, H - 7.4, H - 11.4]

    def sym_word(x, yy, sym, word):
        ts = ov.text(x, yy, sym, va="center", ha="left", fontsize=SYM_PT, color=INK)
        tw = ov.annotate(word, xy=(1.0, 0.5), xycoords=ts, xytext=(3.0, 0), textcoords="offset points",
                         va="center", ha="left", fontsize=7, color=INK)
        return [ts, tw]

    legend_texts = []
    c1 = 9.0
    for yy, col, t in zip(LY, (FIT, SCORE, TEST), ("inner fit window", "inner score window", "test window")):
        ov.add_patch(Rectangle((c1, yy - 1.3), 5.0, 2.6, facecolor=col, edgecolor="none"))
        legend_texts.append(ov.text(c1 + 6.5, yy, t, va="center", ha="left", color=INK))
    c2 = 41.0
    ov.plot([c2, c2 + 5.0], [LY[0], LY[0]], color=MUTED, lw=1.0, solid_capstyle="butt")
    legend_texts.append(ov.text(c2 + 6.5, LY[0], "driver-lag years before the first fit year", va="center",
                                color=INK))
    for yy, sym, word in ((LY[1], TAU_IN, "inner cut"), (LY[2], TAU, "training cut")):
        ov.plot([c2 + 2.5, c2 + 2.5], [yy - 1.5, yy + 1.5], color=INK, lw=0.9, solid_capstyle="butt")
        legend_texts += sym_word(c2 + 6.5, yy, sym, word)
    c3 = 92.0
    ov.plot([c3 + 2.5], [LY[0]], marker="o", ms=4.2, mfc="white", mec=INK, mew=0.8)
    legend_texts += sym_word(c3 + 6.5, LY[0], r"$\tau^{g}_{L}$", "guard cut, example lead")
    ov.plot([c3 + 2.5], [LY[1]], marker="o", ms=4.2, mfc=INK, mec=INK, mew=0.8)
    legend_texts += sym_word(c3 + 6.5, LY[1], r"$\tau_{L}$", "fit cut, example lead")
    ov.plot([c3, c3 + 5.0], [LY[2], LY[2]], color=INK2, lw=1.6, solid_capstyle="butt")
    tg = ov.text(c3 + 6.5, LY[2], "guard rows", va="center", ha="left", color=INK)
    tgi = ov.annotate(r"($\tau_{\mathrm{in}}$, $\tau_{L}$]", xy=(1.0, 0.5), xycoords=tg, xytext=(3.0, 0),
                      textcoords="offset points", va="center", ha="left", fontsize=SYM_PT, color=INK)
    legend_texts += [tg, tgi]
    c4 = 137.0
    ov.plot([c4 + 2.5], [LY[0] - 0.4], marker=PADLOCK, ms=7.0, color=INK, ls="none")
    legend_texts.append(ov.text(c4 + 6.0, LY[0] + 1.0, "adoption locked, then test", va="center", color=INK))
    legend_texts.append(ov.text(c4 + 6.0, LY[0] - 1.9, "labels opened for scoring", va="center", color=INK))
    ov.plot([c4 + 2.5], [LY[2] + 0.6], marker="D", ms=3.3, color=INK, ls="none")
    legend_texts.append(ov.text(c4 + 6.0, LY[2] + 2.0, "test-exposed choice", va="center", color=INK))
    legend_texts.append(ov.text(c4 + 6.0, LY[2] - 0.9, "(Table 1)", va="center", color=INK))

    # ---- panel b: order of events within one run (not to scale; no dates) ------------------------------------
    PB_HEAD = AX_B - 14.0
    ov.text(2.0, PB_HEAD, "b", fontsize=9, fontweight="bold", va="center", ha="left", color=INK)
    ov.text(7.0, PB_HEAD, "Order of events in each run (not to scale; no dates; steps as in Box 1, Section 2.6)",
            va="center", ha="left", color=INK2)
    boxes = [
        ("Design work", ["test-exposed", "choices fixed", "(Table 1)"], "D"),
        ("Run locked", ["engine, written rules,", "constants, dataset", "package, inputs, library",
                        "versions and launch", "settings hashed"], None),
        ("Inner round", ["trees fitted at the", "training and inner cuts,", "routers at the inner cut;",
                         "arms searched and", "guarded on the decision", "surface, which holds no",
                         "test-window row"], None),
        ("Nowcast lock\u2020", ["adoption locked, then", "test labels opened for", "scoring in the same",
                                "recorded second; test", "round forecasts from the", "objects fitted at the",
                                "training cut"], "lock"),
        ("Each forecast lead\u2020", ["refit at the fit cut;", "pinned arm fitted at the", "guard cut, checked by",
                                      "the skill guard on the", "guard rows; adoption", "locked, then test labels",
                                      "opened for scoring"], "lock"),
    ]
    box_facts = ["P23, P28; Table 1", "P1, P2, M4; Section 3.2", "K22, K28, M20, M38, M46; Box 1 step 1-2",
                 "P17, K22, K37, M38; Box 1 step 3", "M47, K23, P17, K37; Box 1 step 4"]
    yb1, yb0 = PB_HEAD - 3.5, PB_HEAD - 3.5 - 28.5
    PADX, GAP, ICON = 1.8, 2.4, 4.6
    # measure the text first, then size each box to its widest line
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    mm_per_px = W / fig.bbox.width

    def width_mm(s, **kw):
        t = ov.text(0, 0, s, **kw)
        wmm = t.get_window_extent(rend).width * mm_per_px
        t.remove()
        return wmm

    widths = []
    for title, body, icon in boxes:
        wt = width_mm(title, fontweight="bold") + (ICON if icon else 0.0)
        wb = max(width_mm(b) for b in body)
        widths.append(max(wt, wb) + 2 * PADX + 0.6)
    xb = 4.0
    need(xb + sum(widths) + GAP * (len(boxes) - 1) <= W - 1.5, "panel b runs off the page")
    prev = None
    for k, ((title, body, icon), wd) in enumerate(zip(boxes, widths)):
        ov.add_patch(FancyBboxPatch((xb, yb0), wd, yb1 - yb0, boxstyle="round,pad=0,rounding_size=1.2",
                                    facecolor=BOXFACE, edgecolor=BOXEDGE, lw=0.6))
        box_texts.append((ov.text(xb + PADX, yb1 - 3.0, title, fontweight="bold", va="center", ha="left",
                                  color=INK), xb, xb + wd))
        for j, t in enumerate(body):
            box_texts.append((ov.text(xb + PADX, yb1 - 7.0 - 3.0 * j, t, va="center", ha="left", color=INK),
                              xb, xb + wd))
        if icon == "D":
            ov.plot([xb + wd - 2.6], [yb1 - 3.0], marker="D", ms=3.3, color=INK, ls="none")
        elif icon == "lock":
            ov.plot([xb + wd - 2.6], [yb1 - 3.2], marker=PADLOCK, ms=7.0, color=INK, ls="none")
        if prev is not None:
            ov.add_patch(FancyArrowPatch((prev + 0.2, (yb0 + yb1) / 2), (xb - 0.2, (yb0 + yb1) / 2),
                                         arrowstyle="-|>", mutation_scale=7, lw=0.7, color=INK))
        rec("all", "event_order_box_%d" % (k + 1), title + ": " + " ".join(body), None, None, "", "schematic", "",
            box_facts[k])
        prev = xb + wd
        xb += wd + GAP
    note = ("\u2020 On the gridded problems, test-window labels enter before a lock only as own-history features and "
            "persistence inputs,\n   each as known at its row's issue step.")
    tnote = ov.text(4.0, yb0 - 1.2, note, va="top", ha="left", color=INK2, linespacing=1.25)
    rec("all", "panel_b_note", note, None, None, "", "adoption.json.lock.json pre_lock_test_window_reads (rows above)",
        "", "M10, D54 (a), M38, P17; S7.6")

    # ---- layout checks (fail loud) ----------------------------------------------------------------------------
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()

    def ext(t):
        e = t.get_window_extent(rend)
        return e.x0 * mm_per_px, e.x1 * mm_per_px, e.y0 * mm_per_px, e.y1 * mm_per_px

    for t, x0b, x1b in box_texts:
        a0, a1, _, _ = ext(t)
        need(a0 >= x0b and a1 <= x1b - 0.8 + (4.6 if t.get_fontweight() == "bold" else 0.0),
             "panel b text %r overflows its box" % t.get_text())
    for t in texts_left:
        need(ext(t)[1] <= AX_L + 2.0, "left-column text %r runs into the plot" % t.get_text())
    for t in legend_texts + [tnote]:
        need(ext(t)[1] <= W - 0.5, "text %r runs off the page" % t.get_text())
    boxes_a = [ext(t) for t in texts_a]
    for i1 in range(len(boxes_a)):
        for i2 in range(i1 + 1, len(boxes_a)):
            a, b = boxes_a[i1], boxes_a[i2]
            overlap = min(a[1], b[1]) - max(a[0], b[0]) > 0.2 and min(a[3], b[3]) - max(a[2], b[2]) > 0.2
            need(not overlap, "panel a labels overlap: %r and %r" % (texts_a[i1].get_text(), texts_a[i2].get_text()))

    fig.savefig(os.path.join(OUT, "fig2.pdf"))
    fig.savefig(os.path.join(OUT, "fig2.png"), dpi=300)
    with open(os.path.join(OUT, "fig2_data.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["problem", "element", "value", "x_start", "x_end", "label",
                                           "source_file", "source_key", "fact_ids"])
        w.writeheader()
        w.writerows(rows)
    print("wrote fig2.pdf, fig2.png, fig2_data.csv (%d rows); script size %.2f pt"
          % (len(rows), SYM_PT * _mathtext.SHRINK_FACTOR))


if __name__ == "__main__":
    main()
