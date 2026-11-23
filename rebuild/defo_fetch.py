"""Problem #4 (deforestation) -- STEP 1: fetch the Hansen GFC granules we actually need.

WHAT THIS DOES
  Works out which Hansen Global Forest Change 10x10 degree granules cover the 42 forested regions
  from the forest census, then downloads three layers for each: lossyear, treecover2000, datamask.

WHY THESE THREE AND NOT MORE
  lossyear      -> the target. Pixel value 1..25 = year of FIRST loss, 0 = no loss.
  treecover2000 -> the DENOMINATOR and the MASK only, never a feature. It is a co-product of the same
                   model run that emits lossyear, so as a predictor it hands over the target's own
                   support set; but it is a single year-2000 epoch fixed before the panel window
                   opens, so as an offset it carries zero temporal look-ahead. See DEFORESTATION_SCOPE.md §4.
  datamask      -> to separate "no loss" from "not land" / "not observed". Without it, permanent
                   water and no-data both read as zero loss and inflate the zero mass.

  gain and lossyear-derived "years since loss" are deliberately NOT fetched as features. lossyear is a
  SINGLE STATIC RASTER encoding the whole 2001-2025 history including the test window, so any feature
  read off its value is the time-since-last-fire trap. It is only ever binarised per year and
  truncated at the last training year.

VERSION IS PINNED. GFC-2025-v1.13. Each GFC release re-derives a pixel's loss year using the full
archive including later imagery, so mixing versions mixes label definitions. Pin one, record it,
never mix. (All three of v1.11 / v1.12 / v1.13 were probed live and return HTTP 200.)

CRASH-SAFE AND RESUMABLE. Each file downloads to a .part and is renamed only on a verified
Content-Length match, so an interrupted run loses at most one file and a re-run skips everything
already complete. Safe to stop with Ctrl-C and restart.

RUN IT:
    py -3.9 -u defo_fetch.py
    py -3.9 -u defo_fetch.py --check      # verify what is on disk, download nothing
"""
import os
import sys
import time
import urllib.request
import urllib.error
import numpy as np
import pandas as pd

VERSION = "GFC-2025-v1.13"
BASE = "https://storage.googleapis.com/earthenginepartners-hansen/%s" % VERSION
PREFIX = "Hansen_%s" % VERSION
LAYERS = ["lossyear", "treecover2000", "datamask"]

OUT = "D:/hansen"                      # HDD, not the full C: drive
CENSUS = "D:/run89full/forest_census.csv"
BBOX = "D:/run89full/forest_region_bbox.csv"
FRAC_MIN = 0.25
PAD = 0.02          # half a 4 km cell, in degrees -- see region_tiles()
CHECK_ONLY = "--check" in sys.argv

os.makedirs(OUT, exist_ok=True)


def log(m):
    print(m, flush=True)
    with open(os.path.join(OUT, "_fetch.log"), "a", encoding="utf-8") as f:
        f.write(m + "\n")


def tiles_for(lon0, lon1, lat0, lat1):
    """Hansen granule top-left corners covering a bbox. Tiles are 10x10 deg, named by top-left:
    latitude 80N down to 50S, longitude 180W to 170E."""
    out = set()
    for tlat in range(80, -60, -10):
        if tlat <= lat0 or tlat - 10 >= lat1:
            continue
        for tlon in range(-180, 180, 10):
            if tlon >= lon1 or tlon + 10 <= lon0:
                continue
            ns = "%02dN" % tlat if tlat >= 0 else "%02dS" % abs(tlat)
            ew = "%03dE" % tlon if tlon >= 0 else "%03dW" % abs(tlon)
            out.add("%s_%s" % (ns, ew))
    return out


