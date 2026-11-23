"""Ingest the MONTHLY NDVI TARGET (MODIS MOD13A3.061, 1km) via NASA AppEEARS -- no HDF4
needed (AppEEARS returns NetCDF subsetted to YOUR regions, server-side). Auth uses the
Earthdata creds earthaccess saved to ~/.netrc.

Workflow per region (RESUMABLE): submit an 'area' task over the region's bounding box -->
AppEEARS processes it server-side (minutes) --> download the NetCDF --> grid-sample at each
cell --> write <out>/<region>_ndvi.parquet [cell_id, year, month, ndvi_modis].

State is tracked in <out>/_appeears_tasks.json (region -> task_id), so each run:
  1) SUBMITS a task for any region without one, then
  2) HARVESTS any task now 'done' (download + sample + write), skipping finished regions.
Every network call retries on transient errors; a single failed task is just retried next
cycle (the whole run never dies on one blip). Re-run any time to continue.

  py -3.9 presplit_cc/ingest_modis_ndvi_appeears.py --region thar_desert --wait   # one region
  py -3.9 presplit_cc/ingest_modis_ndvi_appeears.py --out OUT --tmp TMP --wait    # all 133, poll to done
"""
import glob
import json
import netrc
import os
import sys
import time
from collections import Counter

import numpy as np
import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ingest_luh3_drivers import grid_indices          # noqa: E402  reuse validated geometry

cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
CC = "cell_id"
API = "https://appeears.earthdatacloud.nasa.gov/api"
PRODUCT, LAYER, OUTCOL = "MOD13A3.061", "_1_km_monthly_NDVI", "ndvi_modis"
START, END = "01-01-2002", "12-31-2023"        # defaults: the window the panel was built from

# --start/--end override the window. THREE THINGS MUST CARRY THE WINDOW or a second window
# silently collides with the first: the AppEEARS task-state key, the task NAME, and the output
# filename. Without that, requesting 2024 would find the 2002-2023 task already registered for the
# region, skip it, and leave you believing you had 2024 data. (This project has now been bitten by
# an under-keyed cache three times -- colscale, the routing checkpoint, and the shifted panel --
# every time producing a plausible result computed from the wrong inputs.)
def _tag(start, end):
    """'2024' for a single year, else '2024-2025'. Empty for the default window so every existing
    file and task key keeps its current name."""
    if (start, end) == ("01-01-2002", "12-31-2023"):
        return ""
    a, b = start.split("-")[-1], end.split("-")[-1]
    return "_" + (a if a == b else f"{a}-{b}")


def _req(method, url, retries=6, **kw):
    """HTTP with retries on any transient error (ConnectionReset/timeout/5xx)."""
    import requests
    kw.setdefault("timeout", 90)
    last = None
    for a in range(retries):
        try:
            r = requests.request(method, url, **kw)
            r.raise_for_status()
            return r
        except Exception as e:
            last = e
            time.sleep(min(5 * (a + 1), 40))
    raise last


def _token():
    nr = netrc.netrc(os.path.join(os.path.expanduser("~"), ".netrc"))
    user, _, pwd = nr.authenticators("urs.earthdata.nasa.gov")
    return _req("post", f"{API}/login", auth=(user, pwd)).json()["token"]


