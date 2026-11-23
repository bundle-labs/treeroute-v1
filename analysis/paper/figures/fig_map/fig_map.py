"""Figure 1: the study regions and the coral bleaching reef sites, one full-width map (190 mm). Round 4 (2026-11-11): figures renumbered by first citation: map (unnumbered) -> 1, 1 -> 2, 2 -> 3, 3 -> 4, 4 -> 5 (folders keep their names; paper/figures/FIGURE_NUMBERS.md). Tier 1 length plan (2026-11-12, ruling AU7): A1-07 and A1-08 shortened the caption, so two PHRASES entries changed (the open-outline sentence now ends 'coverage rule (named in Supplement S1.5).' and the reef-site sentence '188 in south Florida (Supplement S9.3).'); FACT_NEEDLES is unchanged, as the caption still cites the same facts; NAMES is kept as the key-to-name map of the six regions, which the caption no longer lists.

Owner ruling AT13 (2026-11-09): "A map of the study regions goes in the main text beside Table 1, with regions shaded
by problem and coral sites as dots".

What is drawn
  * Every one of the 133 panel regions, as the area its locations cover on a 0.25-degree drawing grid, clipped to the
    coastline: each footprint pixel is cut, on a 1/32-degree raster (about the panel's 4 km spacing), to the cells
    whose centre lies on GSHHG level-1 land. Only the sea cuts; lakes do not. One traced outline per region. All are
    NDVI regions and 127 are PM2.5 regions, so the shading separates the regions by the two other gridded problems:
    burned fraction and forest loss (blue), burned fraction only (orange), forest loss only (aqua), neither (grey).
    Line texture repeats that split without colour: 45-degree lines (rising to the right) for burned fraction,
    135-degree lines (falling) for forest loss, both for both, none for neither. A filled region's white gap is drawn
    only where it meets land or another region (on the coast the sea is already white).
  * The six regions without PM2.5 are drawn open (white inside, outline and texture in their category colour); their
    outline is traced after bridging gaps and inlets narrower than about 1 degree, so that it does not fill narrow
    channels with ink.
  * The reef sites of the 83 kept coral bleaching regions, each site (the package's key_unit, fact K1) once: filled
    dots in the 37 scored regions, open dots in the 46 training-only regions. Regions are drawn above the dots, so the
    small coastal regions that hold reef sites (south Florida above all) stay visible, and the clipping keeps the
    regions off the sea, where the dots are. The caption says how many dot centres the regions still cover, and the
    script stops if a coral bleaching region has more than half of its reef sites covered (MAX_COVERED_SHARE).
  * Coastlines (GSHHG 2.3.7, low resolution, level 1; lakes, levels 2-4, only if LAKES), a recessive graticule, and
    nothing else (no region names).
Design: chosen from two candidates (one map with four categories; five small-multiple maps, one per problem). The
single map keeps every region at twice the small multiples' scale and shows each region's whole membership at once;
the small multiples' strength, a cue that does not depend on colour, is carried here by the line textures (45 and
135 degrees only, used because the figure must survive greyscale print, as Figures 4 and 5 do) and by the open
outlines.

Inputs (read only; only the columns named)
  ROOT/engine/datasets/{pm25,ndvi,fire}/data/static/part-0.parquet      region, lat, lon
  D:/defo_features/static/part-0.parquet                                region, lat, lon
  ROOT/engine/datasets/coral/split.yaml                                 excluded and kept (seen_during_design) lists
  ROOT/engine/datasets/coral/dataset.yaml                               the package's lead-file pattern
  D:/treeroute/coral_build/coral_store/20261020_014201/lead_0.parquet   unit_id, group, lat, lon, mark (the package)
  D:/treeroute/coral_build/coral_data/visits.parquet                    site_key, group, lat, lon, mark (census and
                                                                        cross-checks only; nothing drawn from it)
  D:/coral/drivers/gshhg/gshhg-shp-2.3.7.zip                            GSHHS_shp/l/GSHHS_l_L1..L4.shp, README.TXT
                                                                        and LICENSE.TXT, read in memory
No label, sea-temperature or answer column is read (ruling AT7). The reef sites and their scored or training-only
status come from the package's lead-0 rows, which reproduce fact D52; the site id is the package's unit_id.

Outputs (next to this script): fig_map.pdf (vector, fonts embedded), fig_map.png (300 dpi), fig_map_data.csv (one row
per region, then one row per drawn reef site).

Checks (fail loud, SystemExit): every count drawn or stated is recounted from the inputs and checked against the
expected values below (existing facts cited by ID; new values are proposed in FACTS_TO_ADD.md, F1-F9), against the
caption (fig_map_caption.md, which must cite exactly the facts listed in FACT_NEEDLES), against FACTS_TO_ADD.md (key
phrases) and against the data file read back; every cited fact must contain its needle in paper/PAPER_FACTS.md;
layout (no text off the page or overlapping, every font at least 7 pt, text measured at print resolution); no tool
named and no e-mail address in the figure text, the caption or FACTS_TO_ADD.md; fonts embedded as TrueType in the
PDF; the PNG at 300 dpi. No random draws.

Run:  py -3.12 -I fig_map.py            (ROOT = this file's parents[3]; --root overrides it for a copy elsewhere)
"""
import sys

sys.dont_write_bytecode = True

import argparse  # noqa: E402
import math  # noqa: E402
import re  # noqa: E402
import struct  # noqa: E402
import zipfile  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection, PolyCollection  # noqa: E402
from matplotlib.patches import PathPatch, Rectangle  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(description="Draw the study-region map (Figure 1).")
ap.add_argument("--root", default=None, help="project root (default: this file's parents[3])")
ARGS = ap.parse_args()
ROOT = Path(ARGS.root).resolve() if ARGS.root else Path(__file__).resolve().parents[3]
FACTS_MD = ROOT / "paper" / "PAPER_FACTS.md"
CAPTION_MD = HERE / "fig_map_caption.md"
FACTS_TO_ADD_MD = HERE / "FACTS_TO_ADD.md"
STEM = "fig_map"


def need(cond, msg):
    """Fail loud (works under python -O too)."""
    if not cond:
        raise SystemExit("CHECK FAILED: " + msg)


need(FACTS_MD.is_file() and (ROOT / "engine" / "datasets").is_dir(), f"not the project root: {ROOT}")

STATIC = {
    "pm25": ROOT / "engine" / "datasets" / "pm25" / "data" / "static" / "part-0.parquet",
    "ndvi": ROOT / "engine" / "datasets" / "ndvi" / "data" / "static" / "part-0.parquet",
    "fire": ROOT / "engine" / "datasets" / "fire" / "data" / "static" / "part-0.parquet",
    "defo": Path("D:/defo_features/static/part-0.parquet"),
}
SPLIT = ROOT / "engine" / "datasets" / "coral" / "split.yaml"
CORAL_DATASET = ROOT / "engine" / "datasets" / "coral" / "dataset.yaml"
LEAD0 = Path("D:/treeroute/coral_build/coral_store/20261020_014201/lead_0.parquet")
VISITS = Path("D:/treeroute/coral_build/coral_data/visits.parquet")
GSHHG_ZIP = Path("D:/coral/drivers/gshhg/gshhg-shp-2.3.7.zip")
GSHHG_LEVELS = {lv: f"GSHHS_shp/l/GSHHS_l_L{lv}.shp" for lv in (1, 2, 3, 4)}  # land, lakes, islands, ponds
# Lakes: the brief named level 1 only, so levels 2-4 are read and counted but not drawn, and the caption says "Lakes are
# not drawn." True draws them (lakes white, islands in lakes as land, ponds white) and the caption must then credit
# "Coastlines and lakes". The lead's choice (FACTS_TO_ADD F8): with lakes the Caspian Sea and the large lakes show,
# but the lake outlines come from the older WDBII data, so the Aral Sea shows its full pre-1990 extent.
LAKES = False

