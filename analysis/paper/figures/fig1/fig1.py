"""Figure 2: architecture schematic of treeroute v1 (a diagram, not a data plot). Round 4 (2026-11-11): figures renumbered by first citation: map (unnumbered) -> 1, 1 -> 2, 2 -> 3, 3 -> 4, 4 -> 5 (folders keep their names; paper/figures/FIGURE_NUMBERS.md).

Brief: paper/draft/fig1_spec.md; text: paper/draft/02_method.md Section 2; outline Fig. 1 row
(facts M4, M11-M47, M59); terms: paper/draft/GLOSSARY.md. Revised 2026-10-27 after two independent
checks (decision log: paper/draft/review_logs/figsupp_fig1_log.md; the pre-revision script is in
paper/draft/_snapshots/20261027T1500Z_figsupp/fig1/).

The figure carries no result numbers. Every number it does carry (trees per region, depth, history-depth
thresholds, row budget, pool sizes, rule count) is a design constant. Each claim is listed in FACTS
below with its fact ID and a text needle, and the script asserts, before drawing, that the needle occurs
in that fact's entry of PAPER_FACTS.md (or in the named draft or engine file): fail loud if a fact
changed. After drawing it also asserts, for each claim, that the drawn text (figure probe) and the
caption fig1_caption.md (caption probe) still carry it, so fig1_data.csv says truthfully where each
claim appears.

Outputs (same folder): fig1.pdf (vector, fonts embedded), fig1.png (300 dpi), fig1_data.csv (every
checked claim with where it appears, and every label drawn). A layout check after drawing prints any
text that leaves its box, overlaps other text or leaves the page, and asserts every font is >= 7 pt.

Run: python -X utf8 fig1.py   (Python 3.12, matplotlib 3.11; reads only small text files; imports no
engine code; writes nothing outside this folder; no random draws).
"""
import csv
import math
import os
import re
import sys

sys.dont_write_bytecode = True

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle, Circle, FancyArrowPatch, Arc

ROOT = r"C:/Users/<user>/Desktop/data set for reserch paper"
FACTS_PATH = ROOT + "/paper/PAPER_FACTS.md"
NEIGHBOUR_PY = ROOT + "/engine/treeroute/route/neighbour.py"
METHOD_MD = ROOT + "/paper/draft/02_method.md"
OUT_DIR = ROOT + "/paper/figures/fig1"
CAPTION_MD = OUT_DIR + "/fig1_caption.md"

# Script capitals for the overlap block B(u) and the usable trees K(u) (the paper's \mathcal B, \mathcal K).
# They are drawn as Unicode script letters, which mathtext takes from the STIX fallback font, so that every
# other math letter stays in Arial (one text face; see the typography note in section 2).
SB, SK = chr(0x212C), chr(0x1D4A6)

