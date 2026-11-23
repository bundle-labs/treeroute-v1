"""Figure 4: nowcast contrast per region (forest plot), five problems. Round 4 (2026-11-11): figures renumbered by first citation: map (unnumbered) -> 1, 1 -> 2, 2 -> 3, 3 -> 4, 4 -> 5 (folders keep their names; paper/figures/FIGURE_NUMBERS.md).

Brief: paper/draft/tables/fig_3_spec.md (drafted 2026-10-26).
Revised 2026-10-27 after two independent checks; decision log:
paper/draft/review_logs/figsupp_fig3_log.md. Copies: the builder's version is in
paper/draft/_snapshots/20261027T1500Z_figsupp/fig3_pre_revise_attempt1/; the
version this revision started from is in
paper/draft/_snapshots/20261027T1500Z_figsupp/fig3/.
Facts checked against paper/PAPER_FACTS.md: R5 (mean contrast, interval, regions
better; coral pooled contrast 1.597), R16 (regions worse), K63 (burned fraction: 4
regions at exactly 0), P14 (verdict rule), P15 (equivalence bands), P16 (jackknife
over regions, z = 1.96; equal-weight estimand vs pooled MAE difference).
Not in PAPER_FACTS, recomputed here and asserted (the caption states them, with
this source): burned fraction has 7 regions whose test labels are all 0
(mae_predict_zero == 0); 4 of them are the ties (both MAEs 0, both forecasts 0)
and the other 3 have contrast > 0 (drawn as better).

Sources (read only; absolute paths):
  per-region contrasts  D:/treeroute/runs/_headline_tables/<pkg>/per_group_*.csv
                        rows: lead == 0 and rows == "all"; columns group,
                        contrast, mae_reference, mae_adopted, mae_predict_zero,
                        n_adopted, n_reference
  mean, interval, band, D:/treeroute/runs/_headline_tables/<pkg>/verdicts_*.csv
  pooled difference     row: lead == 0 and rows == "all" (source verdict.json);
                        columns contrast_mean, contrast_se, contrast_low,
                        contrast_high, band, n_groups, groups_better, tag,
                        sign_flip_groups, pooled_contrast

Outputs (next to this script): fig3.pdf (vector), fig3.png (300 dpi),
fig3_data.csv (every plotted value with its source).

Every check below fails loudly (AssertionError) instead of drawing a figure
that disagrees with the fact sheet. No randomness anywhere.
"""
import sys

sys.dont_write_bytecode = True

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import (FixedLocator, FuncFormatter, MultipleLocator,  # noqa: E402
                               NullLocator)
from matplotlib.transforms import ScaledTranslation, blended_transform_factory  # noqa: E402

