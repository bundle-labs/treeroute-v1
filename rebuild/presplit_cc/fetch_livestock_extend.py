"""Extend AGLW livestock to 2022 & 2023 with GENUINE FAOSTAT national data (PATH A, method-consistent).
AGLW ends 2021 and is FAOSTAT-anchored, so the genuine extension = rescale the frozen 2021 per-species
grid by the real FAOSTAT national head-count ratio (Y/2021) -- exactly what AGLW does for a new year while
holding the 2021 subnational pattern fixed. Downloads the live FAOSTAT QCL bulk (no login), computes India
per-species ratios for 2022 & 2023, saves them, and writes 2022/2023 GeoTIFFs by multiplying each *_2021.tif
in D:\\ndvi_drivers\\livestock_aglw\\.

HONEST CAVEAT (also written into the ratios CSV): India 2020-2024 FAOSTAT stocks are FAO estimates/
imputations off the 2019 (20th) Livestock Census (flags I/E), NOT new measurements; and the rescale is
national-UNIFORM, so it adds NO new Thar-specific 2022-2023 signal. Genuine FAOSTAT figures, not fresh
ground truth -> label the layers 'FAOSTAT-rescaled extrapolation (2021 pattern frozen)'.
RUN: py -3.9 presplit_cc/fetch_livestock_extend.py   (after fetch_livestock_extract.py; needs rasterio)
"""
import glob
import os
import zipfile

import pandas as pd
import requests

DIR = r"D:\ndvi_drivers\livestock_aglw"
ZIP = os.path.join(DIR, "faostat_qcl.zip")
URL = "https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_All_Data_(Normalized).zip"
# FAOSTAT item code -> substrings that match the AGLW tif basename (lowercased)
SPECIES = {866: ("cattl",), 946: ("buff",), 976: ("sheep",), 1016: ("goat",), 1096: ("hors",)}


def dl():
    if os.path.exists(ZIP) and os.path.getsize(ZIP) > 1_000_000:
        print(f"have {os.path.basename(ZIP)}", flush=True)
        return
    print("downloading FAOSTAT QCL bulk (~34 MB, no login) ...", flush=True)
    with requests.get(URL, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(ZIP, "wb") as f:
            for ch in r.iter_content(1 << 20):
                f.write(ch)
    print("done", flush=True)


def ratios():
    zf = zipfile.ZipFile(ZIP)
    csvname = max((n for n in zf.namelist() if n.lower().endswith(".csv")), key=lambda n: zf.getinfo(n).file_size)
    print(f"reading {csvname} (chunked, filtering India / Stocks) ...", flush=True)
    items, keep = set(SPECIES), []
    cols = ("Area", "Item Code", "Element Code", "Year", "Value")
    for chunk in pd.read_csv(zf.open(csvname), encoding="latin-1", low_memory=False,
                             usecols=lambda c: c in cols, chunksize=200000):
        m = ((chunk["Area"] == "India") & (chunk["Element Code"] == 5111)
             & (chunk["Item Code"].isin(items)) & (chunk["Year"].isin([2021, 2022, 2023])))
        if m.any():
            keep.append(chunk[m])
    df = pd.concat(keep, ignore_index=True)
    piv = df.pivot_table(index="Item Code", columns="Year", values="Value", aggfunc="first")
    out = {}
    for ic in SPECIES:
        v21, v22, v23 = piv.loc[ic, 2021], piv.loc[ic, 2022], piv.loc[ic, 2023]
        out[ic] = dict(r22=v22 / v21, r23=v23 / v21, v21=v21, v22=v22, v23=v23)
    return out


def main():
    os.makedirs(DIR, exist_ok=True)
    dl()
    r = ratios()
    rt = pd.DataFrame([{"item_code": ic, "species": SPECIES[ic][0], "head_2021": r[ic]["v21"],
                        "head_2022": r[ic]["v22"], "head_2023": r[ic]["v23"],
                        "ratio_2022": round(r[ic]["r22"], 4), "ratio_2023": round(r[ic]["r23"], 4),
                        "note": "FAO estimate off 2019 census; national-uniform, no Thar-specific signal"}
                       for ic in SPECIES])
    rcsv = os.path.join(DIR, "india_faostat_ratios.csv")
    rt.to_csv(rcsv, index=False)
    print("\nIndia FAOSTAT ratios (genuine data):\n" + rt.drop(columns="note").to_string(index=False))
    print(f"saved {rcsv}", flush=True)

    try:
        import rasterio
    except ImportError:
        print("\nrasterio not installed -> ratios saved; run `pip install rasterio` then re-run to write rasters")
        return
    tifs21 = [p for p in glob.glob(os.path.join(DIR, "*.tif")) if "2021" in os.path.basename(p)]
    if not tifs21:
        print("\nno *_2021.tif found in livestock_aglw -> run fetch_livestock_extract.py first, then re-run")
        return
    made = 0
    for p in tifs21:
        b = os.path.basename(p).lower()
        ic = next((k for k, subs in SPECIES.items() if any(s in b for s in subs)), None)
        if ic is None:
            continue
        with rasterio.open(p) as src:
            data = src.read(1).astype("float32")
            prof = src.profile
            prof.update(dtype="float32")
            nod = src.nodata
        for yr, key in ((2022, "r22"), (2023, "r23")):
            arr = data * r[ic][key]
            if nod is not None:
                arr[data == nod] = nod
            out = p.replace("2021", str(yr))
            with rasterio.open(out, "w", **prof) as dst:
                dst.write(arr, 1)
            made += 1
            print(f"  {os.path.basename(out)}  x{r[ic][key]:.4f}", flush=True)
    print(f"\nwrote {made} rescaled GeoTIFFs (2022/2023). Label: 'FAOSTAT-rescaled extrapolation (2021 pattern frozen)'.")


if __name__ == "__main__":
    main()
