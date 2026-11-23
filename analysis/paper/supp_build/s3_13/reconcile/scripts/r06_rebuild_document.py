# r06: the reconciler's own reconstruction of the whole tables.md: the constant texts (header comment, headings,
# captions, panel labels, headers, notes) are taken from the fenced blocks of OUT\spec\TABLE_SPEC.md by their
# first line (never retyped), the placeholders are filled by the spec's rules, and the table bodies come from
# r04 (the reconciler's own re-derivation from the sources). The result is compared byte for byte with
# OUT\A\tables.md and OUT\B\tables.md, and the layout rules of spec 0 and 2.9 are checked. With --write PATH
# the reconstruction is written to PATH (UTF-8, no BOM, LF). Otherwise read-only.
# Version 2 (2026-11-17): changed only where spec version 2 changed this script's input: the S3.18 panel b block
# has 10 lines (C4), the S3.18 notes block is found by its new first line and has 3 lines (C4), and the S3.23-S3.27
# caption template's new placeholder {shares_sentence} is filled with the two values of its bullet in spec 4.7 (C1);
# a check that no caption placeholder is left was added with it. Original: scripts\v1\r06_rebuild_document.py.
# Version 3 (2026-11-17): changed only where spec version 3 changed this script's input: the S3.18 panel b label
# (block 14) and the S3.18 notes block (block 16) are found by their new first lines (V3-2), and the value of
# {extra_src} (V3-3), which version 2 of this script typed in, is now taken from its bullet in spec 4.7, so that it
# is not retyped. Version 2 is kept as scripts\v2\r06_rebuild_document.py.
# Version 4 (2026-11-17): changed only where spec version 4 changed this script's input: the S3.18 panel b table
# (block 15), whose header line is new (V4-7), is found by its new first line. The other blocks that version 4 changed
# keep the start by which this script finds them. Version 3 is kept as scripts\v3\r06_rebuild_document.py.
import sys, re, json, runpy, hashlib, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import *  # noqa: E402,F401,F403

sys.stdout.reconfigure(encoding="utf-8")
G = runpy.run_path(str(HERE / "r04_rebuild_bodies.py"), run_name="r04")
EXP, PL = G["EXP"], G["PL"]
if G["fails"] or G["diffs"]:
    raise Stop("r04 did not pass")
spec = (OUT / "spec" / "TABLE_SPEC.md").read_text(encoding="utf-8").split("\n")
blocks, cur, inb = [], None, False
for l in spec:
    if l.startswith("```"):
        if inb:
            blocks.append(cur)
            inb = False
        else:
            cur, inb = [], True
        continue
    if inb:
        cur.append(l)
print("fenced blocks in the spec:", len(blocks))
used = set()


def blk(prefix, n=None, exact=False):
    hits = [i for i, b in enumerate(blocks) if b and (b[0] == prefix if exact else b[0].startswith(prefix))]
    if len(hits) != 1:
        raise Stop("block %r: %d hits" % (prefix, len(hits)))
    used.add(hits[0])
    b = blocks[hits[0]]
    if n is not None and len(b) != n:
        raise Stop("block %r has %d lines" % (prefix, len(b)))
    return list(b)


def table(header_lines, rows):
    return header_lines + ["| " + " | ".join(r) + " |" for r in rows]


def hdr(cells):
    return ["| " + " | ".join(cells) + " |", "|" + "---|" * len(cells)]


SA, SB, SC, SD, DAG, DDAG, SECT = "\u1d43", "\u1d47", "\u1d9c", "\u1d48", "\u2020", "\u2021", "\u00a7"
doc = []
doc.append(blk("<!-- Draft tables of Supplement S3.13", 1))
doc.append(blk("## Main text: Table 9", 1))
# Table 9
doc.append(blk("**Table 9.**", 1))
doc.append(table(blk("| Problem | Main set | W [95% CI]", 2), EXP[("9", "")]))
doc.append(blk("\u1d43 Burned fraction: every rival explains in another link (LightGBM, the random forest and Ridge in log(y + c), the Tweedie booster in log \u03bc), and Ridge also failed its skill guard, so the main set is treeroute v1 alone. W needs two models and is undefined, and the cells that need a rival are empty (\u2013): agreement between treeroute v1 and a rival cannot separate the link from the model there. The cross-link", 4))
doc.append(blk("## Supplement S3.13: SHAP comparison of the main runs", 1))
# S3.18
doc.append(blk("**Table S3.18 (post hoc).**", 1))
doc.append(blk("**a. Explained models.**", 1))
doc.append(table(blk("| Problem | Model (data name) |", 2), EXP[("S3.18", "a")]))
doc.append(blk("**b. Rivals and naive baselines left out.**", 1))
doc.append(blk("| Problem | Rival or naive baseline | Why it has no SHAP value |", 10))
n18 = blk("Panel b lists the nowcast's rivals and naive baselines", 3)
if not n18[1].startswith("\u1d43 Failed: the raw model"):
    raise Stop("S3.18 notes block")