# ----------------------------------------------------------------------------------------------------
# 1. Fact checks. Each row: (element, claim, value, fact ID, source file, needle that must occur in that
#    fact's entry (or file), figure probe, caption probe). A probe is a substring that must occur in one
#    drawn label (figure) or in the caption with HTML comments stripped; None = not carried there.
# ----------------------------------------------------------------------------------------------------
F, M, C, N = FACTS_PATH, METHOD_MD, CAPTION_MD, NEIGHBOUR_PY
FACTS = [
    ("package", "dataset package: data, column facts, ban list, split file, optional feature script", "",
     "M4", F, "an optional feature script (which also builds the router context)",
     "optional feature script", "optional feature script"),
    ("package", "the package is the only hand-set input", "", "M4", F, "The only hand-set input is a dataset package",
     "the only hand-set input", "only hand-set input"),
    ("settings", "36 written rules set every modelling setting", "36", "M4", F, "R1-R36",
     "36 written rules", "36 written rules"),
    ("settings", "set before any compute", "", "M4", F, "before any compute", "before any compute",
     "before any compute"),
    ("settings", "four qualifiers on plug-and-predict, incl. coral bleaching's hand-set test window", "4", "M6", F,
     "Coral's 2016-2019 window departs from R3: it was set by leaving out the 2020 survey visits, and signed after the yearly counts were seen",
     "four disclosed qualifiers", "Four disclosed qualifiers"),
    ("settings", "NDVI's context drivers are test-exposed", "5", "K12", F, "five drivers from the run89 top-5 list (test-exposed",
     None, "five context drivers are test-exposed"),
    ("settings", "coral bleaching enters as a table; feature timing and marks vouched for", "", "M6", F,
     "the owner vouches for its features and train/test marks", None, "table of survey visits"),
    ("settings", "46 training-only regions on coral bleaching", "46", "M6", F, "46 coral groups are train-only donors",
     None, "46 training-only regions"),
    ("settings", "plug-and-predict claimed for the four gridded problems only", "", "02 §2.9", M,
     "Plug-and-predict is therefore claimed for the four gridded packages only", None,
     "claimed for the four gridded problems only"),
    ("tree bank", "100 specialist trees per region", "100", "M11", F, "Each group trains 100 trees",
     "100 specialist trees", "100 specialist trees"),
    ("tree bank", "tree depth 8", "8", "M11", F, "depth 8", "(depth 8)", "(depth 8)"),
    ("tree bank", "bootstrap bags of the region's training rows", "", "M11", F, "drawn with replacement",
     "bootstrap bags", "bootstrap bags"),
    ("tree bank", "corrector: depth-6 tree on out-of-bag residuals", "6", "M15", F, "depth 6", "corrector",
     "depth-6 tree"),
    ("tree bank", "no corrector below 50 out-of-bag rows; most coral trees have none", "50", "M15", F,
     "On coral, 5,851-6,384 of the 8,300 trees per bank have no corrector", None,
     "fewer than 50 out-of-bag rows has no corrector"),
    ("tree bank", "placebo: control, never selectable", "", "M15", F, "It is never selectable",
     "control, never selectable", "never selectable"),
    ("tree bank", "tree inputs: kept columns (lagged) and own-history features; not the router context", "", "K9", F,
     "router-context columns are a separate block and are not tree inputs", "never the router",
     "the router context is never a tree input"),
    ("tree bank", "no own-history features on coral bleaching", "", "M35", F, "Coral: none", None,
     "own-history features (none on coral bleaching)"),
    ("tree-answer table", "location u uses only trees outside its overlap block", "", "M16", F,
     "never sees the trees of its own overlap block", SK + r"(u)", "outside the block"),
    ("tree-answer table", "every tree answer is an out-of-region prediction", "", "M18", F,
     "out-of-group prediction", "own mask", "out-of-region predictions"),
    ("tree-answer table", "most overlap blocks hold one region (24 of 401 hold two)", "", "M17", F,
     "Two-group blocks", None, "most overlap blocks hold a single region"),
    ("tree-answer table", "coral rows are survey visits", "", "K1", F, "each survey visit is one row",
     "survey visits on coral", "survey visits on coral bleaching"),
    ("router", "history depth h: median valid labels per location", "", "K6", F, "h is the numpy median",
     "history depth", "history depth"),
    ("router", "one router type per problem", "", "M21", F, "The kind is set by h", "one router type per problem",
     "one router type per problem"),
    ("per-location router", "h >= 24", "24", "M21", F, "h >= 24 gives per-unit", r"$h \geq 24$", r"$h \ge 24$"),
    ("region router", "2 <= h < 24", "2;24", "M21", F, "2 <= h < 24 gives region", r"$2 \leq h < 24$",
     r"$2 \le h < 24$"),
    ("neighbour router", "h < 2", "2", "M21", F, "h < 2 gives neighbour", r"$h < 2$", r"$h < 2$"),
    ("per-location router", "PM2.5, NDVI, burned fraction", "", "M59", F,
     "Per-unit (with the exact trees-off = normal identity): PM2.5, NDVI and fire",
     "PM2.5, NDVI, burned fraction", "serves PM2.5, NDVI and burned fraction"),
    ("region router", "forest loss", "", "M59", F, "Region (one pooled ridge per group, no context, no GLS): defo",
     "forest loss", "serves forest loss"),
    ("neighbour router", "coral bleaching", "", "M59", F,
     "Neighbour (no normal column, no climatology identity, constant donor-median reference): coral",
     "coral bleaching", "serves coral bleaching"),
    ("per-location router", "design [1 | n_u - nbar_u | z | T]; intercept and normal unpenalised", "", "M22", F,
     "The intercept and normal are unpenalised", r"$n_u-\bar{n}_u$", "intercept and normal are unpenalised"),
    ("per-location router", "penalties a_ctx kappa_ctx, a_tree kappa_tree; kappa = mean diagonal of own block",
     "", "M22", F, "each scaled by the mean diagonal of their own block's Gram",
     r"$a_{\mathrm{tree}}\kappa_{\mathrm{tree}}$", "mean diagonal"),
    ("per-location router", "penalty scale on the weighted Gram (X'WX)", "", "K16", F,
     "the mean diagonal of its block of X'WX", None, "weighted Gram matrix"),
    ("per-location router", "router fit rows: the location's own rows at or before the cut", "", "K15", F,
     "The fit rows are the scored unit's own rows", "own router fit rows", "own router fit rows"),
    ("per-location router", "trees-off fit = seasonal normal (exact)", "", "M33", F,
     "trees-off equals the normal exactly", "trees-off fit = seasonal normal (exact)",
     "equals the seasonal normal exactly"),
    ("per-location router", "short-history fallback below 24 router fit rows", "24", "M29", F,
     "fewer than 24 valid fit rows are routed by their group's region router", None,
     "fewer than 24 router fit rows"),
    ("region router", "at most 60,000 router fit rows of whole bank locations", "60000", "M27", F,
     "largest evenly spaced set of whole units within 60,000 rows", "60,000 router fit rows",
     "60,000 router fit rows"),
    ("region router", "no router context, no error weighting", "", "M27", F, "There is no GLS solve",
     "no error weighting", "no error weighting"),
    ("region router", "penalty lambda kappa^c_tree (centred tree Gram)", "", "K7", F,
     "lambda x (trace of the Gram of the tree block centred", r"$\lambda\,\kappa^{c}_{\mathrm{tree}}$",
     "column-centred tree block"),
    ("region router", "trees-off fit = seasonal normal (exact)", "", "K8", F,
     "asserted equal to the normal on every score row", "trees-off fit = seasonal normal (exact)",
     "In both routers"),
    ("neighbour router", "150 nearest earlier training visits", "150", "M28", F, "150 nearest", "150 nearest",
     "150 nearest"),
    ("neighbour router", "then the 50 most similar in tree inputs", "50", "M28", F, "50 most similar",
     "50 most similar", "50 most similar"),
    ("neighbour router", "fewer than 12 eligible visits: training median", "12", "M28", F,
     "fewer than 12 eligible rows", None, "fewer than 12 visits are eligible"),
    ("neighbour router", "masks its own overlap block and every block in the pool", "", "M28", F,
     "drops the blocks of the row's own group and of every group in its pool", None, "every block in the pool"),
    ("neighbour router", "design [1 | z | T], intercept alone unpenalised", "", "K19", F,
     "only the intercept unpenalised", r"$\mathbf{z}$", "only the intercept unpenalised"),
    ("neighbour router", "penalties trace-normalised per block (a kappa)", "", "(code)", N,
     "each penalised block trace-normalised on its own raw block", r"$a_{\mathrm{ctx}}\kappa_{\mathrm{ctx}}$",
     "per-location penalty grid"),
    ("neighbour router", "no normal; reference and decline target = training median", "", "M43", F,
     "the donor median for the neighbour kind", "reference = training median",
     "reference and decline target are the training median"),
    ("adaptation layer", "links identity, log(y + c), arcsine sqrt(y/U)", "", "M39", F,
     "arcsine(sqrt(y/UB)) on [0, UB]", r"$\arcsin\sqrt{y/U}$", r"$\arcsin\sqrt{y/U}$"),
    ("adaptation layer", "links admitted by rules on declared bounds and training values", "", "K27", F,
     "the training rows hold at least one positive value", "and training values",
     "declared bounds and training values"),
    ("adaptation layer", "log constant c from the training rows at the lead's fit cut", "", "K27", F,
     "c is the 1st percentile (numpy linear) of positive training y at each lead's fit cut", None,
     "The log constant $c$"),
    ("adaptation layer", "answer type plain / corrected x weighting uniform / error-weighted", "", "M40", F,
     "the arms are plain and corrector, each unweighted and GLS-weighted", "answer type: plain",
     "an answer type (plain or corrected)"),
    ("adaptation layer", "error weight omega = sigma-hat^-2", "", "M41", F, "The weight is 1/sigma^2",
     r"$\omega=\hat{\sigma}^{-2}$", r"$\omega = \hat\sigma^{-2}$"),
    ("adaptation layer", "trees-off fits and placebos never selectable", "", "M40", F,
     "Trees-off (the guard reference) and the placebo are never selectable",
     "never selectable: trees-off fits, placebos", "Trees-off fits and placebos are never selectable"),
    ("adaptation layer", "lowest surface MAE in units of y, back-transformed, clipped", "", "K30", F,
     "scored by MAE in y units, on back-transformed, clipped predictions", "lowest MAE on the decision",
     "after back-transformation and clipping"),
    ("adaptation layer", "decision surface: scored locations' inner-score rows", "", "M46", F,
     "the scored units' inner-score rows", "inner score window", "inner score window"),
    ("adaptation layer", "coral decision surface: training visits, one fold per region", "", "K31", F,
     "There is one fold per group (R13)", None, "in one fold per region"),
    ("adaptation layer", "decision rows predicted by trees and routers fitted at the inner cut", "", "K22", F,
     "the bank is refit at the inner (guard) cut", None, "fitted at the inner cut"),
    ("adaptation layer", "error-weight target from trees that saw the inner score window", "", "K28", F,
     "at the nowcast they come from trees that saw the inner-score years", None, "not fully out of sample"),
    ("skill guard", "surface MAE strictly below the reference, no margin", "", "M43", F,
     "strictly below its own link's trees-off MAE", "strictly below", "strictly below (with no margin)"),
    ("skill guard", "reference = own-link trees-off fit (coral: training median)", "", "K33", F,
     "Each link's trees-off, back-transformed and clipped, is that link's guard reference",
     "reference: own-link trees-off fit", "its own link's trees-off fit"),
    ("skill guard", "nowcast guard reuses the decision surface (no separate hold-out)", "", "M46", F,
     "there is no separate holdout", None, "there is no separate hold-out"),
    ("skill guard", "adopt lowest-MAE admitted arm, else decline", "", "M44", F,
     "If none is eligible, the layer declines to the decline target", "admitted arm",
     "The admitted arm with the lowest surface MAE is adopted"),
    ("decline target", "arithmetic normal (gridded) / training median (coral)", "", "M44", F,
     "the identity (arithmetic) normal for grid kinds, the donor median for neighbour", "arithmetic normal",
     "the arithmetic normal, or the training median on coral bleaching"),
    ("skill guard", "log/arcsine reference differs from decline target (gridded)", "", "K33", F,
     "This holds for log and arcsine arms alike", "differs from the decline target",
     "which differs from the decline target"),
    ("lock", "adoption locked before test labels are opened", "", "M38", F,
     "Test labels open only if the hash matches", "adoption locked", "locked before the test labels are opened"),
    ("test round", "test round: refit at tau, open test labels, forecast", "", "K22", F,
     "The test round reads the fit-cut objects", "Test round", "In the test round"),
    ("forecast ladder", "each lead's adoption locked before its test labels", "", "P17", F,
     "At every lead of every run", "lock", "Each lead's adoption is locked"),
    ("forecast ladder", "tree bank refitted at the fit cut tau_L", "", "M47", F,
     "The bank, correctors and c are refit at the lead's fit cut", "tree bank refitted",
     "refitted at the fit cut"),
    ("forecast ladder", "pinned arm = nowcast's adopted arm and penalty", "", "M47", F,
     "The arm and penalty are PINNED to the nowcast's adoption", "pinned arm", "pins the nowcast's adoption directly"),
    ("forecast ladder", "pinned arm after a decline = best tree arm and its penalty", "", "K23", F,
     "its best tree arm and that arm's penalty", "best tree arm", "its best tree arm and that arm's penalty"),
    ("forecast ladder", "skill guard on guard rows, trees at the guard cut tau^g_L; fail declines", "", "M47", F,
     "A guard bank at the lead's guard cut serves the guard. If it fails, the lead declines", "guard cut",
     "guard cut"),
    ("forecast ladder", "leads 6 and 12 months (PM2.5, NDVI, burned fraction)", "6;12", "M9", F,
     "PM2.5, NDVI and fire: nowcast + 6 and 12 months", None, "6 and 12 months"),
    ("forecast ladder", "lead 1 year (forest loss)", "1", "M9", F, "Defo: nowcast + 1 year", None, "1 year"),
    ("forecast ladder", "leads 183 and 365 days (coral)", "183;365", "M9", F, "Coral: 0, 183 and 365 days", None,
     "183 and 365 days"),
    ("test exposure", "penalty-grid centres test-exposed", "", "M24", F, "are test-exposed", None,
     "the penalty-grid centres"),
    ("test exposure", "60,000-row budget test-exposed", "60000", "P23", F, "The 60,000-row budget", None,
     "60,000-row budget"),
    ("test exposure", "inner-cut refit of the trees test-exposed", "", "M19", F,
     "A7.inner_cut_bank_refit = True, test-exposed", None, "the refit of the trees at the inner cut"),
]


