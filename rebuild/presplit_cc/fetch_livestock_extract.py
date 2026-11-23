"""Extract the AGLW livestock rasters we need from the downloaded LivestockMap.zip (7.4 GB, Downloads).
Pulls ONLY cattle/buffalo/horse/sheep/goat for 2002-2021, skips macOS AppleDouble junk (._* / __MACOSX),
flattens into D:\\ndvi_drivers\\livestock_aglw\\. Reads the zip on C: (no C: writes), extracts to D:.
Crash-safe: skips members already extracted. First prints the zip's species/year inventory so you can see
what's inside before it commits.
RUN: py -3.9 presplit_cc/fetch_livestock_extract.py
"""
import os
import re
import shutil
import zipfile

ZIP = r"C:\Users\<user>\Downloads\LivestockMap.zip"
OUT = r"D:\ndvi_drivers\livestock_aglw"
SPECIES = ("cattl", "buff", "hors", "sheep", "goat")   # substrings (lowercased) of wanted species
Y0, Y1 = 2002, 2021
YEAR_RE = re.compile(r"(19|20)\d{2}")


def base_ok(name):
    b = os.path.basename(name)
    return b.lower().endswith(".tif") and not b.startswith("._") and "__MACOSX" not in name


def main():
    if not os.path.exists(ZIP):
        raise SystemExit(f"zip not found: {ZIP}")
    os.makedirs(OUT, exist_ok=True)
    zf = zipfile.ZipFile(ZIP)
    reals = [n for n in zf.namelist() if base_ok(n)]

    # inventory
    inv = {}
    for n in reals:
        b = os.path.basename(n)
        m = YEAR_RE.search(b)
        yr = int(m.group(0)) if m else None
        sp = b[:m.start()].strip("_ ").lower() if m else b.lower()
        inv.setdefault(sp, []).append(yr)
    print("ZIP inventory (real .tif, species -> year span, count):")
    for sp in sorted(inv):
        ys = [y for y in inv[sp] if y]
        print(f"  {sp:12s} {min(ys) if ys else '?'}-{max(ys) if ys else '?'}  ({len(inv[sp])} files)")

    # extract wanted
    todo = []
    for n in reals:
        b = os.path.basename(n)
        m = YEAR_RE.search(b)
        if not m:
            continue
        yr = int(m.group(0))
        sp = b[:m.start()].lower()
        if Y0 <= yr <= Y1 and any(s in sp for s in SPECIES):
            todo.append((n, b))
    print(f"\nextracting {len(todo)} files (species {SPECIES}, {Y0}-{Y1}) -> {OUT}", flush=True)
    done = skip = 0
    for n, b in todo:
        dst = os.path.join(OUT, b)
        if os.path.exists(dst) and os.path.getsize(dst) > 1000:
            skip += 1
            continue
        with zf.open(n) as src, open(dst, "wb") as out:
            shutil.copyfileobj(src, out, 1 << 20)
        done += 1
        if done % 20 == 0:
            print(f"  {done} extracted ...", flush=True)
    tot = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) / 1e6
    print(f"\ndone: {done} extracted, {skip} already present | {OUT} = {tot:.0f} MB")
    print("The 7.4 GB zip on C: can be deleted now to reclaim space (all wanted rasters are on D:).")


if __name__ == "__main__":
    main()
