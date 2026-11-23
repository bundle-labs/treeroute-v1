"""Print the structural fields of NDVI's model meta.json files that bear on the context columns.

Read only. Prints the top-level keys, the context ('c__') players, the variable each maps to, and the
merged duplicates. No SHAP value is printed.
"""
import json
import sys

ROOT = r"D:\treeroute\analysis\shap_v1\out\ndvi\lead_0"
MODELS = ["treeroute", "rival_lgbm", "rival_rf", "rival_ridge", "rival_bardl_h1", "treeroute_B1"]


def main():
    for m in MODELS:
        path = ROOT + "\\" + m + "\\meta.json"
        with open(path, "r", encoding="utf-8") as fh:
            meta = json.load(fh)
        print("==", m)
        print("  keys:", sorted(meta.keys()))
        players = meta.get("players")
        variables = meta.get("variables")
        vmap = meta.get("variable_map") or meta.get("var_map") or meta.get("variable_of")
        if isinstance(players, list):
            ctx = [p for p in players if isinstance(p, str) and p.startswith("c__")]
            print("  players:", len(players), " c__ players:", len(ctx))
            for p in ctx:
                v = vmap.get(p) if isinstance(vmap, dict) else None
                print("    ", p, "->", v)
        else:
            print("  players type:", type(players).__name__)
        if isinstance(variables, list):
            cv = [v for v in variables if isinstance(v, str) and (v.startswith("ctx") or v == "calendar")]
            print("  variables:", len(variables), " context/calendar variables:", cv)
        dm = meta.get("duplicates_merged")
        print("  duplicates_merged:", dm if not isinstance(dm, (list, dict)) else (len(dm), dm))
        for k in ("families", "family_of", "family_map"):
            if k in meta:
                f = meta[k]
                if isinstance(f, dict):
                    cc = {kk: vv for kk, vv in f.items() if isinstance(vv, str) and "context" in vv.lower()}
                    print("  ", k, "context-family members:", cc)
                else:
                    print("  ", k, type(f).__name__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
