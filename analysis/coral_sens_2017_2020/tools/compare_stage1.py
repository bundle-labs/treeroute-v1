"""Compare the sensitivity stage-1 visit table with the headline one (read only; prints, writes nothing).

    python -I -B compare_stage1.py

Expected: the same 14,839 visits, every column identical except `mark`; the mark changes only for
2016 visits (test -> train) and 2020 visits (unused -> test). Also prints the census cuts and counts of both.
"""
import json

import pandas as pd

HEAD = r"D:\treeroute\coral_build\coral_data"
SENS = r"D:\treeroute\analysis\coral_sens_2017_2020\coral_data"

h = pd.read_parquet(HEAD + r"\visits.parquet").set_index("row_id").sort_index()
s = pd.read_parquet(SENS + r"\visits.parquet").set_index("row_id").sort_index()
print("rows: headline %d, sensitivity %d, same row_id set: %s" % (len(h), len(s), h.index.equals(s.index)))
print("columns equal: %s" % (list(h.columns) == list(s.columns)))
other = [c for c in h.columns if c != "mark"]
diff_cols = [c for c in other if not h[c].equals(s[c])]
print("columns other than mark that differ: %s" % diff_cols)
yr = pd.to_datetime(h.target_date).dt.year
chg = h.mark != s.mark
print("mark changes by (year, headline mark -> sensitivity mark):")
print(pd.DataFrame({"year": yr[chg], "head": h.mark[chg], "sens": s.mark[chg]}).value_counts().sort_index()
      .to_string())
print("unchanged marks outside 2016 and 2020: %s" % bool((~chg | yr.isin([2016, 2020])).all()))
ch = json.load(open(HEAD + r"\visits_census.json"))
cs = json.load(open(SENS + r"\visits_census.json"))
for k in ("test_years", "cuts", "sample_rows", "sample_first_year", "split", "visits_unused_after_window",
          "rows_present_L0", "rows_present_L183", "rows_present_L365", "groups_zero_rows_at_a_cut",
          "groups_one_unit", "month_precision_in_inner_score_years"):
    print("%s\n  headline:    %s\n  sensitivity: %s" % (k, ch.get(k), cs.get(k)))
sample = s[s.present_L0 & (s.mark != "unused")]
print("sensitivity present_L0 rows by year and mark (2012 on):")
print(sample.groupby([pd.to_datetime(sample.target_date).dt.year, "mark"]).size().loc[2012:].to_string())