doc.append(n18)
# S3.19
doc.append(blk("**Table S3.19 (post hoc).**", 1))
doc.append(table(blk("| Problem | Frame rows", 2), EXP[("S3.19", "")]))
n19 = blk("\u1d43 Frame: the labelled test rows", 4)
tmpl = blk("{Problem}: variable level ({nv})", 1)[0]
for p in PROBS:
    pl = PL[p]
    n19.append(tmpl.replace("{Problem}", PDISP[p]).replace("{nv}", COUNT(len(pl["variable"]["structural_zero"])))
               .replace("{names_v}", ", ".join("`%s`" % x for x in pl["variable"]["structural_zero"]))
               .replace("{nf}", COUNT(len(pl["feature"]["structural_zero"])))
               .replace("{names_f}", ", ".join("`%s`" % x for x in pl["feature"]["structural_zero"])))
doc.append(n19)
# S3.20
doc.append(blk("**Table S3.20 (post hoc).**", 1))
doc.append(table(blk("| Problem | Model | Rows checked", 2), EXP[("S3.20", "")]))
n20 = blk("\u1d43 Rows checked: every test row", 4)
ex = {p: load_json(model_dir(p, "rival_ridge") / "exactness.json") for p in ("pm25", "ndvi", "fire", "defo")}
for p in ("pm25", "ndvi", "fire", "defo"):
    n20[1] = n20[1].replace("{bit_%s}" % p, COUNT(ex[p]["bit_equal_rows"])).replace("{rows_%s}" % p, COUNT(ex[p]["rows"]))
if "{" in n20[1]:
    raise Stop("S3.20 placeholder left")
doc.append(n20)
# S3.21
doc.append(blk("**Table S3.21 (post hoc).**", 1))
doc.append(table(blk("| Gate | What it checks |", 2), EXP[("S3.21", "")]))
doc.append(blk("\u1d43 E5 is informational", 2))
# S3.22
doc.append(blk("**Table S3.22 (post hoc).**", 1))
doc.append(table(blk("| Quantity | PM2.5 | NDVI |", 2), EXP[("S3.22", "")]))
doc.append(blk("\u1d43 Burned fraction: every rival explains in another link (LightGBM, the random forest and Ridge in log(y + c), the Tweedie booster in log \u03bc), and Ridge also failed its skill guard, so the main set is treeroute v1 alone. W needs two models and is undefined, and the cells that need a rival are empty (\u2013): agreement between treeroute v1 and a rival cannot separate the link from the model there.", 5, exact=True))
# S3.23-S3.27
cap = blk("**Table S3.{nn} (post hoc).**", 1)[0]
iss = [i for i, l in enumerate(spec) if l.startswith("- `{shares_sentence}`")]
if len(iss) != 1:
    raise Stop("the {shares_sentence} bullet")
i0 = iss[0]
m1, m2 = re.match(r"^  `([^`]+)`;$", spec[i0 + 1]), re.match(r"^  `([^`]+)`$", spec[i0 + 3])
if not (spec[i0].endswith(": fire and coral (the tables with panel g)") and spec[i0 + 2] == "  else (pm25, ndvi, defo)" and m1 and m2):
    raise Stop("the {shares_sentence} values")
SS = {"fire": m1.group(1), "coral": m1.group(1), "pm25": m2.group(1), "ndvi": m2.group(1), "defo": m2.group(1)}
ies = [i for i, l in enumerate(spec) if l.startswith("- `{extra_src}`")]
mx_ = re.match(r"^- `\{extra_src\}`: ndvi `([^`]+)`;$", spec[ies[0]]) if len(ies) == 1 else None
if not (mx_ and spec[ies[0] + 1] == "  else empty."):
    raise Stop("the {extra_src} bullet")