def fact_entry(text, fid):
    """The entry of fact `fid` in PAPER_FACTS.md: its '- **ID (' line and its indented continuation."""
    lines = text.splitlines()
    pat = re.compile(r"^- \*\*" + re.escape(fid) + r" \(")
    for i, ln in enumerate(lines):
        if pat.match(ln):
            out = [ln]
            for nxt in lines[i + 1:]:
                if nxt.startswith("- **") or nxt.startswith("#"):
                    break
                out.append(nxt)
            return "\n".join(out)
    raise SystemExit("FACT CHECK FAILED: fact %s not found in %s" % (fid, FACTS_PATH))


def check_facts():
    texts = {}
    for p in (F, M, N):
        with open(p, encoding="utf-8") as f:
            texts[p] = f.read()
    rows = []
    for element, claim, value, fid, src, needle, fprobe, cprobe in FACTS:
        hay = fact_entry(texts[F], fid) if src == F else texts[src]
        if needle not in " ".join(hay.split()):
            raise SystemExit("FACT CHECK FAILED: %r not in %s (%s)" % (needle, fid, src))
        where = {F: "", M: " (Section 2.9)", N: " (module docstring, 'The local fit (R14)')"}[src]
        rows.append({"element": element, "claim": claim, "value": value, "fact_id": fid,
                     "source": src + where, "checked_needle": needle, "figure_probe": fprobe or "",
                     "caption_probe": cprobe or ""})
    return rows


# ----------------------------------------------------------------------------------------------------
# 2. Style: print sizes in mm and pt; palette validated with the dataviz validator (all pairs, light,
#    white surface): blue #2a78d6, orange #eb6834, aqua-green #1baf7a pass CVD (worst dE 9.2) and
#    normal-vision (worst dE 24.0); the green is below 3:1 contrast, so every green element carries a text
#    label. Colour = component (blue: trees; green: routers; orange: adaptation layer, skill guards and
#    the pinned arm; grey: package, settings, unpenalised design columns, trees-off fit, decline target).
#    Text is always in ink, never in a series colour. Greyscale: every component is named in text, masked
#    cells are hatched in dark ink, the selected pool visits are solid dark dots and the other candidates
#    open rings, controls are dashed.
#    Typography: Arial for text and for math letters (mathtext 'custom' set to Arial); only symbols Arial
#    lacks (script B and K, the radical, not-in, ellipses) come from the STIX fallback.
# ----------------------------------------------------------------------------------------------------
W, H = 175.0, 183.5  # mm (double-column width)
MM = 1 / 25.4

INK = "#0b0b0b"
INK2 = "#52514e"
HAIR = "#c3c2b7"
BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#52514e"


def tint(hex_colour, f):
    """Mix a colour with white: f = share of the colour."""
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    mix = lambda c: int(round(255 - f * (255 - c)))
    return "#%02x%02x%02x" % (mix(r), mix(g), mix(b))


BLUE_T, ORANGE_T, AQUA_T, GREY_T = tint(BLUE, 0.16), tint(ORANGE, 0.16), tint(AQUA, 0.14), "#efeeea"
MASK_T = "#dddcd6"

FS = 7.0      # body text, pt (the minimum at print size)
FS_T = 7.5    # box titles
FS_H = 8.5    # section headers
LH = 2.95     # line height for 7 pt text, mm

plt.rcParams.update({
    "font.family": "Arial",
    "mathtext.fontset": "custom",
    "mathtext.rm": "Arial",
    "mathtext.it": "Arial:italic",
    "mathtext.bf": "Arial:bold",
    "mathtext.sf": "Arial",
    "mathtext.cal": "Arial",
    "mathtext.fallback": "stixsans",
    "hatch.linewidth": 0.45,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
})