# ---------------------------------------------------------------------------------------------------------------------
# 1. Facts. Every fact the caption cites (in its "facts:" lists) must be a key here, and every key must be cited; each
#    needle must occur in that fact's entry of PAPER_FACTS.md.
# ---------------------------------------------------------------------------------------------------------------------
FACT_NEEDLES = {
    "D1": ["The four grids read one panel: 133 regions"],
    "D5": ['the 133 panel regions were "chosen by the author to span biomes, land uses and hazards"',
           "a map goes in the main text (AT13)"],
    "D10": ["127 regions and 2,034,972 cells. 6 polar or edge regions were dropped by a whole-region coverage rule."],
    "D20": ["Fire covers 40 regions and 925,737 units"],
    "D24": ["How the 40 burned-fraction regions were chosen.", "They are a subset of the 133 panel regions (D5)."],
    "D32": ["133 regions, 2,289,236 cells"],
    "D42": ["42 forested regions, 591,809 cells"],
    "D46": ["How the 42 forest-loss regions were chosen."],
    "D51": ["14,839 visits.", "The lead-0 file has 13,694 rows in 94 groups."],
    "D52": ["83 groups (37 scored + 46 donor-only), 11 excluded, 11,338 train / 2,312 test visits"],
    "K1": ["key_unit is the reef site ('<ecoregion id>_<lat>_<lon>' at 4 decimals)"],
    "M6": ["46 coral groups are train-only donors (W1)"],
    "P11": ["PM2.5 127, NDVI 133, fire 40 and defo 42, with no exclusions",
            "Coral has 37 scored + 46 donor-only groups, with 11 excluded (V5)"],
    "D57": ["pm25+ndvi 60; pm25+ndvi+defo 28; pm25+ndvi+fire 26; pm25+ndvi+fire+defo 13; ndvi only 4; ndvi+fire 1; ndvi+defo 1 (sum 133)", "Burned fraction and forest loss 13; burned fraction only 27", "finnish_lapland: NDVI and burned fraction. tierra_del_fuego: NDVI and forest loss."],
    "D58": ["38,207 occupied pixels (38,469 region-pixel pairs)", "falkland_islands keeps 1,486 of its 2,880"],
    "D59": ["8,131 distinct reef sites in the 83 kept coral bleaching regions: 7,065 in the 37 scored regions, 1,066 in the 46 training-only regions", "229 of the 8,131 reef-site centres lie in a drawn region", "1,062 before the clipping"],
    "D60": ["8,572 site keys in 97 regions"],
    "D61": ["level 1: 5,706 records"],
}
# Expected values. Existing facts by ID; the "new" values (FACTS_TO_ADD.md F1-F8) are registered as PAPER_FACTS
# D57 (F1-F3), D58 (F4), D59 (F5, F7), D60 (F6) and D61 (F8); F9 lists drawing parameters.
EXPECT = dict(
    n_regions={"pm25": 127, "ndvi": 133, "fire": 40, "defo": 42},                  # P11, D10, D32/D1, D20/D24, D42/D46
    n_locations={"pm25": 2034972, "ndvi": 2289236, "fire": 925737, "defo": 591809},  # D10, D32, D20, D42
    combos={"pm25+ndvi": 60, "pm25+ndvi+defo": 28, "pm25+ndvi+fire": 26, "pm25+ndvi+fire+defo": 13,
            "ndvi": 4, "ndvi+fire": 1, "ndvi+defo": 1},                              # new F1
    category={"burned fraction and forest loss": 13, "burned fraction only": 27, "forest loss only": 29,
              "neither": 64},                                                        # new F2
    no_pm25={"alaska_north_slope": "ndvi", "canadian_arctic_nunavut": "ndvi", "taimyr_peninsula": "ndvi",
             "yamal_peninsula": "ndvi", "finnish_lapland": "ndvi+fire",
             "tierra_del_fuego": "ndvi+defo"},                                       # new F3 (count 6: D10)
    fire_subset=dict(regions=26, min_share=0.970, fire_locations_in_its_regions=929533),  # new F4
    footprint=dict(pixels=38207, region_pixels=38469, shared_pixels=262, shared_pairs=13,
                   largest_overlap=(("australian_mulga", "brigalow_belt"), 168)),     # new F4
    extent=dict(median=(3.04, 4.02), max=(9.04, 12.00), lat=(-55.00, 75.02)),         # new F4 (degrees, 2 decimals)
    short_sides={"namib_desert": 0.75, "falkland_islands": 0.95, "okavango_delta": 1.02, "brittany_france": 1.20,
                 "sundarbans": 1.43},                                                 # new F4 (all "neither")
    smallest_textured=("tongass_alaska", 1.52),                                       # new F4
    clip=dict(fine_per_pixel=8, kept_share_min=("falkland_islands", 1486, 2880), untouched=71,
              least_kept={"falkland_islands": 0.516, "greece_mainland": 0.704, "western_scotland": 0.765,
                          "tongass_alaska": 0.775, "new_zealand_north_island": 0.790},
              visible_share_min=("australian_mulga", 0.830)),                         # new F4
    coral_groups=dict(excluded=11, kept=83, scored=37, training_only=46),             # D52, P11, M6
    coral_census=dict(visits=14839, lead0_rows=13694, lead0_groups=94),               # D51
    coral_visits=dict(train=11338, test=2312),                                        # D52
    coral_sites=dict(all=8131, scored=7065, training_only=1066, with_test_visit=1262,
                     excluded_not_drawn=26, excluded_rows=44, lat=(-28.16, 34.10)),   # new F5 (1,066 also split.yaml)
    visits_file=dict(site_keys=8572, regions=97,
                     on_neither_list=["Darwin, north Australia", "Easter Island, south central Pacific",
                                      "South Java"],
                     kept_marks={"train": 12168, "test": 2581, "unused": 38},
                     extra_scored=["Gulf of Thailand"], gulf_visits={"train": 219, "test": 10, "unused": 2},
                     gulf_lead0={"train": 152}, kept_sites_train_test=8533),          # new F6
    covered=dict(all=229, by_region={"florida_everglades": 188, "pearl_river_delta": 24, "yucatan_peninsula": 9,
                                     "vietnam_central_highlands": 6, "new_guinea_papua": 1, "caatinga": 1},
                 by_coral_region={"Bahamas and Florida Keys": 188, "Hong Kong": 24,
                                  "Belize and west Caribbean": 9, "South Vietnam": 6,
                                  "Bismarck Sea, New Guinea": 1, "Brazil": 1},
                 group_sites={"Bahamas and Florida Keys": 2848, "Hong Kong": 80, "Belize and west Caribbean": 598,
                              "South Vietnam": 39, "Bismarck Sea, New Guinea": 25, "Brazil": 109},
                 most=("Hong Kong", 24, 80), unclipped=1062, unclipped_hong_kong=80),  # new F7
    gshhg_records={1: 5706, 2: 4367, 3: 506, 4: 11},                                  # new F8
    figure_mm=(190.0, 88.7),                                                          # F9 (drawing parameter)
)
MAX_COVERED_SHARE = 0.5   # no coral bleaching region may have more than half of its reef-site centres under regions
# Display names of the six regions without PM2.5. Since the Tier 1 length plan (2026-11-12) the caption no longer lists
# them (it points to the note after Supplement S1.5's register table, which uses these names), so no caption
# phrase uses NAMES or name_list; both are kept as the key-to-name map of that note.
NAMES = {"alaska_north_slope": "Alaska North Slope", "canadian_arctic_nunavut": "Canadian Arctic (Nunavut)",
         "taimyr_peninsula": "Taimyr Peninsula", "yamal_peninsula": "Yamal Peninsula",
         "finnish_lapland": "Finnish Lapland", "tierra_del_fuego": "Tierra del Fuego"}
GSHHG_REFERENCE = ("Wessel, P., and W. H. F. Smith (1996), A global, self-consistent, hierarchical, "
                   "high-resolution shoreline database, J. Geophys. Res., 101(B4), 8741\u20138743.")
