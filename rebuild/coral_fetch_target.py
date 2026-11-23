"""Fetch the CORAL BLEACHING TARGET corpus to D:\\coral\\target. Target only -- no drivers.

    py -3.9 -u coral_fetch_target.py            # fetch everything not already complete
    py -3.9 -u coral_fetch_target.py --list     # show what would be fetched, fetch nothing
    py -3.9 -u coral_fetch_target.py --only mermaid,agrra
    py -3.9 -u coral_fetch_target.py --force gcbd

WHAT THIS FETCHES, AND WHY ONLY THIS. Every curated bleaching database is frozen (GCBD ends 2020,
Urcelay-Donner ends 2017) and NOAA CRW publishes none of its four field-observation streams. So the
target does not live in one place -- it is federated across six services, three of which are live web
apps with no stability guarantee. That is the whole reason this script exists: it takes a DATED
SNAPSHOT with a hash, so an experiment run in March and rerun in June sees the same bytes. Never
re-fetch inside an experiment; point the experiment at the snapshot.

DRIVERS ARE DELIBERATELY ABSENT. No SST, no DHW, no ERA5, no IBTrACS, no reef mask. Those are a
separate ingester with a completely different shape (162 GB of daily SST if the leak-free MMM
recompute is chosen). Mixing them here would make the target snapshot depend on a decision that has
not been made yet.

CRASH SAFETY. Every source writes into its own directory and records itself in _manifest.json only
after it completes. Re-running skips completed sources, so an interrupted run resumes by restarting
it. Paged APIs checkpoint per page, so a 17-page pull that dies on page 12 refetches 5 pages, not 17.

PII BLOCKLIST -- READ BEFORE ADDING A SOURCE. AGRRA's BleachingPoints layer carries submitter names,
email addresses and phone numbers. It is refused by name below and must stay refused. Caching
personal contact details onto a research drive is a hazard that no amount of later care undoes.
"""
import argparse
import hashlib
import io
import json
import os
import sys
import time
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    raise SystemExit("pip install requests")

ROOT = r"D:\coral\target"
RAW = os.path.join(ROOT, "raw")
MANIFEST = os.path.join(ROOT, "_manifest.json")
LOG = os.path.join(ROOT, "_fetch_log.txt")

UA = {"User-Agent": "coral-bleaching-research/1.0 (academic; contact via project)"}
TIMEOUT = 120

# Layers that must never be cached. Substring match, case-insensitive, applied to every ArcGIS
# layer name before any request is issued for it.
PII_BLOCKLIST = ("bleachingpoints",)


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg):
    line = "[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def load_manifest():
    if os.path.exists(MANIFEST):
        try:
            return json.load(io.open(MANIFEST, encoding="utf-8"))
        except Exception:
            log("manifest unreadable, starting a new one")
    return {"created": now(), "sources": {}}


def save_manifest(m):
    """Atomic write -- a crash mid-save must not destroy the record of what is already on disk."""
    m["updated"] = now()
    tmp = MANIFEST + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(m, indent=2, sort_keys=True))
    os.replace(tmp, MANIFEST)


def get(url, params=None, tries=4, stream=False, expect_json=False):
    """One GET with backoff. MERMAID paging is genuinely flaky -- 2 of 17 pages failed on a first
    pass and succeeded on retry -- so retry is required, not defensive padding."""
    last = None
    for k in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=TIMEOUT, stream=stream)
            if r.status_code == 200:
                if expect_json:
                    return r.json()
                return r
            last = "HTTP %d" % r.status_code
        except Exception as e:
            last = "%s: %s" % (type(e).__name__, str(e)[:120])
        if k < tries - 1:
            time.sleep(2 ** k)
    raise RuntimeError("%s -- %s" % (url, last))


def download(url, dest, params=None):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    r = get(url, params=params, stream=True)
    tmp = dest + ".part"
    n = 0
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            if chunk:
                f.write(chunk)
                n += len(chunk)
    os.replace(tmp, dest)
    return n


def file_rec(path, url):
    return {"path": path, "bytes": os.path.getsize(path), "sha256": sha256(path),
            "url": url, "retrieved": now()}


# --------------------------------------------------------------------------------------------
# Sources. Each returns a dict describing what it wrote. Raising is fine -- main() isolates them.
# --------------------------------------------------------------------------------------------