fig = plt.figure(figsize=(W * MM, H * MM))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.set_aspect("equal")
ax.axis("off")

LOG = []      # every text drawn: (element, text)
TEXTS = []    # (artist, container bounds or None) for the layout check


def Y(yt):
    """Top-based mm to axes y."""
    return H - yt


def text(x, yt, s, size=FS, weight="normal", ha="left", va="top", color=INK, el="", inside=None, **kw):
    LOG.append((el, s))
    t = ax.text(x, Y(yt), s, fontsize=size, fontweight=weight, ha=ha, va=va, color=color, zorder=8, **kw)
    TEXTS.append((t, inside))
    return t


def lines(x, yt, rows_, size=FS, color=INK, ha="left", lh=LH, el="", weight="normal", inside=None):
    for i, s in enumerate(rows_):
        if s:
            text(x, yt + i * lh, s, size=size, color=color, ha=ha, el=el, weight=weight, inside=inside)


def box(x, yt, w, h, fc="white", ec=INK2, lw=0.6, ls="-", r=1.2, z=1):
    ax.add_patch(FancyBboxPatch((x, Y(yt + h)), w, h, boxstyle="round,pad=0,rounding_size=%g" % r,
                                fc=fc, ec=ec, lw=lw, ls=ls, zorder=z))
    return (x, yt, w, h)


def rect(x, yt, w, h, fc="white", ec=INK2, lw=0.4, hatch=None, z=2, ls="-", hatchcolor=None):
    kw = {"hatchcolor": hatchcolor} if hatchcolor else {}
    ax.add_patch(Rectangle((x, Y(yt + h)), w, h, fc=fc, ec=ec, lw=lw, hatch=hatch, zorder=z, ls=ls, **kw))
    return (x, yt, w, h)


def arrow(x1, y1t, x2, y2t, color=INK2, lw=0.7, ls="-", ms=6, z=3):
    ax.add_patch(FancyArrowPatch((x1, Y(y1t)), (x2, Y(y2t)), arrowstyle="-|>", mutation_scale=ms,
                                 color=color, lw=lw, ls=ls, zorder=z, shrinkA=0, shrinkB=0))


def line(xs, yts, color=INK2, lw=0.7, ls="-", z=3):
    ax.plot(xs, [Y(v) for v in yts], color=color, lw=lw, ls=ls, zorder=z, solid_capstyle="butt")


def diamond(cx, cyt, w, h, fc, ec, lw=0.8, z=2):
    pts = [(cx, Y(cyt - h / 2)), (cx + w / 2, Y(cyt)), (cx, Y(cyt + h / 2)), (cx - w / 2, Y(cyt))]
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, zorder=z))


def tree_glyph(x, yt, w=2.0, h=2.5, fc=BLUE, ec=BLUE, ls="-", lw=0.5, z=4):
    """A small tree: triangle crown plus trunk; (x, yt) is the crown's top-left corner."""
    ax.add_patch(Polygon([(x, Y(yt + h * 0.8)), (x + w, Y(yt + h * 0.8)), (x + w / 2, Y(yt))], closed=True,
                         fc=fc, ec=ec, lw=lw, ls=ls, zorder=z))
    line([x + w / 2, x + w / 2], [yt + h * 0.8, yt + h], color=ec, lw=0.6, z=z)


def padlock(x, yt, s=4.0, ec=INK, fc=GREY_T):
    """Padlock icon, s wide; (x, yt) is the top-left of the shackle."""
    bh = 0.7 * s
    ax.add_patch(Arc((x + s / 2, Y(yt + 0.45 * s)), 0.62 * s, 0.75 * s, theta1=0, theta2=180,
                     ec=ec, lw=0.9, zorder=5))
    for dx in (-0.31 * s, 0.31 * s):
        line([x + s / 2 + dx] * 2, [yt + 0.45 * s, yt + 0.55 * s], color=ec, lw=0.9, z=5)
    ax.add_patch(FancyBboxPatch((x, Y(yt + 0.55 * s + bh)), s, bh, boxstyle="round,pad=0,rounding_size=0.4",
                                fc=fc, ec=ec, lw=0.8, zorder=5))
    ax.add_patch(Circle((x + s / 2, Y(yt + 0.55 * s + bh * 0.45)), 0.09 * s, fc=ec, ec=ec, zorder=6))


def text_right_edge(t):
    fig.canvas.draw()
    bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
    return ax.transData.inverted().transform((bb.x1, bb.y0))[0]


def section(x, yt, num, title, rest="", el=""):
    t = text(x, yt, "%s  %s" % (num, title), size=FS_H, weight="bold", el=el)
    if rest:
        text(text_right_edge(t) + 1.6, yt + 0.55, rest, size=FS, color=INK2, el=el)


def design_row(x0, yt, blocks, penalties, el, inside):
    """Design-matrix blocks (label, width, fill) with their penalties underneath; returns block centres."""
    x = x0
    centres = []
    for (lab, w, fc), pen in zip(blocks, penalties):
        rect(x, yt, w, 4.6, fc=fc, ec=INK2, lw=0.5)
        text(x + w / 2, yt + 2.3, lab, ha="center", va="center", el=el, inside=inside)
        text(x + w / 2, yt + 5.6, pen, ha="center", el=el, color=INK2, inside=inside)
        centres.append(x + w / 2)
        x += w + 0.7
    return centres


rows = check_facts()

# ====================================================================================================
# A. Dataset package and settings (top band)
# ====================================================================================================
TOPH = 17.0
B_pkg = box(2, 1.5, 82, TOPH, fc=GREY_T, ec=GREY)
text(4, 2.6, "Dataset package (the only hand-set input)", size=FS_T, weight="bold", el="package", inside=B_pkg)
lines(4, 6.4, ["data · column facts · ban list · split file ·",
               "optional feature script (builds the router context)"], el="package", inside=B_pkg)
arrow(84, 1.5 + TOPH / 2, 90, 1.5 + TOPH / 2)
B_set = box(90, 1.5, 83, TOPH, fc=GREY_T, ec=GREY)
text(92, 2.6, "Settings", size=FS_T, weight="bold", el="settings", inside=B_set)
lines(92, 6.4, ["36 written rules set every modelling setting from the package",
                "and fixed engine constants, before any compute;",
                "four disclosed qualifiers (Section 2.9), e.g. coral bleaching's",
                "test window, set by hand"], el="settings", inside=B_set)

# ====================================================================================================
# B. 1 Tree bank and the tree-answer table
# ====================================================================================================
Y1 = 1.5 + TOPH + 3.3          # section 1 header
section(2, Y1, "1", "Tree bank", el="tree bank")
R0 = Y1 + 5.7                  # first region box
arrow(32, 1.5 + TOPH, 32, R0)  # package data -> the regions' trees

