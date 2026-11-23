"""Graphical abstract of the methods paper: treeroute v1 in one picture, read left to right, and one result line. Round 4 (2026-11-11): figures renumbered by first citation: map (unnumbered) -> 1, 1 -> 2, 2 -> 3, 3 -> 4, 4 -> 5 (folders keep their names; paper/figures/FIGURE_NUMBERS.md).

Approved as drawn by the author on 2026-11-11 (ruling AU1), with no optional element. The drawing brief is
paper/draft/submission/graphical_abstract_brief.md. The drawing follows the brief as written and
leaves out every optional element of its section 5 (the "treeroute v1" name, the padlock beside the diamond and
the window strip under block C). Owner ruling AT21 (2026-11-09): the graphical abstract is drawn by a plotting
script, like Figures 2-5, from the brief.

What is drawn (brief sections 1, 4-7): block A, trees from other regions (four region rows of six tree glyphs
with an ellipsis; the third row masked by hatching that stops before its ellipsis; the note below the block ends
in a key swatch with the masked row's fill and hatching); block B, ridge weights over the trees (two location
markers, each with its own chart of six signed weights, both joined to one seasonal-normal box by a thick grey
line, the anchor); block C, the skill guard (diamond; yes: forecast with the trees; no: decline to the normal);
and the result band across the full width. No arrow runs from block B to the band (honesty rule 2). The decline
box is plain grey (rule 3). The bars are illustrative shapes, not values from a run: no ticks, no numbers, fixed
constants (rule 6).

The flow line: both ink arrows and the diamond's centre share one height. The A -> B arrow leaves block A level
with the gap between its first two rows and enters block B between the two weight charts; the B -> C arrow leaves
block B above the seasonal-normal box. So nothing inside block B lines up with an arrow (no box, zero line or
anchor line), and the picture cannot be read as "seasonal normal -> skill guard" or as "trees -> location 2
only". The brief puts the A -> B arrow "at mid height" with approximate positions (its section 5); the arrow now
sits above block A's own mid height, at the mid height of block B's charts and of the diamond.

Revision of 2026-11-10, after the check of the first draft (no text and no number changed): the flow line above
(the seasonal-normal box moved below it; location 2's anchor branch runs straight into the box; block A's note
sits on the baselines of note 6's second and third lines); location 2's stripes at 135 degrees, so 45-degree
hatching means "masked" only; the key swatch; the mask hatching stops before the ellipsis.

Revision of 2026-11-10 by the lead agent: the result line adds "where predict-zero did better" (fact R3b,
the only nowcast that a naive baseline beat), after the check found the line milder than the abstract; the
brief was changed first (section 1, section 6 row 11: 39 words, and honesty rule 5), and this script follows it.

Checks (each stops the script with "GA CHECK FAILED" on any mismatch):
  1. Before drawing: each needle of the brief's section 8 occurs in its fact's entry of paper/PAPER_FACTS.md
     (R4, R5, D54, R6, R17, R3b, M59, M43, M44), and each is still quoted in the brief's section 8; added needles
     cover every other fact the brief's section 6 cites for a text row; the range 1.0-20.2% is re-derived from
     R4 (the smallest and largest of the five changes against the deciding reference).
  2. Before drawing: every text row drawn, joined over its lines, equals the brief's section 6 table (text,
     fact IDs and word count: 48 words in the picture, 39 in the result line).
  3. After drawing: layout check (every text inside its box or zone and inside the canvas; no text overlaps
     another text or a mark it does not belong to; every font >= 11 pt; block titles 12 pt bold; result line
     11 pt bold; no "graphical abstract" or other banned string in the image); and the flow-line check (the
     seasonal-normal box, both zero lines and the anchor branches at least 1.5 mm off the arrows' line; the line
     level with the gap between block A's first two rows and between the two weight charts; the key swatch inside
     the note's zone; the mask hatching covers all six trees and stays clear of the masked row's ellipsis).
  4. After saving: canvas 2000 x 800 px; TIFF RGB, LZW, 300 dpi; PDF fonts embedded as TrueType (Arial only).

Outputs (this folder): ga.pdf (vector, fonts embedded), ga.tif (300 dpi, LZW), ga.png (preview only),
ga_data.csv (every drawn string with its position, fact IDs and checked needles; the needle checks; the
illustrative bar heights), renders/ga_491w.png and renders/ga_500x200.png (the 300-dpi raster scaled down with
a Lanczos filter, as a screen shows it). The PDF carries no creator, producer or date metadata.

Style (brief sections 3-4): canvas 2000 x 800 px at 300 dpi (169.3 x 67.7 mm, ratio 5:2), white; Figure 2's
colour roles, tint() and tree glyph (blue #2a78d6: trees; green #1baf7a: routers; orange #eb6834: skill guard;
grey #52514e / #efeeea: the normal and the decline target; #dddcd6 with dark hatching: masked trees); Arial,
pdf.fonttype 42; text always in ink #0b0b0b. The three hues, validated with the dataviz validator on all pairs
against the white surface: CVD worst dE 9.2 (#1baf7a / #eb6834, deutan), normal vision worst dE 24.0, PASS; the
green is below 3:1 contrast (2.82), so every green mark is outlined in ink and its box is titled. Identity is
never colour alone: masked = grey + 45-degree hatching + note + key swatch; the two locations' bars = solid vs
white stripes at 135 degrees (the mirror angle, so that 45-degree hatching means "masked" only).

Paths are built from this file's location (ROOT = parents[3]). Run: py -3.12 -I ga.py   (Python 3.12.10,
matplotlib 3.11.0, numpy, Pillow; reads two text files; writes only into this folder; no random draws).
"""
import csv
import itertools
import math
import re
import sys

sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
FACTS_MD = ROOT / "paper" / "PAPER_FACTS.md"
BRIEF_MD = ROOT / "paper" / "draft" / "submission" / "graphical_abstract_brief.md"
RENDERS = HERE / "renders"


def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()


def fail(msg):
    raise SystemExit("GA CHECK FAILED: " + msg)


for _p in (FACTS_MD, BRIEF_MD):
    if not _p.is_file():
        fail("missing input %s" % rel(_p))
FACTS_TEXT = FACTS_MD.read_text(encoding="utf-8")
BRIEF_TEXT = BRIEF_MD.read_text(encoding="utf-8")


def flat(s):
    return " ".join(s.split())


# ------------------------------------------------------------------------------------------------------------
# 1. Needle checks against PAPER_FACTS.md (before drawing)
# ------------------------------------------------------------------------------------------------------------
def fact_entry(fid):
    """The entry of fact `fid` in PAPER_FACTS.md: its '- **ID (' line and its indented continuation (fig1.py)."""
    lines = FACTS_TEXT.splitlines()
    pat = re.compile(r"^- \*\*" + re.escape(fid) + r" \(")
    for i, ln in enumerate(lines):
        if pat.match(ln):
            out = [ln]
            for nxt in lines[i + 1:]:
                if nxt.startswith("- **") or nxt.startswith("#"):
                    break
                out.append(nxt)
            return "\n".join(out)
    fail("fact %s not found in %s" % (fid, rel(FACTS_MD)))


