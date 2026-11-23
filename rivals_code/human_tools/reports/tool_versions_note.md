# Which script version fetched what (written 2026-10-21)

From 2026-10-21 07:21 on, `fetch_products.py` copies itself to `D:\treeroute\human_tools\versions\<sha256>.py`
at the start of every run, and each run record in a product_manifest.json names that copy (`tool_copy`).

Earlier runs used versions whose source was NOT kept (the file was edited in place before this rule):

| Script SHA-256 (first 8) | Source kept? | What it fetched (from the manifests' run records and file times) |
|---|---|---|
| `1b4fed13` | no | ALL of D4 GADM (52 files, 734,542,779 bytes, run 06:10:18-06:13:38). Also a 2-request pfeg D6 test run (06:06:30, 0 new, 2 failed). |
| `fa72b6b6` | no | The 45 pfeg D6 files (run started 06:14:24, stopped by hand, no finish time) and the first 9 PIFSC D6 files (06:24:40-06:30:12). |
| `1d76b45c` | yes, `versions\1d76b45c...fc30.py` | The other 591 PIFSC D6 v1 files (06:30:39-06:46:54). |
| `e2a851c6` and later | yes | Closing run of the pfeg manifest (no network; 45 files skipped by hash) and D6 v2. |

Correction to the skeptic note: the pfeg files were fetched by `fa72b6b6`, not `1b4fed13`; the pfeg manifest's
top-level `tool` says `1b4fed13` only because that run created the manifest.

D4 file records have no `served_by` field (the field was added after D4 ran). Every D4 request URL is in the
manifest's `requests` section (`https://geodata.ucdavis.edu/gadm/gadm3.6/gpkg/gadm36_<ISO>_gpkg.zip`), and every
file's SHA-256 was re-checked by the skeptic review on 2026-10-21 (all 52 match). The file contents are what
matter for the defo build; the lost source only means the exact fetch code cannot be re-read.