reg_y = [R0, R0 + 7.0, R0 + 14.0, None, R0 + 23.5]
reg_lab = ["region 1", "region 2", "region 3", None, "region G"]
for yt, lab in zip(reg_y, reg_lab):
    if yt is None:
        text(22, R0 + 21.5, r"$\vdots$", ha="center", va="center", size=8, el="tree bank")
        continue
    bx = box(2, yt, 40, 6.0, fc=BLUE_T, ec=BLUE, lw=0.6, r=0.8)
    text(3.5, yt + 3.0, lab, va="center", el="tree bank", inside=bx)
    for k in range(6):
        tree_glyph(15.0 + k * 3.25, yt + 1.6, w=2.2, h=2.9)
    text(35.4, yt + 3.0, r"$\cdots$", va="center", el="tree bank", inside=bx)
lines(2, R0 + 31.2, ["each region: 100 specialist trees",
                     "(depth 8) on bootstrap bags of",
                     "its own training rows"], el="tree bank", color=INK2)

# Detail of one tree (zoom out of region 2)
px, pyt, pw, ph = 45.5, R0, 42.0, 36.4
B_tree = box(px, pyt, pw, ph, fc="white", ec=BLUE, lw=0.6, r=1.0)
line([42.0, px], [R0 + 7.0, pyt + 1.0], color=BLUE, lw=0.5, ls=(0, (2, 1.5)))
line([42.0, px], [R0 + 13.0, pyt + ph - 1.0], color=BLUE, lw=0.5, ls=(0, (2, 1.5)))
text(px + 2, pyt + 1.2, r"Each tree $k$", size=FS_T, weight="bold", el="tree bank", inside=B_tree)
tree_glyph(px + 2.2, pyt + 5.0, w=3.0, h=3.6)
lines(px + 7.0, pyt + 6.2, [r"tree answer $T_k$"], el="tree bank", inside=B_tree)
tree_glyph(px + 2.7, pyt + 11.6, w=2.0, h=2.6, fc=tint(BLUE, 0.45))
lines(px + 7.0, pyt + 11.0, [r"corrector $C_k$", r"$\rightarrow$ corrected answer $T_k+C_k$"],
      el="tree bank", inside=B_tree)
tree_glyph(px + 2.7, pyt + 18.0, w=2.0, h=2.6, fc="white", ls=(0, (1.5, 1.0)))
lines(px + 7.0, pyt + 17.4, ["placebo of the corrector:", "control, never selectable"], el="tree bank",
      inside=B_tree)
line([px + 2, px + pw - 2], [pyt + 24.0, pyt + 24.0], color=HAIR, lw=0.5)
lines(px + 2, pyt + 24.8, ["tree inputs: columns the ban list",
                           "keeps (lagged) and own-history",
                           "features; never the router context"], el="tree bank", color=INK2, inside=B_tree)

# Tree-answer table
tx0 = 91.0
TT = R0 - 1.4
t_title = text(tx0, TT, "Tree-answer table", size=FS_T, weight="bold", el="tree-answer table")
text(text_right_edge(t_title) + 1.6, TT + 0.4, "rows: location-steps (survey visits on coral", color=INK2,
     el="tree-answer table")
text(text_right_edge(t_title) + 1.6, TT + 3.35, "bleaching); columns: trees by region", color=INK2,
     el="tree-answer table")

cw = 3.15                    # cell width
gx0 = tx0 + 11.0             # first cell column
HDR = TT + 7.4               # header row of region labels
groups = [("region 1", 4), ("region 2", 4), ("region 3", 4), (None, 1), ("region G", 4)]
col_x = []                   # (x, group index) for data columns
x = gx0
for gi, (lab, n) in enumerate(groups):
    if lab is None:
        text(x + cw * n / 2, HDR + 1.8, r"$\cdots$", ha="center", va="center", el="tree-answer table")
        x += cw * n + 0.8
        continue
    rect(x, HDR, cw * n, 3.6, fc=BLUE_T, ec=BLUE, lw=0.5)
    text(x + cw * n / 2, HDR + 1.8, lab, ha="center", va="center", el="tree-answer table")
    for j in range(n):
        col_x.append((x + j * cw, gi))
    x += cw * n + 0.8
grid_right = x - 0.8
arrow(px + pw, pyt + ph / 2, tx0 + 0.2, pyt + ph / 2)

rh = 2.45
row_spec = [("u'", 2, (0,)), ("u", 3, (1, 2)), ("u''", 2, (4,))]   # (row, steps, masked region columns)
G0 = HDR + 4.4
yt = G0
text(tx0, HDR + 1.8, "location", va="center", el="tree-answer table", color=INK2)
band_bounds = {}
for lab, n, masked_groups in row_spec:
    y_start = yt
    for r_ in range(n):
        for cx, gi in col_x:
            masked = gi in masked_groups
            rect(cx, yt, cw, rh, fc=MASK_T if masked else "white", ec=HAIR, lw=0.35,
                 hatch="///" if masked else None, hatchcolor=INK2 if masked else None, z=2)
        yt += rh
    band_bounds[lab] = (y_start, yt)
    shown = {"u'": r"$u'$", "u": r"$u$", "u''": r"$u''$"}[lab]
    text(tx0 + 5.0, (y_start + yt) / 2, shown, ha="center", va="center", el="tree-answer table", size=FS_T)
    line([tx0, grid_right], [yt, yt], color=INK2, lw=0.5, z=4)
line([tx0, grid_right], [G0, G0], color=INK2, lw=0.5, z=4)
ub0, ub1 = band_bounds["u"]
rect(gx0, ub0, grid_right - gx0, ub1 - ub0, fc="none", ec=INK, lw=0.9, z=5)
# bracket under regions 2 and 3
r2_x = [c for c, g in col_x if g == 1][0]
r3_x = [c for c, g in col_x if g == 2][-1] + cw
yb = yt + 1.2
line([r2_x, r2_x, r3_x, r3_x], [yb - 0.6, yb, yb, yb - 0.6], color=INK, lw=0.6)
text((r2_x + r3_x) / 2, yb + 0.6, r"overlap block $%s(u)$ of $u$ (in region 2): masked" % SB,
     ha="center", el="tree-answer table")
lines(tx0, yb + 4.4, [r"$u$ may use only the trees $%s(u)=\{k:$ region$(k)\notin %s(u)\}$" % (SK, SB),
                      "(leave-one-block-out tree bank; each location has its own mask)"],
      el="tree-answer table", lh=3.1)
TABLE_FEED_Y = (ub0 + ub1) / 2

# ====================================================================================================
# C. 2 Router: three router types
# ====================================================================================================
SEC2 = max(R0 + 31.2 + 2 * LH + 3.0, yb + 4.4 + 3.1 + 3.4) + 1.4
section(2, SEC2, "2", "Router", r"one router type per problem, set by the history depth $h$ (Table 1)",
        el="router")
RW = 55.6
RX = [2.0, 2.0 + RW + 2.1, 2.0 + 2 * (RW + 2.1)]
RC = [xr + RW / 2 for xr in RX]
RT, RH = SEC2 + 7.2, 35.2
FEED = RT - 2.2
FEED_X = 166.0
# feed: from the table's right edge to the three routers
line([grid_right, FEED_X, FEED_X], [TABLE_FEED_Y, TABLE_FEED_Y, FEED], color=INK2, lw=0.7)
line([RC[0], FEED_X], [FEED, FEED], color=INK2, lw=0.7)
for cx in RC:
    arrow(cx, FEED, cx, RT)