# Numbers the image shows (all in the result line, the brief's text row 11), each from PAPER_FACTS.md:
#   "all 5 problems"      R5 ("all five HELPS"); R4 lists the five nowcast changes (asserted to be five below)
#   "1.0" and "20.2"      R4 ("fire -1.0%", "NDVI -20.2%": the smallest and largest change against the deciding
#                         reference, re-derived below); "barely" = R5 ("by a hair") and P29 (post hoc, t-based
#                         interval: HELPS becomes CANNOT TELL)
#   "2016"                D54 ("concentrated in 2016")
#   "6 of 9"              R6 ("of the 9 non-zero leads, 6 declined and 3 kept the model")
#   "each beaten by a naive baseline" (no number) R17 ("6 of 6 decline answers lost to a naive baseline")
#   "where predict-zero did better" (no number) R3b ("+2.36% vs PZ (worse)": the only nowcast that a naive
#                         baseline beat)
# The picture's other text carries no number. Pixel, dpi, mm and pt values are production specifications.

# The brief's section 8 needles, verbatim (origin "brief").
BRIEF_NEEDLES = [
    ("R4", "NDVI -20.2%"), ("R4", "fire -1.0%"),
    ("R5", "all five HELPS"), ("R5", "by a hair"),
    ("D54", "concentrated in 2016"),
    ("R6", "6 declined and 3 kept"),
    ("R17", "6 of 6 decline answers lost to a naive baseline"),
    ("R3b", "+2.36% vs PZ (worse)"),
    ("M59", "PM2.5, NDVI and fire"),
    ("M43", "strictly below"),
    ("M44", "declines to the decline target"),
]
# Needles added by this script for the other facts that the brief's section 6 cites for each text row (and P13,
# which honesty rule 4 cites for "the normal" on coral bleaching). Origin "added".
N = {   # key: (fact ID, needle)
    "M11": ("M11", "Each group trains 100 trees"),
    "M16": ("M16", "never sees the trees of its own overlap block"),
    "M17": ("M17", "Overlap blocks"),
    "M18": ("M18", "Masking the block makes every tree answer an out-of-group prediction"),
    "M21": ("M21", "h >= 24 gives per-unit"),
    "M22 ridge": ("M22", "The ridge penalties a_ctx and a_tree"),
    "M22 anchor": ("M22", "unpenalised anchor (its weight fitted)"),
    "M23": ("M23", "The tree weights are signed ridge coefficients, not convex mixture weights"),
    "M27": ("M27", "One pooled ridge per group"),
    "M28": ("M28", "For each scored row it builds a strict pool"),
    "M32": ("M32", "per season key"),
    "M44 adopt": ("M44", "The eligible arm with the lowest surface MAE is adopted"),
    "M45": ("M45", "a decline falls back to the arithmetic normal"),
    "M46": ("M46", "there is no separate holdout"),
    "M47": ("M47", "A guard bank at the lead's guard cut serves the guard"),
    "P13": ("P13", "The normal is the donor median"),
    "P29": ("P29", "HELPS becomes CANNOT TELL"),
    "R6 leads": ("R6", "of the 9 non-zero leads"),
}


def nd(key):
    """(fact ID, needle, origin) for an added needle."""
    return N[key] + ("added",)


def bd(fid, needle):
    if (fid, needle) not in BRIEF_NEEDLES:
        fail("not a brief needle: %s %r" % (fid, needle))
    return (fid, needle, "brief section 8")


# Needles per text row of the brief's section 6 (row 12 = the ellipsis glyphs of block A, not a text row).
ROW_NEEDLES = {
    1: [nd("M11"), nd("M16")],
    2: [nd("M16"), nd("M17"), nd("M18")],
    3: [nd("M21"), nd("M22 ridge"), bd("M59", "PM2.5, NDVI and fire")],
    4: [nd("M32")],
    5: [nd("M22 anchor"), nd("M23")],
    6: [nd("M21"), nd("M27"), nd("M28"), bd("M59", "PM2.5, NDVI and fire")],
    7: [bd("M43", "strictly below"), nd("M46"), nd("M47"), nd("P13")],
    8: [bd("M43", "strictly below")],
    9: [nd("M44 adopt")],
    10: [bd("M44", "declines to the decline target"), nd("M45"), nd("P13")],
    11: [bd("R4", "NDVI -20.2%"), bd("R4", "fire -1.0%"), bd("R5", "all five HELPS"), bd("R5", "by a hair"),
         nd("P29"), bd("D54", "concentrated in 2016"), bd("R6", "6 declined and 3 kept"), nd("R6 leads"),
         bd("R17", "6 of 6 decline answers lost to a naive baseline"), bd("R3b", "+2.36% vs PZ (worse)"),
         nd("P13")],
    12: [nd("M11")],
}

NEEDLE_ROWS = []   # for ga_data.csv
_seen = set()
for fid, needle in BRIEF_NEEDLES:
    if '"%s"' % needle not in BRIEF_TEXT:
        fail("brief section 8 no longer quotes the needle %r (%s); report it, do not change the text" % (needle, fid))
for row, items in ROW_NEEDLES.items():
    for fid, needle, origin in items:
        if (fid, needle) in _seen:
            continue
        _seen.add((fid, needle))
        if needle not in flat(fact_entry(fid)):
            fail("needle %r not in fact %s of %s" % (needle, fid, rel(FACTS_MD)))
        NEEDLE_ROWS.append((fid, needle, origin))
for fid, needle in BRIEF_NEEDLES:
    if (fid, needle) not in _seen:
        fail("brief needle %s %r is not attached to a text row" % (fid, needle))

# R4: the range shown is the smallest and largest of the five nowcast changes against the deciding reference.
_r4 = [ln for ln in fact_entry("R4").splitlines() if "Against the deciding reference" in ln]
if len(_r4) != 1:
    fail("R4: expected one 'Against the deciding reference' line")
_chg = dict((k, float(v)) for k, v in re.findall(r"(PM2\.5|NDVI|fire|defo|coral) -(\d+\.\d)%", _r4[0]))
if sorted(_chg) != sorted(["PM2.5", "NDVI", "fire", "defo", "coral"]):
    fail("R4: the five changes against the deciding reference were not all found: %r" % _chg)
LO_KEY, HI_KEY = min(_chg, key=_chg.get), max(_chg, key=_chg.get)
RANGE = "(%.1f–%.1f%%" % (_chg[LO_KEY], _chg[HI_KEY])
if (LO_KEY, HI_KEY) != ("fire", "NDVI"):
    fail("R4: the range ends are %s and %s, not burned fraction and NDVI" % (LO_KEY, HI_KEY))
N_PROBLEMS = len(_chg)

# ------------------------------------------------------------------------------------------------------------
# 2. Text rows: the brief's section 6 table, and the lines drawn for each row
# ------------------------------------------------------------------------------------------------------------
BRIEF_ROWS = {}
for m in re.finditer(r"^\| (\d+) \| ([^|]+?) \| ([^|]+?) \| (\d+) \| ([^|]+?) \|\s*$", BRIEF_TEXT, flags=re.M):
    BRIEF_ROWS[int(m.group(1))] = dict(where=m.group(2), text=m.group(3), words=int(m.group(4)),
                                       facts=m.group(5))
