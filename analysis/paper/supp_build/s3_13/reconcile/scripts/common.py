# common helpers of the reconciler's scripts: paths (found from this file's place), the spec's format
# functions (TABLE_SPEC.md 2.5 and 2.6, re-implemented here), source readers and a tables.md parser.
import math, re, json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2]
SHAP = Path("D:/treeroute/analysis/shap_v1")
V = SHAP / "verify_v1"
MINUS, ENDASH = "\u2212", "\u2013"
D = 2000
PROBS = ["pm25", "ndvi", "fire", "defo", "coral"]
PDISP = {"pm25": "PM2.5", "ndvi": "NDVI", "fire": "Burned fraction", "defo": "Forest loss", "coral": "Coral bleaching"}
PINLINE = {"pm25": "PM2.5", "ndvi": "NDVI", "fire": "burned fraction", "defo": "forest loss", "coral": "coral bleaching"}
ORDER = ["treeroute", "rival_ridge", "rival_rf", "rival_lgbm", "rival_lgbm_tweedie", "rival_hgb_l1", "rival_bardl_h1"]
INLINE = {"treeroute": "treeroute v1", "rival_ridge": "Ridge", "rival_rf": "random forest", "rival_lgbm": "LightGBM",
          "rival_lgbm_tweedie": "Tweedie booster", "rival_hgb_l1": "absolute-error booster", "rival_bardl_h1": "BARDL"}
HEADER = {"treeroute": "treeroute v1", "rival_ridge": "Ridge", "rival_rf": "Random forest", "rival_lgbm": "LightGBM",
          "rival_lgbm_tweedie": "Tweedie booster", "rival_hgb_l1": "Absolute-error booster", "rival_bardl_h1": "BARDL"}
LINKDISP = {"identity": "identity", "log_c": "log(y + c)", "log_mu": "log \u03bc", "arcsine": "arcsine"}
FAMS = ["own history", "global indices", "local drivers", "context and calendar", "seasonal normal"]
FAMLABEL = {"own history": "(no own-history input)", "global indices": "(no global-index input)",
            "local drivers": "(no local-driver input)", "context and calendar": "(no context or calendar input)",
            "seasonal normal": "(no seasonal-normal input)"}
SUP = str.maketrans("0123456789-", "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u207b")


class Stop(Exception):
    pass


def finite(x):
    return x is not None and isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def NUM2(x):
    if not finite(x):
        raise Stop("NUM2 of %r" % (x,))
    if x == 0.0:
        return "0.00"
    s = format(x, ".2f")
    if s[0] == "-":
        s = MINUS + s[1:]
    return s


def PCT1(x):
    if not finite(x) or x < 0:
        raise Stop("PCT1 of %r" % (x,))
    if x == 0.0:
        return "0.0%"
    y = 100.0 * x
    if y < 0.05:
        return "<0.1%"
    return format(y, ".1f") + "%"


def COUNT(n):
    if isinstance(n, bool) or not (isinstance(n, int) or (isinstance(n, float) and n.is_integer())):
        raise Stop("COUNT of %r" % (n,))
    return format(int(n), ",")


def SCI2(x):
    if x == 0.0:
        return "0"
    m, e = format(abs(x), ".1e").split("e")
    return (MINUS if x < 0 else "") + m + " \u00d7 10" + str(int(e)).translate(SUP)


def SECS(x):
    return format(x, ",.1f")


def MED(x):
    return COUNT(x) if float(x).is_integer() else format(x, ".1f")


def CI2(v, lo, hi, nf, f=NUM2):
    head = f(v) if finite(v) else "undefined"
    if nf is None or nf == 0:
        return head
    s = head + " [" + f(lo) + ", " + f(hi) + "]"
    if nf < D:
        s += " (" + COUNT(nf) + " finite draws)"
    return s


def CIP(v, lo, hi, nf):
    return CI2(v, lo, hi, nf, f=PCT1)


def SIGN(v, k, lo, hi, nf):
    head = NUM2(v) if finite(v) else "undefined"
    if nf > 0:
        head += " [" + NUM2(lo) + ", " + NUM2(hi) + "]"
    extras = [COUNT(k) + (" sign" if k == 1 else " signs")]
    if 0 < nf < D:
        extras.append(COUNT(nf) + " finite draws")
    return head + " (" + "; ".join(extras) + ")"


def TOP(name, share):
    return "`" + name + "` " + PCT1(share)


def selftest():
    vec = [(NUM2(0.625), "0.62"), (NUM2(0.875), "0.88"), (NUM2(-0.004), MINUS + "0.00"), (NUM2(-0.0), "0.00"),
           (NUM2(-0.1214), MINUS + "0.12"), (PCT1(0.0625), "6.2%"), (PCT1(0.0002), "<0.1%"), (PCT1(0.0), "0.0%"),
           (PCT1(0.14169933950641164), "14.2%"), (COUNT(1140), "1,140"), (COUNT(10.0), "10"),
           (SCI2(9.237055564881302e-14), "9.2 \u00d7 10\u207b\u00b9\u2074"),
           (SCI2(2.220446049250313e-16), "2.2 \u00d7 10\u207b\u00b9\u2076"), (SECS(2636.6), "2,636.6")]
    for got, want in vec:
        if got != want:
            raise Stop("self-test %r != %r" % (got, want))
    return len(vec)


def nan2none(x):
    if isinstance(x, float) and math.isnan(x):
        return None
    return x


def load_json(path, strict=False):
    txt = Path(path).read_text(encoding="utf-8")
    if strict:
        def bad(c):
            raise Stop("non-strict JSON constant %s in %s" % (c, path))
        return json.loads(txt, parse_constant=bad)
    return json.loads(txt)


def comp(p):
    return SHAP / "out" / p / "lead_0" / "compare"


def model_dir(p, m):
    return SHAP / "out" / p / "lead_0" / m


def parse_tables(text):
    """tables[(tid, panel)] = dict(header, rows, lines); notes[tid] = [(line, text)]"""
    lines = text.split("\n")
    tables, notes = {}, {}
    cur, pan, i = None, "", 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r"^\*\*Table (9|S3\.\d+)\b", ln)
        if m:
            cur, pan = m.group(1), ""
            notes.setdefault(cur, [])
            i += 1
            continue
        m = re.match(r"^\*\*([a-g])\. ", ln)
        if m:
            pan = m.group(1)
            i += 1
            continue
        if ln.startswith("| ") and i + 1 < len(lines) and lines[i + 1].startswith("|---"):
            header = ln[2:-2].split(" | ")
            rows, nums = [], []
            j = i + 2
            while j < len(lines) and lines[j].startswith("| "):
                rows.append(lines[j][2:-2].split(" | "))
                nums.append(j + 1)
                j += 1
            tables[(cur, pan)] = dict(header=header, rows=rows, lines=nums, hline=i + 1)
            i = j
            continue
        if ln and cur and not ln.startswith("#") and not ln.startswith("**") and not ln.startswith("<!--"):
            notes[cur].append((i + 1, ln))
        i += 1
    return lines, tables, notes
