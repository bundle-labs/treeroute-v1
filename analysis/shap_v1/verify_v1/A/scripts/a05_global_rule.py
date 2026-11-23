# Round 14, implementer A: section 8's global-index rule on the lead-0 test set.
# "global indices (a variable all of whose columns take one value per time step across every unit of the
#  lead's test set)". The lead's test set: the run's lead-0 test export that the rival SHAP step read
# (SHAP\logs\rival_shap_<p>_lead0.log, line "test set: ... (D:\treeroute\rival_export\<p>\<run>\lead_0)"),
# one parquet per region under lead_0\test\. Only the columns `unit`, `time` and the players' feature columns
# are read. Output: V\A\work\global_rule_<p>.json.
import json, os, sys, glob
import numpy as np
import pyarrow.parquet as pq

SHAP = r"D:\treeroute\analysis\shap_v1"
V_A = r"D:\treeroute\analysis\shap_v1\verify_v1\A"
EXPORT = {
    "coral": r"D:\treeroute\rival_export\coral\20261020_f3b8e3da\lead_0\test",
    "defo": r"D:\treeroute\rival_export\defo\20261017_d71c61f4\lead_0\test",
    "fire": r"D:\treeroute\rival_export\fire\20261017_869d1f38\lead_0\test",
    "pm25": r"D:\treeroute\rival_export\pm25\20261007_74e67609\lead_0\test",
    "ndvi": r"D:\treeroute\rival_export\ndvi\20261016_d1de3158\lead_0\test",
}


def problem_models(p):
    with open(os.path.join(SHAP, "out", p, "lead_0", "compare", "per_lead.json"), "r", encoding="utf-8") as fh:
        pl = json.load(fh)
    return list(pl["models"])


def union_variable_map(p, models):
    vm = {}
    for m in models:
        with open(os.path.join(SHAP, "out", p, "lead_0", m, "meta.json"), "r", encoding="utf-8") as fh:
            meta = json.load(fh)
        for k, v in meta["variable_map"].items():
            if k in vm and vm[k] != v:
                raise SystemExit("inconsistent variable map for %s %s" % (p, k))
            vm[k] = v
    return vm


def named_family(v):
    # the families that section 8 names by their variables (they come before the data rule)
    if v.startswith("hist_"):
        return "own_history"
    if v == "normal":
        return "seasonal_normal"
    if v == "calendar" or v.startswith("ctx:"):
        return "context_and_calendar"
    return None