HT = Path("D:/treeroute/runs/_headline_tables")
OUT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Panels, in the brief's order (by router type). Check values are fact-sheet
# values: counts R5/R16/K63, band P15, mean and interval R5 (as printed there),
# coral pooled contrast R5/P16.
# scale: tick values are contrast / scale (the axis label names the unit).
# ticks: labelled ticks, with at least one negative tick where a region is worse.
# check_zero_label: (regions whose test labels are all 0, i.e. mae_predict_zero
#   == 0; of those, tied with both MAEs 0; of those, better). Recomputed values,
#   not fact-sheet values; the caption's burned-fraction "four ... three further"
#   relies on them. (Coral's one such region has a single test visit and is worse.)
# ---------------------------------------------------------------------------
PANELS = [
    dict(key="pm25", title="PM2.5", router="Per-location router",
         per_group=HT / "per_group_4cabd2107446.csv",
         verdicts=HT / "verdicts_9abcea419ce2.csv",
         scale=1.0, unit=r"µg m$^{-3}$",
         ticks=[-1, 0, 1, 2, 3], minor=None,
         check_counts=(127, 108, 19, 0), check_band=0.0462,
         check_r5=(0.2651, 0.1774, 0.3527), check_pooled=None,
         check_zero_label=(0, 0, 0),
         size_by_rows=False),
    dict(key="ndvi", title="NDVI", router="Per-location router",
         per_group=HT / "ndvi" / "per_group_6385d3cbe10e.csv",
         verdicts=HT / "ndvi" / "verdicts_c4cd7e7c2610.csv",
         scale=1e-3, unit=r"NDVI, in units of 10$^{-3}$",
         ticks=[-5, 0, 10, 20, 30], minor=5,
         check_counts=(133, 122, 11, 0), check_band=0.000597,
         check_r5=(0.007918, 0.00675, 0.009086), check_pooled=None,
         check_zero_label=(0, 0, 0),
         size_by_rows=False),
    dict(key="fire", title="Burned fraction", router="Per-location router",
         per_group=HT / "fire" / "per_group_7d85ccc4a6f0.csv",
         verdicts=HT / "fire" / "verdicts_7ee7167afe8d.csv",
         scale=1e-4, unit=r"Fraction, in units of 10$^{-4}$",
         ticks=[-1, 0, 2, 4, 6, 8], minor=1,
         check_counts=(40, 23, 13, 4), check_band=1.36e-5,
         check_r5=(4.23e-05, 1.46e-07, 8.45e-05), check_pooled=None,
         check_zero_label=(7, 4, 3),
         size_by_rows=False),
    dict(key="defo", title="Forest loss", router="Region router",
         per_group=HT / "defo" / "per_group_f3b9e681f897.csv",
         verdicts=HT / "defo" / "verdicts_bf99c6741bce.csv",
         scale=1e-3, unit=r"Fraction, in units of 10$^{-3}$",
         ticks=[0, 1, 2, 3, 4], minor=None,
         check_counts=(42, 42, 0, 0), check_band=1.10e-4,
         check_r5=(0.000299, 8.7e-05, 5.1e-04), check_pooled=None,
         check_zero_label=(0, 0, 0),
         size_by_rows=False),
    dict(key="coral", title="Coral bleaching", router="Neighbour router",
         per_group=HT / "coral" / "per_group_1e2505d594fc.csv",
         verdicts=HT / "coral" / "verdicts_a9d948cbf26b.csv",
         scale=1.0, unit="Percentage points",
         ticks=[-5, 0, 10, 20, 30], minor=5,
         check_counts=(37, 23, 14, 0), check_band=0.918,
         check_r5=(5.21, 1.97, 8.44), check_pooled=1.597,
         check_zero_label=(1, 0, 0),
         size_by_rows=True),  # marker area = test survey visits (n_adopted)
]

Z = 1.96  # P16: jackknife over regions at z = 1.96
TIE = "tie (both MAEs 0)"


def sig_round(x, sig):
    """Round to `sig` significant figures (for matching fact-sheet prints)."""
    if x == 0:
        return 0.0
    return float(f"{x:.{sig}g}")


def matches_print(value, printed):
    """True if `value` rounds to the fact sheet's printed number."""
    s = f"{printed:.6e}".split("e")[0].rstrip("0").rstrip(".")
    sig = max(1, len(s.replace("-", "").replace(".", "").lstrip("0")))
    return np.isclose(sig_round(value, sig), printed, rtol=1e-9, atol=0)