B_r = [box(xr, RT, RW, RH, fc=AQUA_T, ec=AQUA, lw=0.8) for xr in RX]

DESC = RT + 8.6     # description lines
DR = RT + 18.9      # design row
PILL = RT + 28.8    # identity pill

# --- per-location router
x0 = RX[0] + 2.0
text(x0, RT + 1.3, r"Per-location router   $h \geq 24$", size=FS_T, weight="bold", el="per-location router",
     inside=B_r[0])
text(x0, RT + 4.8, "PM2.5, NDVI, burned fraction", color=INK2, el="per-location router", inside=B_r[0])
lines(x0, DESC, [r"one ridge per location in link $\phi$, on its",
                 "own router fit rows"], el="per-location router", inside=B_r[0])
text(x0, DR + 2.3, "design", va="center", color=INK2, el="per-location router", inside=B_r[0])
text(x0, DR + 6.9, "penalty", va="center", color=INK2, el="per-location router", inside=B_r[0])
c_pl = design_row(x0 + 9.6, DR,
                  [(r"$1$", 4.0, GREY_T), (r"$n_u-\bar{n}_u$", 11.6, GREY_T), (r"$\mathbf{z}$", 10.0, "white"),
                   (r"$\mathbf{T}$", 15.6, BLUE_T)],
                  ["0", "0", r"$a_{\mathrm{ctx}}\kappa_{\mathrm{ctx}}$", r"$a_{\mathrm{tree}}\kappa_{\mathrm{tree}}$"],
                  el="per-location router", inside=B_r[0])

# --- region router
x1 = RX[1] + 2.0
text(x1, RT + 1.3, r"Region router   $2 \leq h < 24$", size=FS_T, weight="bold", el="region router",
     inside=B_r[1])
text(x1, RT + 4.8, "forest loss", color=INK2, el="region router", inside=B_r[1])
lines(x1, DESC, ["one pooled ridge per region on at most",
                 "60,000 router fit rows; no router context,",
                 "no error weighting"], el="region router", inside=B_r[1])
text(x1, DR + 2.3, "design", va="center", color=INK2, el="region router", inside=B_r[1])
text(x1, DR + 6.9, "penalty", va="center", color=INK2, el="region router", inside=B_r[1])
c_rg = design_row(x1 + 9.6, DR,
                  [(r"$1$", 4.0, GREY_T), (r"$n_u-\bar{n}$", 11.6, GREY_T), (r"$\mathbf{T}$", 26.3, BLUE_T)],
                  ["0", "0", r"$\lambda\,\kappa^{c}_{\mathrm{tree}}$"], el="region router", inside=B_r[1])

# trees-off identity (per-location and region routers)
for i, cen in ((0, c_pl), (1, c_rg)):
    xm = (cen[0] + cen[1]) / 2
    arrow(xm, DR + 4.9, xm, PILL, ls=(0, (2.2, 1.4)), color=INK, lw=0.7)
    bp = box(RX[i] + 2.0, PILL, RW - 4.0, 4.6, fc=GREY_T, ec=GREY, lw=0.6, r=2.2, z=2)
    text(RX[i] + RW / 2, PILL + 2.3, "trees-off fit = seasonal normal (exact)", ha="center", va="center",
         el="climatology identity", inside=bp)

# --- neighbour router
x2 = RX[2] + 2.0
text(x2, RT + 1.3, r"Neighbour router   $h < 2$", size=FS_T, weight="bold", el="neighbour router",
     inside=B_r[2])
text(x2, RT + 4.8, "coral bleaching", color=INK2, el="neighbour router", inside=B_r[2])
lines(x2, DESC, ["one ridge per scored survey visit (star) on the",
                 "50 most similar in tree inputs (dark dots)",
                 "of the 150 nearest earlier training visits"], el="neighbour router", inside=B_r[2])
text(x2, DR + 2.3, "design", va="center", color=INK2, el="neighbour router", inside=B_r[2])
text(x2, DR + 6.9, "penalty", va="center", color=INK2, el="neighbour router", inside=B_r[2])
c_nb = design_row(x2 + 9.6, DR,
                  [(r"$1$", 4.0, GREY_T), (r"$\mathbf{z}$", 10.0, "white"), (r"$\mathbf{T}$", 11.0, BLUE_T)],
                  ["0", r"$a_{\mathrm{ctx}}\kappa_{\mathrm{ctx}}$", r"$a_{\mathrm{tree}}\kappa_{\mathrm{tree}}$"],
                  el="neighbour router", inside=B_r[2])
# map inset beside the design row: open rings = other candidates, solid dark dots = the 50 selected
mx = x2 + 9.6 + 4.0 + 10.0 + 11.0 + 3 * 0.7 + 1.6
mw = RX[2] + RW - 1.6 - mx
myt, mh = DR - 0.4, 9.6
rect(mx, myt, mw, mh, fc="white", ec=HAIR, lw=0.5, z=2)
mcx, mcy = mx + mw / 2, Y(myt + mh / 2)
golden = math.pi * (3 - math.sqrt(5))
for i in range(1, 60):
    rr = math.sqrt(i / 59.0) * 9.0
    th = i * golden
    qx, qy = mcx + rr * math.cos(th), mcy + rr * math.sin(th)
    if abs(qx - mcx) > mw / 2 - 0.6 or abs(qy - mcy) > mh / 2 - 0.6:
        continue
    selected = rr < 4.1 and (i % 3 == 0)
    if selected:
        ax.add_patch(Circle((qx, qy), 0.42, fc=INK, ec=INK, lw=0.25, zorder=4))
    else:
        ax.add_patch(Circle((qx, qy), 0.3, fc="white", ec=INK2, lw=0.4, zorder=4))
ax.add_patch(Circle((mcx, mcy), 4.25, fc="none", ec=INK, lw=0.55, ls=(0, (2, 1.2)), zorder=4))
ax.plot([mcx], [mcy], marker="*", ms=6.0, mfc="white", mec=INK, mew=0.5, zorder=6)
bp = box(RX[2] + 2.0, PILL, RW - 4.0, 4.6, fc=GREY_T, ec=GREY, lw=0.6, r=2.2, z=2)
text(RX[2] + RW / 2, PILL + 2.3, "no normal; reference = training median", ha="center", va="center",
     el="neighbour router", inside=bp)

# ====================================================================================================
# D. 3 Adaptation layer, skill guard, decline, lock, test round    |    4 Forecast ladder
# ====================================================================================================
BUS = RT + RH + 1.4
DT = BUS + 2.0
LX0 = 118.0                          # forecast ladder left edge
section(5.5, DT, "3", "Adaptation layer", r"nowcast ($L=0$), chosen on pre-test rows", el="adaptation layer")
section(LX0, DT, "4", "Forecast ladder", r"each lead $L \geq 1$ (Table 1)", el="forecast ladder")
AT = DT + 4.8
AX, AW = 5.5, 54.5
BUSX = 2.5
# routers -> arms: a bus under the routers, down the left margin, into the arms box
for cx in RC:
    line([cx, cx], [RT + RH, BUS], color=INK2, lw=0.7)
