# Round 14 spec writer: column-NAME inspection only (schemas and meta.json names; no row value, no statistic).
# Prints, per problem: the phi__/phiv__ names that are not phi__x__* (context, calendar, normal, own history),
# the differences in player/variable names between pieces, a few phi__x__ name examples,
# and the NAMES (keys) inside meta.json's checks_passed and duplicates_merged.
# Run: py -3.9 -I -B inspect_names.py
import json
import os
import sys

import pyarrow.parquet as pq

SHAP = r"D:\treeroute\analysis\shap_v1"
PROBLEMS = ["coral", "defo", "fire", "pm25", "ndvi"]


def names(path):
    sch = pq.read_schema(path)
    n = list(sch.names)
    return [c for c in n if c.startswith("phi__")], [c for c in n if c.startswith("phiv__")]


def main():
    for p in PROBLEMS:
        lead = os.path.join(SHAP, "out", p, "lead_0")
        pieces = [d for d in sorted(os.listdir(lead)) if d != "compare"]
        print("=" * 80)
        print("PROBLEM", p, "pieces:", pieces)
        ref = "treeroute"
        phi_ref, phiv_ref = names(os.path.join(lead, ref, "rows.parquet"))
        print("  treeroute phi__ not x__:", [c for c in phi_ref if not c.startswith("phi__x__")])
        print("  treeroute phiv__ special:", [c for c in phiv_ref if c[6:] in ("normal", "calendar")
                                              or c[6:].startswith("ctx:") or c[6:].startswith("hist_")])
        print("  treeroute phi__x__ examples:", sorted(c for c in phi_ref if c.startswith("phi__x__"))[:3])
        print("  treeroute phiv__ examples:", sorted(phiv_ref)[:3])
        print("  treeroute phi__ order sorted?", phi_ref == sorted(phi_ref), " phiv__ order sorted?", phiv_ref == sorted(phiv_ref))
        for d in pieces:
            if d == ref:
                continue
            phi, phiv = names(os.path.join(lead, d, "rows.parquet"))
            only_p = sorted(set(phi) - set(phi_ref))
            only_r = sorted(set(phi_ref) - set(phi))
            only_vp = sorted(set(phiv) - set(phiv_ref))
            only_vr = sorted(set(phiv_ref) - set(phiv))
            same_order = (phi == phi_ref, phiv == phiv_ref)
            print("  %-20s phi only here %s | phi only in treeroute: %d names %s | phiv only here %s | phiv only in treeroute: %d %s | same order %s"
                  % (d, only_p[:12], len(only_r), only_r[:5], only_vp[:12], len(only_vr), only_vr[:5], same_order))
        for d in pieces:
            mp = os.path.join(lead, d, "meta.json")
            with open(mp, "r", encoding="utf-8") as f:
                meta = json.load(f)
            cp = meta.get("checks_passed")
            dm = meta.get("duplicates_merged")
            cp_desc = sorted(cp.keys()) if isinstance(cp, dict) else type(cp).__name__
            cp_types = sorted(set(type(v).__name__ for v in cp.values())) if isinstance(cp, dict) else None
            if isinstance(dm, dict):
                dm_keys = sorted(dm.keys())
                dm_vtypes = sorted(set(type(v).__name__ for v in dm.values()))
            else:
                dm_keys, dm_vtypes = type(dm).__name__, None
            print("  %-20s checks_passed keys %s types %s | duplicates_merged keys %s value types %s | background type %s"
                  % (d, cp_desc, cp_types, dm_keys, dm_vtypes, type(meta.get("background")).__name__))
    return 0


if __name__ == "__main__":
    sys.exit(main())