def fetch_figshare(article_id, outdir, want=None):
    """Resolve a figshare article to its file list and download. Resolving through the API rather
    than hardcoding an ndownloader URL matters: the article id and the file id are different
    numbers that look alike, and hardcoding the wrong one silently fetches a different file."""
    meta = get("https://api.figshare.com/v2/articles/%s" % article_id, expect_json=True)
    out = {"article": article_id, "title": meta.get("title"), "version": meta.get("version"),
           "modified": meta.get("modified_date"), "license": (meta.get("license") or {}).get("name"),
           "files": []}
    for f in meta.get("files", []):
        name = f["name"]
        if want and not any(w.lower() in name.lower() for w in want):
            continue
        dest = os.path.join(outdir, name)
        if os.path.exists(dest) and os.path.getsize(dest) == f.get("size", -1):
            log("    have %s (%.1f MB)" % (name, os.path.getsize(dest) / 1e6))
        else:
            log("    get  %s (%.1f MB)" % (name, f.get("size", 0) / 1e6))
            download(f["download_url"], dest)
        rec = file_rec(dest, f["download_url"])
        if f.get("supplied_md5"):
            rec["figshare_md5"] = f["supplied_md5"]
        out["files"].append(rec)
    return out


def fetch_zenodo(record_id, outdir, want=None):
    meta = get("https://zenodo.org/api/records/%s" % record_id, expect_json=True)
    md = meta.get("metadata", {})
    out = {"record": record_id, "title": md.get("title"),
           "license": str((md.get("license") or {}).get("id")), "files": []}
    for f in meta.get("files", []):
        name = f.get("key")
        if want and not any(w.lower() in name.lower() for w in want):
            continue
        url = "https://zenodo.org/api/records/%s/files/%s/content" % (record_id, requests.utils.quote(name))
        dest = os.path.join(outdir, name)
        size = (f.get("size") or 0)
        if os.path.exists(dest) and os.path.getsize(dest) == size:
            log("    have %s (%.1f MB)" % (name, os.path.getsize(dest) / 1e6))
        else:
            log("    get  %s (%.1f MB)" % (name, size / 1e6))
            download(url, dest)
        out["files"].append(file_rec(dest, url))
    return out


def fetch_mermaid(outdir):
    """MERMAID summary sample events, paged as JSON.

    JSON NOT CSV, on purpose. The bulk CSV silently drops the 7-bin severity breakdown -- 78 columns
    but only a single collapsed percent_bleached field. The JSON carries the bins, and the bins are
    what let a row be folded onto an ordinal cut set later.
    """
    os.makedirs(outdir, exist_ok=True)
    first = get("https://api.datamermaid.org/v1/summarysampleevents/",
                params={"limit": 1, "page": 1}, expect_json=True)
    total = first.get("count", 0)
    limit = 1000
    pages = (total + limit - 1) // limit
    log("    %d events over %d pages" % (total, pages))
    got, failed = 0, []
    for p in range(1, pages + 1):
        dest = os.path.join(outdir, "page_%04d.json" % p)
        if os.path.exists(dest) and os.path.getsize(dest) > 2:
            got += 1
            continue
        try:
            d = get("https://api.datamermaid.org/v1/summarysampleevents/",
                    params={"limit": limit, "page": p}, expect_json=True, tries=5)
            tmp = dest + ".part"
            with io.open(tmp, "w", encoding="utf-8") as f:
                f.write(json.dumps(d))
            os.replace(tmp, dest)
            got += 1
            log("    page %d/%d  (%d records)" % (p, pages, len(d.get("results", []))))
        except Exception as e:
            failed.append({"page": p, "error": str(e)[:160]})
            log("    page %d/%d FAILED: %s" % (p, pages, str(e)[:80]))
    return {"reported_count": total, "pages_expected": pages, "pages_on_disk": got,
            "failed_pages": failed, "endpoint": "api.datamermaid.org/v1/summarysampleevents/",
            "note": "JSON not CSV -- the CSV drops the 7-bin severity breakdown"}


def arcgis_layers(service_root):
    """List (name, url) for every layer under an ArcGIS services root or a single FeatureServer."""
    out = []
    if "/FeatureServer" in service_root:
        js = get(service_root, params={"f": "json"}, expect_json=True)
        for lyr in js.get("layers", []) + js.get("tables", []):
            out.append((lyr.get("name", "layer"), "%s/%d" % (service_root.rstrip("/"), lyr["id"])))
        if not out:
            out.append((service_root.rsplit("/", 2)[-2], service_root))
        return out
    js = get(service_root, params={"f": "json"}, expect_json=True)
    for s in js.get("services", []):
        if s.get("type") != "FeatureServer":
            continue
        url = "%s/%s/FeatureServer" % (service_root.rstrip("/"), s["name"].split("/")[-1])
        try:
            out.extend(arcgis_layers(url))
        except Exception as e:
            log("      skip %s (%s)" % (s["name"], str(e)[:60]))
    return out


