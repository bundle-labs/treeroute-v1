"""C18 read-only check: did the short-history fallback route any scored row in the headline runs?
Reads derived.json (R12, R20:fallback_rows), decision_checks.json, test_pass_router.json, guard_report.json,
ladder/lead_*/lead.json, and the column names of test_preds.parquet / guard_preds / lead test_preds.
Writes nothing except stdout."""
import sys, json, glob, os, hashlib
sys.dont_write_bytecode = True
import pyarrow.parquet as pq

RUNS = {
    "pm25": "D:/treeroute/runs/pm25/headline/20261007_74e67609",
    "ndvi": "D:/treeroute/runs/ndvi/headline/20261016_d1de3158",
    "fire": "D:/treeroute/runs/fire/headline/20261017_869d1f38",
    "defo": "D:/treeroute/runs/defo/headline/20261017_d71c61f4",
    "coral": "D:/treeroute/runs/coral/headline/20261020_f3b8e3da",
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def find_key(obj, keys, path=""):
    """Yield (path, value) for every dict key in keys anywhere in obj."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            pp = path + "/" + str(k)
            if k in keys:
                yield pp, v
            yield from find_key(v, keys, pp)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from find_key(v, keys, path + "[%d]" % i)


def short(v, n=400):
    s = json.dumps(v, default=str)
    return s if len(s) <= n else s[:n] + "...(%d chars)" % len(s)


for pkg, run in RUNS.items():
    print("=" * 100)
    print(pkg, run)
    d = os.path.join(run, "derived.json")
    print("derived.json sha256", sha(d)[:8])
    der = load(d)
    r12 = der.get("R12")
    if r12 is not None:
        inp = r12.get("inputs", {})
        print("R12 value", r12.get("value"), "| h", inp.get("h"), "| units", inp.get("units"),
              "| units_scope", inp.get("units_scope"), "| fallback_units", inp.get("fallback_units"),
              "| fallback_share", inp.get("fallback_share"), "| flags", r12.get("flags"))
    fr = der.get("R20:fallback_rows")
    if fr is not None:
        inp = fr.get("inputs", {})
        print("R20:fallback_rows value", short(fr.get("value")), "| groups_with_fallback", inp.get("groups_with_fallback"),
              "| extra_rows", inp.get("extra_rows"), "| short_at_cuts", short(inp.get("short_at_cuts")),
              "| router_cuts", inp.get("router_cuts"))
        print("   rule:", inp.get("rule"))
    # runtime records
    for name in ("decision_checks.json", "test_pass_router.json", "guard_report.json"):
        p = os.path.join(run, name)
        if not os.path.isfile(p):
            print(name, "absent")
            continue
        doc = load(p)
        hits = list(find_key(doc, {"fallback", "fallback_levels", "fallback_decision_surface", "fallback_test_pass",
                                   "short_units", "fallback_units_scored", "n_units_fallback", "fallback_gls_note"}))
        print(name, "sha", sha(p)[:8], "hits:")
        for pth, v in hits:
            print("   ", pth, "=", short(v, 600))
    for lj in sorted(glob.glob(os.path.join(run, "ladder", "lead_*", "lead.json"))):
        doc = load(lj)
        hits = list(find_key(doc, {"fallback", "fallback_levels", "short_units", "fallback_units_scored",
                                   "n_units_fallback"}))
        print(os.path.relpath(lj, run), "hits:")
        for pth, v in hits:
            print("   ", pth, "=", short(v, 600))
    # whole-text search for 'short_units' / '"fallback"' in every json of the run folder
    for jp in sorted(glob.glob(os.path.join(run, "**", "*.json"), recursive=True)):
        if os.path.getsize(jp) > 5e6:
            continue
        with open(jp, "r", encoding="utf-8") as f:
            txt = f.read()
        n1 = txt.count('"short_units"')
        n2 = txt.count('"fallback":')
        n3 = txt.count('"fallback_units_scored": ')
        if n1 or n2 or n3:
            # count non-zero fallback_units_scored
            import re
            nz = [m for m in re.findall(r'"fallback_units_scored": (\d+)', txt) if m != "0"]
            print("  text", os.path.relpath(jp, run), "short_units:", n1, "fallback-key:", n2,
                  "fallback_units_scored entries:", n3, "nonzero:", nz)
    # parquet columns
    for pp in [os.path.join(run, "test_preds.parquet")] + sorted(glob.glob(os.path.join(run, "ladder", "lead_*", "*_preds.parquet"))):
        if os.path.isfile(pp):
            sch = pq.read_schema(pp)
            cols = list(sch.names)
            hit = [c for c in cols if any(s in c.lower() for s in ("fallback", "router", "route", "kind", "short", "region"))]
            print("  parquet", os.path.relpath(pp, run), "ncols", len(cols), "router-ish cols:", hit)
