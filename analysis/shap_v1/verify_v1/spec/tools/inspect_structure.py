# Round 14 spec writer: structure-only inspection (names, dtypes, shapes; no statistic, no row value).
# Reads: the schema of each piece's rows.parquet (pyarrow.parquet.read_schema, no data pages),
#        each piece's meta.json and rows.parquet.done.json (key names and types only here),
#        each compare\per_lead.json (only the structural keys are printed),
#        each compare\bootstrap_draws.npy (shape and dtype only, mmap).
# Run: py -3.9 -I -B inspect_structure.py
import json
import os
import re
import sys
from collections import Counter, OrderedDict

import numpy as np
import pyarrow.parquet as pq

SHAP = r"D:\treeroute\analysis\shap_v1"
PROBLEMS = ["coral", "defo", "fire", "pm25", "ndvi"]
WHITELIST = ["models", "main_set", "declined_by_guard", "links", "rows", "sample_sha256"]
SHA_RE = re.compile(r"sha[-_]?256|hash|digest", re.I)
MAP_RE = re.compile(r"map", re.I)
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def schema_summary(path):
    sch = pq.read_schema(path)
    names = list(sch.names)
    types = {n: str(sch.field(n).type) for n in names}
    other = [n for n in names if not (n.startswith("phi__") or n.startswith("phiv__"))]
    phi = [n for n in names if n.startswith("phi__")]
    phiv = [n for n in names if n.startswith("phiv__")]
    sub = Counter()
    for n in phi:
        rest = n[len("phi__"):]
        if rest.startswith("x__"):
            sub["phi__x__*"] += 1
        elif rest.startswith("c__ctx:top5:"):
            sub["phi__c__ctx:top5:*"] += 1
        elif rest.startswith("c__"):
            sub["phi__c__* (other)"] += 1
        else:
            sub["phi__" + rest] += 1
    vsub = Counter()
    for n in phiv:
        rest = n[len("phiv__"):]
        if rest.startswith("ctx:"):
            vsub["phiv__ctx:*"] += 1
        elif rest in ("normal", "calendar"):
            vsub["phiv__" + rest] += 1
        elif rest.startswith("hist_"):
            vsub["phiv__hist_*"] += 1
        else:
            vsub["phiv__<variable> (other)"] += 1
    return {
        "n_columns": len(names),
        "other_columns": [(n, types[n]) for n in other],
        "phi_count": len(phi),
        "phi_dtypes": sorted(set(types[n] for n in phi)),
        "phi_subpatterns": dict(sub),
        "phiv_count": len(phiv),
        "phiv_dtypes": sorted(set(types[n] for n in phiv)),
        "phiv_subpatterns": dict(vsub),
        "num_rows_in_footer": pq.ParquetFile(path).metadata.num_rows,
    }


def type_summary(v):
    if isinstance(v, dict):
        return "dict[%d]" % len(v)
    if isinstance(v, list):
        return "list[%d]" % len(v)
    return type(v).__name__


def find_paths(obj, pred, path=()):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = path + (str(k),)
            if pred(str(k), v):
                out.append((p, v))
            else:
                out.extend(find_paths(v, pred, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(find_paths(v, pred, path + ("[%d]" % i,)))
    return out


def main():
    for p in PROBLEMS:
        lead = os.path.join(SHAP, "out", p, "lead_0")
        print("=" * 100)
        print("PROBLEM", p)
        # per_lead.json: structural keys only
        pl_path = os.path.join(lead, "compare", "per_lead.json")
        with open(pl_path, "r", encoding="utf-8") as f:
            pl = json.load(f, object_pairs_hook=OrderedDict)
        print("-- per_lead.json structural keys")
        for k in WHITELIST:
            if k in pl:
                print("   %s = %s" % (k, json.dumps(pl[k])))
            else:
                print("   %s : ABSENT at top level" % k)
        shas = find_paths(pl, lambda k, v: bool(SHA_RE.search(k)) and isinstance(v, str) and bool(HEX64.match(v)))
        for path, v in shas:
            print("   sha path %s = %s" % ("/".join(path), v))
        maps = find_paths(pl, lambda k, v: bool(MAP_RE.search(k)))
        for path, v in maps:
            print("   map path %s : %s" % ("/".join(path), type_summary(v)))
        n_other = len([k for k in pl.keys() if k not in WHITELIST])
        print("   (other top-level keys, not printed: %d)" % n_other)
        # bootstrap draws: shape and dtype only
        bd = np.load(os.path.join(lead, "compare", "bootstrap_draws.npy"), mmap_mode="r")
        print("-- bootstrap_draws.npy shape=%s dtype=%s" % (tuple(bd.shape), bd.dtype))
        del bd
        # pieces
        for piece in sorted(os.listdir(lead)):
            if piece == "compare":
                continue
            d = os.path.join(lead, piece)
            print("-- piece", piece, ":", sorted(os.listdir(d)))
            rp = os.path.join(d, "rows.parquet")
            if os.path.exists(rp):
                s = schema_summary(rp)
                print("   rows.parquet: n_columns=%d footer_rows=%d" % (s["n_columns"], s["num_rows_in_footer"]))
                print("   other columns:", s["other_columns"])
                print("   phi__: %d cols, dtypes %s, %s" % (s["phi_count"], s["phi_dtypes"], s["phi_subpatterns"]))
                print("   phiv__: %d cols, dtypes %s, %s" % (s["phiv_count"], s["phiv_dtypes"], s["phiv_subpatterns"]))
            mp = os.path.join(d, "meta.json")
            if os.path.exists(mp):
                with open(mp, "r", encoding="utf-8") as f:
                    meta = json.load(f, object_pairs_hook=OrderedDict)
                print("   meta.json keys:", [(k, type_summary(v)) for k, v in meta.items()])
            dp = os.path.join(d, "rows.parquet.done.json")
            if os.path.exists(dp):
                with open(dp, "r", encoding="utf-8") as f:
                    done = json.load(f, object_pairs_hook=OrderedDict)
                print("   done.json keys:", [(k, type_summary(v)) for k, v in done.items()])
    return 0


if __name__ == "__main__":
    sys.exit(main())