line([BUSX, RC[2]], [BUS, BUS], color=INK2, lw=0.7)
line([BUSX, BUSX], [BUS, AT + 7.0], color=INK2, lw=0.7)
arrow(BUSX, AT + 7.0, AX, AT + 7.0)

AH = 38.6
B_arm = box(AX, AT, AW, AH, fc=ORANGE_T, ec=ORANGE, lw=0.8)
text(AX + 2.0, AT + 1.3, "Arms: link × answer type × weighting", size=FS_T, weight="bold", el="adaptation layer",
     inside=B_arm)
lines(AX + 2.0, AT + 5.0, [r"link $\phi$: identity · $\log(y+c)$ · $\arcsin\sqrt{y/U}$",
                           "(admitted by rules on declared bounds",
                           "and training values)",
                           r"answer type: plain $T_k$ · corrected $T_k+C_k$",
                           r"weighting: uniform · error-weighted, $\omega=\hat{\sigma}^{-2}$"],
      el="adaptation layer", lh=3.35, inside=B_arm)
line([AX + 2.0, AX + AW - 2.0], [AT + 22.6, AT + 22.6], color=tint(ORANGE, 0.5), lw=0.5)
lines(AX + 2.0, AT + 23.3, ["penalty point: lowest MAE on the decision",
                            "surface (inner score window, pre-test)",
                            "reference: own-link trees-off fit",
                            "(coral: training median)",
                            "never selectable: trees-off fits, placebos"], el="adaptation layer", lh=2.95,
      inside=B_arm)

# skill guard diamond
gcx, gcy, gw, gh = 76.5, AT + 13.5, 27.0, 27.0
arrow(AX + AW, gcy, gcx - gw / 2, gcy)
diamond(gcx, gcy, gw, gh, fc=ORANGE_T, ec=ORANGE, lw=0.9)
text(gcx, gcy - 6.4, "Skill guard", ha="center", size=FS_T, weight="bold", el="skill guard")
lines(gcx, gcy - 3.0, ["surface MAE", "strictly below", "the reference?"], ha="center", el="skill guard",
      lh=2.65)

# yes -> adopt
YX, YW = 94.0, 21.5
arrow(gcx + gw / 2, gcy, YX, gcy)
text((gcx + gw / 2 + YX) / 2, gcy - 0.6, "yes", ha="center", va="bottom", color=INK2, el="skill guard")
B_yes = box(YX, gcy - 7.0, YW, 14.0, fc=ORANGE_T, ec=ORANGE, lw=0.8)
lines(YX + YW / 2, gcy - 5.9, ["adopt the", "admitted arm", "with the lowest", "surface MAE"], ha="center",
      el="skill guard", inside=B_yes)
# no -> decline
NT = gcy + gh / 2 + 3.4
arrow(gcx, gcy + gh / 2, gcx, NT)
text(gcx + 1.0, gcy + gh / 2 + 0.6, "no", va="top", color=INK2, el="skill guard")
DW = 27.0
NH = 15.0
B_dec = box(gcx - DW / 2, NT, DW, NH, fc=GREY_T, ec=GREY, lw=0.8)
text(gcx, NT + 1.0, "Decline", ha="center", size=FS_T, weight="bold", el="decline target", inside=B_dec)
lines(gcx, NT + 4.5, ["to the decline target:", "the arithmetic normal", "(coral: training median)"],
      ha="center", el="decline target", lh=2.95, inside=B_dec)
# lock: the adoption (adopted arm or decline)
B_lock = box(YX, NT, YW, NH, fc="white", ec=INK, lw=0.8)
padlock(YX + 1.6, NT + 1.0, s=3.2)
text(YX + 6.3, NT + 1.4, "Lock", size=FS_T, weight="bold", el="lock", inside=B_lock)
lines(YX + YW / 2, NT + 5.6, ["adoption locked", "before test labels", "are opened"],
      ha="center", el="lock", lh=2.95, inside=B_lock)
arrow(YX + YW / 2, gcy + 7.0, YX + YW / 2, NT)
arrow(gcx + DW / 2, NT + NH / 2, YX, NT + NH / 2)
# test round (nowcast)
TRX, TRT = gcx - DW / 2, NT + NH + 3.4
TRW, TRH = YX + YW - TRX, 14.2
B_tr = box(TRX, TRT, TRW, TRH, fc="white", ec=INK2, lw=0.8)
text(TRX + 2.0, TRT + 1.2, "Test round (nowcast)", size=FS_T, weight="bold", el="test round", inside=B_tr)
lines(TRX + 2.0, TRT + 4.9, [r"trees and routers refitted at $\tau$; test",
                             "labels opened; forecast: the adopted arm,",
                             "or the decline target after a decline"], el="test round", inside=B_tr)
arrow(YX + YW / 2, NT + NH, YX + YW / 2, TRT)
# the known mismatch, stated where the guard is drawn
FN = AT + AH + 1.4
lines(AX, FN, ["On gridded problems a log or arcsine arm's",
               "reference (that link's back-transformed",
               "normal) differs from the decline target",
               "(the arithmetic normal)."], el="skill guard", color=INK2)

# ---- forecast ladder
LG = 3.0
LCW = (173.0 - LX0 - LG) / 2
cols = [LX0, LX0 + LCW + LG]
yh = DT + 5.2
yb1 = yh + 3.4
yb2 = yb1 + 9.6        # pinned arm (one bar across both leads: every lead pins the nowcast's adoption)
yb3 = yb2 + 10.4
GB = 13.4
BAR_H = 7.4
B_bar = box(LX0, yb2, 2 * LCW + LG, BAR_H, fc=ORANGE_T, ec=ORANGE, lw=0.8)
lines(LX0 + LCW + LG / 2, yb2 + 0.9, ["pinned arm = the adopted arm and penalty",
                                      "(after a decline: its best tree arm)"], ha="center",
      el="forecast ladder", inside=B_bar)
