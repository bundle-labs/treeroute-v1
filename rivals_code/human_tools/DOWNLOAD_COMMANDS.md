# Human-rival downloads: what the owner runs

Written 2026-10-21. Approval: owner ruling AB1 (`OWNER_RULINGS_2026-10-06.md:176`): D0', D1, D2, D3, D4, D6 approved;
D5 NOT approved (it is not in the script). Plan: `RIVALS_PLAN_HUMAN.md` section 4.

Plain summary:
- **Done already (public, no key):** D4 (GADM country files) and D6 (NOAA coral heat-stress values). Section 3.
- **Waiting on you:** D0', D1, D2, D3 need your own Copernicus key files. Section 1 is the one-time setup;
  section 2 is the commands.
- **ATTENTION, one decision before D3:** merged boxes need about 8.22 GB, above the 1.5-6.3 GB you approved.
  Either run per-region boxes (1.94 GB, inside the approval) or re-approve 8.22 GB. The script refuses merged
  D3 until you pass the new size. See 2.4.

---

## 1. One-time key setup (you do this; the agent never reads, writes or copies a key)

Today only `C:\Users\<user>\.cdsapirc` exists (Climate Data Store). D1 comes from the Atmosphere Data
Store (ADS); D0', D2 and D3 come from the Early Warning Data Store (EWDS). Each store needs its own small key
file in the same two-line format as `.cdsapirc`:

```
url: <store address>
key: <your ECMWF personal access token>
```

The same ECMWF personal access token works on all the Copernicus stores (CDS, ADS, EWDS). You log in to each
store with the same ECMWF account.

**Step 1. Log in once to each store** with your ECMWF account:
- ADS: https://ads.atmosphere.copernicus.eu
- EWDS: https://ewds.climate.copernicus.eu

**Step 2. Accept the licences** (a download fails with a "required licences not accepted" error otherwise).
On each dataset page, open the **Download** tab, scroll to **Terms of use**, click **Accept**:
- ADS, D1: https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4-monthly
  (CAMS / "Licence to use Copernicus Products")
- EWDS, D2: https://ewds.climate.copernicus.eu/datasets/cems-fire-historical-v1 (CEMS fire licence, CC-BY 4.0)
- EWDS, D0' and D3: https://ewds.climate.copernicus.eu/datasets/cems-fire-seasonal (CEMS fire licence, CC-BY 4.0)

**Step 3. Make the two key files.** Either way works:

(a) Copy your CDS file and change only the `url:` line. This never shows the key on screen:

```powershell
(Get-Content "$HOME\.cdsapirc") -replace '^url:.*$', 'url: https://ads.atmosphere.copernicus.eu/api'  | Set-Content -Encoding ascii "$HOME\.adsapirc"
(Get-Content "$HOME\.cdsapirc") -replace '^url:.*$', 'url: https://ewds.climate.copernicus.eu/api' | Set-Content -Encoding ascii "$HOME\.ewdsapirc"
```

(b) Or open Notepad, type the two lines (url as above, key copied from your profile page on the store), and
save as `C:\Users\<user>\.adsapirc` and `C:\Users\<user>\.ewdsapirc` (save type "All files", so
Notepad does not add `.txt`).

If your `.cdsapirc` still holds an old-style key (two parts joined by a colon, from before the 2024 CDS move),
use (b) with the token from the profile page instead.

**Step 4. Check** (shows only the `url:` lines, never the key):

```powershell
Select-String -Path "$HOME\.adsapirc","$HOME\.ewdsapirc" -Pattern '^url:'
py -3.9 -I D:\treeroute\human_tools\fetch_products.py --dry-run D0p D1 D2 D3 --no-network | Select-String 'key file|SIZE|TOTAL'
```

Every "key file" line must say `present`. The real run also checks that each file points at the right store and
refuses with a plain message if not.

---

## 2. The download commands (in this order)

General rules for every command below:
- Run in a PowerShell window. Keep the PC on and awake while it runs (Settings > System > Power: Sleep = Never
  while the queue runs). The jobs are network only: small RAM, no heavy-job lock.
- **Progress:** each command writes a log. In a second window:
  `Get-Content D:\treeroute\human_tools\reports\run_<name>.log -Tail 5 -Wait` (Ctrl+C stops watching only).
  The Copernicus client prints the request status (queued / running / successful) and each finished file prints
  its size, time and SHA-256.
- **Resume:** stop with Ctrl+C at any time. Run the SAME command again: finished files are skipped after their
  SHA-256 is re-checked, and only the missing ones are requested. A file only counts as finished after it is
  fully downloaded and passes a format check (it is written as `.part` first).