def load_panel(p):
    pg = pd.read_csv(p["per_group"], usecols=[
        "package", "run", "lead", "rows", "group", "scored_units",
        "contrast", "mae_reference", "mae_adopted", "mae_predict_zero",
        "n_adopted", "n_reference"])
    sel = pg[(pg["lead"] == 0) & (pg["rows"] == "all")].copy()
    assert sel["run"].nunique() == 1, f"{p['key']}: more than one run"
    assert not sel["group"].duplicated().any(), f"{p['key']}: duplicate regions"
    c = sel["contrast"].to_numpy(float)
    recomputed = (sel["mae_reference"] - sel["mae_adopted"]).to_numpy(float)
    assert np.allclose(c, recomputed, rtol=0, atol=1e-12 * max(1.0, np.abs(c).max())), \
        f"{p['key']}: contrast != mae_reference - mae_adopted"
    assert (sel["n_adopted"] == sel["n_reference"]).all(), f"{p['key']}: row counts differ"

    G, n_better, n_worse, n_zero = p["check_counts"]
    got = (len(sel), int((c > 0).sum()), int((c < 0).sum()), int((c == 0).sum()))
    assert got == (G, n_better, n_worse, n_zero), \
        f"{p['key']}: counts {got} != fact sheet {p['check_counts']} (R5, R16, K63)"
    # A contrast of exactly 0 is drawn as a tie with both MAEs 0: check that both
    # MAEs and predict-zero's MAE are 0 there (all test labels and both forecasts 0).
    z = sel[sel["contrast"] == 0]
    assert ((z["mae_reference"] == 0) & (z["mae_adopted"] == 0)
            & (z["mae_predict_zero"] == 0)).all(), f"{p['key']}: a tie with nonzero MAE"
    # Reverse direction: regions whose test labels are all 0 (mae_predict_zero == 0)
    # are not all ties; count them, the ties among them and the better ones.
    zl = (sel["mae_predict_zero"] == 0).to_numpy()
    got_zl = (int(zl.sum()), int((zl & (c == 0)).sum()), int((zl & (c > 0)).sum()))
    assert got_zl == p["check_zero_label"], \
        f"{p['key']}: all-zero-label regions / tied / better {got_zl} != {p['check_zero_label']}"
    sel["all_test_labels_zero"] = zl

    vd = pd.read_csv(p["verdicts"])
    vrow = vd[(vd["lead"] == 0) & (vd["rows"] == "all")]
    assert len(vrow) == 1, f"{p['key']}: expected one lead-0 'all' verdict row"
    v = vrow.iloc[0]
    assert v["source"] == "verdict.json" and v["tag"] == "helps", f"{p['key']}: verdict row"
    assert int(v["n_groups"]) == G and int(v["groups_better"]) == n_better
    # Worse regions == the verdict file's sign_flip_groups, exactly (the field is
    # the sorted names joined by single spaces; names may contain spaces/commas).
    worse = sorted(sel.loc[sel["contrast"] < 0, "group"])
    if worse:
        assert " ".join(worse) == str(v["sign_flip_groups"]), f"{p['key']}: sign_flip_groups"
    else:
        assert pd.isna(v["sign_flip_groups"]), f"{p['key']}: sign_flip_groups not empty"

    # Recompute the locked mean and its jackknife-over-regions SE (P16).
    mean = c.mean()
    loo = (c.sum() - c) / (G - 1)
    se = np.sqrt((G - 1) / G * np.sum((loo - loo.mean()) ** 2))
    assert np.isclose(mean, v["contrast_mean"], rtol=1e-9, atol=0), f"{p['key']}: mean"
    assert np.isclose(se, v["contrast_se"], rtol=1e-9, atol=0), f"{p['key']}: se"
    assert np.isclose(v["contrast_low"], v["contrast_mean"] - Z * v["contrast_se"], rtol=1e-9)
    assert np.isclose(v["contrast_high"], v["contrast_mean"] + Z * v["contrast_se"], rtol=1e-9)

    # Pooled MAE difference = the test-row-weighted mean of the region contrasts.
    n = sel["n_adopted"].to_numpy(float)
    wmean = float((c * n).sum() / n.sum())
    assert np.isclose(wmean, v["pooled_contrast"], rtol=1e-9, atol=0), f"{p['key']}: pooled"
    if p["check_pooled"] is not None:
        assert matches_print(v["pooled_contrast"], p["check_pooled"]), f"{p['key']}: R5 pooled"

    # Against the fact sheet's prints (R5 mean and interval; P15 band).
    for val, printed, name in zip(
            (v["contrast_mean"], v["contrast_low"], v["contrast_high"]),
            p["check_r5"], ("mean", "low", "high")):
        assert matches_print(val, printed), f"{p['key']}: R5 {name} {val} vs {printed}"
    assert matches_print(v["band"], p["check_band"]), f"{p['key']}: P15 band {v['band']}"
    # P14: HELPS = interval low > 0 and mean >= band (what the caption says).
    assert v["contrast_low"] > 0 and v["contrast_mean"] >= v["band"], f"{p['key']}: P14"

    # Sort: most negative at the bottom (y = 1), largest at the top (y = G).
    sel = sel.sort_values(["contrast", "group"], kind="mergesort").reset_index(drop=True)
    sel["y"] = np.arange(1, G + 1)
    sel["sign_class"] = np.where(sel["contrast"] > 0, "better",
                                 np.where(sel["contrast"] < 0, "worse", TIE))
    return sel, v, dict(mean=mean, se=se, wmean=wmean)