EXTRA_SRC_NDVI = mx_.group(1)
print("{extra_src} for ndvi, from spec line %d: %s" % (ies[0] + 1, EXTRA_SRC_NDVI))
NN = {"pm25": "23", "ndvi": "24", "fire": "25", "defo": "26", "coral": "27"}
la, lb = blk("**a. Variable level: every pair.**", 1), blk("**b. Feature level: every pair.**", 1)
ha = blk("| Pair | Link | Spearman over J |", 2)
lc, hc = blk("**c. Agreement within the main set", 1), blk("| Statistic | Variable level | Feature level |", 2)
ld, le = blk("**d. Variable level: each model's top 10", 1), blk("**e. Feature level: each model's top 10", 1)
lf, lg = blk("**f. Family shares", 1), blk("**g. Arcsine-link models", 1)
nfire = blk("\u1d43 The main set is treeroute v1 alone", 1)
nall1 = blk("Sign agreement: of the players in the union", 2)
nndvi = blk("\u2021 BARDL reads three variables", 1)[0]
nall2 = blk("\u00a7 Families are sums of variable-level attributions, so at the feature level the family-share distance is the variable-level value repeated (ruling BB2).", 2)
nfc = blk("Panel g: each arcsine-link model's", 1)
TID = {"pm25": "S3.23", "ndvi": "S3.24", "fire": "S3.25", "defo": "S3.26", "coral": "S3.27"}
for p in PROBS:
    tid, pl = TID[p], PL[p]
    models = [m for m in ORDER if m in pl["models"]]
    g_clause = "; and the arcsine-link models' top 10 on their rows with a forecast above 0 (g)" if p in ("fire", "coral") else ""
    extra_src = EXTRA_SRC_NDVI if p == "ndvi" else ""
    extra_rul = {"ndvi": ", BB3", "defo": ", BB4", "coral": ", BB4"}.get(p, "")
    doc.append([cap.replace("{nn}", NN[p]).replace("{Problem}", PDISP[p]).replace("{p}", p).replace("{g_clause}", g_clause)
                .replace("{extra_src}", extra_src).replace("{extra_rulings}", extra_rul).replace("{shares_sentence}", SS[p])])
    if "{" in doc[-1][0]:
        raise Stop("caption placeholder left: " + p)
    doc.append(la)
    doc.append(table(ha, EXP[(tid, "a")]))
    doc.append(lb)
    hb = ha[0][2:-2].split(" | ")
    hb = [("Family-share distance (TV)" + SECT) if h == "Family-share distance (TV)" else h for h in hb]
    if pl["feature"]["active"] >= 200:
        hb.insert(hb.index("Jaccard top 10") + 1, "Jaccard top 20")
    doc.append(table(hdr(hb), EXP[(tid, "b")]))
    doc.append(lc)
    doc.append(table(hc, EXP[(tid, "c")]))
    names = [HEADER[m] + (DDAG if (p == "ndvi" and m == "rival_bardl_h1") else "") for m in models]
    doc.append(ld)
    doc.append(table(hdr(["Rank"] + names), EXP[(tid, "d")]))
    doc.append(le)
    doc.append(table(hdr(["Rank"] + names), EXP[(tid, "e")]))
    doc.append(lf)
    doc.append(table(hdr(["Family"] + [HEADER[m] for m in models]), EXP[(tid, "f")]))
    if pl["nonzero_forecast_rows"]:
        doc.append(lg)
        doc.append(table(hdr(["Rank"] + [HEADER[m] for m in ORDER if m in pl["nonzero_forecast_rows"]]), EXP[(tid, "g")]))
    notes = []
    if p == "fire":
        notes += nfire
    notes += nall1
    if p == "ndvi":
        notes.append(G["ENOTE"][("S3.24", "ddag")])
        # the ndvi note template of the spec, placeholders turned into wildcards, must match the filled line
        rx = "^" + re.sub(r"\\\{[a-z0-9_]+\\\}", ".+?", re.escape(nndvi)) + "$"
        if not re.match(rx, G["ENOTE"][("S3.24", "ddag")]):
            raise Stop("ndvi note does not follow the spec template")
    notes += nall2
    if p in ("fire", "coral"):
        notes += nfc
    doc.append(notes)
