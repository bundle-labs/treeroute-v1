# Round 14, implementer A: variable maps per problem (meta.json; names only, no statistic).
import json, os, sys
from collections import defaultdict
import pyarrow.parquet as pq

SHAP = r"D:\treeroute\analysis\shap_v1"


def load_meta(p, m):
    with open(os.path.join(SHAP, "out", p, "lead_0", m, "meta.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


def main():
    probs = sys.argv[1:] or ["coral", "defo", "fire", "pm25", "ndvi"]
    for p in probs:
        base = os.path.join(SHAP, "out", p, "lead_0")
        pieces = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)) and d != "compare")
        maps = {}
        for m in pieces:
            meta = load_meta(p, m)
            vm = meta["variable_map"]
            # check consistency with row-file columns
            cols = pq.ParquetFile(os.path.join(base, m, "rows.parquet")).schema_arrow.names
            phi = [c[5:] for c in cols if c.startswith("phi__")]
            phiv = [c[6:] for c in cols if c.startswith("phiv__")]
            ok_players = sorted(phi) == sorted(meta["players"]) == sorted(vm.keys())
            ok_vars = sorted(phiv) == sorted(meta["variables"]) == sorted(set(vm.values()))
            print(p, m, "players==cols:", ok_players, "variables==cols:", ok_vars, "n_players", len(phi), "n_vars", len(phiv))
            maps[m] = vm
        # are maps consistent across pieces for shared players?
        allp = defaultdict(set)
        for m, vm in maps.items():
            for k, v in vm.items():
                allp[k].add(v)
        incons = {k: v for k, v in allp.items() if len(v) > 1}
        print(p, "players with inconsistent variable across pieces:", incons)
        var_players = defaultdict(set)
        for k, vs in allp.items():
            for v in vs:
                var_players[v].add(k)
        print(p, "variables (union):", len(var_players))
        for v in sorted(var_players):
            print("   ", v, "<-", sorted(var_players[v]))


if __name__ == "__main__":
    main()
