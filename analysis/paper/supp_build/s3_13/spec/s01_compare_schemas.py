"""Spec writer's helper (read-only): schemas and key columns of the compare files of every problem.

Usage: py -3.9 -I -B s01_compare_schemas.py
Prints, per problem: the columns, dtypes and row count of importance.parquet, families.parquet, pairs.parquet and
bootstrap_stats.parquet; the distinct values of their key columns; a few full rows of pairs.parquet; and the
keys of pairs.parquet.done.json. Opens nothing but SHAP\\out\\<p>\\lead_0\\compare\\ files. Writes nothing.
"""
import json
import os

import pandas as pd

SHAP = r"D:\treeroute\analysis\shap_v1"
PROBLEMS = ["coral", "fire", "pm25", "defo", "ndvi"]
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_colwidth", 60)


def show(df, name):
    print("  --- %s: %d rows x %d cols" % (name, len(df), df.shape[1]))
    for c in df.columns:
        print("     %-28s %s" % (c, df[c].dtype))


def main():
    for p in PROBLEMS:
        cdir = os.path.join(SHAP, "out", p, "lead_0", "compare")
        print("=" * 100)
        print(p)
        imp = pd.read_parquet(os.path.join(cdir, "importance.parquet"))
        show(imp, "importance.parquet")
        for c in imp.columns:
            if imp[c].dtype == object and imp[c].nunique() < 12:
                print("     distinct %s: %s" % (c, sorted(imp[c].unique().tolist())))
        print(imp.head(3).to_string())
        fam = pd.read_parquet(os.path.join(cdir, "families.parquet"))
        show(fam, "families.parquet")
        print(fam.to_string())
        pairs = pd.read_parquet(os.path.join(cdir, "pairs.parquet"))
        show(pairs, "pairs.parquet")
        for c in pairs.columns:
            if pairs[c].dtype == object and pairs[c].nunique() < 40:
                print("     distinct %s: %s" % (c, pairs[c].unique().tolist()))
        print(pairs.head(4).T.to_string())
        bs = pd.read_parquet(os.path.join(cdir, "bootstrap_stats.parquet"))
        show(bs, "bootstrap_stats.parquet")
        for c in bs.columns:
            if bs[c].dtype == object and bs[c].nunique() < 40:
                print("     distinct %s: %s" % (c, bs[c].unique().tolist()))
        print(bs.head(3).to_string())
        with open(os.path.join(cdir, "pairs.parquet.done.json"), encoding="utf-8") as f:
            d = json.load(f)
        print("  pairs.parquet.done.json keys:", sorted(d.keys()))


if __name__ == "__main__":
    main()