doc.append(blk("## Supplement S3.13: treeroute v1's B1 sensitivity", 1))
# S3.28
doc.append(blk("**Table S3.28 (post hoc; sensitivity).**", 1))
h28 = blk("| Statistic | PM2.5 | NDVI | Burned fraction |", 2)
doc.append(blk("**a. Variable level: the pair (main run, B1 run).**", 1))
doc.append(table(h28, EXP[("S3.28", "a")]))
doc.append(blk("**b. Feature level: the pair (main run, B1 run).**", 1))
doc.append(table(h28, EXP[("S3.28", "b")]))
doc.append(blk("\u2013: not defined, because the pair's J", 2))
# S3.29
doc.append(blk("**Table S3.29 (post hoc; sensitivity).**", 1))
for lab, first, key in (("**a. Variable level: the B1 run's family shares", "Family", "a"), ("**b. Variable level: the B1 run's top 3", "Quantity", "b"),
                        ("**c. Variable level: the B1 run's top 10", "Rank", "c"), ("**d. Feature level: the B1 run's top 10", "Rank", "d")):
    doc.append(blk(lab, 1))
    doc.append(table(hdr([first, "PM2.5", "NDVI", "Burned fraction"]), EXP[("S3.29", key)]))
doc.append(blk("Under B1 the month and the seasonal normal can take credit", 1))
# S3.30
doc.append(blk("**Table S3.30 (post hoc; sensitivity).**", 1))
doc.append(blk("**a. Background pairs and seconds", 1))
doc.append(table(blk("| Problem | Background pairs | Total seconds | Tree-SHAP seconds |", 2), EXP[("S3.30", "a")]))
doc.append(blk("**b. Forest loss: the B1 run against the main run.**", 1))
doc.append(table(blk("| Check | Result |", 2), EXP[("S3.30", "b")]))
doc.append(blk("Coral bleaching: B1 is not defined", 2))

out = "\n\n".join("\n".join(b) for b in doc) + "\n"
mine = out.encode("utf-8")
ta = (OUT / "A" / "tables.md").read_bytes()
tb = (OUT / "B" / "tables.md").read_bytes()
print("reconstruction: lines", out.count("\n"), "bytes", len(mine), "sha256", hashlib.sha256(mine).hexdigest())
print("equal to OUT\\A\\tables.md:", mine == ta, "; equal to OUT\\B\\tables.md:", mine == tb)
if mine != ta:
    la_, lm = ta.decode("utf-8").split("\n"), out.split("\n")
    for i, (x, y) in enumerate(zip(la_, lm), 1):
        if x != y:
            print("first differing line", i)
            print("  A   :", x[:300])
            print("  mine:", y[:300])
            break
# fenced blocks never used (the spec's regexes, the format pseudo-code and other non-output blocks are expected here)
unused = [i for i in range(len(blocks)) if i not in used]
print("fenced blocks used:", len(used), "not used:", [(i, blocks[i][0][:50]) for i in unused])
# layout rules (spec 0 and 2.9) on the builders' file
t = ta.decode("utf-8")
L = t.split("\n")
lay = []
if ta.startswith(b"\xef\xbb\xbf"):
    lay.append("BOM")
if b"\r" in ta:
    lay.append("CR")
if b"\t" in ta:
    lay.append("tab")
if not t.endswith("\n") or t.endswith("\n\n"):
    lay.append("end of file")
for i, l in enumerate(L[:-1], 1):
    if l != l.rstrip(" "):
        lay.append("trailing space line %d" % i)
    if i > 1 and l == "" and L[i - 2] == "":
        lay.append("double blank line %d" % i)
    if l.startswith("| "):
        cells = l[2:-2].split(" | ")
        if not l.endswith(" |") or any(c != c.strip(" ") or c == "" for c in cells):
            lay.append("cell padding or empty cell line %d" % i)
print("layout problems:", lay[:10], "count", len(lay))
if len(sys.argv) == 3 and sys.argv[1] == "--write":
    dest = Path(sys.argv[2])
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    print("written:", dest.name, hashlib.sha256(dest.read_bytes()).hexdigest())