for i, (cxl, sub) in enumerate(zip(cols, ["1", "2"])):
    mid = cxl + LCW / 2
    text(mid, yh, r"lead $L_{%s}$" % sub, ha="center", size=FS_T, weight="bold", el="forecast ladder")
    b1 = box(cxl, yb1, LCW, 7.0, fc=BLUE_T, ec=BLUE, lw=0.7)
    lines(mid, yb1 + 0.8, ["tree bank refitted", r"at the fit cut $\tau_{L_{%s}}$" % sub], ha="center",
          el="forecast ladder", inside=b1)
    arrow(mid, yb1 + 7.0, mid, yb2)
    arrow(mid, yb2 + BAR_H, mid, yb3)
    b3 = box(cxl, yb3, LCW, GB, fc=ORANGE_T, ec=ORANGE, lw=0.7)
    diamond(cxl + 2.7, yb3 + 2.2, 3.0, 3.0, fc="white", ec=ORANGE, lw=0.7, z=4)
    text(cxl + 4.9, yb3 + 0.8, "skill guard", weight="bold", el="forecast ladder", inside=b3)
    lines(cxl + 1.4, yb3 + 4.0, ["on the guard rows,", "trees fitted at the",
                                 r"guard cut $\tau^{g}_{L_{%s}}$" % sub],
          el="forecast ladder", lh=2.75, inside=b3)
    # lock of this lead's adoption, then pass / fail
    LKY = yb3 + GB + 2.2
    arrow(mid, yb3 + GB, mid, LKY)
    lk = box(cxl + 4.0, LKY, LCW - 8.0, 5.0, fc="white", ec=INK, lw=0.7, r=0.8)
    padlock(cxl + 5.4, LKY + 0.75, s=2.4)
    text(cxl + 8.9, LKY + 2.5, "lock", va="center", el="forecast ladder", inside=lk)
    arrow(cxl + 6.0, LKY + 5.0, cxl + 6.0, LKY + 7.6)
    text(cxl + 0.8, LKY + 7.9, "pass: forecast", el="forecast ladder")
    arrow(cxl + LCW - 4.0, LKY + 5.0, cxl + LCW - 4.0, LKY + 11.8)
    text(cxl + LCW - 3.2, LKY + 5.5, "fail", color=INK2, el="forecast ladder")
B_ld = box(LX0, LKY + 11.8, 2 * LCW + LG, 5.0, fc=GREY_T, ec=GREY, lw=0.7)
text(LX0 + LCW + LG / 2, LKY + 14.3, "decline to the decline target", ha="center", va="center",
     el="forecast ladder", inside=B_ld)
# pin: from the locked nowcast adoption to the pinned-arm bar shared by every lead
PINX = (YX + YW + LX0) / 2
line([YX + YW, PINX, PINX], [NT + 4.0, NT + 4.0, yb2 + BAR_H / 2])
arrow(PINX, yb2 + BAR_H / 2, LX0, yb2 + BAR_H / 2)

# ----------------------------------------------------------------------------------------------------
# 3. Layout check: no text outside its box, no two texts overlapping, nothing off the page.
# ----------------------------------------------------------------------------------------------------
fig.canvas.draw()
rend = fig.canvas.get_renderer()
inv = ax.transData.inverted()


def data_bbox(t):
    bb = t.get_window_extent(renderer=rend)
    (x0_, y0_), (x1_, y1_) = inv.transform((bb.x0, bb.y0)), inv.transform((bb.x1, bb.y1))
    return x0_, H - y1_, x1_, H - y0_      # x0, top, x1, bottom (top-based mm)


problems = []
boxes_ = [(t, data_bbox(t), ins) for t, ins in TEXTS if t.get_text().strip()]
TOL = 0.25
for t, (a0, at, a1, ab), ins in boxes_:
    if a0 < 0.3 or a1 > W - 0.3 or at < 0.3 or ab > H - 0.3:
        problems.append("off page: %r" % t.get_text())
    if ins is not None:
        bx_, by_, bw_, bh_ = ins
        if a0 < bx_ + 0.4 - TOL or a1 > bx_ + bw_ - 0.4 + TOL or at < by_ - TOL or ab > by_ + bh_ + TOL:
            problems.append("outside its box: %r (text %.1f-%.1f x %.1f-%.1f; box %.1f-%.1f x %.1f-%.1f)"
                            % (t.get_text(), a0, a1, at, ab, bx_, bx_ + bw_, by_, by_ + bh_))
for i in range(len(boxes_)):
    for j in range(i + 1, len(boxes_)):
        (ti, (a0, at, a1, ab), _), (tj, (b0, bt, b1, bb_), _) = boxes_[i], boxes_[j]
        if min(a1, b1) - max(a0, b0) > TOL and min(ab, bb_) - max(at, bt) > TOL:
            problems.append("overlap: %r / %r" % (ti.get_text(), tj.get_text()))
min_size = min(t.get_fontsize() for t, _ in TEXTS)
bottom = max(b[1][3] for b in boxes_)
print("layout check: %d problem(s); smallest font %.1f pt; lowest text at %.1f of %.1f mm"
      % (len(problems), min_size, bottom, H))
for p in problems:
    print("  -", p)
assert min_size >= 7.0

# ----------------------------------------------------------------------------------------------------
# 4. Where each checked claim appears: assert every figure probe is in a drawn label and every caption
#    probe in the caption (HTML comments stripped); fail loud otherwise.
# ----------------------------------------------------------------------------------------------------
drawn = [s for _, s in LOG if s.strip()]
with open(CAPTION_MD, encoding="utf-8") as f:
    cap = " ".join(re.sub(r"<!--.*?-->", " ", f.read(), flags=re.S).split())
missing = []
for r_ in rows:
    fp, cp = r_["figure_probe"], r_["caption_probe"]
    r_["in_figure"] = "yes" if fp else "no"
    r_["in_caption"] = "yes" if cp else "no"
    if fp and not any(fp in s for s in drawn):
        missing.append("figure probe %r (%s)" % (fp, r_["claim"]))
    if cp and cp not in cap:
        missing.append("caption probe %r (%s)" % (cp, r_["claim"]))
    if not fp and not cp:
        missing.append("claim carried nowhere: %r" % r_["claim"])
if missing:
    raise SystemExit("PROBE CHECK FAILED:\n  " + "\n  ".join(missing))
words = sum(len(re.sub(r"\$[^$]*\$", "X", s).split()) for s in drawn)
print("probe check passed: %d claims (%d drawn, %d in caption); %d words drawn"
      % (len(rows), sum(r["in_figure"] == "yes" for r in rows), sum(r["in_caption"] == "yes" for r in rows),
         words))

# ----------------------------------------------------------------------------------------------------
# 5. Save and write the data file
# ----------------------------------------------------------------------------------------------------
os.makedirs(OUT_DIR, exist_ok=True)
fig.savefig(OUT_DIR + "/fig1.pdf")
fig.savefig(OUT_DIR + "/fig1.png", dpi=300)

FIELDS = ["kind", "element", "text", "in_figure", "in_caption", "value", "fact_id", "source", "checked_needle",
          "figure_probe", "caption_probe"]
with open(OUT_DIR + "/fig1_data.csv", "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=FIELDS)
    wr.writeheader()
    for r_ in rows:
        wr.writerow({"kind": "checked claim", "element": r_["element"], "text": r_["claim"],
                     "in_figure": r_["in_figure"], "in_caption": r_["in_caption"], "value": r_["value"],
                     "fact_id": r_["fact_id"], "source": r_["source"], "checked_needle": r_["checked_needle"],
                     "figure_probe": r_["figure_probe"], "caption_probe": r_["caption_probe"]})
    for el, s in LOG:
        if s.strip():
            wr.writerow({"kind": "label drawn", "element": el, "text": s, "in_figure": "yes", "in_caption": "",
                         "value": "", "fact_id": "", "source": "drawn by fig1.py; facts in the checked-claim rows",
                         "checked_needle": "", "figure_probe": "", "caption_probe": ""})
print("wrote", OUT_DIR, "| claims checked:", len(rows), "| labels:", len(drawn),
      "| size %.0f x %.0f mm" % (W, H))
