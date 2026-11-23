"""Skeptic (numbers lens), round 14: look at the structure of the row files and draws (no compare tables)."""
import json, os, sys, hashlib
import numpy as np
import pyarrow.parquet as pq

SHAP = r"D:\treeroute\analysis\shap_v1"
OUT = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\numbers\work"

probs = ["coral", "defo", "fire", "pm25", "ndvi"]
lines = []
def P(*a):
    s = " ".join(str(x) for x in a)
    lines.append(s)
    print(s)

for p in probs:
    base = os.path.join(SHAP, "out", p, "lead_0")
    P("=" * 20, p)
    pl = json.load(open(os.path.join(base, "compare", "per_lead.json"), encoding="utf-8"))
    for k in ["models", "main_set", "declined_by_guard", "links", "rows"]:
        P(k, pl.get(k))
    P("per_lead keys (names only):", sorted(pl.keys()))
    d = np.load(os.path.join(base, "compare", "bootstrap_draws.npy"), mmap_mode="r")
    P("draws", d.shape, d.dtype, "min", int(d.min()), "max", int(d.max()))
    cnt = np.bincount(np.asarray(d).ravel(), minlength=d.shape[1])
    P("draw counts per index: min", cnt.min(), "max", cnt.max(), "expected", d.shape[0])
    with open(os.path.join(base, "compare", "bootstrap_draws.npy"), "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()
    P("sha file", h, "per_lead", pl.get("draws_sha256"), "match", h == pl.get("draws_sha256"))
    for m in sorted(os.listdir(base)):
        if m == "compare":
            continue
        rp = os.path.join(base, m, "rows.parquet")
        if not os.path.exists(rp):
            P(m, "no rows.parquet")
            continue
        t = pq.read_table(rp, columns=["row", "unit", "group", "time", "year", "pre", "resid_flag"]).to_pandas()
        meta = json.load(open(os.path.join(base, m, "meta.json"), encoding="utf-8"))
        P(m, "rows", len(t), "groups", t["group"].nunique(), "units", t["unit"].nunique(),
          "years", sorted(t["year"].unique().tolist()), "flagged", int(t["resid_flag"].sum()),
          "link", meta.get("link"), "c", meta.get("c"), "ub", meta.get("ub"), "bg", meta.get("background"),
          "pnz", meta.get("players_nonzero"), "vnz", meta.get("variables_nonzero"),
          "dup", meta.get("duplicates_merged"))
    t = pq.read_table(os.path.join(base, "treeroute", "rows.parquet"), columns=["row", "unit", "group", "time", "year"]).to_pandas()
    P("first rows of treeroute keys:")
    P(t.head(5).to_string())
    g = t.groupby("group").size()
    P("rows per group: min", g.min(), "max", g.max(), "n", len(g))
    P("groups sorted first 5:", sorted(t["group"].unique().tolist())[:5])

open(os.path.join(OUT, "s00_inspect.txt"), "w", encoding="utf-8").write("\n".join(lines))
