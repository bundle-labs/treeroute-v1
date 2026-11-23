"""Compare sensitivity lead tables with the published headline lead tables (read only; prints, writes nothing).

    python -I -B compare_features.py <sensitivity build folder>
      e.g. ...\\validate\\tiny_check\\tiny   (validation)   or   ...\\coral_data\\full   (after the owner's stage 2)

For each lead 0/183/365: every row present in both tables must be equal in EVERY column except `mark`, bit for bit
(floats compared as bytes, NaN included); `mark` may differ only for 2016 visits (headline test -> sensitivity
train). Rows only in the sensitivity table must all be 2020 visits (the headline did not write them); rows only in
the headline table must not exist. Same column names, order and Arrow types. Exit 0 when all hold, 1 otherwise.
The stage-2 features depend on the row (site, dates, lead) and the sources only, not on the mark, so a full
sensitivity build must pass this with 0 differing cells.
"""
import os
import sys

import numpy as np
import pyarrow.parquet as pq

HEAD = r"D:\treeroute\coral_build\coral_store\20261020_014201"
LEADS = (0, 183, 365)


def main(folder):
    ok = True
    for L in LEADS:
        th = pq.read_table(os.path.join(HEAD, "lead_%d.parquet" % L))
        ts = pq.read_table(os.path.join(folder, "lead_%d.parquet" % L))
        if th.schema != ts.schema:
            print("lead %d: SCHEMA DIFFERS" % L)
            ok = False
            continue
        h = th.to_pandas().set_index("row_id")
        s = ts.to_pandas().set_index("row_id")
        common = s.index.intersection(h.index)
        only_s = s.index.difference(h.index)
        only_h_in_scope = 0          # (a tiny build holds a subset; full builds must hold every headline row)
        if len(s) > 1000:
            only_h_in_scope = len(h.index.difference(s.index))
        years_only_s = sorted(set(s.loc[only_s, "target_date"].map(lambda d: d.year))) if len(only_s) else []
        diff_cells = 0
        diff_cols = []
        for c in h.columns:
            if c == "mark":
                continue
            a, b = h.loc[common, c], s.loc[common, c]
            if a.dtype.kind == "f":
                same = np.array_equal(a.to_numpy().view("u8"), b.to_numpy().view("u8"))
                n = int((a.to_numpy().view("u8") != b.to_numpy().view("u8")).sum())
            else:
                same = a.equals(b)
                n = int((a != b).sum())
            if not same:
                diff_cells += n
                diff_cols.append(c)
        mk = h.loc[common, "mark"] != s.loc[common, "mark"]
        yrs = s.loc[common, "target_date"].map(lambda d: d.year)
        mark_bad = int((mk & (yrs != 2016)).sum())
        mark_2016 = (h.loc[common][yrs == 2016].mark.unique().tolist(), s.loc[common][yrs == 2016].mark.unique().tolist())
        lead_ok = (diff_cells == 0 and mark_bad == 0 and years_only_s in ([], [2020]) and only_h_in_scope == 0)
        ok &= lead_ok
        print("lead %d: %s | sens rows %d, headline rows %d, common %d | cells differing (non-mark) %d %s | mark "
              "changes %d (outside 2016: %d; 2016 headline->sens %s) | rows only in sens: %d, years %s | headline rows "
              "missing from a full sens build: %d"
              % (L, "OK" if lead_ok else "FAIL", len(s), len(h), len(common), diff_cells, diff_cols, int(mk.sum()),
                 mark_bad, mark_2016, len(only_s), years_only_s, only_h_in_scope))
    print("RESULT: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