def _geo(cells, pad=0.03):
    x0, x1 = float(cells["lon"].min()) - pad, float(cells["lon"].max()) + pad
    y0, y1 = float(cells["lat"].min()) - pad, float(cells["lat"].max()) + pad
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {},
            "geometry": {"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}}]}


def submit(tok, region, cells, start=START, end=END):
    body = {"task_type": "area", "task_name": f"ndvi_{region}"[:80],
            "params": {"dates": [{"startDate": start, "endDate": end}],
                       "layers": [{"product": PRODUCT, "layer": LAYER}],
                       "output": {"format": {"type": "netcdf4"}, "projection": "geographic"},
                       "geo": _geo(cells)}}
    return _req("post", f"{API}/task", json=body, headers={"Authorization": f"Bearer {tok}"}).json()["task_id"]


def task_status(tok, tid):
    return _req("get", f"{API}/task/{tid}", headers={"Authorization": f"Bearer {tok}"}).json().get("status", "unknown")


def download_nc(tok, tid, tmp):
    H = {"Authorization": f"Bearer {tok}"}
    files = _req("get", f"{API}/bundle/{tid}", headers=H).json()["files"]
    ncs = [f for f in files if f["file_name"].endswith(".nc")]
    if not ncs:
        return None
    fid = ncs[0]["file_id"]
    out = os.path.join(tmp, f"{tid}.nc")
    for a in range(6):
        try:
            with _req("get", f"{API}/bundle/{tid}/{fid}", headers=H, stream=True, timeout=1800) as r:
                with open(out, "wb") as fh:
                    for c in r.iter_content(1 << 20):
                        fh.write(c)
            return out
        except Exception:
            time.sleep(5 * (a + 1))
    raise RuntimeError("download failed after retries")


def sample(ncfile, cells):
    from netCDF4 import Dataset, num2date
    nc = Dataset(ncfile)
    vn = next(v for v in nc.variables if "NDVI" in v.upper())
    lan = next(v for v in nc.variables if v.lower() in ("lat", "latitude", "y"))
    lon_ = next(v for v in nc.variables if v.lower() in ("lon", "longitude", "x"))
    tn = next(v for v in nc.variables if v.lower() in ("time", "t"))
    glat = np.asarray(nc.variables[lan][:]); glon = np.asarray(nc.variables[lon_][:])
    tv = nc.variables[tn]
    dates = num2date(tv[:], tv.units, getattr(tv, "calendar", "standard"))
    yms = [(d.year, d.month) for d in dates]
    il, ia = grid_indices(cells["lon"].to_numpy(), cells["lat"].to_numpy(), glon, glat)
    v = nc.variables[vn]                       # netCDF4 auto-applies scale_factor + masks _FillValue
    out = []
    cid = cells[CC].to_numpy()
    for j, (y, m) in enumerate(yms):
        arr = np.ma.filled(v[j, :, :].astype("float32"), np.nan)
        arr = np.where(np.abs(arr) <= 1.0, arr, np.nan)   # NDVI valid in [-1,1]; fill/sentinel -> NaN
        out.append(pd.DataFrame({CC: cid, "year": y, "month": m, OUTCOL: arr[ia, il]}))
    nc.close()
    return pd.concat(out, ignore_index=True)


def main(argv):
    def opt(flag, d=None):
        return argv[argv.index(flag) + 1] if flag in argv else d
    out_dir = opt("--out", os.path.join(os.path.dirname(cfg["data"]["master_dir"]), "modis_ndvi_monthly"))
    tmp = opt("--tmp", os.path.join(out_dir, "_nc"))
    only = opt("--region"); limit = opt("--limit"); wait = "--wait" in argv
    start, end = opt("--start", START), opt("--end", END)
    tag = _tag(start, end)
    if tag:
        print(f"WINDOW {start} .. {end}  ->  outputs '<region>_ndvi{tag}.parquet', "
              f"task keys '<region>{tag}'", flush=True)
    os.makedirs(out_dir, exist_ok=True); os.makedirs(tmp, exist_ok=True)
    state_f = os.path.join(out_dir, "_appeears_tasks.json")
    state = json.load(open(state_f)) if os.path.exists(state_f) else {}

    masters = {}
    for d in (cfg["data"]["master_dir"], cfg["forecast"]["regions_dir"]):
        for p in glob.glob(os.path.join(d, "*_master_*.parquet")):
            if ".bak." not in p:
                masters.setdefault(os.path.basename(p).split("_master_")[0], p)
    regs = sorted(masters)
    if only:
        regs = [r for r in regs if r == only]
    if limit:
        regs = regs[:int(limit)]
    cells = {r: pd.read_parquet(masters[r], columns=[CC, "lon", "lat"]).drop_duplicates(CC) for r in regs}

    def out_of(r):
        return os.path.join(out_dir, f"{r}_ndvi{tag}.parquet")

    def key_of(r):
        return f"{r}{tag}"

    # PHASE 1: submit tasks for regions with neither output nor a task
    tok = _token()
    for r in regs:
        if os.path.exists(out_of(r)) or key_of(r) in state:
            continue
        try:
            state[key_of(r)] = submit(tok, r, cells[r], start, end)
            json.dump(state, open(state_f, "w"))
            print(f"  submitted {r} [{start}..{end}] -> {state[key_of(r)]}", flush=True)
        except Exception as e:
            print(f"  submit FAIL {r}: {type(e).__name__}: {e}", flush=True)

    # PHASE 2: harvest done tasks; SELF-HEAL tasks that fail or whose status check keeps
    # erroring (broken server-side) by re-submitting a fresh task. One task's trouble never
    # kills the loop, and a dead task ID is replaced instead of polled forever.
    BAD = {"error", "failed", "expired", "deleted", "deletion", "cancelled", "canceled"}
    STUCK = 40                                         # ~30 min of "processing" -> likely a zombie task
    fails = {}                                         # region -> consecutive bad cycles
    proc = {}                                          # region -> consecutive "processing" cycles
    resubs = {}                                        # region -> times re-submitted (capped)
    while True:
        pending = [r for r in regs if not os.path.exists(out_of(r)) and key_of(r) in state]
        if not pending:
            print("ALL REGIONS HARVESTED.", flush=True); break
        try:
            tok = _token()
        except Exception as e:
            print(f"  token error, retry in 60s: {type(e).__name__}", flush=True); time.sleep(60); continue
        st_count = Counter(); last = {}
        for r in pending:
            try:
                st = task_status(tok, state[key_of(r)])
            except Exception:
                st = "req_err"                         # status GET failed even after 6 retries
            last[r] = st; st_count[st] += 1
            if st == "done":
                try:                                   # harvest errors retry next cycle (not a task failure)
                    nc = download_nc(tok, state[key_of(r)], tmp)
                    df = sample(nc, cells[r])
                    df.to_parquet(out_of(r), index=False)
                    try:
                        os.remove(nc)
                    except OSError:
                        pass
                    fails[r] = 0
                    print(f"  HARVESTED {r}  ({df[OUTCOL].notna().mean()*100:.0f}% valid)", flush=True)
                except Exception as e:
                    print(f"  [harvest retry] {r}: {type(e).__name__}", flush=True)
            elif st in BAD or st == "req_err":
                fails[r] = fails.get(r, 0) + 1
                if fails[r] >= 3:                       # confirmed broken for ~3 cycles -> fresh task
                    try:
                        old = state[key_of(r)]; state[key_of(r)] = submit(tok, r, cells[r], start, end)
                        json.dump(state, open(state_f, "w")); fails[r] = 0
                        print(f"  RE-SUBMITTED {r} (was {st}, {old[:8]}) -> {state[key_of(r)][:8]}", flush=True)
                    except Exception as e:
                        print(f"  resubmit FAIL {r}: {type(e).__name__}: {e}", flush=True)
                else:
                    print(f"  [{st}] {r} ({fails[r]}/3 before resubmit)", flush=True)
            else:
                fails[r] = 0                           # healthy: pending / queued / processing
                if st == "processing":
                    proc[r] = proc.get(r, 0) + 1
                    if proc[r] >= STUCK and resubs.get(r, 0) < 2:   # zombie -> fresh task (capped at 2)
                        try:
                            old = state[key_of(r)]; state[key_of(r)] = submit(tok, r, cells[r], start, end)
                            json.dump(state, open(state_f, "w"))
                            proc[r] = 0; resubs[r] = resubs.get(r, 0) + 1
                            print(f"  RESUBMIT-STUCK {r} (processing {STUCK} cycles, {old[:8]}) -> {state[key_of(r)][:8]}", flush=True)
                        except Exception as e:
                            print(f"  resubmit FAIL {r}: {type(e).__name__}", flush=True)
                else:
                    proc[r] = 0
        remaining = [r for r in regs if not os.path.exists(out_of(r)) and r in state]
        print(f"  status: {dict(st_count)}  ({len(remaining)} pending)", flush=True)
        if remaining and len(remaining) <= 12:          # tail visibility: show each region's state
            print("    tail: " + ", ".join(f"{r}={last.get(r, '?')}" for r in remaining), flush=True)
        if not wait:
            print("re-run to harvest more (or pass --wait).", flush=True); break
        time.sleep(45)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
