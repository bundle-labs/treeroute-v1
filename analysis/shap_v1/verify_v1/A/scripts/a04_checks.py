# Round 14, implementer A: structural checks of rows, regions and draws (no statistic of section 8).
import json, os, hashlib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

SHAP = r"D:\treeroute\analysis\shap_v1"
PROBLEMS = ["coral", "defo", "fire", "pm25", "ndvi"]


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    for p in PROBLEMS:
        base = os.path.join(SHAP, "out", p, "lead_0")
        with open(os.path.join(base, "compare", "per_lead.json"), "r", encoding="utf-8") as fh:
            pl = json.load(fh)
        models = list(pl["models"])
        dsha = pl["draws_sha256"]
        del pl
        print("=" * 20, p)
        keys0 = None
        for m in models + (["treeroute_B1"] if os.path.isdir(os.path.join(base, "treeroute_B1")) else []):
            t = pq.read_table(os.path.join(base, m, "rows.parquet"),
                              columns=["row", "unit", "group", "time", "year", "pre", "resid_flag"]).to_pandas()
            k = t[["row", "unit", "group", "time", "year"]]
            if keys0 is None:
                keys0 = k.copy()
                first = list(dict.fromkeys(k["group"].tolist()))
                srt = sorted(set(k["group"].tolist()))
                print("  rows sorted 0..n-1:", bool((k["row"].values == np.arange(len(k))).all()), "n", len(k))
                print("  G", len(srt), "first-appearance order == sorted order:", first == srt)
                rows_per_region = k.groupby("group").size()
                print("  rows per region: min", int(rows_per_region.min()), "max", int(rows_per_region.max()))
            same = k.reset_index(drop=True).equals(keys0.reset_index(drop=True))
            print("  %-20s same keys/order as first: %s; resid_flag sum %d; pre>0 rows %d; pre NaN %d" % (
                m, same, int(t["resid_flag"].sum()), int((t["pre"] > 0).sum()), int(t["pre"].isna().sum())))
        dp = os.path.join(base, "compare", "bootstrap_draws.npy")
        d = np.load(dp)
        sf = sha_file(dp)
        sd = hashlib.sha256(np.ascontiguousarray(d).tobytes()).hexdigest()
        print("  draws", d.shape, d.dtype, "C-contig", d.flags["C_CONTIGUOUS"], "file sha == per_lead:", sf == dsha,
              " data-bytes sha == per_lead:", sd == dsha)
        # each draw: G regions with replacement; distinct counts
        nd = np.array([len(np.unique(r)) for r in d])
        print("  distinct regions per draw: min", nd.min(), "median", np.median(nd), "max", nd.max())


if __name__ == "__main__":
    main()
