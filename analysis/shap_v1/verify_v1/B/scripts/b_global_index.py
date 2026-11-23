# Implementer B, round 14: section 8's global-index rule on the lead's test set (item 3).
# "global indices (a variable all of whose columns take one value per time step across every unit of the lead's
# test set)". The lead's test set: the rivals' export of the headline run, lead_0/test/*.parquet (one file per
# region). Only the columns needed are read: unit, time, issue and the x__ columns of the candidate variables.
# Writes V\B\work\global_<problem>.json. No SHAP value is read here except the variable maps of meta.json.
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

SHAP = Path(r"D:\treeroute\analysis\shap_v1")
OUT = Path(r"D:\treeroute\analysis\shap_v1\verify_v1\B\work")
EXPORT = {"coral": r"D:\treeroute\rival_export\coral\20261020_f3b8e3da",
          "defo": r"D:\treeroute\rival_export\defo\20261017_d71c61f4",
          "fire": r"D:\treeroute\rival_export\fire\20261017_869d1f38",
          "pm25": r"D:\treeroute\rival_export\pm25\20261007_74e67609",
          "ndvi": r"D:\treeroute\rival_export\ndvi\20261016_d1de3158"}
EXPORT_SHORT = {"coral": r"D:\treeroute\rival_export\coral\20261020_f3b8e3da\lead_0\test\*.parquet",
                "defo": r"D:\treeroute\rival_export\defo\20261017_d71c61f4\lead_0\test\*.parquet",
                "fire": r"D:\treeroute\rival_export\fire\20261017_869d1f38\lead_0\test\*.parquet",
                "pm25": r"D:\treeroute\rival_export\pm25\20261007_74e67609\lead_0\test\*.parquet",
                "ndvi": r"D:\treeroute\rival_export\ndvi\20261016_d1de3158\lead_0\test\*.parquet"}


def special_family(v):
    if v == "normal":
        return "seasonal_normal"
    if v.startswith("hist_"):
        return "own_history"
    if v == "calendar" or v.startswith("ctx:"):
        return "context_and_calendar"
    return None


def main(problems):
    for p in problems:
        t0 = time.time()
        lead = SHAP / "out" / p / "lead_0"
        pl = json.loads((lead / "compare" / "per_lead.json").read_text(encoding="utf-8"))
        models = list(pl["models"])
        vmap = {}
        for m in models:  # items 1-8 code: never a treeroute_B1 folder
            meta = json.loads((lead / m / "meta.json").read_text(encoding="utf-8"))
            for k, v in meta["variable_map"].items():
                assert vmap.get(k, v) == v
                vmap[k] = v
        variables = sorted(set(vmap.values()))
        cand = [v for v in variables if special_family(v) is None]
        cols_of = {v: sorted(k for k, vv in vmap.items() if vv == v) for v in cand}
        need = sorted(set(c for v in cand for c in cols_of[v]))
        assert all(c.startswith("x__") for c in need), [c for c in need if not c.startswith("x__")]
        man = json.loads((Path(EXPORT[p]) / "lead_0" / "export_manifest.json").read_text(encoding="utf-8"))
        files = sorted((Path(EXPORT[p]) / "lead_0" / "test").glob("*.parquet"))
        frames = []
        for f in files:
            t = pq.read_table(f, columns=["unit", "time", "issue"] + need).to_pandas()
            frames.append(t)
        df = pd.concat(frames, ignore_index=True)
        del frames
        n_rows = len(df)
        assert n_rows == man["counts"]["test"], (p, n_rows, man["counts"]["test"])
        issue_eq_time = bool((df["issue"] == df["time"]).all())
        g = df.groupby("time", sort=True)
        size = g.size()
        cnt = g[need].count()
        mn = g[need].min()
        mx = g[need].max()
        # rule (primary): at every time step one value, a missing value counting as a value of its own
        all_nan = cnt.eq(0)
        no_nan_one = cnt.eq(size, axis=0) & mn.eq(mx)
        pass_col = (all_nan | no_nan_one).all(axis=0)
        # variant: missing values ignored
        pass_col_ign = (all_nan | mn.eq(mx)).all(axis=0)
        nan_any = (cnt.lt(size, axis=0)).any(axis=0)
        res = {"problem": p, "n_test_rows": int(n_rows), "n_time_steps": int(len(size)), "n_units": int(df["unit"].nunique()),
               "issue_equals_time": issue_eq_time,
               "records": sorted([EXPORT_SHORT[p], EXPORT_SHORT[p].replace("\\test\\*.parquet", "\\export_manifest.json")]),
               "columns_read": sorted(["unit", "time", "issue"] + need),
               "candidates": cand, "columns_of": cols_of,
               "column_pass": {c: bool(pass_col[c]) for c in need},
               "column_pass_ignore_missing": {c: bool(pass_col_ign[c]) for c in need},
               "column_has_missing": {c: bool(nan_any[c]) for c in need},
               "rows_per_time_min": int(size.min()), "rows_per_time_max": int(size.max()),
               "time_steps_with_one_row": int((size == 1).sum())}
        gi = sorted(v for v in cand if all(res["column_pass"][c] for c in cols_of[v]))
        gi_ign = sorted(v for v in cand if all(res["column_pass_ignore_missing"][c] for c in cols_of[v]))
        res["global_indices"] = gi
        res["global_indices_ignore_missing"] = gi_ign
        res["seconds"] = round(time.time() - t0, 1)
        (OUT / ("global_%s.json" % p)).write_text(json.dumps(res, indent=1, sort_keys=True), encoding="utf-8")
        print(p, "rows", n_rows, "time steps", len(size), "units", res["n_units"], "issue==time", issue_eq_time,
              "| rows/time", res["rows_per_time_min"], res["rows_per_time_max"], "| one-row steps", res["time_steps_with_one_row"])
        print("   global indices:", gi)
        if gi != gi_ign:
            print("   ignoring missing values instead:", gi_ign)
        print("   %.1f s" % res["seconds"])
        del df, g, cnt, mn, mx


if __name__ == "__main__":
    main(sys.argv[1:] or ["coral", "defo", "fire", "pm25", "ndvi"])
