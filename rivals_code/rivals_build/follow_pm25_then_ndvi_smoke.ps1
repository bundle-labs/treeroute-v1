# follow_pm25_then_ndvi_smoke.ps1 -- the agent's follower (2026-10-21, owner away).
# The owner started the pm25 export in their own window at 23:19. This script waits until no rivals.cli / engine
# process has run for 5 minutes in a row, then finishes the pm25 board (every step resumable; steps already done are
# skipped or quickly re-checked), then runs the NDVI smoke check (RIVALS_OWNER_COMMANDS.md 6a).
# It stops at the first failure. It deletes nothing. Log: logs_owner\follow_<stamp>.log
$ErrorActionPreference = 'Continue'
Set-Location D:\treeroute\rivals_build
$CFG = "D:\treeroute\rivals_build\rivals_production.yaml"
$ENG = "C:\Users\<user>\Desktop\data set for reserch paper\engine"
$stamp = Get-Date -Format yyyyMMdd_HHmmss
New-Item -ItemType Directory -Force D:\treeroute\rivals_build\logs_owner | Out-Null
$LOG = "D:\treeroute\rivals_build\logs_owner\follow_$stamp.log"
function Log([string]$m) { $line = "[$(Get-Date -Format s)] $m"; Add-Content -Encoding utf8 -Path $LOG -Value $line; Write-Host $line }
function Busy { @(Get-CimInstance Win32_Process | Where-Object { ($_.CommandLine -match 'rivals\.cli' -or $_.CommandLine -match '-m treeroute' -or $_.CommandLine -match 'smoke_run\.py') -and $_.CommandLine -notmatch 'Get-CimInstance' -and $_.CommandLine -notmatch 'follow_pm25' }).Count -gt 0 }
function Step([string]$name, [string[]]$cliArgs) {
    Log "START $name : rivals.cli $($cliArgs -join ' ')"
    & py -3.9 -B -m rivals.cli @cliArgs --config $CFG 2>&1 | ForEach-Object { Add-Content -Encoding utf8 -Path $LOG -Value "$_" }
    $code = $LASTEXITCODE
    Log "END $name exit $code"
    if ($code -ne 0) { Log "STOPPED at $name (exit $code). Send this log to the agent."; exit 1 }
}
Log "waiting for the owner's pm25 run to go idle (5 quiet minutes)"
$quiet = 0
while ($quiet -lt 5) { if (Busy) { $quiet = 0 } else { $quiet++ }; Start-Sleep -Seconds 60 }
Log ("idle. free RAM GB {0:N1}; free D: GB {1:N1}" -f ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB), ((Get-PSDrive D).Free/1GB))

$RUN = "D:\treeroute\runs\pm25\headline\20261007_74e67609"
$OUT = "D:\treeroute\rivals\pm25\20261007_74e67609"
if (-not (Test-Path "$OUT\board.md")) {
    if (-not (Test-Path "D:\treeroute\rival_export\pm25\20261007_74e67609\ACCEPTED_ALL_LEADS.json")) {
        Step "pm25 export (resume)" @("export", "--run", $RUN, "--package", "$ENG\datasets\pm25", "--lead", "all", "--resume")
        if (-not (Test-Path "D:\treeroute\rival_export\pm25\20261007_74e67609\ACCEPTED_ALL_LEADS.json")) { Log "STOPPED: no ACCEPTED_ALL_LEADS.json after the pm25 export"; exit 1 }
    }
    if (-not (Test-Path "$OUT\board.json")) { Step "pm25 init" @("init", "--run", $RUN, "--export", "D:\treeroute\rival_export\pm25\20261007_74e67609\lead_0", "--out", "D:\treeroute\rivals") }
    Step "pm25 tune" @("tune", "--out", $OUT, "--resume")
    Step "pm25 lock" @("lock", "--out", $OUT)
    foreach ($L in 0, 6, 12) { Step "pm25 refit $L" @("refit", "--out", $OUT, "--lead", "$L", "--resume") }
    foreach ($L in 0, 6, 12) { Step "pm25 score $L" @("score", "--out", $OUT, "--lead", "$L") }
    Step "pm25 board" @("board", "--out", $OUT)
}
Log "PM2.5 BOARD DONE: $OUT\board.md"

Log "START ndvi smoke run (section 6a)"
$smokeOut = & py -3.9 -B pt\integ\smoke_run.py "$ENG\datasets\ndvi" 2>&1 | ForEach-Object { $l = "$_"; Add-Content -Encoding utf8 -Path $LOG -Value $l; $l }
$doneLine = $smokeOut | Where-Object { $_ -match 'SMOKE DONE' } | Select-Object -Last 1
if (-not $doneLine) { Log "STOPPED: the NDVI smoke run did not print SMOKE DONE"; exit 1 }
$SM = (($doneLine -replace '.*SMOKE DONE\s+', '') -replace '\s+in\s+[\d.]+\s*s\s*$', '').Trim()   # the line ends "in <secs> s"
Log "ndvi smoke folder: $SM"
& py -3.9 -B -m rivals.cli export --run $SM --package "$ENG\datasets\ndvi" --lead all --resume --config pt\integ\integ_smoke.yaml 2>&1 | ForEach-Object { Add-Content -Encoding utf8 -Path $LOG -Value "$_" }
if ($LASTEXITCODE -ne 0) { Log "STOPPED: NDVI smoke export exit $LASTEXITCODE"; exit 1 }
$p15 = & py -3.9 -B pt\integ\parity_p15.py $SM "pt\integ\_export_smoke\ndvi\$(Split-Path $SM -Leaf)" pt\integ\parity_p15_ndvi_smoke.json 2>&1 | ForEach-Object { $l = "$_"; Add-Content -Encoding utf8 -Path $LOG -Value $l; $l }
if (-not ($p15 -match 'P15 pass')) { Log "STOPPED: NDVI smoke P15 did not pass"; exit 1 }
Log "NDVI SMOKE CHECK PASSED. Next (owner): free disk (section 7), then defo (section 5) and NDVI (section 6b)."
Log ("free D: GB at the end: {0:N1}" -f ((Get-PSDrive D).Free/1GB))
exit 0