def arcgis_dump(layer_url, dest, page=1000):
    """Page a layer with resultOffset. ArcGIS caps maxRecordCount (usually 1000) and will happily
    return exactly 1000 of 1,747 features without saying so -- hence the returnCountOnly check."""
    n = get(layer_url + "/query",
            params={"where": "1=1", "returnCountOnly": "true", "f": "json"},
            expect_json=True).get("count", 0)
    feats, off = [], 0
    while off < n:
        js = get(layer_url + "/query",
                 params={"where": "1=1", "outFields": "*", "returnGeometry": "true",
                         "resultOffset": off, "resultRecordCount": page, "f": "geojson"},
                 expect_json=True)
        batch = js.get("features", [])
        if not batch:
            break
        feats.extend(batch)
        off += len(batch)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "FeatureCollection", "features": feats}))
    os.replace(tmp, dest)
    return n, len(feats)


def fetch_arcgis(service_root, outdir, match=(), label=""):
    os.makedirs(outdir, exist_ok=True)
    layers = arcgis_layers(service_root)
    out = {"root": service_root, "layers": [], "refused_pii": []}
    for name, url in layers:
        low = name.lower()
        if any(b in low for b in PII_BLOCKLIST):
            log("    REFUSED (PII) %s" % name)
            out["refused_pii"].append(name)
            continue
        if match and not any(m.lower() in low for m in match):
            continue
        dest = os.path.join(outdir, "%s.geojson" % name.replace("/", "_"))
        if os.path.exists(dest) and os.path.getsize(dest) > 2:
            log("    have %s" % name)
        else:
            try:
                reported, got = arcgis_dump(url, dest)
                log("    get  %-46s %d/%d features" % (name[:46], got, reported))
            except Exception as e:
                log("    FAIL %s: %s" % (name, str(e)[:80]))
                continue
        rec = file_rec(dest, url)
        rec["layer"] = name
        out["layers"].append(rec)
    return out


AGRRA_BASE = "https://services8.arcgis.com/C2yYpahRgrVlBqfg/arcgis/rest/services"

# EXPLICIT, not enumerated. The org publishes 101 layers and only a handful carry a bleaching field;
# an enumeration with a loose name filter walks straight into FishBiomassDensityBySite (36,680
# features) and the whole MPA-boundary catalogue. Worse, enumerating the service root does NOT list
# Coral_Health_Survey_mapping at all -- the layer holding the recent 2023-26 surveys, which is the
# scarcest data in the entire project. It was found through the ArcGIS Online item search instead.
# So: name the layers.
AGRRA_LAYERS = [
    # 1,747 surveys, 343 fields. Per-species ss_<SPP>_bleached / _partialBleached / _pale. This is
    # the detailed coral health survey and the only open source of Caribbean 2023-26 bleaching.
    ("Coral_Health_Survey_mapping", AGRRA_BASE + "/Coral_Health_Survey_mapping/FeatureServer/0"),
    # 819 surveys, 74 fields -- the basic protocol plus Florida BleachWatch.
    ("Coral_Health_Survey_Basic_mapping",
     AGRRA_BASE + "/Coral_Health_Survey_Basic_mapping/FeatureServer/0"),
    # 1,834 sites carrying CORALBLCH -- the only layer on the main org with a bleaching field.
    # CORALBLCH == -999 on ~406 rows (22.1%); read naively the column mean is -211.70.
    ("BaseBySite", AGRRA_BASE + "/BaseBySite/FeatureServer/0"),
    # 3,208 site records -- coordinates and metadata for the join. Longitudes run to +88 in a
    # Caribbean dataset, so bbox-filter downstream and log the rejects.
    ("AGRRA_Sites_Website", AGRRA_BASE + "/AGRRA_Sites_Website/FeatureServer/0"),
]


