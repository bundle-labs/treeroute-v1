# finish_ndvi_smoke.ps1 -- the last two steps of the NDVI smoke check (RIVALS_OWNER_COMMANDS.md 6a) for a smoke run
# that already finished. The follower of 2026-10-22 stopped here only because it read the folder name with the
# trailing " in 327.8 s" of the SMOKE DONE line (fixed in follow_pm25_then_ndvi_smoke.ps1). Deletes nothing.
param([string]$SM = "D:\treeroute\rivals_build\runs\ndvi\smoke\20261022_9b1ee548")
$ErrorActionPreference = 'Continue'
Set-Location D:\treeroute\rivals_build
$ENG = "C:\Users\<user>\Desktop\data set for reserch paper\engine"
$LOG = "D:\treeroute\rivals_build\logs_owner\finish_ndvi_smoke_$(Get-Date -Format yyyyMMdd_HHmmss).log"
function Log([string]$m) { $line = "[$(Get-Date -Format s)] $m"; Add-Content -Encoding utf8 -Path $LOG -Value $line; Write-Host $line }
if (-not (Test-Path "$SM\DONE.json")) { Log "STOPPED: $SM has no DONE.json"; exit 1 }
Log "START ndvi smoke export: $SM"
& py -3.9 -B -m rivals.cli export --run $SM --package "$ENG\datasets\ndvi" --lead all --resume --config pt\integ\integ_smoke.yaml 2>&1 | ForEach-Object { Add-Content -Encoding utf8 -Path $LOG -Value "$_" }
if ($LASTEXITCODE -ne 0) { Log "STOPPED: NDVI smoke export exit $LASTEXITCODE"; exit 1 }
Log "START P15"
$p15 = & py -3.9 -B pt\integ\parity_p15.py $SM "pt\integ\_export_smoke\ndvi\$(Split-Path $SM -Leaf)" pt\integ\parity_p15_ndvi_smoke.json 2>&1 | ForEach-Object { $l = "$_"; Add-Content -Encoding utf8 -Path $LOG -Value $l; $l }
if (-not ($p15 -match 'P15 pass')) { Log "STOPPED: NDVI smoke P15 did not pass"; exit 1 }
Log "NDVI SMOKE CHECK PASSED. Next (owner): defo (section 5), then NDVI (section 6b)."
Log ("free D: GB at the end: {0:N1}" -f ((Get-PSDrive D).Free/1GB))
exit 0
