# Skeptic (version 5 check, item 2, V5-1): Table 9 now glosses the family "context and calendar" as "the
# router-context columns that copy no tree input". Is any router-context player of the family (c__ players that are
# not merged) a copy of a tree input (an x__ player) on some problem? First pass, names only: per problem, the c__
# players of every model (meta.json `players`), their variables (meta.json `variable_map`), and every x__ player whose
# name shares a word with a context column's name (lat, lon, month, doy, mmm, sin, cos, day, year, season); and the
# non-phi column names of treeroute's rows.parquet (does it hold input values?). Read-only; prints only.
import json, os, re, sys
import pyarrow.parquet as pq
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
words = re.compile(r"(?i)(?:^|_)(lat|lon|abslat|latitude|longitude|month|doy|mmm|sin\d?|cos\d?|year|calendar|harm\w*)(?:_|$|\d)")
for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    base = SHAP + r"\out\%s\lead_0" % p
    PL = json.load(open(base + r"\compare\per_lead.json", encoding="utf-8"))
    fam = PL["families"]
    print("=" * 20, p)
    for m in PL["models"]:
        M = json.load(open(os.path.join(base, m, "meta.json"), encoding="utf-8"))
        pl = M.get("players")
        pl = list(pl) if isinstance(pl, (list, dict)) else []
        vm = M.get("variable_map") or {}
        c = [x for x in pl if str(x).startswith("c__")]
        xs = [x for x in pl if str(x).startswith("x__") and words.search(str(x)[3:])]
        print("  %-18s players %d (x__ %d, c__ %d): c__ %s" % (m, len(pl), sum(1 for x in pl if str(x).startswith("x__")),
                                                         len(c), [(x, vm.get(x), fam.get(vm.get(x))) for x in c]))
        print("  %-18s x__ players with a context-like word: %s" % ("", [(x, vm.get(x), fam.get(vm.get(x))) for x in xs]))
    f = os.path.join(base, "treeroute", "rows.parquet")
    names = pq.read_schema(f).names
    print("  treeroute rows.parquet: %d columns; not phi*: %s" % (len(names), [n for n in names if not n.startswith("phi")][:30]))
