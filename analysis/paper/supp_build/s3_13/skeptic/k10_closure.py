# Skeptic (version 2 check, item 1): is each change C1-C9 and gap G1-G4 closed in tables_agreed.md and in the spec?
# Read-only; prints only.
import json, os, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
SHAP = r"D:\treeroute\analysis\shap_v1"
V = SHAP + r"\verify_v1"
T1 = open(os.path.join(OUT, "reconcile", "tables_agreed_v1.md"), encoding="utf-8").read()
T2 = open(os.path.join(OUT, "reconcile", "tables_agreed.md"), encoding="utf-8").read()
S1 = open(os.path.join(OUT, "spec", "TABLE_SPEC_v1.md"), encoding="utf-8").read()
S2 = open(os.path.join(OUT, "spec", "TABLE_SPEC.md"), encoding="utf-8").read()
L2 = T2.split("\n")
S2L = S2.split("\n")
sec9 = S2.index("## 9. Version 2")

# the order's texts, wrapped lines joined
order = open(os.path.join(OUT, "_brief", "fix_order_v2.md"), encoding="utf-8").read().split("\n")
blocks, cur = [], None
for ln in order:
    if ln.startswith("- "):
        if cur is not None:
            blocks.append(cur)
        cur = ln[2:]
    elif ln.startswith("  ") and cur is not None:
        cur += " " + ln[2:]
    else:
        if cur is not None:
            blocks.append(cur)
        cur = None
if cur is not None:
    blocks.append(cur)
pairs = []
for b in blocks:
    m = re.search(r"OLD:? ?(?:row label: )?`([^`]+)`.*?NEW:? `([^`]+)`", b)
    if m:
        pairs.append((m.group(1), m.group(2)))
NEW13 = re.search(r"NEW: `(Top-10 shares \(d, e\)[^`]+)`", " ".join(blocks)).group(1)
NEW25 = re.search(r"NEW: `(Top-10 shares \(d, e, g\)[^`]+)`", " ".join(blocks)).group(1)
OLDSH = "Shares are of a model's total mean absolute SHAP value over J, without intervals, as in the comparison's files."
C9 = re.search(r"Add, after its first sentence: `([^`]+)`", " ".join(blocks)).group(1)
NOTE4 = re.search(r"before the line that starts `ᵃ Failed`: `([^`]+)`", " ".join(blocks)).group(1)
print("OLD/NEW pairs parsed from the order:", len(pairs))


def where(txt, T):
    return [i + 1 for i, x in enumerate(T.split("\n")) if txt in x]


def spec_where(txt):
    return [i + 1 for i, x in enumerate(S2L) if txt in x]


for old, new in pairs:
    o2 = where(old, T2)
    n2 = where(new, T2)
    o1 = where(old, T1)
    so = [n for n in spec_where(old) if n < S2[:sec9].count("\n") + 1]
    sn = spec_where(new)
    print("OLD in v1 lines %s | OLD in v2 lines %s | NEW in v2 lines %s | spec: NEW at %s, OLD before section 9 at %s :: %s"
          % (o1[:6], o2, n2[:6], sn[:6], so, new[:70]))
for name, txt in [("C1 (d, e)", NEW13), ("C1 (d, e, g)", NEW25)]:
    print(name, "in v2 lines", where(txt, T2), "| in spec lines", spec_where(txt))
print("C1 old caption sentence: v1 lines", where(OLDSH, T1), "v2 lines", where(OLDSH, T2), "spec before sec 9", [n for n in spec_where(OLDSH) if n < 1257])
print("C9: in v2 line", where(C9, T2), "| spec", spec_where(C9))
l1v1 = T1.split("\n")[0]
print("C9: v2 line 1 == v1 line 1 with the sentence inserted after 'each problem. ':",
      l1v1.replace("the nowcast of each problem. ", "the nowcast of each problem. " + C9 + " ", 1) == L2[0])
print("C4: new note at v2 lines", where(NOTE4, T2), "(next line starts 'ᵃ Failed':", L2[where(NOTE4, T2)[0]].startswith("ᵃ Failed"), ")",
      "| CRW Outlook row in v2:", where("| Coral bleaching | CRW Outlook |", T2), "| in spec before sec 9:",
      [n for n in spec_where("| Coral bleaching | CRW Outlook |") if n < 1257])
