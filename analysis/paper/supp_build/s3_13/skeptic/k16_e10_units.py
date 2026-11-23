# Skeptic (version 2 check of C6): the location that gate E10 checked on PM2.5, NDVI and burned fraction is a sampled
# location, and its test rows; E10's row count against test rows + router fit rows. Read-only; prints only.
import json, sys
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
for p in ["pm25", "ndvi", "fire"]:
    g = json.load(open(SHAP + r"\rebuild\%s\lead_0\gates.json" % p, encoding="utf-8"))
    v = g["gates"]["E10_exported_trees"]["values"]
    R = pd.read_parquet(SHAP + r"\out\%s\lead_0\treeroute\rows.parquet" % p, columns=["unit", "time"])
    m = json.load(open(SHAP + r"\sample\%s\sample_manifest.json" % p, encoding="utf-8"))
    units = set(R.unit)
    n_test = g["result"]["rows_checked"] / g["gates"]["E8_predictions"]["values"]["units"]
    print("%-5s E10 unit sampled: %s (explained rows of that unit: %d) | E10 rows %d = %d test rows per location + %d other rows | sampled locations %d"
          % (p, v["unit"] in units, int((R.unit == v["unit"]).sum()), v["rows_x_trees"][0], n_test, v["rows_x_trees"][0] - n_test, len(units)))