def fetch_arcgis_explicit(layers, outdir):
    os.makedirs(outdir, exist_ok=True)
    out = {"layers": [], "refused_pii": []}
    for name, url in layers:
        if any(b in name.lower() for b in PII_BLOCKLIST):
            log("    REFUSED (PII) %s" % name)
            out["refused_pii"].append(name)
            continue
        dest = os.path.join(outdir, "%s.geojson" % name)
        if os.path.exists(dest) and os.path.getsize(dest) > 2:
            log("    have %s" % name)
        else:
            reported, got = arcgis_dump(url, dest)
            log("    get  %-40s %d/%d features" % (name[:40], got, reported))
        rec = file_rec(dest, url)
        rec["layer"] = name
        out["layers"].append(rec)
    return out


def fetch_ncrmp(outdir):
    """NOAA NCRMP colony-level surveys from the NCEI ERDDAP. Discovered rather than hardcoded, so a
    renamed or newly added jurisdiction is picked up instead of silently missed."""
    os.makedirs(outdir, exist_ok=True)
    base = "https://www.ncei.noaa.gov/erddap/tabledap/"
    idx = get(base + "allDatasets.csv",
              params={"datasetID,title,minTime,maxTime": None}) if False else \
        get("https://www.ncei.noaa.gov/erddap/tabledap/allDatasets.csv?datasetID,title,minTime,maxTime")
    rows = [l.split(",") for l in idx.text.splitlines()]
    ids = sorted({r[0].strip('"') for r in rows
                  if r and r[0].strip('"').startswith("CRCP_Coral_Demographic_Survey")})
    log("    %d CRCP demographic datasets on the server" % len(ids))
    out = {"datasets": []}
    for ds in ids:
        dest = os.path.join(outdir, ds + ".csv")
        url = base + ds + ".csv"
        if os.path.exists(dest) and os.path.getsize(dest) > 1024:
            log("    have %s (%.1f MB)" % (ds, os.path.getsize(dest) / 1e6))
        else:
            try:
                n = download(url, dest)
                log("    get  %-52s %.1f MB" % (ds[:52], n / 1e6))
            except Exception as e:
                log("    FAIL %s: %s" % (ds, str(e)[:80]))
                continue
        out["datasets"].append(file_rec(dest, url))
    return out


def fetch_bcodmo_csv(outdir):
    """The BCO-DMO flat CSV -- DEFECTIVE, fetched ONLY as a provenance cross-check.

    NEVER MODEL ON THIS FILE. It carries fabricated class midpoints (41.0% of Donner rows sit on
    exactly 5.5 / 30.5 / 75.0), ClimSST == 262.15 K (-11 C) in 7,188 rows, a string 'nd' as its
    missing sentinel so pandas types nearly every numeric column as object, and it collapses the
    colony-severity channel into the population one and mislabels the result.

    It is here because the project's single go/no-go question is whether a Reef Check zero is a
    measured zero or an unfilled field, and the fastest way to answer that is to diff the same rows
    across three independent renderings of the same database -- SQLite, Access, and this CSV. 6,290
    Reef Check rows reportedly read 'nd' here while the SQLite has segment values for all 22,325.
    That discrepancy IS the evidence. Keeping the file is how the diff stays reproducible.
    """
    url = ("https://datadocs.bco-dmo.org/dataset/773466/file/B11vA82u7y2Owp/"
           "global_bleaching_environmental.csv")
    dest = os.path.join(outdir, "global_bleaching_environmental.DEFECTIVE_crosscheck_only.csv")
    if os.path.exists(dest) and os.path.getsize(dest) > 1 << 20:
        log("    have flat CSV (%.1f MB)" % (os.path.getsize(dest) / 1e6))
    else:
        n = download(url, dest)
        log("    get  flat CSV (%.1f MB)" % (n / 1e6))
    return {"files": [file_rec(dest, url)], "dataset": "BCO-DMO 773466",
            "WARNING": "DEFECTIVE -- provenance cross-check only, never model on this file"}


