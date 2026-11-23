"""VALIDATION ONLY: a small visit table for a tiny stage-2 build through the builder copy (never a run input).

    python -I -B make_tiny_check_visits.py

Takes the sensitivity stage-1 table (coral_data/visits.parquet) and keeps: every 2020 visit (the rows the headline
tables do not have) plus every 100th written visit by sorted row_id (a fixed stride, no random draw). Writes
validate/tiny_check/visits.parquet, a copy of visits_census.json, and tiny_groups.txt (the --groups argument).
The tiny build then (a) proves the --visits-dir copy end to end, (b) gives the 2020 rows' features for the plan
preview, and (c) lets compare_features.py check that the copy reproduces the headline features byte for byte.
"""
import os
import shutil

import pandas as pd

SENS = r"D:\treeroute\analysis\coral_sens_2017_2020\coral_data"
OUT = r"D:\treeroute\analysis\coral_sens_2017_2020\validate\tiny_check"
STRIDE = 100

os.makedirs(OUT, exist_ok=True)
v = pd.read_parquet(os.path.join(SENS, "visits.parquet"))
written = v[v.present_L0 & (v.mark != "unused")]
ids = sorted(written.row_id)
pick = set(ids[::STRIDE])
yr = pd.to_datetime(v.target_date).dt.year
keep = v[(yr == 2020) | v.row_id.isin(pick)].reset_index(drop=True)
keep.to_parquet(os.path.join(OUT, "visits.parquet"), index=False)
shutil.copyfile(os.path.join(SENS, "visits_census.json"), os.path.join(OUT, "visits_census.json"))
groups = sorted(keep.group.unique())
with open(os.path.join(OUT, "tiny_groups.txt"), "w", encoding="utf-8") as f:
    f.write(";".join(groups))
print("kept %d visits (%d of 2020, %d stride), %d groups, %d sites; written-at-L0 among them: %d"
      % (len(keep), int((pd.to_datetime(keep.target_date).dt.year == 2020).sum()), len(pick), len(groups),
         keep.site_key.nunique(), int((keep.present_L0 & (keep.mark != 'unused')).sum())))
print(keep.groupby([pd.to_datetime(keep.target_date).dt.year.rename("year"), "mark"]).size().loc[2014:].to_string())
