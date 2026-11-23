# Round 14, implementer A: inspection of structure only (no statistic).
# Prints per_lead.json's structural keys only, meta.json summaries and row-file key columns.
import json, os, sys, hashlib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

SHAP = r"D:\treeroute\analysis\shap_v1"
PROBLEMS = ["coral", "defo", "fire", "pm25", "ndvi"]
STRUCT = ["models", "main_set", "declined_by_guard", "links", "rows", "sample_sha256", "draws_sha256"]


def main():
    for p in PROBLEMS:
        base = os.path.join(SHAP, "out", p, "lead_0")
        with open(os.path.join(base, "compare", "per_lead.json"), "r", encoding="utf-8") as fh:
            pl = json.load(fh)
        print("=" * 30, p)
        for k in STRUCT:
            print("  per_lead.%s = %r" % (k, pl.get(k, "<absent>")))
        del pl
        pieces = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)) and d != "compare")
        for d in pieces:
            mp = os.path.join(base, d, "meta.json")
            with open(mp, "r", encoding="utf-8") as fh:
                meta = json.load(fh)
            print("  --", d)
            print("     keys:", sorted(meta.keys()))
            for k in ["model", "problem", "lead", "link", "c", "ub", "guard", "background", "pass", "checks_passed",
                      "rows", "players_nonzero", "variables_nonzero", "duplicates_merged", "kind", "arm", "pairs",
                      "trees_used", "value_function", "sample_sha256"]:
                if k in meta:
                    v = meta[k]
                    s = repr(v)
                    if len(s) > 300:
                        s = s[:300] + "..."
                    print("     %s = %s" % (k, s))
            print("     n players =", len(meta.get("players", [])), " n variables =", len(meta.get("variables", [])))
            vm = meta.get("variable_map", {})
            print("     variable_map type:", type(vm).__name__, "len", len(vm))
            rp = os.path.join(base, d, "rows.parquet")
            pf = pq.ParquetFile(rp)
            print("     rows.parquet rows:", pf.metadata.num_rows, "cols:", pf.metadata.num_columns)
    # row keys of one piece per problem
    for p in PROBLEMS:
        rp = os.path.join(SHAP, "out", p, "lead_0", "treeroute", "rows.parquet")
        t = pq.read_table(rp, columns=["row", "unit", "group", "time", "year", "resid_flag"]).to_pandas()
        print("=" * 30, p, "treeroute keys")
        print(t.head(5).to_string())
        print("  n unique unit:", t["unit"].nunique(), " group:", t["group"].nunique(), " time:", t["time"].nunique(),
              " year:", sorted(t["year"].unique().tolist()))
        print("  group examples:", sorted(t["group"].unique().tolist())[:10])
        print("  resid_flag sum:", int(t["resid_flag"].sum()))
        d = np.load(os.path.join(SHAP, "out", p, "lead_0", "compare", "bootstrap_draws.npy"), mmap_mode="r")
        print("  draws shape", d.shape, d.dtype, "min", int(np.min(d)), "max", int(np.max(d)))


if __name__ == "__main__":
    main()