if sorted(BRIEF_ROWS) != list(range(1, 12)):
    fail("brief section 6: expected text rows 1-11, found %r" % sorted(BRIEF_ROWS))


def nwords(s):
    return len(re.findall(r"[A-Za-z0-9(][^\s]*", s))


for r_, d_ in BRIEF_ROWS.items():
    if nwords(d_["text"]) != d_["words"]:
        fail("brief row %d: %d words counted, %d listed" % (r_, nwords(d_["text"]), d_["words"]))
if sum(BRIEF_ROWS[r]["words"] for r in range(1, 11)) != 48 or BRIEF_ROWS[11]["words"] != 39:
    fail("brief word counts are no longer 48 in the picture and 39 in the result line")
for r_, items in ROW_NEEDLES.items():
    if r_ > 11:
        continue
    cited = set(re.findall(r"\b([A-Z]\d+[a-z]?)\b", BRIEF_ROWS[r_]["facts"]))
    covered = {fid for fid, _, _ in items}
    if cited - covered:
        fail("row %d: facts %s cited by the brief have no needle" % (r_, sorted(cited - covered)))

RESULT = BRIEF_ROWS[11]["text"]
if RANGE not in RESULT or ("all %d problems" % N_PROBLEMS) not in RESULT or "6 of 9" not in RESULT \
        or "2016" not in RESULT:
    fail("result line does not carry the checked numbers %r, all %d, 6 of 9, 2016" % (RANGE, N_PROBLEMS))

# Lines drawn per row (rows 6 and 11 are wrapped by measurement below). Row 8 is drawn as two labels.
LINES = {
    1: ["Trees from", "other regions"],
    2: ["own and overlapping", "regions masked"],
    3: ["Ridge weights over the trees"],
    4: ["seasonal", "normal"],
    5: ["anchor"],
    7: ["Trees beat", "the normal before", "the test?"],
    8: ["yes", "no"],
    9: ["forecast with", "the trees"],
    10: ["decline to", "the normal"],
}
for r_, ls in LINES.items():
    joined = " / ".join(ls) if r_ == 8 else " ".join(ls)
    if joined != BRIEF_ROWS[r_]["text"]:
        fail("row %d drawn as %r, brief says %r" % (r_, joined, BRIEF_ROWS[r_]["text"]))

# Strings the image must not carry: the Elsevier heading rule, honesty rule 7 (and the glossary's "decline", never
# "fall back"), and no text about the plotting tool or about AI (brief section 2; the word "AI" is checked apart).
BANNED = ["graphical abstract", "pre-registered", "preregistered", "leave-one-region-out", "fall back",
          "fallback", "matplotlib", "generative", "artificial intelligence", "agent"]

# ------------------------------------------------------------------------------------------------------------
# 3. Style (Figure 2's roles and helpers; brief sections 3-4)
# ------------------------------------------------------------------------------------------------------------
DPI = 300
PX_W, PX_H = 2000, 800
MM = 25.4 / DPI                         # mm per canvas pixel
W, H = PX_W * MM, PX_H * MM             # 169.33 x 67.73 mm

INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#52514e"


def tint(hex_colour, f):
    """Mix a colour with white: f = share of the colour (fig1.py)."""
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    mix = lambda c: int(round(255 - f * (255 - c)))  # noqa: E731
    return "#%02x%02x%02x" % (mix(r), mix(g), mix(b))


BLUE_T, ORANGE_T, AQUA_T, GREY_T = tint(BLUE, 0.16), tint(ORANGE, 0.16), tint(AQUA, 0.14), "#efeeea"
MASK_T = "#dddcd6"

FS = 11.0          # smallest text, pt (brief section 3)
FS_T = 12.0        # block titles, pt bold
LH = FS * 1.2 * 25.4 / 72      # line pitch of 11 pt text, mm (4.66)
LH_T = FS_T * 1.2 * 25.4 / 72  # line pitch of 12 pt text, mm (5.08)
PT = 25.4 / 72                 # mm per pt
LW_BOX = 1.0       # box edges, pt
LW_ARROW = 1.5     # ink arrows, pt
LW_ANCHOR = 2.8    # the thick grey anchor line, pt
HATCH_LW = 0.9     # hatch lines, pt

plt.rcParams.update({
    "font.family": "Arial",
    "mathtext.fontset": "custom",
    "mathtext.rm": "Arial",
    "mathtext.it": "Arial:italic",
    "mathtext.bf": "Arial:bold",
    "hatch.linewidth": HATCH_LW,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
})

fig = plt.figure(figsize=(PX_W / DPI, PX_H / DPI), dpi=DPI, facecolor="white")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.set_aspect("equal")
ax.axis("off")
REND = fig.canvas.get_renderer()


def Y(yt):
    """Top-based mm to axes y."""
    return H - yt


def text_width(s, size=FS, weight="normal"):
    t = fig.text(0, 0, s, fontsize=size, fontweight=weight)
    w = t.get_window_extent(renderer=REND).width * MM
    t.remove()
    return w


def text_height(size=FS, weight="normal"):
    """Height of one line's layout box (ascent + descent), mm."""
    t = fig.text(0, 0, "Hg", fontsize=size, fontweight=weight)
    h = t.get_window_extent(renderer=REND).height * MM
    t.remove()
    return h


H11, H12 = text_height(FS), text_height(FS_T, "bold")


TEXTS = []     # every text drawn: dict(artist, row, element, line, container, allow)
GRAPHICS = {}  # mark name -> polygon (top-based mm), for the overlap check
CONTAINERS = {}  # box or zone name -> polygon (top-based mm)