# ---------------------------------------------------------------------------
# Style: static print figure (Nature/AGU-like double column, 175 mm).
# Palette: dataviz reference slots 1 (blue) and 8 (red), validated as a pair
# with validate_palette.js (light): CVD dE 21.6, normal-vision dE 32.3, PASS.
# Sign is also carried by fill (filled / open), so it survives greyscale; the
# four tied regions (both MAEs 0) have their own shape (grey square).
# ---------------------------------------------------------------------------
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e1e0d9"       # as Figure 5
BAND = "#b9b7b0"       # ~70% grey, summary row only, with edge lines at +-b
BLUE = "#2a78d6"       # final answer better
RED = "#e34948"        # final answer worse (open)
ZERO_FACE = "#b5b3ac"  # tie: both MAEs 0 (grey square)

plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 7,
    "mathtext.fontset": "custom",
    "mathtext.rm": "Arial",
    "mathtext.it": "Arial:italic",
    "mathtext.bf": "Arial:bold",
    "axes.linewidth": 0.5,
    "axes.edgecolor": INK2,
    "xtick.major.width": 0.5,
    "xtick.major.size": 2.0,
    "xtick.minor.width": 0.4,
    "xtick.minor.size": 1.2,
    "xtick.color": INK2,
    "xtick.labelcolor": INK,
    "xtick.labelsize": 7,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
    "axes.unicode_minus": True,
})

MM = 1 / 25.4
FIG_W, FIG_H = 175.0, 141.0  # mm
LEFT, RIGHT = 7.0, 2.0
GAP_IN, GAP_OUT = 3.5, 7.5   # within a router group / between groups
PANEL_W = (FIG_W - LEFT - RIGHT - 2 * GAP_IN - 2 * GAP_OUT) / 5
SUM_BOTTOM, SUM_H, SUM_GAP = 24.0, 10.0, 1.2   # mm from the bottom edge
MAIN_H = 92.0
MAIN_TOP = SUM_BOTTOM + SUM_H + SUM_GAP + MAIN_H
MS = 2.5        # marker diameter, pt (uniform panels)
GAPS_AFTER = [GAP_IN, GAP_IN, GAP_OUT, GAP_OUT]
# Summary row: the mean is a tall, narrow diamond (height MEAN_MS pt, width 0.35
# of that, ~0.56 mm) so that the 95% bar shows on both sides of it even where the
# whole interval is ~1 mm at print size (PM2.5). Caps are thinner and shorter
# than the diamond. CAP_H is the cap half-height in summary-row y units
# (2 units = SUM_H mm).
MEAN_MARKER = [(0, 1), (0.35, 0), (0, -1), (-0.35, 0), (0, 1)]
MEAN_MS = 4.6
CAP_H = 0.11
TICK_LEN, TICK_PAD = 2.0, 1.5   # pt; summary-row x ticks

# Coral: marker AREA proportional to test survey visits (diameter ~ sqrt(n)),
# with a floor so that the smallest regions stay visible and open/filled stays
# readable; regions with SIZE_FLOOR_N visits or fewer share the floor size.
SIZE_K = 0.40                  # pt per sqrt(visit)
SIZE_MIN = 1.8                 # pt
SIZE_FLOOR_N = int((SIZE_MIN / SIZE_K) ** 2)   # = 20
SIZE_KEY = [SIZE_FLOOR_N, 100, 400]


def diameter(n):
    return max(SIZE_MIN, SIZE_K * np.sqrt(n))


def fx(mm):
    return mm / FIG_W


def fy(mm):
    return mm / FIG_H


