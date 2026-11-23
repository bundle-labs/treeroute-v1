"""VALIDATION ONLY: preview lead tables for an engine `plan` (dry run) of the sensitivity package, before stage 2.

    python -I -B make_preview_tables.py

NEVER a run input: the run reads the owner's full stage-2 build (coral_data/full). This preview lets the engine's
own loader and derive step (R3-R7, T-MARK, G-SPLIT, R18 donor-only, G-SUPPORT, the cuts) be checked now, in seconds.

Each preview lead file = the published headline lead file's rows (read only), with `mark` taken from the
sensitivity stage-1 table by row_id (2016 visits become train), plus the 2020 rows of the validation tiny build
(validate/tiny_check/tiny, built by the builder copy; compare_features.py showed that copy reproduces the
headline features bit for bit), sorted by row_id in code-point order (T-ROWID). Writes validate/preview_tables/.
"""
import os

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

HEAD = r"D:\treeroute\coral_build\coral_store\20261020_014201"
SENS_VISITS = r"D:\treeroute\analysis\coral_sens_2017_2020\coral_data\visits.parquet"
TINY = r"D:\treeroute\analysis\coral_sens_2017_2020\validate\tiny_check\tiny"
OUT = r"D:\treeroute\analysis\coral_sens_2017_2020\validate\preview_tables"
LEADS = (0, 183, 365)

os.makedirs(OUT, exist_ok=True)
marks = pd.read_parquet(SENS_VISITS, columns=["row_id", "mark"]).set_index("row_id")["mark"]
for L in LEADS:
    th = pq.read_table(os.path.join(HEAD, "lead_%d.parquet" % L))
    h = th.to_pandas()
    new_mark = marks.reindex(h.row_id).to_numpy()
    if pd.isna(new_mark).any():
        raise SystemExit("a headline row has no sensitivity stage-1 mark")
    changed = int((h.mark.to_numpy() != new_mark).sum())
    h["mark"] = new_mark
    t = pq.read_table(os.path.join(TINY, "lead_%d.parquet" % L)).to_pandas()
    add = t[t.target_date.map(lambda d: d.year) == 2020]
    if set(add.row_id) & set(h.row_id):
        raise SystemExit("a 2020 row is already in the headline table")
    df = pd.concat([h, add], ignore_index=True)
    df = df.iloc[sorted(range(len(df)), key=lambda i: df.row_id.iat[i])].reset_index(drop=True)
    tab = pa.Table.from_pandas(df, schema=th.schema, preserve_index=False)
    pq.write_table(tab, os.path.join(OUT, "lead_%d.parquet" % L))
    print("lead %d: %d headline rows (%d marks changed) + %d rows of 2020 = %d rows; marks %s"
          % (L, len(h), changed, len(add), len(df), df.mark.value_counts().to_dict()))