print("C4: D15 in v2 visible text:", where("D15", T2), "| 'last visit' in v2:", where("last visit", T2))

# G1: part census of cells.json
J = json.load(open(os.path.join(OUT, "reconcile", "cells.json"), encoding="utf-8"))
E = J["entries"]
pf = Counter((e["table"], e["part"]) for e in E if e["panel"] == "f" and e["table"] in ("S3.23", "S3.24", "S3.25", "S3.26", "S3.27"))
print("G1 panel f parts:", dict(pf), "total", sum(pf.values()))
cen = Counter((e["table"], e["panel"], e["part"]) for e in E)
print("G1 part census (table, panel, part):")
for k in sorted(cen):
    print("   ", k, cen[k])
print("tables_file:", J["tables_file"], "| spec:", J["spec"], "| file beside it named tables.md:",
      os.path.exists(os.path.join(OUT, "reconcile", "tables.md")))

# G2: bytes of the three text sources, and every log / register / maxima entry re-read as G2 says
srcs = {"SHAP\\SAMPLE_REGISTER.txt": SHAP + r"\SAMPLE_REGISTER.txt",
        "V\\_lead\\outputs\\bardl_maxima.txt": V + r"\_lead\outputs\bardl_maxima.txt"}
for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    srcs["SHAP\\logs\\tr_shap_%s_lead0.log" % p] = SHAP + r"\logs\tr_shap_%s_lead0.log" % p
for k, f in srcs.items():
    b = open(f, "rb").read()
    print("G2", k, "BOM", b.startswith(b"\xef\xbb\xbf"), "CRLF", b.count(b"\r\n"), "lone CR", b.count(b"\r") - b.count(b"\r\n"),
          "lone LF", b.count(b"\n") - b.count(b"\r\n"))
SET = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] (\w+) lead 0: (\d+) rows, (\d+) background pairs,")
DONE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] treeroute SHAP (\w+) lead 0 done in ([0-9.]+) s \(tree SHAP ([0-9.]+) s\)$")
MAX = re.compile(r"^\s+(jaccard_top5|jaccard_top10|jaccard_top20|rho20|rbo090|rbo095)\s+spread ([0-9.]+) -> \S+ \(3 sig\. \S+\) at (\w+)/(\w+)/(\S+); values ([0-9.\-]+) / ([0-9.\-]+) / ([0-9.\-]+)$")
text = {k: open(f, encoding="utf-8-sig").read().split("\n") for k, f in srcs.items()}
ok = bad = 0
for e in E:
    if e["source"] not in text:
        continue
    m = re.match(r"line (\d+): (.+)$", e["selector"])
    ln = text[e["source"]][int(m.group(1)) - 1]
    fld = m.group(2)
    if fld == "background pairs":
        v = int(SET.match(ln).group(4))
    elif fld in ("total seconds", "tree SHAP seconds"):
        g = DONE.match(ln)
        v = float(g.group(3 if fld == "total seconds" else 4))
    elif fld == "n":
        v = int(dict(x.split("=", 1) for x in ln.split() if "=" in x)["n"])
    else:
        g = MAX.match(ln)
        v = float(g.group({"spread": 2, "value 1": 6, "value 3": 8}[fld]))
    if [v] == e["stored"] or (len(e["stored"]) == 1 and e["stored"][0] == v):
        ok += 1
    else:
        bad += 1
        print("   G2 mismatch", e["selector"], e["stored"], v)
print("G2: text-source entries re-read as G2 says (utf-8-sig, universal newlines, line without its end): %d agree, %d differ" % (ok, bad))

# G3 and G4
e3m = [e for e in E if e["row"] == "E3m"]
print("G3 E3m entries:", [(e["column"], e["selector"], e["stored"], e["printed"]) for e in e3m])
g = json.load(open(SHAP + r"\rebuild\pm25\lead_0\gates.json", encoding="utf-8"))
print("G3 pm25 E3m values.files is a list of", len(g["gates"]["E3m_recorded_path_map"]["values"]["files"]))
print("G4 v2 line 165 coral cell:", L2[164].split(" | ")[-1])
print("G4 spec rule:", [n for n in spec_where("appended once, at the end of the joined cell")])