SOURCES = {
    # Article 17076290 holds file 31573496. Those two numbers look alike and are NOT
    # interchangeable: passing the file id to the articles endpoint returns a bare 404, which is
    # exactly how the first run of this script failed. Always resolve article -> files.
    "gcbd": ("Global Coral Bleaching Database, SQLite (figshare 17076290, CC0, ends 2020)",
             lambda: fetch_figshare("17076290", os.path.join(RAW, "gcbd"))),
    "gcbd_access": ("GCBD, MS Access original (figshare 17076287) -- second rendering for the "
                    "NULL-vs-zero audit",
                    lambda: fetch_figshare("17076287", os.path.join(RAW, "gcbd"))),
    "gcbd_flatcsv": ("GCBD flat CSV (BCO-DMO 773466) -- DEFECTIVE, cross-check only",
                     lambda: fetch_bcodmo_csv(os.path.join(RAW, "gcbd"))),
    "urcelay_donner": ("Urcelay-Donner Bleaching Database V2 (Zenodo, ends 2017)",
                       lambda: fetch_zenodo("6780843", os.path.join(RAW, "urcelay_donner"),
                                            want=["Bleaching Database V2"])),
    "zenodo_11024073": ("Redefining-DHW compilation incl. Database_v7_EDT2 (NOAA-compiled)",
                        lambda: fetch_zenodo("11024073", os.path.join(RAW, "zenodo_11024073"),
                                             want=["Database_v7", "Subquery 4_Bleaching",
                                                   "Region Delineation", "Basin Delineation"])),
    "mermaid": ("MERMAID / WCS summary sample events (LIVE -- covers 2023-25)",
                lambda: fetch_mermaid(os.path.join(RAW, "mermaid"))),
    "agrra": ("AGRRA coral health surveys (LIVE -- Caribbean, covers 2023-26)",
              lambda: fetch_arcgis_explicit(AGRRA_LAYERS, os.path.join(RAW, "agrra"))),
    "cordio_wio": ("CORDIO / WIO coral bleaching observations (LIVE -- East Africa)",
                   lambda: fetch_arcgis(
                       "https://services8.arcgis.com/pAAZQwSFzOOuurmq/arcgis/rest/services/"
                       "WIO_COral_Bleaching_obs_2009_2023/FeatureServer",
                       os.path.join(RAW, "cordio_wio"))),
    "ncrmp": ("NOAA NCRMP colony-level surveys via NCEI ERDDAP (LIVE)",
              lambda: fetch_ncrmp(os.path.join(RAW, "ncrmp"))),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", default="", help="comma-separated source keys")
    ap.add_argument("--force", default="", help="comma-separated source keys to refetch")
    A = ap.parse_args()

    keys = [k.strip() for k in A.only.split(",") if k.strip()] or list(SOURCES)
    force = {k.strip() for k in A.force.split(",") if k.strip()}
    bad = [k for k in keys if k not in SOURCES]
    if bad:
        raise SystemExit("unknown source(s): %s\nknown: %s" % (", ".join(bad), ", ".join(SOURCES)))

    if A.list:
        print("\nTARGET SOURCES -> %s\n" % ROOT)
        for k in SOURCES:
            print("  %-16s %s" % (k, SOURCES[k][0]))
        print("\nDrivers are NOT fetched here -- separate ingester, separate storage decision.")
        print("PII blocklist active: %s\n" % ", ".join(PII_BLOCKLIST))
        return 0

    os.makedirs(RAW, exist_ok=True)
    man = load_manifest()
    log("=" * 78)
    log("CORAL TARGET FETCH -> %s" % ROOT)
    log("sources: %s" % ", ".join(keys))
    ok, skipped, failed = [], [], []
    for k in keys:
        desc, fn = SOURCES[k]
        if k in man["sources"] and man["sources"][k].get("status") == "complete" and k not in force:
            log("SKIP %s -- already complete (--force %s to refetch)" % (k, k))
            skipped.append(k)
            continue
        log("")
        log("--- %s : %s" % (k, desc))
        t0 = time.time()
        try:
            res = fn()
            res["status"] = "complete"
            res["elapsed_s"] = round(time.time() - t0, 1)
            res["description"] = desc
            man["sources"][k] = res
            save_manifest(man)
            ok.append(k)
            log("    done in %.1fs" % res["elapsed_s"])
        except Exception as e:
            man["sources"][k] = {"status": "failed", "error": str(e)[:400],
                                 "description": desc, "attempted": now()}
            save_manifest(man)
            failed.append((k, str(e)[:120]))
            log("    FAILED: %s" % str(e)[:200])

    total = 0
    for dirpath, _, files in os.walk(RAW):
        for f in files:
            if not f.endswith(".part"):
                total += os.path.getsize(os.path.join(dirpath, f))
    log("")
    log("=" * 78)
    log("fetched %d | skipped %d | failed %d | on disk %.1f MB"
        % (len(ok), len(skipped), len(failed), total / 1e6))
    for k, e in failed:
        log("  FAILED %-16s %s" % (k, e))
    log("manifest -> %s" % MANIFEST)
    log("Re-run to resume; failures are retried, completed sources are skipped.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