# Words that would name the tool that wrote this script (figure text, caption, FACTS_TO_ADD.md).
BANNED_TOOL = re.compile(r"\b(AI|agents?|LLM|chatbot|language model|assistant|dataviz|skills?|Claude|Anthropic)\b",
                         re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def fact_entry(text, fid):
    lines = text.splitlines()
    pat = re.compile(r"^- \*\*" + re.escape(fid) + r" \(")
    for i, ln in enumerate(lines):
        if pat.match(ln):
            out = [ln]
            for nxt in lines[i + 1:]:
                if nxt.startswith("- **") or nxt.startswith("#"):
                    break
                out.append(nxt)
            return " ".join(" ".join(out).split())
    raise SystemExit(f"CHECK FAILED: fact {fid} not found in {FACTS_MD.name}")


facts_text = FACTS_MD.read_text(encoding="utf-8")
for fid, needles in FACT_NEEDLES.items():
    entry = fact_entry(facts_text, fid)
    for nd_ in needles:
        need(nd_ in entry, f"{nd_!r} not in fact {fid}")


def close_to(x, want, tol=0.005):
    return abs(float(x) - float(want)) <= tol


# ---------------------------------------------------------------------------------------------------------------------
# 2. Regions: membership, categories, footprints.
# ---------------------------------------------------------------------------------------------------------------------
tabs = {}
for k, p in STATIC.items():
    t = pq.read_table(p, columns=["region", "lat", "lon"]).to_pandas()
    need(len(t) == EXPECT["n_locations"][k], f"{k}: {len(t)} locations")
    need(t["region"].nunique() == EXPECT["n_regions"][k], f"{k}: {t['region'].nunique()} regions")
    need(t[["lat", "lon"]].notna().all().all(), f"{k}: missing coordinates")
    need(not t.duplicated(["region", "lat", "lon"]).any(), f"{k}: duplicated locations")
    tabs[k] = t
sets = {k: set(t["region"].unique()) for k, t in tabs.items()}
REGIONS = sorted(sets["ndvi"])
need(all(s <= sets["ndvi"] for s in sets.values()), "a region outside the NDVI panel")
combo = pd.Series({r: "+".join(k for k in ("pm25", "ndvi", "fire", "defo") if r in sets[k]) for r in REGIONS})
need(combo.value_counts().to_dict() == EXPECT["combos"], f"combinations {combo.value_counts().to_dict()}")
no_pm25 = sorted(set(REGIONS) - sets["pm25"])
need({r: combo[r] for r in no_pm25} == EXPECT["no_pm25"], f"regions without PM2.5 {no_pm25}")
need(len(no_pm25) == 6, "six regions without PM2.5 (D10)")

# the footprints use the NDVI locations; the other problems use the same locations (burned fraction: a subset)
nd = tabs["ndvi"]
key_nd = nd.assign(la=nd["lat"].round(6), lo=nd["lon"].round(6))[["region", "la", "lo"]]
for k in ("pm25", "fire", "defo"):
    t = tabs[k]
    hit = t.assign(la=t["lat"].round(6), lo=t["lon"].round(6))[["region", "la", "lo"]].merge(
        key_nd, on=["region", "la", "lo"], how="left", indicator=True)
    need(len(hit) == len(t) and (hit["_merge"] == "both").all(), f"{k}: a location that is not an NDVI location")
del key_nd, hit
n_nd = nd.groupby("region").size()
for k in ("pm25", "defo"):
    need((tabs[k].groupby("region").size() == n_nd[sorted(sets[k])]).all(), f"{k}: not all NDVI locations")
share = tabs["fire"].groupby("region").size() / n_nd[sorted(sets["fire"])]
EF = EXPECT["fire_subset"]
need(int((share < 1).sum()) == EF["regions"] and share.min() >= EF["min_share"]
     and round(share.min(), 4) == 0.9704, f"burned fraction: {int((share < 1).sum())} subset regions, "
                                          f"min share {share.min():.4f}")
need(int(n_nd[sorted(sets["fire"])].sum()) == EF["fire_locations_in_its_regions"], "NDVI locations of the fire regions")

CATS = ["burned fraction and forest loss", "burned fraction only", "forest loss only", "neither"]  # slot order


def category(r):
    f, d = r in sets["fire"], r in sets["defo"]
    return CATS[0] if f and d else CATS[1] if f else CATS[2] if d else CATS[3]


CAT = {r: category(r) for r in REGIONS}
need(pd.Series(CAT).value_counts().to_dict() == EXPECT["category"], f"categories {pd.Series(CAT).value_counts()}")

g = nd.groupby("region")
reg = pd.DataFrame({"n_locations": g.size(), "centroid_lat": g["lat"].mean(), "centroid_lon": g["lon"].mean(),
                    "lat0": g["lat"].min(), "lat1": g["lat"].max(), "lon0": g["lon"].min(),
                    "lon1": g["lon"].max()}).loc[REGIONS]
need((reg.lon1 - reg.lon0).max() < 180, "a region crosses the antimeridian")
LON0, LON1, LAT0, LAT1 = -180.0, 180.0, -60.0, 80.0   # map crop (drawing parameter, F9)
need(reg.lat0.min() > LAT0 + 1 and reg.lat1.max() < LAT1 - 1, "a region outside the map's latitude crop")
# region extents (F4)
dlat, dlon = reg.lat1 - reg.lat0, reg.lon1 - reg.lon0
EE = EXPECT["extent"]
need(close_to(dlat.median(), EE["median"][0]) and close_to(dlon.median(), EE["median"][1])
     and close_to(dlat.max(), EE["max"][0]) and close_to(dlon.max(), EE["max"][1])
     and close_to(reg.lat0.min(), EE["lat"][0]) and close_to(reg.lat1.max(), EE["lat"][1]),
     f"region extents {dlat.median():.4f} x {dlon.median():.4f}, max {dlat.max():.4f} x {dlon.max():.4f}")
short = np.minimum(dlat, dlon).sort_values(kind="stable")
need(list(short.index[:5]) == list(EXPECT["short_sides"])
     and all(close_to(short[r], v) for r, v in EXPECT["short_sides"].items())
     and all(CAT[r] == CATS[3] for r in short.index[:5]), f"smallest regions {short.head(5).round(4).to_dict()}")
tex_first = next(r for r in short.index if CAT[r] != CATS[3])
need(tex_first == EXPECT["smallest_textured"][0] and close_to(short[tex_first], EXPECT["smallest_textured"][1]),
     f"smallest textured region {tex_first}")

RES = 0.25  # drawing grid, degrees (F9)
ix = np.floor((nd["lon"].to_numpy() + 180.0) / RES).astype(np.int64)
iy = np.floor((nd["lat"].to_numpy() + 90.0) / RES).astype(np.int64)
pix = pd.DataFrame({"region": nd["region"].to_numpy(), "ix": ix, "iy": iy}).drop_duplicates()
need(set(pix.region) == set(REGIONS), "a region without pixels")
EP = EXPECT["footprint"]
per_pixel = pix.groupby(["ix", "iy"]).region.agg(list)
shared = per_pixel[per_pixel.map(len) > 1].map(lambda v: tuple(sorted(v))).value_counts()
need(len(pix) == EP["region_pixels"] and len(per_pixel) == EP["pixels"]
     and int(shared.sum()) == EP["shared_pixels"] and per_pixel.map(len).max() == 2
     and len(shared) == EP["shared_pairs"] and (shared.index[0], int(shared.iloc[0])) == EP["largest_overlap"],
     f"footprint pixels {len(pix)} / {len(per_pixel)}, shared {int(shared.sum())} in {len(shared)} pairs")
NPIX = pix.groupby("region").size()


def trace_mask(M):
    """Outline of the True cells of a boolean grid M[row j, column i] as closed rings of cell-corner indices (i, j),
    interior on the left: outer rings counter-clockwise, holes clockwise. Two cells that touch only at a corner stay
    apart (the left-most turn is taken at such a pinch vertex)."""
    P = np.pad(M, 1)
    C = P[1:-1, 1:-1]
    out = {}
    for mask, (a0, b0, a1, b1) in ((C & ~P[:-2, 1:-1], (0, 0, 1, 0)),     # bottom edge (no cell below)
                                   (C & ~P[1:-1, 2:], (1, 0, 1, 1)),      # right edge
                                   (C & ~P[2:, 1:-1], (1, 1, 0, 1)),      # top edge
                                   (C & ~P[1:-1, :-2], (0, 1, 0, 0))):    # left edge
        jj, ii = np.nonzero(mask)
        for i, j in zip(ii.tolist(), jj.tolist()):
            out.setdefault((i + a0, j + b0), []).append((i + a1, j + b1))
    rings = []
    while out:
        start = min(out)
        ring, cur, d_in = [start], start, None
        while True:
            nxts = out[cur]
            if len(nxts) > 1 and d_in is not None:
                # pinch vertex (two cells touching at a corner): take the left-most turn, consistently
                def turn(b):
                    d = (b[0] - cur[0], b[1] - cur[1])
                    return -(d_in[0] * d[1] - d_in[1] * d[0])
                nxts.sort(key=turn)
            nxt = nxts.pop(0)
            if not nxts:
                del out[cur]
            d_in = (nxt[0] - cur[0], nxt[1] - cur[1])
            if nxt == start:
                break
            ring.append(nxt)
            cur = nxt
        keep = []
        n = len(ring)
        for k in range(n):
            a, b, c = ring[k - 1], ring[k], ring[(k + 1) % n]
            if (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) != 0:
                keep.append(b)
        rings.append(keep)
    return rings


# ---------------------------------------------------------------------------------------------------------------------
# 3. Coral bleaching reef sites: the package's lead-0 rows of the 83 kept regions (key columns only); a reef site is the
#    package's unit_id (K1). visits.parquet is read for the census (D51) and the cross-checks of F5 and F6 only. (Its
#    own marks would give a 38th scored region, Gulf of Thailand, whose 10 test-marked survey visits are not in the
#    lead files, and 402 reef sites the package never uses; F6.)
# ---------------------------------------------------------------------------------------------------------------------
excluded, kept, sec = [], [], None
split_text = SPLIT.read_text(encoding="utf-8")
for ln in split_text.splitlines():
    if ln.startswith("excluded:"):
        sec = "ex"
    elif ln.startswith("seen_during_design:"):
        sec = "kept"
    elif ln.startswith("#") or not ln.strip():
        continue
    elif sec == "ex" and ln.startswith("  "):
        excluded.append(ln.strip().split(":", 1)[0])
    elif sec == "kept" and ln.startswith("- "):
        kept.append(ln[2:].strip())
    else:
        raise SystemExit(f"CHECK FAILED: split.yaml: unexpected line {ln!r}")
EG = EXPECT["coral_groups"]
need(len(excluded) == EG["excluded"] and len(set(excluded)) == len(excluded), f"{len(excluded)} excluded regions")
need(len(kept) == EG["kept"] and len(set(kept)) == len(kept), f"{len(kept)} kept regions")
need(not set(kept) & set(excluded), "a region both kept and excluded")
header = " ".join(split_text.replace("#", " ").split())
need("After V5: 83 groups (37 scored + 46 donor-only), 11,338 train and 2,312 test visits" in header,
     "split.yaml header changed")
need("1,874 train visits (1,066 sites" in header, "split.yaml header: training-only reef sites")
m = re.search(r"target:\s*'([^']+)'", CORAL_DATASET.read_text(encoding="utf-8"))
need(m is not None and m.group(1).replace("{lead}", "0") == LEAD0.as_posix(), "the coral package's lead files moved")

EC0 = EXPECT["coral_census"]
l0 = pq.read_table(LEAD0, columns=["unit_id", "group", "lat", "lon", "mark"]).to_pandas()
need(len(l0) == EC0["lead0_rows"] and l0["group"].nunique() == EC0["lead0_groups"], "lead-0 census (D51)")
need(l0[["unit_id", "group", "lat", "lon", "mark"]].notna().all().all(), "lead-0: missing key values")
need(set(l0["group"]) == set(kept) | set(excluded), "lead-0 regions differ from split.yaml")
l0k = l0[l0["group"].isin(kept)]
need(l0k["mark"].value_counts().to_dict() == EXPECT["coral_visits"], f"marks {l0k['mark'].value_counts().to_dict()}")
scored_groups = set(l0k.loc[l0k["mark"] == "test", "group"])
need(len(scored_groups) == EG["scored"], f"{len(scored_groups)} scored regions")
need(len(set(kept) - scored_groups) == EG["training_only"], "training-only regions")
l0k = l0k.assign(la=l0k["lat"].round(6), lo=l0k["lon"].round(6))
sites = l0k.groupby("unit_id").agg(lat=("lat", "first"), lon=("lon", "first"), la=("la", "first"),
                                   lo=("lo", "first"), group=("group", "first"), n_groups=("group", "nunique"),
                                   n_la=("la", "nunique"), n_lo=("lo", "nunique"),
                                   has_test=("mark", lambda s: bool((s == "test").any()))).reset_index()
need((sites.n_groups == 1).all() and (sites.n_la == 1).all() and (sites.n_lo == 1).all(),
     "a unit_id with two regions or two positions")
need(not sites.duplicated(["la", "lo"]).any(), "two unit_ids at one position (6 decimals)")
need(all(u.endswith(f"_{a:.4f}_{b:.4f}") for u, a, b in zip(sites.unit_id, sites.lat, sites.lon)),
     "unit_id is not '<ecoregion id>_<lat>_<lon>' at 4 decimals (K1)")
sites["status"] = np.where(sites["group"].isin(scored_groups), "scored", "training-only")
sites = sites.sort_values("unit_id").reset_index(drop=True)
ES = EXPECT["coral_sites"]
need(len(sites) == ES["all"], f"{len(sites)} reef sites")
need(int((sites.status == "scored").sum()) == ES["scored"], "reef sites in scored regions")
need(int((sites.status == "training-only").sum()) == ES["training_only"], "reef sites in training-only regions")
need(int(sites.has_test.sum()) == ES["with_test_visit"], "reef sites with a test visit")
need(close_to(sites.lat.min(), ES["lat"][0]) and close_to(sites.lat.max(), ES["lat"][1]), "reef-site latitudes")
l0x = l0[l0["group"].isin(excluded)]
need(len(l0x) == ES["excluded_rows"] and l0x.groupby([l0x["lat"].round(6), l0x["lon"].round(6)]).ngroups
     == ES["excluded_not_drawn"], "reef sites of the excluded regions")
need(sites.lat.between(LAT0, LAT1).all() and sites.lon.between(LON0, LON1).all(), "a reef site off the map")

# visits.parquet: census (D51) and cross-checks (F5: every reef site is one site_key of the same region; F6)
v = pq.read_table(VISITS, columns=["site_key", "group", "lat", "lon", "mark"]).to_pandas()
EV = EXPECT["visits_file"]
need(len(v) == EC0["visits"], "visits.parquet row count (D51)")
need(v.site_key.nunique() == EV["site_keys"] and v.group.nunique() == EV["regions"], "visits.parquet: keys, regions")
need(sorted(set(v.group) - set(kept) - set(excluded)) == EV["on_neither_list"], "visits.parquet: regions on no list")
vk = v[v.group.isin(kept)]
need(vk.mark.value_counts().to_dict() == EV["kept_marks"], f"visits.parquet marks {vk.mark.value_counts().to_dict()}")
need(sorted(set(vk.loc[vk.mark == "test", "group"]) - scored_groups) == EV["extra_scored"]
     and scored_groups <= set(vk.loc[vk.mark == "test", "group"]), "visits.parquet: scored regions")
need(v.loc[v.group == "Gulf of Thailand", "mark"].value_counts().to_dict() == EV["gulf_visits"]
     and l0.loc[l0.group == "Gulf of Thailand", "mark"].value_counts().to_dict() == EV["gulf_lead0"], "Gulf of Thailand")
vt = vk[vk.mark.isin(["train", "test"])]
n_vt = vt.assign(la=vt.lat.round(6), lo=vt.lon.round(6)).drop_duplicates(["la", "lo"]).shape[0]
need(n_vt == EV["kept_sites_train_test"], f"visits.parquet: {n_vt} reef sites with a train or test visit")
vs = v.assign(la=v["lat"].round(6), lo=v["lon"].round(6))[["site_key", "group", "la", "lo"]].drop_duplicates()
need(not vs.duplicated(["la", "lo"]).any() and not vs.duplicated(["site_key"]).any(), "site keys not one-to-one")
xs = sites[["la", "lo", "group"]].merge(vs, on=["la", "lo"], how="left", suffixes=("", "_v"), validate="one_to_one")
need(xs.site_key.notna().all() and (xs.group == xs.group_v).all(), "a reef site that is not a visits.parquet site")
del v, vk, vt, vs, xs

# ---------------------------------------------------------------------------------------------------------------------
# 4. Coastlines: GSHHG 2.3.7, low resolution, levels 1-4 read from the zip in memory and counted (levels 2-4, the lakes,
#    drawn only if LAKES). The footprints are clipped to level-1 land on a fine raster (cell centre inside a level-1
#    polygon), so they stay off the sea; lakes never clip.
# ---------------------------------------------------------------------------------------------------------------------
def read_polygons(shp, member):
    need(struct.unpack(">i", shp[0:4])[0] == 9994, f"{member}: not a shapefile")
    need(struct.unpack(">i", shp[24:28])[0] * 2 == len(shp), f"{member}: shapefile length")
    version, stype = struct.unpack("<ii", shp[28:36])
    need(version == 1000 and stype == 5, f"{member}: not a polygon shapefile")
    rings, n_rec, off = [], 0, 100
    while off < len(shp):
        _, clen = struct.unpack(">ii", shp[off:off + 8])
        c = shp[off + 8: off + 8 + 2 * clen]
        t = struct.unpack("<i", c[:4])[0]
        n_rec += 1
        need(t == 5, f"{member} record {n_rec}: shape type {t}, not a polygon")
        nparts, npts = struct.unpack("<ii", c[36:44])
        parts = list(struct.unpack(f"<{nparts}i", c[44:44 + 4 * nparts])) + [npts]
        xy = np.frombuffer(c, dtype="<f8", count=2 * npts, offset=44 + 4 * nparts).reshape(npts, 2)
        for a, b in zip(parts[:-1], parts[1:]):
            rings.append(xy[a:b])
        off += 8 + 2 * clen
    need(off == len(shp), f"{member}: records do not end at the file end")
    return rings, n_rec


with zipfile.ZipFile(GSHHG_ZIP) as z:
    GSHHG = {lv: read_polygons(z.read(mem), mem) for lv, mem in GSHHG_LEVELS.items()}
    README = z.read("README.TXT").decode("utf-8")
    LICENCE = z.read("LICENSE.TXT").decode("utf-8")
need({lv: n for lv, (_, n) in GSHHG.items()} == EXPECT["gshhg_records"], "GSHHG record counts")
need("Version 2.3.7 June 15, 2017" in README and "Distributed under the Lesser GNU Public License" in README,
     "GSHHG README: version or licence line changed")
need(GSHHG_REFERENCE in " ".join(README.split()), "GSHHG README: the reference changed")
need("GNU Lesser General Public" in LICENCE and "License (LGPL) version 3 or later" in " ".join(LICENCE.split()),
     "GSHHG LICENSE.TXT changed")
LAND = GSHHG[1][0]
for lv, (rings, _) in GSHHG.items():
    a = np.concatenate(rings)
    need(a[:, 0].min() >= -180 and a[:, 0].max() <= 180 and np.abs(a[:, 1]).max() <= 90, f"GSHHG L{lv} extent")
    need(all(len(r) >= 4 and np.array_equal(r[0], r[-1]) for r in rings), f"GSHHG L{lv}: a ring is not closed")


def land_raster(rings, lon0, lat0, nx, ny, step):
    """Cells of a lon/lat raster (rows from lat0 north, columns from lon0 east, cell size step) whose centre lies
    inside an odd number of the rings: an even-odd scanline fill, exact for the cell centres."""
    X0 = np.concatenate([r[:-1, 0] for r in rings])
    Y0 = np.concatenate([r[:-1, 1] for r in rings])
    X1 = np.concatenate([r[1:, 0] for r in rings])
    Y1 = np.concatenate([r[1:, 1] for r in rings])
    lo, hi = np.minimum(Y0, Y1), np.maximum(Y0, Y1)
    # an edge crosses row k when lo <= y_k < hi, y_k = lat0 + (k + 0.5) step (half-open: a closed ring crosses
    # every row an even number of times)
    k0 = np.clip(np.ceil((lo - lat0) / step - 0.5).astype(np.int64), 0, ny)
    k1 = np.clip(np.ceil((hi - lat0) / step - 0.5).astype(np.int64), 0, ny)     # exclusive
    n = np.maximum(k1 - k0, 0)
    e = np.repeat(np.arange(len(X0)), n)
    k = np.repeat(k0, n) + np.arange(int(n.sum())) - np.repeat(np.cumsum(n) - n, n)
    yc = lat0 + (k + 0.5) * step
    xc = X0[e] + (yc - Y0[e]) * (X1[e] - X0[e]) / (Y1[e] - Y0[e])
    o = np.lexsort((xc, k))
    k, xc = k[o], xc[o]
    need(len(k) % 2 == 0 and (k[0::2] == k[1::2]).all(), "land raster: a row with an odd number of crossings")
    c0 = np.clip(np.ceil((xc[0::2] - lon0) / step - 0.5).astype(np.int64), 0, nx)
    c1 = np.clip(np.ceil((xc[1::2] - lon0) / step - 0.5).astype(np.int64), 0, nx)  # exclusive
    diff = np.zeros((ny, nx + 1), np.int8)
    np.add.at(diff, (k[0::2], c0), 1)
    np.add.at(diff, (k[0::2], c1), -1)
    out = np.cumsum(diff, axis=1, dtype=np.int8)[:, :nx]
    need(out.min() >= 0 and out.max() <= 1, "land raster: overlapping spans")
    return out == 1


SUB = EXPECT["clip"]["fine_per_pixel"]       # fine cells per footprint-pixel side: 1/32 degree (F9)
FINE = RES / SUB
NXF, NYF = int(round((LON1 - LON0) / FINE)), int(round((LAT1 - LAT0) / FINE))
LANDF = land_raster(LAND, LON0, LAT0, NXF, NYF, FINE)
J0 = int(round((LAT0 + 90.0) / RES))          # footprint row of the map's southern edge (footprint rows count from 90 S)

MASK, KEPT = {}, {}
for r, d in pix.groupby("region"):
    ix0, iy0 = int(d.ix.min()), int(d.iy.min())
    C = np.zeros((int(d.iy.max()) - iy0 + 1, int(d.ix.max()) - ix0 + 1), bool)
    C[d.iy.to_numpy() - iy0, d.ix.to_numpy() - ix0] = True
    F = np.repeat(np.repeat(C, SUB, axis=0), SUB, axis=1)
    fi0, fj0 = ix0 * SUB, (iy0 - J0) * SUB
    need(fj0 >= 0 and fi0 >= 0 and fi0 + F.shape[1] <= NXF and fj0 + F.shape[0] <= NYF, f"{r}: off the raster")
    F &= LANDF[fj0:fj0 + F.shape[0], fi0:fi0 + F.shape[1]]
    need(F.any(), f"{r}: nothing left after clipping to the coastline")
    MASK[r] = (fi0, fj0, F)
    KEPT[r] = (int(F.sum()), int(C.sum()) * SUB * SUB)
kept_share = pd.Series({r: a / b for r, (a, b) in KEPT.items()}).sort_values(kind="stable")
r_min = kept_share.index[0]
need((r_min, *KEPT[r_min]) == EXPECT["clip"]["kept_share_min"], f"least kept after clipping: {r_min} {KEPT[r_min]}")
need(kept_share.head(5).round(3).to_dict() == EXPECT["clip"]["least_kept"]
     and int((kept_share == 1).sum()) == EXPECT["clip"]["untouched"],
     f"clipping: {kept_share.head(5).round(3).to_dict()}, {int((kept_share == 1).sum())} regions untouched")


def close_mask(M, rad):
    """Morphological closing (dilate, then erode) with a disc of radius rad cells: bridges gaps and inlets narrower
    than about 2 rad cells and leaves the rest of the shape as it was (the result stays inside M's bounding box)."""
    off = [(dj, di) for dj in range(-rad, rad + 1) for di in range(-rad, rad + 1) if di * di + dj * dj <= rad * rad]
    P = np.pad(M, 2 * rad)
    D = np.zeros_like(P)
    for dj, di in off:
        D |= np.roll(P, (dj, di), axis=(0, 1))
    E = np.ones_like(P)
    for dj, di in off:
        E &= np.roll(D, (dj, di), axis=(0, 1))
    out = E[2 * rad:-2 * rad, 2 * rad:-2 * rad]
    need(out.shape == M.shape and (out | ~M).all(), "closing lost cells")
    return out


# What is drawn: the clipped cells; for the six open regions (outline only, no fill colour) the clipped cells with gaps
# and inlets narrower than about 1 degree (0.5 mm at print, twice the outline) bridged, so that the outline does not
# fill narrow channels with ink (drawing only; F9).
OPEN_CLOSE = 2 * SUB   # closing radius, fine cells (0.5 degree)
DRAWN = {r: (MASK[r][0], MASK[r][1], close_mask(MASK[r][2], OPEN_CLOSE) if r in no_pm25 else MASK[r][2])
         for r in REGIONS}

# drawing order: larger footprints first, so a smaller region that overlaps a larger one stays on top
ORDER = sorted(REGIONS, key=lambda r: (-NPIX[r], r))


def window(a, b):
    """Overlap of the drawn masks of regions a and b: slices into a's and b's mask, or None."""
    (ai, aj, A), (bi, bj, B) = DRAWN[a], DRAWN[b]
    i0, i1 = max(ai, bi), min(ai + A.shape[1], bi + B.shape[1])
    j0, j1 = max(aj, bj), min(aj + A.shape[0], bj + B.shape[0])
    if i0 >= i1 or j0 >= j1:
        return None
    return (slice(j0 - aj, j1 - aj), slice(i0 - ai, i1 - ai)), (slice(j0 - bj, j1 - bj), slice(i0 - bi, i1 - bi))


visible = {}
for k, r in enumerate(ORDER):
    V = DRAWN[r][2].copy()
    for s in ORDER[k + 1:]:
        w = window(r, s)
        if w is not None:
            V[w[0]] &= ~DRAWN[s][2][w[1]]
    visible[r] = V.sum() / DRAWN[r][2].sum()
vis = pd.Series(visible)
print(f"clipping: least kept {r_min} {kept_share.min():.3f}; least visible {vis.idxmin()} {vis.min():.3f}")
need((vis.idxmin(), round(vis.min(), 3)) == EXPECT["clip"]["visible_share_min"],
     f"least visible region: {vis.idxmin()} {vis.min():.4f}")

# reef-site dots whose centre lies in a drawn (clipped) region: the regions are drawn above the dots
sfi = np.floor((sites.lon.to_numpy() - LON0) / FINE).astype(np.int64)
sfj = np.floor((sites.lat.to_numpy() - LAT0) / FINE).astype(np.int64)
n_cov = np.zeros(len(sites), np.int64)
top = np.full(len(sites), "", dtype=object)
for r in ORDER:
    fi0, fj0, F = DRAWN[r]
    li, lj = sfi - fi0, sfj - fj0
    inb = (li >= 0) & (li < F.shape[1]) & (lj >= 0) & (lj < F.shape[0])
    hitr = np.zeros(len(sites), bool)
    hitr[inb] = F[lj[inb], li[inb]]
    n_cov += hitr
    top[hitr] = r
need(n_cov.max() <= 1, "a reef site under two regions")
sites["covered_by_region"] = top
cov = sites.loc[sites.covered_by_region != "", "covered_by_region"].value_counts()
cov_g = sites.loc[sites.covered_by_region != "", "group"].value_counts()
EC = EXPECT["covered"]
need(int(cov.sum()) == EC["all"] and cov.to_dict() == EC["by_region"] and cov_g.to_dict() == EC["by_coral_region"],
     f"covered reef sites {cov.to_dict()} / {cov_g.to_dict()}")
n_site = sites.group.value_counts()
need(n_site[cov_g.index].to_dict() == EC["group_sites"], "reef sites of the coral bleaching regions with covered sites")
g_share = (cov_g / n_site[cov_g.index]).sort_values(ascending=False, kind="stable")
most = (g_share.index[0], int(cov_g[g_share.index[0]]), int(n_site[g_share.index[0]]))
need(most == EC["most"] and g_share.iloc[0] <= MAX_COVERED_SHARE,
     f"a coral bleaching region is mostly covered: {most}")
# before clipping (0.25-degree pixels only), for FACTS_TO_ADD F7
owner = {(i, j) for i, j in zip(pix.ix, pix.iy)}
unclipped = np.array([(int(math.floor((lo + 180.0) / RES)), int(math.floor((la + 90.0) / RES))) in owner
                      for la, lo in zip(sites.lat, sites.lon)])
need(int(unclipped.sum()) == EC["unclipped"] and int((unclipped & (sites.group == "Hong Kong")).sum())
     == EC["unclipped_hong_kong"] == n_site["Hong Kong"], f"{int(unclipped.sum())} reef sites under unclipped footprints")

# ---------------------------------------------------------------------------------------------------------------------
# 5. Style (as Figures 2, 4 and 5): Arial, 7 pt at print size, fonts embedded, text in ink only.
#    Region hues: the reference palette's first three categorical colours in slot order (blue, orange, aqua), checked
#    all pairs (a map) with a colour-difference check (OKLab Delta E x100, under the Machado et al. 2009 CVD
#    simulation; WCAG 2 contrast) against both surfaces the regions sit on, land #e8e7e1 and white: worst CVD dE 9.2
#    (deutan, aqua vs orange), worst normal-vision dE 24.0 (aqua vs blue); contrast below 3:1 for orange (2.58 on
#    land) and aqua (2.27 on land, 2.82 on white), so the legend, the textures and the data table (fig_map_data.csv)
#    carry the relief. "Neither" is the documented secondary ink #52514e (a neutral, not a slot): normal-vision
#    dE >= 21.8 against each hue. The land fill #e8e7e1 is a derived chrome value (between the palette's neutral
#    #f0efec and its gridline #e1e0d9), dark enough to part land from the white sea in print.
#    Texture (the print channel, 45 and 135 degrees only): white lines on filled regions, lines in the region's colour
#    on open ones. White, not the method's darker tone-on-tone step, because the palette documents no darker steps
#    for orange or aqua. Equal loudness: the crossed category has thinner, wider-spaced lines, so that all three
#    categories lose the same share of their colour to white (about 23.5%, asserted below). With the lines averaged
#    in, as the eye sees a texture it does not resolve, the worst pairs are normal-vision dE 14.1 (blue vs aqua) and
#    CVD dE 4.6 (orange vs aqua); where the lines are resolved, their direction carries the category (F9).
# ---------------------------------------------------------------------------------------------------------------------
INK, INK2, GRID, AXIS = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7"
LAND_FILL, OCEAN = "#e8e7e1", "#ffffff"
COLOUR = {CATS[0]: "#2a78d6", CATS[1]: "#eb6834", CATS[2]: "#1baf7a", CATS[3]: INK2}
# angles, line width (pt) and spacing perpendicular to the lines (mm)
TEXTURE = {CATS[0]: dict(angles=(45, 135), lw=0.25, gap=0.7), CATS[1]: dict(angles=(45,), lw=0.4, gap=0.6),
           CATS[2]: dict(angles=(135,), lw=0.4, gap=0.6), CATS[3]: dict(angles=(), lw=0.0, gap=1.0)}
plt.rcParams.update({
    "font.family": "Arial", "font.size": 7, "mathtext.fontset": "custom", "mathtext.rm": "Arial",
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none", "text.color": INK,
    "axes.unicode_minus": True,
})
MM = 1 / 25.4
PT = 25.4 / 72                        # mm per point
DPI = 300                             # print resolution: the figure is laid out and measured at it
FIG_W = 190.0                         # Elsevier full width, mm
ML, MR, MT = 8.0, 1.5, 1.0            # map margins, mm (the left margin holds the latitude labels)
MAP_W = FIG_W - ML - MR
SCALE = MAP_W / (LON1 - LON0)         # mm per degree
MAP_H = SCALE * (LAT1 - LAT0)
LONLAB_H = 4.0                        # longitude labels under the map, mm
LEG_H = 12.5                          # legend block, mm
FIG_H = MT + MAP_H + LONLAB_H + LEG_H + 1.0
need((FIG_W, round(FIG_H, 1)) == EXPECT["figure_mm"], f"figure {FIG_W} x {FIG_H:.2f} mm")
DOT_D = 1.7                           # reef-site dot diameter, pt
EDGE_LW = 0.35                        # white gap where a filled region meets land or another region, pt
OPEN_LW = 0.7                         # outline of an open region (no PM2.5), pt


def white_share(tx):
    c = tx["lw"] * PT / tx["gap"]
    return 1.0 - (1.0 - c) ** len(tx["angles"])


WHITE = {c: white_share(TEXTURE[c]) for c in CATS[:3]}
need(max(WHITE.values()) - min(WHITE.values()) <= 0.01, f"texture loudness differs: {WHITE}")


def hatch(x0, x1, y0, y1, step, angle):
    """Segments at 45 degrees (x = y + c, rising) or 135 degrees (x = -y + c, falling) covering the box
    [x0, x1] x [y0, y1], on a lattice anchored at 0 so that lines line up across regions; clipped later."""
    segs = []
    if angle == 45:
        c = math.floor((x0 - y1) / step) * step
        while c <= x1 - y0:
            segs.append([(y0 + c, y0), (y1 + c, y1)])
            c += step
    elif angle == 135:
        c = math.floor((x0 + y0) / step) * step
        while c <= x1 + y1:
            segs.append([(c - y0, y0), (c - y1, y1)])
            c += step
    else:
        raise SystemExit(f"CHECK FAILED: texture angle {angle}")
    return segs


def region_path(r):
    fi0, fj0, F = DRAWN[r]
    verts, codes = [], []
    for ring in trace_mask(F):
        pts = [(LON0 + (fi0 + i) * FINE, LAT0 + (fj0 + j) * FINE) for i, j in ring]
        verts += pts + [pts[0]]
        codes += [MPath.MOVETO] + [MPath.LINETO] * (len(pts) - 1) + [MPath.CLOSEPOLY]
    return MPath(np.array(verts), codes)


def runs(E):
    """Runs of True along each row of E: (row, first column, last column + 1)."""
    P = np.pad(E.astype(np.int8), ((0, 0), (1, 1)))
    d = np.diff(P, axis=1)
    js, i0 = np.nonzero(d == 1)
    je, i1 = np.nonzero(d == -1)
    need(np.array_equal(js, je), "run bookkeeping")
    return zip(js.tolist(), i0.tolist(), i1.tolist())


def gap_segments(r):
    """The edges of region r's drawn cells whose outside neighbour is land (or another region), merged into straight
    runs, in degrees. The white gap is drawn only there: on the coast the sea is already white, and a white line along a
    ragged coast would eat small island regions."""
    fi0, fj0, F = DRAWN[r]
    h, w = F.shape
    L = np.zeros((h + 2, w + 2), bool)                 # land status of the window and a one-cell border round it
    j_lo, j_hi = max(fj0 - 1, 0), min(fj0 + h + 1, NYF)
    i_lo, i_hi = max(fi0 - 1, 0), min(fi0 + w + 1, NXF)
    L[j_lo - fj0 + 1:j_hi - fj0 + 1, i_lo - fi0 + 1:i_hi - fi0 + 1] = LANDF[j_lo:j_hi, i_lo:i_hi]
    P = np.pad(F, 1)
    C = P[1:-1, 1:-1]
    X = lambda i: LON0 + (fi0 + i) * FINE  # noqa: E731
    Y = lambda j: LAT0 + (fj0 + j) * FINE  # noqa: E731
    segs = []
    for j, a, b in runs(C & ~P[:-2, 1:-1] & L[:-2, 1:-1]):      # bottom edges, outside cell below
        segs.append([(X(a), Y(j)), (X(b), Y(j))])
    for j, a, b in runs(C & ~P[2:, 1:-1] & L[2:, 1:-1]):        # top edges
        segs.append([(X(a), Y(j + 1)), (X(b), Y(j + 1))])
    for i, a, b in runs((C & ~P[1:-1, :-2] & L[1:-1, :-2]).T):  # left edges (columns as rows)
        segs.append([(X(i), Y(a)), (X(i), Y(b))])
    for i, a, b in runs((C & ~P[1:-1, 2:] & L[1:-1, 2:]).T):    # right edges
        segs.append([(X(i + 1), Y(a)), (X(i + 1), Y(b))])
    return segs


fig = plt.figure(figsize=(FIG_W * MM, FIG_H * MM), dpi=DPI)
fig.patch.set_facecolor("white")
map_bottom = FIG_H - MT - MAP_H
ax = fig.add_axes([ML / FIG_W, map_bottom / FIG_H, MAP_W / FIG_W, MAP_H / FIG_H])
ax.set_xlim(LON0, LON1)
ax.set_ylim(LAT0, LAT1)
ax.set_aspect("equal")
ax.axis("off")
ax.add_patch(Rectangle((LON0, LAT0), LON1 - LON0, LAT1 - LAT0, fc=OCEAN, ec="none", zorder=0))
for lon in range(-150, 180, 30):
    ax.plot([lon, lon], [LAT0, LAT1], color=GRID, lw=0.3, zorder=0.5, solid_capstyle="butt")
for lat in (-30, 0, 30, 60):
    ax.plot([LON0, LON1], [lat, lat], color=GRID, lw=0.3, zorder=0.5, solid_capstyle="butt")
# land; with LAKES also lakes (white), islands in lakes (land) and ponds on those islands (white)
for lv, fc in ((1, LAND_FILL), (2, OCEAN), (3, LAND_FILL), (4, OCEAN)):
    if lv == 1 or LAKES:
        ax.add_collection(PolyCollection(GSHHG[lv][0], facecolors=fc, edgecolors="none", zorder=1 + 0.1 * (lv - 1)))
ax.add_patch(Rectangle((LON0, LAT0), LON1 - LON0, LAT1 - LAT0, fc="none", ec=AXIS, lw=0.4, zorder=6))

# reef sites, below the regions: open (training-only) first, filled (scored) on top
sc = sites[sites.status == "scored"]
tr = sites[sites.status == "training-only"]
ax.scatter(tr.lon, tr.lat, s=DOT_D ** 2, marker="o", facecolors="white", edgecolors=INK, linewidths=0.35, zorder=2)
ax.scatter(sc.lon, sc.lat, s=DOT_D ** 2, marker="o", facecolors=INK, edgecolors="white", linewidths=0.2, zorder=2.1)

# regions in ORDER; each region's texture sits just above its own fill and below the next region
n_tex = {45: 0, 135: 0}
n_open = n_gap = 0
for k, r in enumerate(ORDER):
    z = 3 + 0.001 * k
    col = COLOUR[CAT[r]]
    is_open = r in no_pm25
    n_open += is_open
    patch = PathPatch(region_path(r), fc=OCEAN if is_open else col, ec=col if is_open else "none",
                      lw=OPEN_LW if is_open else 0.0, zorder=z, joinstyle="miter")
    ax.add_patch(patch)
    tx = TEXTURE[CAT[r]]
    if tx["angles"]:
        q = reg.loc[r]
        segs = []
        for a in tx["angles"]:
            segs += hatch(q.lon0 - 1, q.lon1 + 1, q.lat0 - 1, q.lat1 + 1, tx["gap"] * math.sqrt(2) / SCALE, a)
            n_tex[a] += 1
        lc = LineCollection(segs, colors=col if is_open else "white", linewidths=tx["lw"], zorder=z + 0.0005,
                            capstyle="butt")
        ax.add_collection(lc)
        lc.set_clip_path(patch)
    if not is_open:   # white gap where the region meets land or another region
        gs = gap_segments(r)
        if gs:
            ax.add_collection(LineCollection(gs, colors="white", linewidths=EDGE_LW, zorder=z + 0.0008,
                                             capstyle="projecting"))
            n_gap += 1
need(n_tex == {45: EXPECT["n_regions"]["fire"], 135: EXPECT["n_regions"]["defo"]}, f"textured regions {n_tex}")
need(n_open == len(no_pm25), "open regions")
print(f"regions drawn: {len(ORDER)} ({n_open} open; {n_gap} filled regions with a white gap on land)")

# graticule labels (secondary ink, never a series colour)
for lat, s in ((60, "60°N"), (30, "30°N"), (0, "0°"), (-30, "30°S")):
    ax.text(LON0 - 1.2 / SCALE, lat, s, ha="right", va="center", fontsize=7, color=INK2, clip_on=False)
for lon, s in ((-120, "120°W"), (-60, "60°W"), (0, "0°"), (60, "60°E"), (120, "120°E")):
    ax.text(lon, LAT0 - 1.0 / SCALE, s, ha="center", va="top", fontsize=7, color=INK2, clip_on=False)

# ---------------------------------------------------------------------------------------------------------------------
# 6. Legend (figure mm coordinates, drawn by hand so that it can be measured; text widths at print resolution).
# ---------------------------------------------------------------------------------------------------------------------
lax = fig.add_axes([0, 0, 1, 1], facecolor="none")
lax.set_xlim(0, FIG_W)
lax.set_ylim(0, FIG_H)
lax.axis("off")
REND = fig.canvas.get_renderer()
need(abs(REND.dpi - DPI) < 1e-9, f"text measured at {REND.dpi} dpi, not {DPI}")
TEXTS = []


def ltext(x, y, s):
    t = lax.text(x, y, s, fontsize=7, va="center", ha="left", color=INK)
    TEXTS.append(t)
    return t


def right_of(t, pad):
    bb = t.get_window_extent(renderer=REND)
    return lax.transData.inverted().transform((bb.x1, bb.y0))[0] + pad


def swatch(x, y, cat, is_open=False, w=3.0, h=2.0):
    col = COLOUR[cat]
    p = Rectangle((x, y - h / 2), w, h, fc=OCEAN if is_open else col, ec=col if is_open else "white",
                  lw=OPEN_LW if is_open else EDGE_LW, joinstyle="miter")
    lax.add_patch(p)
    tx = TEXTURE[cat]
    segs = []
    for a in tx["angles"]:
        segs += hatch(x - 1, x + w + 1, y - h / 2 - 1, y + h / 2 + 1, tx["gap"] * math.sqrt(2), a)
    if segs:
        lc = LineCollection(segs, colors=col if is_open else "white", linewidths=tx["lw"], capstyle="butt")
        lax.add_collection(lc)
        lc.set_clip_path(p)
    return x + w + 1.0


NR = EXPECT["n_regions"]
counts = pd.Series(CAT).value_counts()
y1 = map_bottom - LONLAB_H - 2.2
y2, y3 = y1 - 3.6, y1 - 7.2
t = ltext(ML, y1, f"Regions ({len(REGIONS)}, all NDVI), also used for:")
x = right_of(t, 2.0)
for cat in CATS:                     # slot order: blue, orange, aqua, then the neutral
    x = swatch(x, y1, cat)
    t = ltext(x, y1, f"{cat} ({counts[cat]})")
    x = right_of(t, 3.0)
x = swatch(ML, y2, CATS[3], is_open=True)
ltext(x, y2, f"Open outline: no PM2.5 ({len(no_pm25)} polar or edge regions, left out by PM2.5's whole-region "
             f"coverage rule); the other {len(sets['pm25'])} are PM2.5 regions")
t = ltext(ML, y3, f"Coral bleaching reef sites ({len(sites):,} in {len(kept)} regions):")
x = right_of(t, 2.0)
CLUSTER = np.array([(0.35, -0.45), (1.75, -0.45), (1.05, 0.55)])   # three map-size dots: a glyph, not a bullet
lax.scatter(x + CLUSTER[:, 0], y3 + CLUSTER[:, 1], s=DOT_D ** 2, marker="o", facecolors=INK, edgecolors="none")
t = ltext(x + 2.9, y3, f"{len(sc):,} in the {len(scored_groups)} scored regions")
x = right_of(t, 3.0)
lax.scatter(x + CLUSTER[:, 0], y3 + CLUSTER[:, 1], s=DOT_D ** 2, marker="o", facecolors="white", edgecolors=INK,
            linewidths=0.35)
ltext(x + 2.9, y3, f"{len(tr):,} in the {len(set(kept) - scored_groups)} training-only regions")

# ---------------------------------------------------------------------------------------------------------------------
# 7. Layout check (at print resolution): no text off the page, no two texts overlapping, every font >= 7 pt, legend
#    within the map width; and no text that names a person, an account or a tool.
# ---------------------------------------------------------------------------------------------------------------------
fig.canvas.draw()
rend = fig.canvas.get_renderer()
need(abs(rend.dpi - DPI) < 1e-9, "layout not measured at print resolution")
allt = TEXTS + list(ax.texts)
boxes = [(t, t.get_window_extent(renderer=rend)) for t in allt]
W, H = fig.bbox.width, fig.bbox.height
problems = []
for t, b in boxes:
    if b.x0 < 0 or b.y0 < 0 or b.x1 > W or b.y1 > H:
        problems.append(f"off page: {t.get_text()!r}")
for i in range(len(boxes)):
    for j in range(i + 1, len(boxes)):
        a, b = boxes[i][1], boxes[j][1]
        if min(a.x1, b.x1) - max(a.x0, b.x0) > 0.5 and min(a.y1, b.y1) - max(a.y0, b.y0) > 0.5:
            problems.append(f"overlap: {boxes[i][0].get_text()!r} / {boxes[j][0].get_text()!r}")
need(min(t.get_fontsize() for t in allt) >= 7.0, "a font below 7 pt")
need(not problems, "layout:\n  " + "\n  ".join(problems))
widest = max(lax.transData.inverted().transform((b.x1, 0))[0] for _, b in boxes)
need(widest <= ML + MAP_W + 0.2, f"legend runs past the map's right edge ({widest:.1f} mm)")
need(not any(BANNED_TOOL.search(t.get_text()) for t in allt), "figure text names a tool")
print(f"layout check passed: {len(allt)} texts; widest text ends at {widest:.1f} of {FIG_W:.0f} mm; "
      f"figure {FIG_W:.0f} x {FIG_H:.1f} mm; map {MAP_W:.1f} x {MAP_H:.1f} mm ({SCALE:.3f} mm per degree)")

# ---------------------------------------------------------------------------------------------------------------------
# 8. Caption and FACTS_TO_ADD.md, checked before anything is written: the numbers and names the caption states,
#    recounted here; the facts it cites (exactly the keys of FACT_NEEDLES); its terms (GLOSSARY.md); key phrases of
#    FACTS_TO_ADD.md; no tool named and no e-mail address in either file. A byte-order mark is tolerated.
# ---------------------------------------------------------------------------------------------------------------------
need(CAPTION_MD.is_file(), f"caption missing: {CAPTION_MD.name}")
need(FACTS_TO_ADD_MD.is_file(), f"missing: {FACTS_TO_ADD_MD.name}")
cap = CAPTION_MD.read_text(encoding="utf-8-sig")
fta = FACTS_TO_ADD_MD.read_text(encoding="utf-8-sig")
visible = " ".join(re.sub(r"<!--.*?-->", " ", cap, flags=re.S).split())
need(visible.startswith("**Figure 1.**"),
     f"caption must start with the figure label; it starts {visible[:40]!r}")


def name_list(keys):
    names = sorted(NAMES[r] for r in keys)
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


ndvi_only = [r for r in no_pm25 if combo[r] == "ndvi"]
fire_np = [r for r in no_pm25 if combo[r] == "ndvi+fire"]
defo_np = [r for r in no_pm25 if combo[r] == "ndvi+defo"]
need(len(ndvi_only) + len(fire_np) + len(defo_np) == len(no_pm25), "six regions: membership")
PHRASES = [
    f"Each of the {len(REGIONS)} panel regions is drawn as the area its locations cover on a {RES}° grid, clipped "
    f"to the coastline.",
    f"All are NDVI regions; {len(sets['pm25'])} are also PM2.5 regions, {len(sets['fire'])} burned-fraction "
    f"regions and {len(sets['defo'])} forest-loss regions.",
    f"burned fraction and forest loss ({counts[CATS[0]]} regions; blue, crossed lines)",
    f"burned fraction only ({counts[CATS[1]]}; orange, lines rising to the right)",
    f"forest loss only ({counts[CATS[2]]}; aqua, lines falling to the right)",
    f"neither ({counts[CATS[3]]}; grey, no lines)",
    f"Open outlines mark the {len(no_pm25)} polar or edge regions without PM2.5, left out by its whole-region "
    "coverage rule (named in Supplement S1.5).",  # Tier 1 (A1-07): the six names are in S1.5's note
    f"Dots are the {len(sites):,} reef sites of the {len(kept)} coral bleaching regions, each drawn once: filled for "
    f"the {len(sc):,} reef sites in the {len(scored_groups)} scored regions, open for the {len(tr):,} in the "
    f"{len(set(kept) - scored_groups)} training-only regions; the {ES['excluded_not_drawn']} reef sites of the "
    f"{len(excluded)} excluded regions are not drawn.",
    f"Regions are drawn over the reef sites and cover the centres of {int(cov.sum()):,} of them, "
    f"{int(cov['florida_everglades'])} in south Florida (Supplement S9.3).",  # Tier 1 (A1-08): the 30% clause is in S9.3
    f"Equirectangular projection, {-int(LAT0)}°S to {int(LAT1)}°N.",
    ("Coastlines and lakes: " if LAKES else "Coastlines: ") + "GSHHG 2.3.7, low resolution (Wessel and Smith "  # Round 4 (2026-11-11): no comma before the year, as the paper cites it (decision LD4)
    "1996), distributed under the GNU Lesser General Public License, version 3 or later." + ("" if LAKES else
                                                                                           " Lakes are not drawn."),
]
for p in PHRASES:
    need(p in visible, f"caption lacks {p!r}")
cited = set()
for mm_ in re.finditer(r"facts:\s*([A-Z][A-Z0-9]*(?:\s*,\s*[A-Z][A-Z0-9]*)*)", cap):
    cited |= {x.strip() for x in mm_.group(1).split(",")}
need(cited == set(FACT_NEEDLES), f"caption cites {sorted(cited)}; needles exist for {sorted(FACT_NEEDLES)}")
for pat in (r"\bcells?\b", r"\bunits?\b", r"\bgroups?\b", r"\becoregions?\b", r"\bfire\b", r"\bdefo\b",
            r"(?<!reef )\bsites?\b", r"(?<!survey )\bvisits?\b"):
    need(re.search(pat, visible, flags=re.I) is None, f"caption term {pat} (GLOSSARY.md)")
for name, text in (("caption", cap), ("FACTS_TO_ADD.md", fta)):
    hit = BANNED_TOOL.search(text)
    need(hit is None, f"{name} names a tool: {hit.group(0) if hit else ''!r}")
    need(EMAIL.search(text) is None, f"{name} holds an e-mail address")
# FACTS_TO_ADD.md must state the values this script asserts (one key phrase per proposed fact)
fta_flat = " ".join(fta.split())
FTA_PHRASES = [
    "pm25+ndvi 60; pm25+ndvi+defo 28; pm25+ndvi+fire 26; pm25+ndvi+fire+defo 13; ndvi only 4; ndvi+fire 1; "
    "ndvi+defo 1 (sum 133)",                                                                               # F1
    f"Burned fraction and forest loss {counts[CATS[0]]}; burned fraction only {counts[CATS[1]]}",          # F2
    "finnish_lapland: NDVI and burned fraction. tierra_del_fuego: NDVI and forest loss.",                    # F3
    f"{EP['pixels']:,} occupied pixels ({EP['region_pixels']:,} region-pixel pairs)",                      # F4
    f"{r_min} keeps {KEPT[r_min][0]:,} of its {KEPT[r_min][1]:,}",                                         # F4
    f"{len(sites):,} distinct reef sites in the {len(kept)} kept coral bleaching regions: {len(sc):,} in the "
    f"{len(scored_groups)} scored regions, {len(tr):,} in the {len(set(kept) - scored_groups)} training-only "
    f"regions",                                                                                            # F5
    f"{EV['site_keys']:,} site keys in {EV['regions']} regions",                                           # F6
    f"{int(cov.sum())} of the {len(sites):,} reef-site centres lie in a drawn region",                     # F7
    f"{EC['unclipped']:,} before the clipping",                                                            # F7
    "level 1: " + f"{EXPECT['gshhg_records'][1]:,} records",                                               # F8
    f"Figure {FIG_W:.0f} x {FIG_H:.1f} mm (Elsevier full width); map {MAP_W:.1f} x {MAP_H:.1f} mm, "
    f"{SCALE:.3f} mm per degree",                                                                          # F9
]
for p in FTA_PHRASES:
    need(p in fta_flat, f"FACTS_TO_ADD.md lacks {p!r}")
print(f"caption check passed: {len(PHRASES)} phrases, facts {', '.join(sorted(cited))}; "
      f"FACTS_TO_ADD.md: {len(FTA_PHRASES)} phrases")

# ---------------------------------------------------------------------------------------------------------------------
# 9. Figure files.
# ---------------------------------------------------------------------------------------------------------------------
PDF, PNG = HERE / f"{STEM}.pdf", HERE / f"{STEM}.png"
fig.savefig(PDF)
fig.savefig(PNG, dpi=DPI)
plt.close(fig)
pdf = PDF.read_bytes()
need(b"/FontFile2" in pdf and b"/Type3" not in pdf and b"ArialMT" in pdf, "PDF fonts: not embedded TrueType Arial")
with Image.open(PNG) as im:
    need(abs(im.info.get("dpi", (0, 0))[0] - DPI) < 1 and im.size[0] == round(FIG_W * MM * DPI), f"PNG {im.size}")

# ---------------------------------------------------------------------------------------------------------------------
# 10. Data file: one row per region, then one row per drawn reef site; read back and checked.
# ---------------------------------------------------------------------------------------------------------------------
rows = []
for r in REGIONS:
    q = reg.loc[r]
    rows.append(dict(record="region", region=r, in_pm25=r in sets["pm25"], in_ndvi=True,
                     in_burned_fraction=r in sets["fire"], in_forest_loss=r in sets["defo"], category=CAT[r],
                     n_locations=int(q.n_locations), centroid_lat=round(float(q.centroid_lat), 4),
                     centroid_lon=round(float(q.centroid_lon), 4)))
for s in sites.itertuples(index=False):   # site id: the package's unit_id (K1); coordinates rounded to 6 decimals
    rows.append(dict(record="reef site", site_id=s.unit_id, lat=float(s.la), lon=float(s.lo),
                     ecoregion_group=s.group, coral_region_status=s.status, covered_by_region=s.covered_by_region))
COLS = ["record", "region", "in_pm25", "in_ndvi", "in_burned_fraction", "in_forest_loss", "category", "n_locations",
        "centroid_lat", "centroid_lon", "site_id", "lat", "lon", "ecoregion_group", "coral_region_status",
        "covered_by_region"]
CSV = HERE / f"{STEM}_data.csv"
data = pd.DataFrame(rows, columns=COLS)
data["n_locations"] = data["n_locations"].astype("Int64")  # integers stay integers next to the site rows' empty cells
data.to_csv(CSV, index=False)
back = pd.read_csv(CSV, dtype={"region": str, "ecoregion_group": str, "covered_by_region": str, "site_id": str},
                   keep_default_na=False, na_values=[""])
rr = back[back.record == "region"]
ss = back[back.record == "reef site"]
need(len(rr) == NR["ndvi"] and rr.region.is_unique, "data file: regions")
for col, key in (("in_pm25", "pm25"), ("in_burned_fraction", "fire"), ("in_forest_loss", "defo")):
    need(int(rr[col].map({"True": 1, "False": 0, True: 1, False: 0}).sum()) == NR[key], f"data file: {col}")
need(rr.category.value_counts().to_dict() == EXPECT["category"], "data file: categories")
need(int(rr.n_locations.astype(int).sum()) == EXPECT["n_locations"]["ndvi"], "data file: locations")
need(len(ss) == ES["all"] and ss.site_id.is_unique and ss.site_id.str.fullmatch(r"\d+_-?\d+\.\d{4}_-?\d+\.\d{4}").all(),
     "data file: reef sites")
need(ss.coral_region_status.value_counts().to_dict() == {"scored": ES["scored"],
                                                         "training-only": ES["training_only"]}, "data file: status")
need(ss.ecoregion_group.nunique() == EG["kept"], "data file: coral regions")
need(ss.covered_by_region.value_counts().to_dict() == EC["by_region"], "data file: covered reef sites")
print(f"wrote {PDF.name}, {PNG.name}, {CSV.name} ({len(rr)} regions, {len(ss):,} reef sites)")
