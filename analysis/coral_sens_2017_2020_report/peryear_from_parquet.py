"""Part 627 item (iii) cross-check: per-year MAE straight from the sensitivity run's test_preds.parquet (read only).

    py -3.9 -I -B D:\\treeroute\\analysis\\coral_sens_2017_2020_report\\peryear_from_parquet.py

It recomputes, independently of the engine's per_year.csv, the per-year and pooled MAE of the adopted arm
(arm__arcsine_corrector_unweighted, not declined), the training (donor-row) median and predict-zero on the
labelled test rows, then compares them with the values logged in engine/PENDING_PARTS.md Part 627 (2026-11-09).
It writes nothing except peryear_from_parquet.csv beside this script, and imports no engine code.
"""
import os
import sys

sys.dont_write_bytecode = True

import pandas as pd  # noqa: E402

RUN = r"D:\treeroute\analysis\coral_sens_2017_2020\run\coral_sens_2017_2020\headline\20261029_75f66839"
COLUMNS = ("arm__arcsine_corrector_unweighted", "base__donor_median", "base__predict_zero")
LOGGED = {  # from the run's per_year.csv (line "key") as logged on 2026-11-09, rounded to 4 decimals
    "arm__arcsine_corrector_unweighted": {2017: 3.3916, 2018: 1.4075, 2019: 5.3832, 2020: 8.7235, "pooled": 3.4829},
    "base__donor_median": {2017: 3.2529, 2018: 1.5390, 2019: 4.6442, 2020: 3.7069, "pooled": 3.1531},
    "base__predict_zero": {2017: 2.8076, 2018: 0.8439, 2019: 4.3037, 2020: 3.4095, "pooled": 2.6662},
}


def main():
    df = pd.read_parquet(os.path.join(RUN, "test_preds.parquet"))
    missing = [c for c in ("year", "y") + COLUMNS if c not in df.columns]
    if missing:
        print("REFUSED: columns missing from test_preds.parquet: %s" % missing)
        return 2
    lab = df[df["y"].notna()].copy()
    print("labelled test rows: %d (expected 1,468)" % len(lab))
    rows, bad = [], 0
    for col in COLUMNS:
        err = (lab[col] - lab["y"]).abs()
        groups = list(err.groupby(lab["year"].astype(int))) + [("pooled", err)]
        for year, e in groups:
            mae = float(e.mean())
            want = LOGGED[col][year]
            ok = abs(round(mae, 4) - want) <= 0.00005
            bad += 0 if ok else 1
            rows.append({"column": col, "year": year, "n": int(e.size), "mae": mae, "logged": want, "match": ok})
            print("%-36s %-7s n %5d  mae %.6f  logged %.4f  %s" % (col, year, e.size, mae, want, "OK" if ok else "DIFFERS"))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "peryear_from_parquet.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print("written: %s" % out)
    print("RESULT: %s" % ("MATCH (all %d values)" % len(rows) if not bad else "DIFFERS (%d of %d)" % (bad, len(rows))))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