def main():
    probs = sys.argv[1:] or ["coral", "defo", "fire", "pm25", "ndvi"]
    for p in probs:
        models = problem_models(p)
        vm = union_variable_map(p, models)
        cols_needed = sorted(k for k in vm if k != "normal")  # 'normal' (the offset) is no test-set column
        files = sorted(glob.glob(os.path.join(EXPORT[p], "*.parquet")))
        # pass 1: the time steps and the columns present in every file
        times = set()
        present = None
        for f in files:
            names = pq.ParquetFile(f).schema_arrow.names
            have = set(c for c in cols_needed if c in names)
            present = have if present is None else (present & have)
            times.update(pq.read_table(f, columns=["time"]).column("time").to_numpy().tolist())
        tlist = np.array(sorted(times), dtype=np.int64)
        T = len(tlist)
        cols = sorted(present)
        missing = [c for c in cols_needed if c not in present]
        C = len(cols)
        n_nan = np.zeros((C, T)); n_val = np.zeros((C, T))
        mn = np.full((C, T), np.inf); mx = np.full((C, T), -np.inf)
        n_rows = 0
        units = set()
        for f in files:
            t = pq.read_table(f, columns=["unit", "time"] + cols)
            ti = np.searchsorted(tlist, t.column("time").to_numpy())
            units.update(t.column("unit").to_pylist())
            n_rows += len(ti)
            for ci, c in enumerate(cols):
                x = t.column(c).to_numpy(zero_copy_only=False).astype(np.float64)
                isn = np.isnan(x)
                n_nan[ci] += np.bincount(ti, weights=isn.astype(np.float64), minlength=T)
                n_val[ci] += np.bincount(ti, weights=(~isn).astype(np.float64), minlength=T)
                a = np.full(T, np.inf); np.minimum.at(a, ti[~isn], x[~isn]); mn[ci] = np.minimum(mn[ci], a)
                b = np.full(T, -np.inf); np.maximum.at(b, ti[~isn], x[~isn]); mx[ci] = np.maximum(mx[ci], b)
        col_one, col_detail = {}, {}
        for ci, c in enumerate(cols):
            has_val = n_val[ci] > 0
            mixed = has_val & (n_nan[ci] > 0)
            spread = np.where(has_val & ~mixed, mx[ci] - mn[ci], 0.0)
            ok = (not mixed.any()) and bool((spread == 0).all())
            scale = np.maximum(np.maximum(np.abs(mx[ci]), np.abs(mn[ci])), 1e-300)
            rel = np.where(has_val & ~mixed, spread / scale, 0.0)
            col_one[c] = ok
            col_detail[c] = {"steps": int(T), "steps_with_rows": int(((n_val[ci] + n_nan[ci]) > 0).sum()),
                             "steps_mixed_nan": int(mixed.sum()), "steps_all_nan": int((~has_val & (n_nan[ci] > 0)).sum()),
                             "max_rel_spread": float(rel.max()) if T else 0.0}
        for c in missing:
            col_one[c] = None
        variables = sorted(set(vm.values()))
        fam, rule = {}, {}
        for v in variables:
            vcols = sorted(k for k, vv in vm.items() if vv == v)
            data_cols = [c for c in vcols if c != "normal"]
            vals = [col_one.get(c) for c in data_cols]
            g = (len(vals) > 0) and all(x is True for x in vals)
            rule[v] = {"columns": vcols, "one_value_per_step": vals, "global_by_rule": g}
            nf = named_family(v)
            fam[v] = nf if nf is not None else ("global_indices" if g else "local_drivers")
        out = {"problem": p, "region_files": len(files), "rows": n_rows, "units": len(units), "time_steps": int(T),
               "columns_read": sorted(["time", "unit"] + cols), "columns_missing": missing,
               "column_one_value_per_step": col_one, "column_detail": col_detail,
               "variable_rule": rule, "variable_family": fam,
               "global_indices": sorted(v for v, f in fam.items() if f == "global_indices"),
               "named_family_also_passing_rule": sorted(v for v in variables if named_family(v) and rule[v]["global_by_rule"])}
        os.makedirs(os.path.join(V_A, "work"), exist_ok=True)
        with open(os.path.join(V_A, "work", "global_rule_%s.json" % p), "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        print(p, "files", len(files), "rows", n_rows, "units", len(units), "steps", T, "missing cols", missing)
        print("  global:", out["global_indices"])
        print("  named families that also pass the rule:", out["named_family_also_passing_rule"])
        near = sorted((c, d["max_rel_spread"]) for c, d in col_detail.items()
                      if col_one[c] is False and d["steps_mixed_nan"] == 0 and d["max_rel_spread"] < 1e-5)
        print("  columns failing only by a relative spread < 1e-5:", near)
        mixedc = sorted(c for c, d in col_detail.items() if d["steps_mixed_nan"] > 0)
        print("  columns with mixed NaN at some step:", len(mixedc), mixedc[:12])
        alln = sorted(c for c, d in col_detail.items() if d["steps_all_nan"] > 0)
        print("  columns all-NaN at some step:", len(alln), alln[:30])
        partial_global = sorted(v for v, r in rule.items() if not r["global_by_rule"] and any(x is True for x in r["one_value_per_step"]))
        print("  variables with some but not all columns one-valued:", partial_global)


if __name__ == "__main__":
    main()