- **Failures:** a failed request is skipped and the run goes on; after 5 failures in a row it stops ("server looks
  down"). Re-run the same command later.
- **Disk:** before each request the script checks D: and refuses if less than 12 GB would remain. D: had
  30.4 GB free on 2026-10-21.
- **Size approval:** the script refuses a product whose expected size is above your AB1 bound x 1.10 (the
  expected sizes are upper bounds). Only `--approved-gb` overrides this, after you re-approve a size.
- **Parallel:** different products may run at the same time in separate windows (for example D1 on ADS while D2
  runs on EWDS). The same product twice is refused by a lock file in `D:\treeroute\human_tools\locks`. If a run
  was killed hard (window closed), that lock file stays: delete it, then re-run.
- Each product goes into its own new folder under `D:\treeroute\human_products\` with a `product_manifest.json`
  (source URL, exact request, file list, sizes, SHA-256, times, script version).

### 2.1 D0' SEAS5 timing probe (first; one request)

```powershell
py -3.9 -I D:\treeroute\human_tools\fetch_products.py --run D0p | Tee-Object -Append D:\treeroute\human_tools\reports\run_D0p.log
```
- One full-size request: the largest merged fire box (box04, 5 regions), 12 starts of 2016, daily leads 150-184,
  25 members. Expected at most 67 MB; plan time 0.5-1 h (`RIVALS_PLAN_HUMAN.md:157`).
- Folder: `D:\treeroute\human_products\cems_fire_seasonal_probe\geff_seas5_r5_fwi_box04_2016`.
- What to read after: the `seconds` and `bytes` of the file in the manifest. These replace the plan's guess for
  D3 (2-15 min per request).
- Optional second probe (your call, about 137 MB): 2016 has 25 members, but 67 of the 240 D3 starts (2017-2022)
  arrive with all 51 members, so they are about twice the size. One probe from 2019 times those:
  ```powershell
  py -3.9 -I D:\treeroute\human_tools\fetch_products.py --run D0p --probe-year 2019 | Tee-Object -Append D:\treeroute\human_tools\reports\run_D0p_2019.log
  ```
  If you skip it, the 2017-2022 requests are assumed to take about twice the 2016 time.

### 2.2 D1 CAMS EAC4 monthly PM2.5 (ADS; can run at the same time as 2.1)

```powershell
py -3.9 -I D:\treeroute\human_tools\fetch_products.py --run D1 | Tee-Object -Append D:\treeroute\human_tools\reports\run_D1.log
```
- One request: pm2p5 monthly mean, 2003-01 to 2023-12, global 0.75 deg, zipped netCDF. Expected at most 117 MB;
  plan time 0.5-1.5 h, mostly the ADS queue.
- Folder: `D:\treeroute\human_products\cams_eac4_monthly_pm2p5\eac4_monthly_mean_2003-2023`.

### 2.3 D2 CEMS GEFF-ERA5 FWI 2003-2022 (EWDS)

Default, merged boxes (10 boxes x 4 five-year blocks = 40 requests, expected at most 2.29 GB):
```powershell
py -3.9 -I D:\treeroute\human_tools\fetch_products.py --run D2 | Tee-Object -Append D:\treeroute\human_tools\reports\run_D2.log
```
Or per-region boxes (40 regions x 4 blocks = 160 requests, expected at most 0.47 GB, less disk):
```powershell
py -3.9 -I D:\treeroute\human_tools\fetch_products.py --run D2 --boxes region | Tee-Object -Append D:\treeroute\human_tools\reports\run_D2_region.log
```
- Time: plan 5-16 h of EWDS queue (measured 1,590 s for one 5-year request, `D:\fire\cems\batch_test.log` line A).
- The merged estimate (2.29 GB) is 4% above the 2.2 GB bound, because these merged boxes hold 119,032 points
  against the plan's ~114,165 (+4.3%; this script joins the pair that adds the fewest points, the plan used a
  greedy merge). Every region's own box is inside its merged box, so nothing is lost; it is inside the 10% slack.
- Folder: `D:\treeroute\human_products\cems_fire_historical_fwi\geff_era5_v4_1_consolidated_fwi_2003-2022_<merged|region>`.

### 2.4 D3 CEMS GEFF-SEAS5 FWI, 240 starts (EWDS; after D0'; needs your box decision)

**ATTENTION: choose one.**

(a) Per-region boxes, inside your approval (40 regions x 21 start years = 840 requests, expected at most 1.94 GB):
```powershell
py -3.9 -I D:\treeroute\human_tools\fetch_products.py --run D3 --boxes region | Tee-Object -Append D:\treeroute\human_tools\reports\run_D3_region.log
```

(b) Merged boxes (10 boxes x 21 = 210 requests, expected at most 8.22 GB). Only after you re-approve 8.22 GB:
```powershell
py -3.9 -I D:\treeroute\human_tools\fetch_products.py --run D3 --approved-gb 8.3 | Tee-Object -Append D:\treeroute\human_tools\reports\run_D3_merged.log
```
Without `--approved-gb` it refuses (above 6.3 GB x 1.10).

- Why merged is bigger than approved: from 2017 on every start arrives with all 51 members (the form has no
  member choice; members 0-24 are kept at processing, `research_fire.md:37`).
- Time: the plan re-derived 2-15 min per request (`RIVALS_PLAN_HUMAN.md:169-173`): merged about 7-50 h serial;
  per-region has 4x more but smaller requests, so the queue wait per request decides it. D0' measures this.
  The script also has `--seas-years-per-request 4` (per-region: 360 requests instead of 840), but requests that
  mix 25- and 51-member years are untested; use it only if D0' shows the queue wait is what costs time.
- Disk: after D1-D3 with merged D3 about 10.7 GB is used and about 19.7 GB stays free; the common exports need
  6.7-10 GB per lead (`RIVALS_PLAN_HUMAN.md:166-168`). Per-region D3 uses about 4.6 GB in all.
- Fire lead 6 cut-off is 18 Nov (Q24, `RIVALS_PLAN_HUMAN.md:226`): start D3 early.
- Folder: `D:\treeroute\human_products\cems_fire_seasonal_fwi\geff_seas5_r5_fwi_starts200208-202207_L150-184_<region|merged>_y1`.

D2 and D3 can run at the same time in two windows (two EWDS queues), and D1 beside them.

**Check what is done for any product** (counts files and bytes in its manifest):
```powershell
py -3.9 -I -c "import json,sys;m=json.load(open(sys.argv[1]));print(len(m['files']),'files',round(sum(v['bytes'] for v in m['files'].values())/1e9,3),'GB','complete' if m.get('complete') else 'not complete')" <folder>\product_manifest.json
```

---

## 3. Already downloaded (public, no key)

| Product | Folder (under `D:\treeroute\human_products\`) | Files | Size | Notes |
|---|---|---|---|---|
| D4 GADM 3.6, all levels incl. level 2, 52 countries for the 42 defo regions | `gadm\3.6_gpkg_defo42` | 52 zip | 734,542,779 B (0.73 GB) | complete; all hashes re-checked. Processing rules to pre-register: `D:\treeroute\human_tools\reports\d4_processing_rules.md` (cell-to-unit by overlap, not centre; Ireland and Hong Kong level-1 fallback). |
| D6 v1, NOAA PIFSC (train, 200 site-days x DHW, BAA 7-day max, HotSpot) | `noaa_crw_dhw_sitedays\v3.1_train_sitedays_n200_pifsc` | 600 csv | 75,333 B | complete. Day = the store's feature_end, which is NOT d* for 40 of 200; 3 sites sit on a pixel edge. Kept as a plain check-date set; superseded by v2. |
| D6 v1, pfeg/PacIOOS copy (cross-check) | `noaa_crw_dhw_sitedays\v3.1_train_sitedays_n200` | 45 of 200 csv | 9,018 B | stopped by hand at 45 (server answers in 25-230 s); manifest closed. Of 45: DHW agrees with PIFSC on 43, alert and HotSpot on 45 (`reports\d6_summary.csv`). |
| D6 v2, NOAA PIFSC (train + test, corrected day d*, SST-cache pixel, + SST) | `noaa_crw_dhw_sitedays\v3.1_sitedays_v2_train200_test100_pifsc` | 1200 csv (300 site-days x DHW, BAA 7-day max, HotSpot, SST) | 149,233 B | complete, 0 failed, 38 min. Day = d* = C - g - 1 (40 train days moved 1 day earlier than v1). Queried at the SST cache's own pixel. Proof (`reports\d6_v2_summary.log`): for all 300 site-days the returned day and pixel are right, and NOAA's SST at that pixel equals our cached SST, including the 3 edge sites (043, 117, 134; in v1 ERDDAP had picked the neighbour pixel for all three). **This is the D6 set to compare against.** |

D6 reference server (your call): we recommend **PIFSC** (NOAA's own server, the one our SST came from,
`coral_fetch_sst.py:42`) as the reference, with pfeg kept as a disclosed cross-check. The plan's pfeg address
redirects to the University of Hawaii PacIOOS copy of the same v3.1 product; on two Florida Keys days its DHW
differs from PIFSC by 0.14 (about one daily HotSpot near the 1 deg C cut-off), so a "refuse above rounding" test
against pfeg would fail on a difference between two copies of NOAA's product, not on our recomputation. If pfeg
must be finished: `py -3.9 -I D:\treeroute\human_tools\fetch_products.py --run D6 --timeout 300`.

D6 v2 adds 100 test site-days (2016-2019; coordinates and dates only, no label read). The research note asked for
"test and train" site-days (`research_coral.md:188`); rule H16 bans test scores, not test coordinates. If you
do not want them used, the compare can drop the rows whose `mark` is `test` in `d6_sitedays_v2.csv`.

Script versions: every run now keeps a copy of the script in `D:\treeroute\human_tools\versions\`. The versions
that fetched D4 (`1b4fed13`) and the pfeg files plus the first 9 PIFSC files (`fa72b6b6`) were not kept:
`D:\treeroute\human_tools\reports\tool_versions_note.md`.