def rect_poly(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def put(x, yt, s, row, element, size=FS, weight="normal", ha="left", va="top", container=None, allow=(), line=0):
    t = ax.text(x, Y(yt), s, fontsize=size, fontweight=weight, ha=ha, va=va, color=INK, zorder=8)
    TEXTS.append(dict(artist=t, row=row, element=element, line=line, text=s, x=x, y=yt, ha=ha, va=va,
                      container=container, allow=set(allow) | ({container} if container else set())))
    return t


def box(name, x0, y0, x1, y1, fc, ec, lw=LW_BOX, r=1.2, z=1, container=True, hatch=None, hatchcolor=None):
    kw = dict(hatch=hatch, hatchcolor=hatchcolor) if hatch else {}
    p = FancyBboxPatch((x0, Y(y1)), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=%g" % r,
                       fc=fc, ec=ec, lw=lw, zorder=z, **kw)
    if hatch:
        p.set_hatch_linewidth(HATCH_LW)
    ax.add_patch(p)
    GRAPHICS[name] = rect_poly(x0, y0, x1, y1)
    if container:
        CONTAINERS[name] = rect_poly(x0, y0, x1, y1)
    return p


def rect(name, x0, y0, x1, y1, fc, ec, lw=0.7, z=3, hatch=None, hatchcolor=None, hatch_lw=HATCH_LW, register=True):
    kw = {}
    if hatch:
        kw = dict(hatch=hatch, hatchcolor=hatchcolor)
    p = Rectangle((x0, Y(y1)), x1 - x0, y1 - y0, fc=fc, ec=ec, lw=lw, zorder=z, **kw)
    if hatch:
        p.set_hatch_linewidth(hatch_lw)
    ax.add_patch(p)
    if register:
        GRAPHICS[name] = rect_poly(x0, y0, x1, y1)


def seg(name, x1, y1, x2, y2, color, lw, z=5):
    """A straight line (axis-aligned), registered as a thin rectangle of its own width."""
    ax.plot([x1, x2], [Y(y1), Y(y2)], color=color, lw=lw, zorder=z, solid_capstyle="butt")
    hw = lw * PT / 2
    GRAPHICS[name] = rect_poly(min(x1, x2) - hw, min(y1, y2) - hw, max(x1, x2) + hw, max(y1, y2) + hw)


def arrow(name, x1, y1, x2, y2, lw=LW_ARROW, ms=14.0):
    ax.add_patch(FancyArrowPatch((x1, Y(y1)), (x2, Y(y2)), arrowstyle="-|>", mutation_scale=ms, color=INK,
                                 lw=lw, shrinkA=0, shrinkB=0, zorder=6, joinstyle="miter", capstyle="butt"))
    hw = max(0.2 * ms, lw / 2) * PT      # head half-width ("-|>": head_width 0.2 x mutation scale)
    GRAPHICS[name] = rect_poly(min(x1, x2) - hw, min(y1, y2) - hw, max(x1, x2) + hw, max(y1, y2) + hw)


def tree_glyph(name, x, yt, w, h, fc, ec, z=4):
    """Figure 2's tree: triangle crown plus trunk; (x, yt) is the crown's top-left corner."""
    ax.add_patch(Polygon([(x, Y(yt + h * 0.8)), (x + w, Y(yt + h * 0.8)), (x + w / 2, Y(yt))], closed=True,
                         fc=fc, ec=ec, lw=0.6, zorder=z))
    ax.plot([x + w / 2, x + w / 2], [Y(yt + h * 0.8), Y(yt + h)], color=ec, lw=1.1, zorder=z,
            solid_capstyle="butt")
    GRAPHICS[name] = rect_poly(x, yt, x + w, yt + h)


# ------------------------------------------------------------------------------------------------------------
# 4. Layout (mm from the top-left corner; brief section 5, positions approximate; the layout check decides)
# ------------------------------------------------------------------------------------------------------------
X0, X1 = 4.0, W - 4.0          # left and right edges of the picture and of the result band
TOP = 2.0
BAND_Y0, BAND_Y1 = 48.0, 65.0  # result band (brief: y 48-65)

# Block A: trees from other regions
A_ROW_Y0, A_ROW_H, A_ROW_GAP = 12.6, 4.9, 1.0
TREE_W, TREE_H, TREE_P = 2.9, 3.7, 4.45
A_ROWS = [A_ROW_Y0 + i * (A_ROW_H + A_ROW_GAP) for i in range(4)]
A_MASKED = 2                   # the third row (brief: "The third row is hatched (masked)")
ELL = "…"
ell_w = text_width(ELL)
A_TREE_X0 = X0 + 1.5
A_TREES_X1 = A_TREE_X0 + 5 * TREE_P + TREE_W    # right edge of the sixth tree
A_ELL_X = A_TREES_X1 + 1.0
A_HATCH_X1 = A_ELL_X - 0.5     # the mask hatching covers the six trees and stops before the ellipsis
A_X1 = A_ELL_X + ell_w + 1.2   # right edge of the region rows
A_BOTTOM = A_ROWS[-1] + A_ROW_H
# Key swatch after the note's last line, with the masked row's look. The hatching repeats every 2.84 mm along x
# (measured on the 300-dpi canvas), so 6 mm shows two to three lines; at 4 mm one lone slash read as a "none" sign.
KEY_W, KEY_H, KEY_GAP = 6.0, 2.8, 1.2

# The flow line (see the header): level with the gap between block A's first two rows. Both ink arrows and the
# diamond's centre sit on it; block B's charts sit above and below it, and the seasonal-normal box below it.
Y_FLOW = A_ROWS[0] + A_ROW_H + A_ROW_GAP / 2
FLOW_CLEAR = 2.0               # the seasonal-normal box's top edge sits this far (mm) below the flow line
MIN_FLOW_CLEAR = 1.5           # the flow-line check's floor for every box, zero line and anchor branch of block B

# Block B: ridge weights over the trees
B_X0, B_X1, B_Y0 = 45.0, 109.5, TOP
BAR_W, BAR_P = 2.3, 3.05
# Illustrative signed weights (mm, + up), fixed constants, not values from a run (honesty rule 6, M23).
BARS = {1: [4.2, -2.4, 3.1, 1.2, -3.3, 2.2],
        2: [-1.7, 3.6, -3.0, 2.5, 1.0, 4.4]}
# Location 1's bars are solid; location 2's carry white stripes at 135 degrees (the back-slash hatch, three lines
# per unit like the mask's "///"), the mirror of block A's 45-degree mask hatching, which then means "masked" only.
BAR_HATCH = {1: None, 2: "\\\\\\"}
UP = max(max(v) for v in BARS.values())
DOWN = -min(min(v) for v in BARS.values())
B_TITLE_Y = B_Y0 + 1.0
Z1 = B_TITLE_Y + H12 + 1.4 + UP                 # zero line, location 1
NB_PAD_X, NB_PAD_Y = 1.6, 1.0
NB_H = H11 + LH + 2 * NB_PAD_Y                  # the seasonal-normal box: two lines
NB_Y0 = Y_FLOW + FLOW_CLEAR                     # its top edge, below the flow line
NB_Y1 = NB_Y0 + NB_H
Z2 = (NB_Y0 + NB_Y1) / 2                        # zero line, location 2: its anchor branch runs straight on into the
                                                # middle of the box (no jog), well below the flow line
if Z2 - UP - (Z1 + DOWN) < 2.0:
    fail("block B: the two weight charts are less than 2 mm apart")
if Z1 + DOWN > Y_FLOW - MIN_FLOW_CLEAR or Z2 - UP < Y_FLOW + MIN_FLOW_CLEAR:
    fail("block B: the flow line (%.2f mm) does not pass between the weight charts (%.2f-%.2f mm) with %.1f mm "
         "to spare" % (Y_FLOW, Z1 + DOWN, Z2 - UP, MIN_FLOW_CLEAR))
B_Y1 = max(Z2 + DOWN, NB_Y1) + 1.3
NOTE6_Y = B_Y1 + 1.3                            # top of note 6's first line
A_NOTE_Y = NOTE6_Y + LH                         # block A's note, on the baselines of note 6's second and third lines
if A_NOTE_Y < A_BOTTOM + 1.0:
    fail("block A: the note would start %.2f mm below the last row (minimum 1.0)" % (A_NOTE_Y - A_BOTTOM))
CH_X0 = B_X0 + 2.8
CH_X1 = CH_X0 + 5 * BAR_P + BAR_W
MK = 4.2                                        # location marker (grid cell) size
MK_X0 = CH_X1 + 1.5
SPINE_X = MK_X0 + MK + 2.9
anchor_w = text_width(LINES[5][0])
ANCHOR_X = SPINE_X + 1.4
nb_w = max(text_width(s) for s in LINES[4]) + 2 * NB_PAD_X
NB_X0 = ANCHOR_X + anchor_w + 1.3
NB_X1 = NB_X0 + nb_w
if NB_X1 > B_X1 - 1.6:
    fail("block B: the seasonal-normal box does not fit (right edge %.1f > %.1f)" % (NB_X1, B_X1 - 1.6))

# Block C: the skill guard. The yes box sits at the left edge of block C, the no box at the right edge, and the
# diamond is centred over the gap between them.
C_X0, C_X1 = 114.3, X1
DIA_A, DIA_B = 20.0, 13.5                       # half-width, half-height of the diamond
OUT_PAD_X, OUT_PAD_Y = 1.6, 1.3
OUT_H = H11 + LH + 2 * OUT_PAD_Y
yes_w = max(text_width(s) for s in LINES[9]) + 2 * OUT_PAD_X
no_w = max(text_width(s) for s in LINES[10]) + 2 * OUT_PAD_X
if C_X1 - C_X0 - yes_w - no_w < 2.5:
    fail("block C: the yes and no boxes do not fit side by side")
DIA_CX, DIA_CY = (C_X0 + yes_w + C_X1 - no_w) / 2, Y_FLOW
OUT_Y0 = DIA_CY + DIA_B + 1.4                   # top of the yes / no boxes, below the diamond's lower tip

# ------------------------------------------------------------------------------------------------------------
# 5. Drawing
# ------------------------------------------------------------------------------------------------------------
# Block A ------------------------------------------------------------------------------------------------
for i, s in enumerate(LINES[1]):
    put(X0, TOP + i * LH_T, s, 1, "block A title", size=FS_T, weight="bold", container="zone A title", line=i)
CONTAINERS["zone A title"] = rect_poly(X0 - 0.5, TOP - 0.5, B_X0 - 2.0, A_ROWS[0] - 0.3)
for k, yt in enumerate(A_ROWS):
    masked = k == A_MASKED
    name = "A row %d" % (k + 1)
    row = box(name, X0, yt, A_X1, yt + A_ROW_H, fc=MASK_T if masked else BLUE_T, ec=INK2 if masked else BLUE,
              lw=0.9, r=0.8, z=2)
    for j in range(6):
        tree_glyph("A row %d tree %d" % (k + 1, j + 1), A_TREE_X0 + j * TREE_P, yt + (A_ROW_H - TREE_H) / 2,
                   TREE_W, TREE_H, fc=MUTED if masked else BLUE, ec=MUTED if masked else BLUE)
    if masked:   # hatching over the masked region's six trees (Figure 2: #dddcd6 with dark hatching). It stops
        #          0.5 mm before the ellipsis, which stays readable, and is clipped to the row's rounded corners.
        _h = Rectangle((X0, Y(yt + A_ROW_H)), A_HATCH_X1 - X0, A_ROW_H, fc="none", ec="none", lw=0, zorder=5,
                       hatch="///", hatchcolor=INK2)
        _h.set_hatch_linewidth(HATCH_LW)
        ax.add_patch(_h)
        _h.set_clip_path(row)
        GRAPHICS[name + " mask hatching"] = rect_poly(X0, yt, A_HATCH_X1, yt + A_ROW_H)
    put(A_ELL_X, yt + A_ROW_H - 1.15, ELL, 12, "block A ellipsis (more trees)", va="baseline", container=name,
        line=k)
for i, s in enumerate(LINES[2]):
    put(X0, A_NOTE_Y + i * LH, s, 2, "block A note (masked row)", container="zone A note", line=i)
CONTAINERS["zone A note"] = rect_poly(X0 - 0.5, A_BOTTOM + 0.3, B_X0 - 2.0, BAND_Y0 - 0.5)
# Key: a swatch with the masked row's fill, edge and hatching after the note's last line, so that the note names
# the hatched row although it sits below the block (brief section 5: "with the note below the block").
KEY_X0 = X0 + text_width(LINES[2][-1]) + KEY_GAP
KEY_Y0 = A_NOTE_Y + (len(LINES[2]) - 1) * LH + 0.4 * H11 - KEY_H / 2    # centred on the capitals of that line
box("A note key", KEY_X0, KEY_Y0, KEY_X0 + KEY_W, KEY_Y0 + KEY_H, fc=MASK_T, ec=INK2, lw=0.9, r=0.4, z=3,
    container=False, hatch="///", hatchcolor=INK2)
arrow("arrow A to B", A_X1 + 1.0, Y_FLOW, B_X0, Y_FLOW)

# Block B ------------------------------------------------------------------------------------------------
box("B box", B_X0, B_Y0, B_X1, B_Y1, fc=AQUA_T, ec=AQUA, lw=LW_BOX, z=1)
put((B_X0 + B_X1) / 2, B_TITLE_Y, LINES[3][0], 3, "block B title", size=FS_T, weight="bold", ha="center",
    container="B box")
for loc, z0 in ((1, Z1), (2, Z2)):
    seg("B zero line %d" % loc, CH_X0 - 0.6, z0, CH_X1 + 0.6, z0, INK2, 0.8, z=4)
    for j, hgt in enumerate(BARS[loc]):
        bx = CH_X0 + j * BAR_P
        y_top, y_bot = (z0 - hgt, z0) if hgt > 0 else (z0, z0 - hgt)
        rect("B bar %d.%d" % (loc, j + 1), bx, y_top, bx + BAR_W, y_bot, fc=AQUA, ec=INK, lw=0.7, z=3,
             hatch=BAR_HATCH[loc], hatchcolor="white" if BAR_HATCH[loc] else None)
    # location marker: a small grid cell with a dot
    rect("B marker %d" % loc, MK_X0, z0 - MK / 2, MK_X0 + MK, z0 + MK / 2, fc="white", ec=INK, lw=1.0, z=4)
    ax.add_patch(Circle((MK_X0 + MK / 2, Y(z0)), 0.75, fc=INK, ec=INK, lw=0, zorder=5))
# the anchor: one thick grey line from both markers to the seasonal-normal box. Location 2's branch runs straight
# on into the middle of the box; location 1's branch joins it down the spine. Of all this, the flow line crosses
# only the spine.
_hw = LW_ANCHOR * PT / 2
ax.plot([MK_X0 + MK, SPINE_X, SPINE_X], [Y(Z1), Y(Z1), Y(Z2)], color=GREY, lw=LW_ANCHOR, zorder=4,
        solid_joinstyle="miter", solid_capstyle="butt")
GRAPHICS["B anchor branch 1"] = rect_poly(MK_X0 + MK, Z1 - _hw, SPINE_X + _hw, Z1 + _hw)
GRAPHICS["B anchor spine"] = rect_poly(SPINE_X - _hw, Z1 - _hw, SPINE_X + _hw, Z2 + _hw)
seg("B anchor line 2", MK_X0 + MK, Z2, NB_X0, Z2, GREY, LW_ANCHOR, z=4)
put(ANCHOR_X, Z2 - _hw - 0.45, LINES[5][0], 5, "block B anchor label", va="bottom", container="B box")
box("B normal box", NB_X0, NB_Y0, NB_X1, NB_Y1, fc=GREY_T, ec=GREY, lw=LW_BOX, r=1.0, z=3)
for i, s in enumerate(LINES[4]):
    put((NB_X0 + NB_X1) / 2, NB_Y0 + NB_PAD_Y + i * LH, s, 4, "block B seasonal normal", ha="center",
        container="B normal box", allow=("B box",), line=i)

# Note 6 under the box: wrapped by measurement, breaks after punctuation preferred, centred under block B.


def wrap(text, nlines, max_w, size, weight, keep=()):
    prot = text
    for ph in keep:
        if ph not in prot:
            fail("wrap: %r not in %r" % (ph, text))
        prot = prot.replace(ph, ph.replace(" ", " "))
    words = prot.split(" ")
    cache = {}

    def wid(s):
        if s not in cache:
            cache[s] = text_width(s.replace(" ", " "), size, weight)
        return cache[s]

    best = None
    for cuts in itertools.combinations(range(1, len(words)), nlines - 1):
        b = (0,) + cuts + (len(words),)
        ls = [" ".join(words[b[i]:b[i + 1]]) for i in range(nlines)]
        ws = [wid(s) for s in ls]
        if max(ws) > max_w:
            continue
        unpunct = sum(1 for s in ls[:-1] if s[-1] not in ",;:.")
        score = (unpunct, max(ws), sum((w_ - sum(ws) / nlines) ** 2 for w_ in ws))
        if best is None or score < best[0]:
            best = (score, [s.replace(" ", " ") for s in ls])
    if best is None:
        fail("wrap: %r does not fit in %d lines of %.1f mm" % (text, nlines, max_w))
    return best[1]


LINES[6] = wrap(BRIEF_ROWS[6]["text"], 3, B_X1 - B_X0, FS, "normal")
for i, s in enumerate(LINES[6]):
    put((B_X0 + B_X1) / 2, NOTE6_Y + i * LH, s, 6, "block B note (history length)", ha="center",
        container="zone B note", line=i)
CONTAINERS["zone B note"] = rect_poly(B_X0 - 0.5, B_Y1 + 0.3, B_X1 + 0.5, BAND_Y0 - 0.5)
arrow("arrow B to C", B_X1, DIA_CY, DIA_CX - DIA_A, DIA_CY)

# Block C ------------------------------------------------------------------------------------------------
DIAMOND = [(DIA_CX, DIA_CY - DIA_B), (DIA_CX + DIA_A, DIA_CY), (DIA_CX, DIA_CY + DIA_B), (DIA_CX - DIA_A, DIA_CY)]
ax.add_patch(Polygon([(x, Y(y)) for x, y in DIAMOND], closed=True, fc=ORANGE_T, ec=ORANGE, lw=1.2, zorder=2))
GRAPHICS["C diamond"] = DIAMOND
CONTAINERS["C diamond"] = DIAMOND
for i, s in enumerate(LINES[7]):
    put(DIA_CX, DIA_CY + (i - 1) * LH, s, 7, "block C skill guard (diamond)", ha="center", va="center",
        container="C diamond", line=i)
OUT_Y1 = OUT_Y0 + OUT_H
box("C yes box", C_X0, OUT_Y0, C_X0 + yes_w, OUT_Y1, fc=ORANGE_T, ec=ORANGE, lw=1.2, z=2)
box("C no box", C_X1 - no_w, OUT_Y0, C_X1, OUT_Y1, fc=GREY_T, ec=GREY, lw=1.2, z=2)
for i, s in enumerate(LINES[9]):
    put(C_X0 + yes_w / 2, OUT_Y0 + OUT_PAD_Y + i * LH, s, 9, "block C yes box", ha="center",
        container="C yes box", line=i)
for i, s in enumerate(LINES[10]):
    put(C_X1 - no_w / 2, OUT_Y0 + OUT_PAD_Y + i * LH, s, 10, "block C no box (decline)", ha="center",
        container="C no box", line=i)


def diamond_lower_edge(x):
    return DIA_CY + DIA_B * (1 - abs(x - DIA_CX) / DIA_A)


for lab, xa, side in (("yes", C_X0 + yes_w / 2, -1), ("no", C_X1 - no_w / 2, +1)):
    y_start = diamond_lower_edge(xa) + 0.25
    arrow("arrow %s" % lab, xa, y_start, xa, OUT_Y0)
    put(xa + side * 1.4, (y_start + OUT_Y0) / 2, lab, 8, "block C arrow label", ha="right" if side < 0 else "left",
        va="center", container="zone C", line=0 if lab == "yes" else 1)
CONTAINERS["zone C"] = rect_poly(C_X0 - 0.5, 0.5, C_X1 + 0.5, BAND_Y0 - 0.5)

# Result band (full width; no arrow into it: honesty rule 2) ---------------------------------------------------
box("band", X0, BAND_Y0, X1, BAND_Y1, fc=GREY_T, ec="none", lw=0, r=1.2, z=1)
KEEP = ["all 5 problems", "1.0–20.2% lower error),", "burned fraction,", "coral bleaching", "6 of 9",
        "naive baseline."]
LINES[11] = wrap(RESULT, 3, X1 - X0 - 2 * 3.0, FS, "bold", keep=KEEP)
_band_mid = (BAND_Y0 + BAND_Y1) / 2
for i, s in enumerate(LINES[11]):
    put((X0 + X1) / 2, _band_mid + (i - 1) * LH, s, 11, "result band", weight="bold", ha="center", va="center",
        container="band", line=i)

for r_ in (6, 11):
    if " ".join(LINES[r_]) != BRIEF_ROWS[r_]["text"]:
        fail("row %d wrapped text differs from the brief" % r_)

# ------------------------------------------------------------------------------------------------------------
# 6. Layout check (after drawing): inside box / zone and canvas, no overlaps, fonts, banned strings
# ------------------------------------------------------------------------------------------------------------
fig.canvas.draw()
inv = ax.transData.inverted()


def bbox_mm(t):
    bb = t.get_window_extent(renderer=REND)
    (x0, y0), (x1, y1) = inv.transform((bb.x0, bb.y0)), inv.transform((bb.x1, bb.y1))
    return x0, H - y1, x1, H - y0       # x0, top, x1, bottom (top-based mm)


def overlap(P, Q, tol=0.0):
    """Separating-axis test for two convex polygons; True if they overlap by more than tol (mm)."""
    for poly in (P, Q):
        n = len(poly)
        for i in range(n):
            (xa, ya), (xb, yb) = poly[i], poly[(i + 1) % n]
            nx, ny = yb - ya, xa - xb
            ln = math.hypot(nx, ny)
            if ln == 0:
                continue
            nx, ny = nx / ln, ny / ln
            pa = [nx * x + ny * y for x, y in P]
            qa = [nx * x + ny * y for x, y in Q]
            if min(max(pa), max(qa)) - max(min(pa), min(qa)) <= tol:
                return False
    return True


def inside(P, poly, margin):
    """True if every vertex of P is inside convex `poly`, at least `margin` mm from each edge."""
    cx = sum(x for x, _ in poly) / len(poly)
    cy = sum(y for _, y in poly) / len(poly)
    n = len(poly)
    for i in range(n):
        (xa, ya), (xb, yb) = poly[i], poly[(i + 1) % n]
        nx, ny = yb - ya, xa - xb
        ln = math.hypot(nx, ny)
        nx, ny = nx / ln, ny / ln
        if nx * (cx - xa) + ny * (cy - ya) < 0:      # point the normal inwards
            nx, ny = -nx, -ny
        for x, y in P:
            if nx * (x - xa) + ny * (y - ya) < margin:
                return False
    return True


problems = []
for d in TEXTS:
    d["bbox"] = bbox_mm(d["artist"])
    d["poly"] = rect_poly(*d["bbox"])
    x0, y0, x1, y1 = d["bbox"]
    if x0 < 0.5 or y0 < 0.5 or x1 > W - 0.5 or y1 > H - 0.5:
        problems.append("off the canvas: %r" % d["text"])
    if d["container"] is None:
        problems.append("no box or zone given for %r" % d["text"])
    elif not inside(d["poly"], CONTAINERS[d["container"]], 0.3):
        problems.append("outside its box %s: %r (%.1f-%.1f x %.1f-%.1f mm)" % (d["container"], d["text"], x0, x1,
                                                                             y0, y1))
    for gname, gpoly in GRAPHICS.items():
        if gname in d["allow"]:
            continue
        if overlap(d["poly"], gpoly, tol=0.05):
            problems.append("text %r overlaps mark %s" % (d["text"], gname))
for i in range(len(TEXTS)):
    for j in range(i + 1, len(TEXTS)):
        if overlap(TEXTS[i]["poly"], TEXTS[j]["poly"], tol=0.0):
            problems.append("texts overlap: %r / %r" % (TEXTS[i]["text"], TEXTS[j]["text"]))
for gname, gpoly in GRAPHICS.items():
    if any(x < 0.5 or x > W - 0.5 or y < 0.5 or y > H - 0.5 for x, y in gpoly):
        problems.append("mark off the canvas: %s" % gname)
sizes = [d["artist"].get_fontsize() for d in TEXTS]
if min(sizes) < FS:
    problems.append("font below 11 pt: %.1f" % min(sizes))
for d in TEXTS:
    size, weight = d["artist"].get_fontsize(), d["artist"].get_fontweight()
    if d["row"] in (1, 3) and (size != FS_T or weight != "bold"):
        problems.append("block title not 12 pt bold: %r" % d["text"])
    if d["row"] == 11 and (size != FS or weight != "bold"):
        problems.append("result line not 11 pt bold: %r" % d["text"])
    if d["artist"].get_color() != INK:
        problems.append("text not in ink: %r" % d["text"])
drawn = " ".join(d["text"] for d in TEXTS)
for bad in BANNED:
    if bad in drawn.lower():
        problems.append("banned string in the image: %r" % bad)
if re.search(r"\bAI\b", drawn):
    problems.append("banned string in the image: 'AI'")
for r_ in range(1, 12):
    got = [d["text"] for d in sorted((d for d in TEXTS if d["row"] == r_), key=lambda d: d["line"])]
    want = BRIEF_ROWS[r_]["text"]
    joined = " / ".join(got) if r_ == 8 else " ".join(got)
    if joined != want:
        problems.append("row %d drawn %r, brief %r" % (r_, joined, want))
picture_words = sum(nwords(d["text"]) for d in TEXTS if d["row"] <= 10)
result_words = sum(nwords(d["text"]) for d in TEXTS if d["row"] == 11)
if (picture_words, result_words) != (48, 39):
    problems.append("word counts %d + %d, brief 48 + 39" % (picture_words, result_words))
# Flow-line check (header): no mark or text of block B within MIN_FLOW_CLEAR of the arrows' line, except the green
# box itself and the anchor spine that the line crosses; the line level with the gap between block A's first two
# rows; the diamond centred on it. Then the key swatch and the mask hatching.
for gname, gpoly in GRAPHICS.items():
    if not gname.startswith("B ") or gname in ("B box", "B anchor spine"):
        continue
    _ys = [y for _, y in gpoly]
    _gap = 0.0 if min(_ys) <= Y_FLOW <= max(_ys) else min(abs(min(_ys) - Y_FLOW), abs(max(_ys) - Y_FLOW))
    if _gap < MIN_FLOW_CLEAR:
        problems.append("flow line: mark %s is %.2f mm from it (minimum %.1f)" % (gname, _gap, MIN_FLOW_CLEAR))
for d in TEXTS:
    if d["row"] in (3, 4, 5):
        _y0, _y1 = d["bbox"][1], d["bbox"][3]
        _gap = 0.0 if _y0 <= Y_FLOW <= _y1 else min(abs(_y0 - Y_FLOW), abs(_y1 - Y_FLOW))
        if _gap < MIN_FLOW_CLEAR:
            problems.append("flow line: text %r is %.2f mm from it (minimum %.1f)" % (d["text"], _gap,
                                                                                      MIN_FLOW_CLEAR))
_shaft = LW_ARROW * PT / 2
if not (A_ROWS[0] + A_ROW_H <= Y_FLOW - _shaft and Y_FLOW + _shaft <= A_ROWS[1]):
    problems.append("flow line: the A -> B arrow is not level with the gap between block A's first two rows")
if DIA_CY != Y_FLOW:
    problems.append("flow line: the diamond is not centred on it")
if not inside(GRAPHICS["A note key"], CONTAINERS["zone A note"], 0.3):
    problems.append("the key swatch is outside block A's note zone")
if any(h and ("/" in h or "x" in h.lower()) for h in BAR_HATCH.values()):
    problems.append("a location's weight bars use the 45-degree hatching that marks masked trees")
if A_HATCH_X1 < A_TREES_X1 + 0.2:
    problems.append("the mask hatching does not cover all six trees of the masked row")
_ell = [d for d in TEXTS if d["row"] == 12 and d["line"] == A_MASKED]
if len(_ell) != 1 or _ell[0]["bbox"][0] - A_HATCH_X1 < 0.3:
    problems.append("the mask hatching reaches the masked row's ellipsis")
print("flow line at %.2f mm: seasonal-normal box %.2f-%.2f mm, zero lines %.2f and %.2f mm, block B to %.2f mm; "
      "notes from %.2f mm (block A) and %.2f mm (note 6)" % (Y_FLOW, NB_Y0, NB_Y1, Z1, Z2, B_Y1, A_NOTE_Y, NOTE6_Y))
print("layout check: %d text(s), %d mark(s), %d problem(s); smallest font %.1f pt; words %d + %d; "
      "result line %d lines; note 6 %d lines"
      % (len(TEXTS), len(GRAPHICS), len(problems), min(sizes), picture_words, result_words, len(LINES[11]),
         len(LINES[6])))
if problems:
    fail("layout check:\n  " + "\n  ".join(problems))

# ------------------------------------------------------------------------------------------------------------
# 7. Save and verify the files
# ------------------------------------------------------------------------------------------------------------
RENDERS.mkdir(exist_ok=True)
fig.canvas.draw()
rgba = np.asarray(fig.canvas.buffer_rgba())
if rgba.shape != (PX_H, PX_W, 4) or int(rgba[..., 3].min()) != 255:
    fail("canvas is %r (alpha min %d), not %d x %d opaque" % (rgba.shape, int(rgba[..., 3].min()), PX_W, PX_H))
img = Image.fromarray(np.ascontiguousarray(rgba[..., :3]), "RGB")
img.save(HERE / "ga.tif", compression="tiff_lzw", dpi=(DPI, DPI))
img.save(HERE / "ga.png", dpi=(DPI, DPI))
fig.savefig(HERE / "ga.pdf", metadata={"Creator": None, "Producer": None, "CreationDate": None})
RENDER_SIZES = {"ga_491w.png": (491, round(PX_H * 491 / PX_W)), "ga_500x200.png": (500, 200)}
for fn, size in RENDER_SIZES.items():
    img.resize(size, Image.LANCZOS).save(RENDERS / fn)

with Image.open(HERE / "ga.tif") as t:
    t.load()
    dpi_ok = all(abs(float(v) - DPI) < 0.5 for v in t.info.get("dpi", (0, 0)))
    if t.size != (PX_W, PX_H) or t.mode != "RGB" or t.info.get("compression") != "tiff_lzw" or not dpi_ok:
        fail("ga.tif is %r %s %r dpi %r" % (t.size, t.mode, t.info.get("compression"), t.info.get("dpi")))
for fn, size in RENDER_SIZES.items():
    with Image.open(RENDERS / fn) as t:
        if t.size != size:
            fail("%s is %r, not %r" % (fn, t.size, size))
pdf = (HERE / "ga.pdf").read_bytes()
if b"/FontFile2" not in pdf or b"ArialMT" not in pdf or b"Arial-BoldMT" not in pdf or b"DejaVu" in pdf \
        or b"Type3" in pdf:
    fail("ga.pdf: fonts are not Arial / Arial Bold embedded as TrueType")
if b"atplotlib" in pdf:
    fail("ga.pdf: carries the plotting library's name")

# ------------------------------------------------------------------------------------------------------------
# 8. ga_data.csv: every drawn string with its position, facts and checked needles; the checks; the shapes
# ------------------------------------------------------------------------------------------------------------
FIELDS = ["kind", "text_row", "element", "line", "text", "font_pt", "weight", "anchor_x_mm", "anchor_y_mm",
          "ha", "va", "bbox_x0_mm", "bbox_y0_mm", "bbox_x1_mm", "bbox_y1_mm", "bbox_px", "box_or_zone",
          "fact_ids", "needles_checked", "source", "note"]


def needles_str(items):
    return " | ".join("%s: \"%s\" (%s)" % (f, n, o) for f, n, o in items)


with open(HERE / "ga_data.csv", "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=FIELDS)
    wr.writeheader()
    for d in sorted(TEXTS, key=lambda d: (d["row"], d["line"])):
        x0, y0, x1, y1 = d["bbox"]
        r_ = d["row"]
        wr.writerow({
            "kind": "drawn string", "text_row": r_ if r_ <= 11 else "", "element": d["element"],
            "line": d["line"] + 1, "text": d["text"], "font_pt": "%g" % d["artist"].get_fontsize(),
            "weight": d["artist"].get_fontweight(), "anchor_x_mm": "%.2f" % d["x"], "anchor_y_mm": "%.2f" % d["y"],
            "ha": d["ha"], "va": d["va"], "bbox_x0_mm": "%.2f" % x0, "bbox_y0_mm": "%.2f" % y0,
            "bbox_x1_mm": "%.2f" % x1, "bbox_y1_mm": "%.2f" % y1,
            "bbox_px": "%d,%d,%d,%d" % tuple(round(v / MM) for v in (x0, y0, x1, y1)),
            "box_or_zone": d["container"],
            "fact_ids": BRIEF_ROWS[r_]["facts"] if r_ <= 11 else "M11",
            "needles_checked": needles_str(ROW_NEEDLES[r_]),
            "source": "%s section 6, row %d" % (rel(BRIEF_MD), r_) if r_ <= 11
            else "%s section 5 (block A: rows of six trees with an ellipsis)" % rel(BRIEF_MD),
            "note": "position: mm from the top-left corner of the 169.3 x 67.7 mm canvas; bbox_px on the "
                    "2000 x 800 px canvas"})
    for fid, needle, origin in NEEDLE_ROWS:
        wr.writerow({"kind": "needle check", "fact_ids": fid, "needles_checked": needle,
                     "source": rel(FACTS_MD), "note": "found in the fact's entry (%s)" % origin})
    wr.writerow({"kind": "derived check", "text": RANGE + " lower error)", "fact_ids": "R4",
                 "needles_checked": "; ".join("%s -%.1f%%" % (k, v) for k, v in _chg.items()),
                 "source": rel(FACTS_MD) + " (R4, 'Against the deciding reference')",
                 "note": "range = smallest (burned fraction) and largest (NDVI) of the five nowcast changes "
                         "against the deciding reference; %d problems" % N_PROBLEMS})
    for loc, hs in BARS.items():
        wr.writerow({"kind": "illustrative shape (not data)", "element": "block B weight chart, location %d"
                     % loc, "text": "", "fact_ids": "M23",
                     "needles_checked": needles_str([nd("M23")]),
                     "note": "bar heights in mm, + up: %s; fixed constants, not values from a run; no ticks, no "
                             "numbers (honesty rule 6)%s" % (", ".join("%g" % v for v in hs),
                                                             "; white stripes at 135 degrees (block A's mask "
                                                             "hatching runs at 45 degrees)" if BAR_HATCH[loc] else
                                                             "; solid")})
    _k = GRAPHICS["A note key"]
    wr.writerow({"kind": "key swatch (no text)", "element": "block A note key", "fact_ids": BRIEF_ROWS[2]["facts"],
                 "bbox_x0_mm": "%.2f" % _k[0][0], "bbox_y0_mm": "%.2f" % _k[0][1],
                 "bbox_x1_mm": "%.2f" % _k[2][0], "bbox_y1_mm": "%.2f" % _k[2][1],
                 "bbox_px": "%d,%d,%d,%d" % tuple(round(v / MM) for v in (_k[0][0], _k[0][1], _k[2][0], _k[2][1])),
                 "box_or_zone": "zone A note", "needles_checked": needles_str(ROW_NEEDLES[2]),
                 "note": "the masked row's look (fill %s, edge %s, hatching at 45 degrees in %s) after the note's last "
                         "line, tying the note to the hatched third row; no words" % (MASK_T, INK2, INK2)})
    for fn in ("ga.pdf", "ga.tif", "ga.png") + tuple("renders/" + k for k in RENDER_SIZES):
        p = HERE / fn
        info = ""
        if fn.endswith((".png", ".tif")):
            with Image.open(p) as t:
                info = "%d x %d px" % t.size
        wr.writerow({"kind": "output file", "text": fn, "note": (info + "; " if info else "") +
                     {"ga.pdf": "vector, fonts embedded (TrueType)", "ga.tif": "300 dpi, LZW, RGB (upload)",
                      "ga.png": "preview only"}.get(fn, "300-dpi raster scaled with a Lanczos filter")})

print("needle checks passed: %d needles (%d from the brief's section 8); range %s from R4"
      % (len(NEEDLE_ROWS), sum(o != "added" for _, _, o in NEEDLE_ROWS), RANGE))
print("result line:", " | ".join(LINES[11]))
print("note 6:", " | ".join(LINES[6]))
print("wrote ga.pdf, ga.tif, ga.png, ga_data.csv, renders/%s" % ", renders/".join(RENDER_SIZES))