def region_tiles():
    if os.path.exists(BBOX):
        B = pd.read_csv(BBOX)
    else:
        C = pd.read_csv(CENSUS)
        rows = []
        for r in C[C.frac_tc30 >= FRAC_MIN].region:
            f = "D:/monthly_panel/%s_monthly_2010.parquet" % r
            if not os.path.exists(f):
                continue
            d = pd.read_parquet(f, columns=["cell_id", "lon", "lat"]).drop_duplicates("cell_id")
            lo = pd.to_numeric(d.lon, errors="coerce").values
            la = pd.to_numeric(d.lat, errors="coerce").values
            m = np.isfinite(lo) & np.isfinite(la) & (np.abs(lo) <= 180) & (np.abs(la) <= 90)
            if m.any():
                rows.append(dict(region=r, cells=int(m.sum()), lon_min=lo[m].min(),
                                 lon_max=lo[m].max(), lat_min=la[m].min(), lat_max=la[m].max()))
        B = pd.DataFrame(rows)
        B.to_csv(BBOX, index=False)
    # PAD the bbox by half a 4 km cell. The ingest assigns 30 m pixels to the NEAREST cell centre,
    # so a cell on the region edge legitimately claims pixels up to half a cell beyond the extreme
    # cell centre -- which can fall in the adjacent granule. Without this the fetch reports "0
    # missing" while the ingest silently drops edge pixels. It did: 8 granules across 5 regions,
    # including yucatan_peninsula, which is a TEST region.
    t = set()
    for _, r in B.iterrows():
        t |= tiles_for(r.lon_min - PAD, r.lon_max + PAD, r.lat_min - PAD, r.lat_max + PAD)
    return B, sorted(t)


def remote_size(url, tries=3):
    for i in range(tries):
        try:
            rq = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(rq, timeout=60) as r:
                return int(r.headers.get("Content-Length", 0))
        except Exception as e:
            if i == tries - 1:
                log("    HEAD failed %s -- %s" % (url, e))
                return -1
            time.sleep(3 * (i + 1))
    return -1


def fetch(url, dst, want):
    """Stream to .part, rename only on a verified size match. Resumes a partial with a Range request."""
    part = dst + ".part"
    have = os.path.getsize(part) if os.path.exists(part) else 0
    if have and have >= want:
        os.remove(part)
        have = 0
    hdr = {}
    mode = "wb"
    if have:
        hdr["Range"] = "bytes=%d-" % have
        mode = "ab"
    try:
        rq = urllib.request.Request(url, headers=hdr)
        with urllib.request.urlopen(rq, timeout=180) as r, open(part, mode) as f:
            n = have
            t0 = time.time()
            last = t0
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                n += len(chunk)
                if time.time() - last > 20:
                    last = time.time()
                    log("      %5.1f%%  %6.1f MB  %5.1f MB/s"
                        % (100.0 * n / max(want, 1), n / 1e6, (n - have) / 1e6 / max(time.time() - t0, 1e-9)))
    except Exception as e:
        log("    DOWNLOAD FAILED %s -- %s" % (os.path.basename(dst), e))
        return False
    got = os.path.getsize(part)
    if want > 0 and got != want:
        log("    SIZE MISMATCH %s got %d want %d -- leaving .part for resume"
            % (os.path.basename(dst), got, want))
        return False
    os.replace(part, dst)
    return True


def main():
    B, tiles = region_tiles()
    log("=" * 96)
    log("HANSEN FETCH | version %s | %d forested regions | %d granules | %d files"
        % (VERSION, len(B), len(tiles), len(tiles) * len(LAYERS)))
    log("  destination %s" % OUT)

    jobs = [(lay, t) for t in tiles for lay in LAYERS]
    done = miss = 0
    tot_bytes = 0
    t0 = time.time()
    for i, (lay, t) in enumerate(jobs, 1):
        name = "%s_%s_%s.tif" % (PREFIX, lay, t)
        dst = os.path.join(OUT, name)
        url = "%s/%s" % (BASE, name)
        if os.path.exists(dst):
            tot_bytes += os.path.getsize(dst)
            done += 1
            continue
        if CHECK_ONLY:
            miss += 1
            continue
        want = remote_size(url)
        if want <= 0:
            log("  [%3d/%3d] %-52s UNREACHABLE" % (i, len(jobs), name))
            miss += 1
            continue
        log("  [%3d/%3d] %-52s %6.1f MB" % (i, len(jobs), name, want / 1e6))
        if fetch(url, dst, want):
            tot_bytes += want
            done += 1
        else:
            miss += 1
        el = (time.time() - t0) / 60
        if done:
            log("      %d ok / %d missing | %.1f GB | %.1f min elapsed | ~%.0f min left"
                % (done, miss, tot_bytes / 2 ** 30, el, el / max(i, 1) * (len(jobs) - i)))

    log("=" * 96)
    log("FETCH %s | %d complete, %d missing | %.1f GB on disk | %.1f min"
        % ("CHECK" if CHECK_ONLY else "DONE", done, miss, tot_bytes / 2 ** 30, (time.time() - t0) / 60))
    if miss and not CHECK_ONLY:
        log("  re-run to retry the %d missing files (completed files are skipped)" % miss)


if __name__ == "__main__":
    main()
