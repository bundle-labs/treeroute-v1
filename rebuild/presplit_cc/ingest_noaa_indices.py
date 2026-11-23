"""Ingest the monthly NOAA / CPC climate-teleconnection INDICES (the 98 tier1_/sst_anom
columns collapse to ~20 index families). These are GLOBAL scalar time series -- same value
every cell -- so this writes ONE small table [year, month, <index cols>] (264 rows for
2002-2023) to broadcast across all cells at model-build time. No grid sampling, no auth.

Sources: NOAA PSL standard '.data' files (12 monthly values per year row) and NOAA CPC
'year month value' ascii files. Robust: each index is fetched independently; failures are
logged and skipped (the table just omits that column), so a dead URL never kills the run.

  py -3.9 presplit_cc/ingest_noaa_indices.py            # writes noaa_indices_monthly.parquet
  py -3.9 presplit_cc/ingest_noaa_indices.py --out PATH.parquet
"""
import os
import re
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
import yaml  # noqa: E402
cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
BUNDLE = os.path.dirname(cfg["data"]["master_dir"])
YEAR_LO, YEAR_HI = 2002, 2023

PSL = "https://psl.noaa.gov/data/correlation/{f}"
CPC = "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/{f}"

# index name -> (url, format).  format: 'psl' (year + 12 vals) or 'cpc' (year month val)
INDICES = {
    "nino12": (PSL.format(f="nina1.anom.data"), "psl"),
    "nino3":  (PSL.format(f="nina3.anom.data"), "psl"),
    "nino4":  (PSL.format(f="nina4.anom.data"), "psl"),
    "nino34": (PSL.format(f="nina34.anom.data"), "psl"),
    "oni":    (PSL.format(f="oni.data"), "psl"),
    "soi":    (PSL.format(f="soi.data"), "psl"),
    "tni":    (PSL.format(f="tni.data"), "psl"),
    "pdo":    (PSL.format(f="pdo.data"), "psl"),
    "amo":    (PSL.format(f="amon.us.data"), "psl"),
    "tna":    (PSL.format(f="tna.data"), "psl"),
    "tsa":    (PSL.format(f="tsa.data"), "psl"),
    "iod":    ("https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data", "psl"),
    "noi":    (PSL.format(f="noi.data"), "psl"),
    "ao":     (CPC.format(f="daily_ao_index/monthly.ao.index.b50.current.ascii"), "cpc"),
    "nao":    (CPC.format(f="pna/norm.nao.monthly.b5001.current.ascii"), "cpc"),
    "pna":    (CPC.format(f="pna/norm.pna.monthly.b5001.current.ascii"), "cpc"),
    "wp":     ("tele", "tele"),     # CPC combined NH teleconnection file
    "epo":    ("tele", "tele"),     # CPC EP/NP column
    "sam":    (CPC.format(f="daily_ao_index/aao/monthly.aao.index.b79.current.ascii"), "cpc"),
}

# CPC combined NH teleconnection indices (NAO EA WP EP/NP PNA ...): one file, many columns
_TELE = {}


def _tele(name):
    if "rows" not in _TELE:
        txt = _get("https://ftp.cpc.ncep.noaa.gov/wd52dg/data/indices/tele_index.nh")
        rows = []
        for line in txt.splitlines():
            p = line.split()
            if len(p) < 3:
                continue
            try:
                y, m = int(p[0]), int(p[1])
            except ValueError:
                continue
            if 1800 < y < 2100 and 1 <= m <= 12:
                # FIXED-WIDTH file: missing flag '-99.90' jams onto the prior value
                # (e.g. '0.56-99.90'), so .split() mis-aligns columns. Extract decimals by
                # regex instead -> '0.56' and '-99.90' separate cleanly. (Year/month are
                # integers with no '.', so they're not captured; trailing variance% is, and
                # sits past the patterns we read.)
                rows.append((y, m, [_clean(float(x)) for x in re.findall(r"-?\d+\.\d+", line)]))
        _TELE["rows"] = rows
    col = {"wp": 2, "epo": 3}[name]                  # NAO=0 EA=1 WP=2 EP/NP=3 PNA=4 (legend cols 3,4,5,6,7)
    return [(y, m, (v[col] if col < len(v) else np.nan)) for y, m, v in _TELE["rows"]]


def _get(url, retries=4):
    import requests
    last = None
    for a in range(retries):
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            return r.text
        except Exception as e:
            last = e; time.sleep(2 * (a + 1))
    raise last


def _clean(v):
    return v if (np.isfinite(v) and abs(v) < 50) else np.nan      # sentinels (-99.99/-999) -> NaN


def parse_psl(text):
    out = []
    for line in text.splitlines():
        p = line.split()
        if len(p) >= 13:
            try:
                y = int(p[0])
            except ValueError:
                continue
            if 1800 < y < 2100:
                for m, x in enumerate(p[1:13], 1):
                    try:
                        out.append((y, m, _clean(float(x))))
                    except ValueError:
                        pass
    return out


def parse_cpc(text):
    out = []
    for line in text.splitlines():
        p = line.split()
        if len(p) >= 3:
            try:
                y, m, v = int(p[0]), int(p[1]), float(p[2])
            except ValueError:
                continue
            if 1800 < y < 2100 and 1 <= m <= 12:
                out.append((y, m, _clean(v)))
    return out


def main(argv):
    out = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(BUNDLE, "noaa_indices_monthly.parquet")
    base = pd.MultiIndex.from_product([range(YEAR_LO, YEAR_HI + 1), range(1, 13)], names=["year", "month"])
    df = pd.DataFrame(index=base)
    ok, fail = [], []
    for name, (url, fmt) in INDICES.items():
        try:
            if fmt == "tele":
                rows = _tele(name)
            else:
                rows = (parse_psl if fmt == "psl" else parse_cpc)(_get(url))
            s = pd.Series({(y, m): v for y, m, v in rows})
            s = s[~s.index.duplicated(keep="last")]
            df[name] = s.reindex(base)
            n = int(df[name].notna().sum())
            (ok if n > 0 else fail).append(f"{name}({n})")
            print(f"  {name:8s} {fmt:3s} {n:3d}/264 months  {url.split('/')[-1]}", flush=True)
        except Exception as e:
            fail.append(name)
            print(f"  {name:8s} FAIL {type(e).__name__}: {e}", flush=True)
    df = df.reset_index()
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"\nwrote {out}  ({df.shape[0]} rows x {df.shape[1]-2} indices)")
    print(f"OK ({len([c for c in INDICES if c in df.columns and df[c].notna().any()])}): "
          f"{[c for c in INDICES if c in df.columns and df[c].notna().any()]}")
    print(f"FAILED/empty: {[c for c in INDICES if c not in df.columns or not df[c].notna().any()]}")
    print("NOTE: the 8 sst_anom_* custom regions (atl3, coral_sea, mediterranean, "
          "subpolar_n_atlantic, global_tropical, iod_east/west) need gridded ERSSTv5 + "
          "region-averaging -- separate ingester; nino34 here covers sst_anom_nino34.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