def half_minus_pt(fig):
    """Half the width of the minus sign at 7 pt, measured with the renderer.

    Negative tick labels are shifted left by this much, so that their digits,
    not the minus-and-digit pair, are centred on the tick (hanging minus). This
    keeps "-1" / "-5" clear of the "0" label next to it.
    """
    r = fig.canvas.get_renderer()
    w = []
    for s in ("−5", "5"):
        t = fig.text(0, 0, s, fontsize=7)
        w.append(t.get_window_extent(r).width * 72 / fig.dpi)
        t.remove()
    return (w[0] - w[1]) / 2


def main():
    fig = plt.figure(figsize=(FIG_W * MM, FIG_H * MM))
    hm = half_minus_pt(fig)
    rows = []
    x_left = LEFT
    panel_x = []
    for i, p in enumerate(PANELS):
        panel_x.append(x_left)
        x_left += PANEL_W + (GAPS_AFTER[i] if i < 4 else 0)

    main_bottom = MAIN_TOP - MAIN_H
    sum_bottom = SUM_BOTTOM

    for i, p in enumerate(PANELS):
        sel, v, rec = load_panel(p)
        s = p["scale"]
        G = len(sel)
        x = sel["contrast"].to_numpy(float) / s
        b = float(v["band"]) / s
        m, lo, hi = (float(v["contrast_mean"]) / s, float(v["contrast_low"]) / s,
                     float(v["contrast_high"]) / s)
        pooled = float(v["pooled_contrast"]) / s

        xmin = min(x.min(), -b, lo, pooled, 0.0)
        xmax = max(x.max(), b, hi, pooled, 0.0)
        pad = 0.07 * (xmax - xmin)
        xlim = (xmin - pad, xmax + pad)
        assert all(xlim[0] < t < xlim[1] for t in p["ticks"]), f"{p['key']}: tick outside"
        if (x < 0).any():
            assert any(t < 0 for t in p["ticks"]), f"{p['key']}: no negative tick"

        ax = fig.add_axes([fx(panel_x[i]), fy(main_bottom), fx(PANEL_W), fy(MAIN_H)])
        axs = fig.add_axes([fx(panel_x[i]), fy(sum_bottom), fx(PANEL_W), fy(SUM_H)],
                           sharex=ax)

        # Band (+-b) only in the summary row, where the verdict uses it (P14).
        axs.axvspan(-b, b, color=BAND, lw=0, zorder=0)
        for e in (-b, b):
            axs.axvline(e, color=INK2, lw=0.4, zorder=0.8)
        for a in (ax, axs):
            a.axvline(0, color=INK2, lw=0.6, zorder=1)
            for side in ("top", "right", "left"):
                a.spines[side].set_visible(False)
            a.set_yticks([])
            a.set_facecolor("white")
        ax.spines["bottom"].set_visible(False)
        ax.set_xlim(*xlim)
        ax.xaxis.set_major_locator(FixedLocator(p["ticks"]))
        ax.xaxis.set_minor_locator(MultipleLocator(p["minor"]) if p["minor"] else NullLocator())
        ax.tick_params(axis="x", which="both", length=0, labelbottom=False)
        axs.tick_params(axis="x", which="major", length=TICK_LEN, pad=TICK_PAD)
        axs.tick_params(axis="x", which="minor", length=1.2)
        # Non-negative tick labels by the formatter; negative ones drawn by hand at
        # the same height, with a hanging minus (digits centred on the tick).
        axs.xaxis.set_major_formatter(FuncFormatter(lambda t, pos: "" if t < 0 else f"{t:g}"))
        tr_neg = (blended_transform_factory(axs.transData, axs.transAxes)
                  + ScaledTranslation(-hm / 72, -(TICK_LEN + TICK_PAD) / 72,
                                      fig.dpi_scale_trans))
        for t in p["ticks"]:
            if t < 0:
                axs.text(t, 0, "−" + f"{-t:g}", transform=tr_neg, ha="center",
                         va="top", fontsize=7, color=INK, clip_on=False)
        for t in p["ticks"]:
            if t != 0:
                for a in (ax, axs):
                    a.axvline(t, color=GRID, lw=0.4, zorder=0.5)
        ax.set_ylim(0.0, G + 1.0)

        better = (sel["sign_class"] == "better").to_numpy()
        worse = (sel["sign_class"] == "worse").to_numpy()
        zero = (sel["sign_class"] == TIE).to_numpy()
        y = sel["y"].to_numpy()
        nvis = sel["n_adopted"].to_numpy(float)
        if p["size_by_rows"]:
            d = np.array([diameter(n) for n in nvis])
        else:
            d = np.full(G, MS)
        sel["marker_diameter_pt"] = d

        def dots(mask, **kw):
            idx = np.where(mask)[0]
            idx = idx[np.argsort(-d[idx], kind="mergesort")]  # big first, small on top
            if len(idx):
                ax.scatter(x[idx], y[idx], s=d[idx] ** 2, zorder=3, **kw)

        dots(better, marker="o", facecolors=BLUE, edgecolors="white", linewidths=0.3)
        dots(worse, marker="o", facecolors="white", edgecolors=RED, linewidths=0.6)
        if zero.any():
            ax.scatter(x[zero], y[zero], s=2.3 ** 2, marker="s", facecolors=ZERO_FACE,
                       edgecolors=INK2, linewidths=0.4, zorder=3)

        # Counts, direct-labelled in the empty lower-right corner.
        lines = [f"{G} regions", f"{int(better.sum())} better", f"{int(worse.sum())} worse"]
        if zero.any():
            lines.append(f"{int(zero.sum())} tied")
        ax.text(0.97, 0.02, "\n".join(lines), transform=ax.transAxes, ha="right",
                va="bottom", fontsize=7, color=INK, linespacing=1.25)

        # Coral: size key, in the empty right half above the counts.
        if p["size_by_rows"]:
            ax.text(0.40, 0.575, "Test survey\nvisits", transform=ax.transAxes, ha="left",
                    va="bottom", fontsize=7, color=INK, linespacing=1.1)
            for k, (nk, yk) in enumerate(zip(SIZE_KEY, (0.53, 0.47, 0.395))):
                ax.scatter([0.47], [yk], s=diameter(nk) ** 2, marker="o", facecolors="none",
                           edgecolors=INK2, linewidths=0.5, transform=ax.transAxes,
                           clip_on=False, zorder=3)
                lab = f"\u2264{nk}" if k == 0 else f"{nk}"
                ax.text(0.58, yk, lab, transform=ax.transAxes, ha="left", va="center",
                        fontsize=7, color=INK)

        # Summary row: diamond = mean, bar = 95% jackknife interval (R5, P16);
        # open triangle = pooled MAE difference (not the verdict; P16).
        axs.set_ylim(-1.0, 1.0)
        y_d, y_p = 0.42, -0.45
        axs.plot([lo, hi], [y_d, y_d], color=INK, lw=1.0, solid_capstyle="butt", zorder=3)
        for e in (lo, hi):
            axs.plot([e, e], [y_d - CAP_H, y_d + CAP_H], color=INK, lw=0.5,
                     solid_capstyle="butt", zorder=3)
        axs.plot([m], [y_d], ls="none", marker=MEAN_MARKER, ms=MEAN_MS, mfc=INK, mec=INK,
                 mew=0, zorder=4)
        axs.plot([pooled], [y_p], ls="none", marker="^", ms=3.4, mfc="white", mec=INK,
                 mew=0.6, zorder=4)
        axs.spines["bottom"].set_color(INK2)
        axs.set_xlabel(p["unit"], fontsize=7, color=INK, labelpad=1.5)

        ax.set_title(p["title"], fontsize=7.5, color=INK, pad=3, loc="left")
        if i == 0:
            ax.set_ylabel("Regions, sorted by contrast", fontsize=7, color=INK, labelpad=2)

        # ---- data rows: every plotted value with its source ----
        src_pg = str(p["per_group"]).replace("\\", "/")
        src_v = str(p["verdicts"]).replace("\\", "/")
        for _, r in sel.iterrows():
            rows.append(dict(
                panel=i + 1, problem=p["title"], router_type=p["router"], mark="region point",
                region=r["group"], y_position=int(r["y"]), sign_class=r["sign_class"],
                value=r["contrast"], plotted_x=r["contrast"] / s, axis_scale=s,
                mae_reference=r["mae_reference"], mae_adopted=r["mae_adopted"],
                mae_predict_zero=r["mae_predict_zero"],
                all_test_labels_zero=bool(r["all_test_labels_zero"]),
                test_rows=int(r["n_adopted"]), marker_diameter_pt=r["marker_diameter_pt"],
                source_file=src_pg, source_filter="lead == 0 and rows == 'all'",
                source_column=("contrast (= mae_reference - mae_adopted, checked); "
                               "test_rows = n_adopted; all_test_labels_zero = "
                               "(mae_predict_zero == 0)"
                               + ("; marker area proportional to n_adopted (survey visits),"
                                  f" floor {SIZE_MIN} pt at <= {SIZE_FLOOR_N}"
                                  if p["size_by_rows"] else "")),
                fact_ids="R5; R16; K63"))
        for mark, val, col, facts in (
                ("band upper edge (+b), summary row", float(v["band"]), "band", "P15"),
                ("band lower edge (-b), summary row", -float(v["band"]), "band (negated)", "P15"),
                ("mean contrast (diamond)", float(v["contrast_mean"]), "contrast_mean", "R5; P16"),
                ("interval low (bar)", float(v["contrast_low"]), "contrast_low", "R5; P16"),
                ("interval high (bar)", float(v["contrast_high"]), "contrast_high", "R5; P16"),
                ("pooled MAE difference (open triangle; not the verdict)",
                 float(v["pooled_contrast"]), "pooled_contrast (= n_adopted-weighted mean of "
                 "contrast, checked)", "R5; P16" if p["check_pooled"] else "P16"),
                ("jackknife SE (not drawn; check)", float(v["contrast_se"]), "contrast_se", "P16")):
            rows.append(dict(
                panel=i + 1, problem=p["title"], router_type=p["router"], mark=mark,
                region="", y_position="", sign_class="", value=val,
                plotted_x=val / s if "SE" not in mark else "", axis_scale=s,
                mae_reference="", mae_adopted="", mae_predict_zero="",
                all_test_labels_zero="", test_rows="", marker_diameter_pt="",
                source_file=src_v, source_filter="lead == 0 and rows == 'all' (source verdict.json)",
                source_column=col, fact_ids=facts))
        rows.append(dict(
            panel=i + 1, problem=p["title"], router_type=p["router"],
            mark="recomputed mean / jackknife SE / row-weighted mean from per-region rows "
                 "(check, not drawn)",
            region="", y_position="", sign_class="",
            value=(f"{float(rec['mean']):.12g} / {float(rec['se']):.12g} / "
                   f"{float(rec['wmean']):.12g}"),
            plotted_x="", axis_scale=s, mae_reference="", mae_adopted="",
            mae_predict_zero="", all_test_labels_zero="", test_rows="",
            marker_diameter_pt="",
            source_file=src_pg, source_filter="lead == 0 and rows == 'all'",
            source_column=("contrast, n_adopted; jackknife over regions (one region dropped at "
                           "a time); each equals the verdicts file"),
            fact_ids="P16"))
        n_zl = int(sel["all_test_labels_zero"].sum())
        n_zl_tie = int((sel["all_test_labels_zero"] & (sel["contrast"] == 0)).sum())
        n_zl_better = int((sel["all_test_labels_zero"] & (sel["contrast"] > 0)).sum())
        rows.append(dict(
            panel=i + 1, problem=p["title"], router_type=p["router"],
            mark=("regions with all test labels 0: total / tied (both MAEs 0; grey squares) / "
                  "better (drawn as better points) (check, not drawn)"),
            region="", y_position="", sign_class="",
            value=f"{n_zl} / {n_zl_tie} / {n_zl_better}",
            plotted_x="", axis_scale=s, mae_reference="", mae_adopted="",
            mae_predict_zero="", all_test_labels_zero="", test_rows="",
            marker_diameter_pt="",
            source_file=src_pg, source_filter="lead == 0 and rows == 'all'",
            source_column="mae_predict_zero == 0; contrast",
            fact_ids="K63 (tied count only); the rest recomputed, not in PAPER_FACTS"))
        if p["size_by_rows"]:
            for nk in SIZE_KEY:
                rows.append(dict(
                    panel=i + 1, problem=p["title"], router_type=p["router"],
                    mark="size key (test survey visits)", region="", y_position="",
                    sign_class="", value=nk, plotted_x="", axis_scale=s, mae_reference="",
                    mae_adopted="", mae_predict_zero="", all_test_labels_zero="",
                    test_rows=nk, marker_diameter_pt=diameter(nk),
                    source_file="", source_filter="",
                    source_column="key level (not data); diameter = max(1.8, 0.40*sqrt(n)) pt",
                    fact_ids=""))

    # Router-type header with a rule over each group of panels.
    head_y = MAIN_TOP + 9.0
    groups = [("Per-location router", 0, 2), ("Region router", 3, 3), ("Neighbour router", 4, 4)]
    for name, a, z in groups:
        x0 = panel_x[a]
        x1 = panel_x[z] + PANEL_W
        fig.add_artist(Line2D([fx(x0), fx(x1)], [fy(head_y - 1.6)] * 2, color=INK2, lw=0.5))
        fig.text(fx((x0 + x1) / 2), fy(head_y), name, ha="center", va="bottom",
                 fontsize=7.5, color=INK2)

    # Shared x description and legend.
    fig.text(fx(LEFT + (FIG_W - LEFT - RIGHT) / 2), fy(sum_bottom - 10.0),
             "Contrast per region: MAE(reference) \u2212 MAE(final answer), in each panel's "
             "target units; positive values favour the final answer",
             ha="center", va="top", fontsize=7.5, color=INK)

    points = [
        Line2D([], [], ls="none", marker="o", ms=MS + 0.6, mfc=BLUE, mec="white", mew=0.3,
               label="Final answer better"),
        Line2D([], [], ls="none", marker="o", ms=MS + 0.6, mfc="white", mec=RED, mew=0.6,
               label="Final answer worse"),
        Line2D([], [], ls="none", marker="s", ms=2.3 + 0.5, mfc=ZERO_FACE, mec=INK2, mew=0.4,
               label="Tie: both MAEs 0 (no burned area, both forecasts 0)"),
    ]
    summary = [
        Patch(facecolor=BAND, edgecolor=INK2, lw=0.4, label="Equivalence band (\u00b1b)"),
        Line2D([], [], color=INK, lw=1.0, marker=MEAN_MARKER, ms=MEAN_MS, mfc=INK, mec=INK,
               mew=0, label="Mean over regions, 95% jackknife interval"),
        Line2D([], [], ls="none", marker="^", ms=3.4, mfc="white", mec=INK, mew=0.6,
               label="Pooled MAE difference (not the verdict)"),
    ]
    for hs, yb in ((points, 4.6), (summary, 0.8)):
        fig.legend(handles=hs, loc="lower center", ncol=len(hs), frameon=False, fontsize=7,
                   bbox_to_anchor=(fx(LEFT + (FIG_W - LEFT - RIGHT) / 2), fy(yb)),
                   handlelength=1.8, handletextpad=0.5, columnspacing=2.0,
                   borderaxespad=0, borderpad=0)

    fig.savefig(OUT / "fig3.pdf")
    fig.savefig(OUT / "fig3.png", dpi=300)
    plt.close(fig)

    data = pd.DataFrame(rows)
    data.insert(0, "figure", "Figure 4")  # relabelled from "Figure 3" on 2026-11-11 (round 5); the figure is Figure 4 (FIGURE_NUMBERS.md)
    data.to_csv(OUT / "fig3_data.csv", index=False, float_format="%.10g")
    print(f"wrote {OUT / 'fig3.pdf'}, fig3.png, fig3_data.csv ({len(data)} rows)")


if __name__ == "__main__":
    main()
