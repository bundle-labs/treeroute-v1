# follow_ndvi.ps1 -- the agent's runner for the NDVI common-rival board (RIVALS_OWNER_COMMANDS.md section 6b) with the
# human NDVI slim of each lead (HUMAN_OWNER_COMMANDS.txt step 5), 2026-10-24. Starts when no human pre-signing runner is
# alive and the machine has been quiet 5 minutes. One lead at a time: export L -> human slim L -> (lead 0: init, probe,
# tune, lock) -> refit L -> score L; then the board. Every step is resumable; finished steps are skipped. A refit or tune
# refused by the harness RAM guard is retried in a fresh process (up to 2 times); any other failure stops. Never adds
# --full-engine-checks (section 6). Deletes nothing (D: had ~104 GB free, enough for all three leads).
# Log: logs_owner\follow_ndvi_<stamp>.log
$ErrorActionPreference = 'Continue'
Set-Location D:\treeroute\rivals_build
$CFG = "D:\treeroute\rivals_build\rivals_production.yaml"
$HCFG = "D:\treeroute\human_rivals_build\human\human_rivals_production.yaml"
$ENG = "C:\Users\<user>\Desktop\data set for reserch paper\engine"
$RUN = "D:\treeroute\runs\ndvi\headline\20261016_d1de3158"
$OUT = "D:\treeroute\rivals\ndvi\20261016_d1de3158"
$EXP = "D:\treeroute\rival_export\ndvi\20261016_d1de3158"
$LOG = "D:\treeroute\rivals_build\logs_owner\follow_ndvi_$(Get-Date -Format yyyyMMdd_HHmmss).log"
function Log([string]$m) { $line = "[$(Get-Date -Format s)] $m"; Add-Content -Encoding utf8 -Path $LOG -Value $line; Write-Host $line }
function FreeGB { (Get-PSDrive D).Free / 1GB }
function Busy { @(Get-CimInstance Win32_Process | Where-Object { ($_.CommandLine -match 'rivals\.cli' -or $_.CommandLine -match 'rivals_human\.cli' -or $_.CommandLine -match '-m treeroute' -or $_.CommandLine -match 'smoke_run\.py') -and $_.CommandLine -notmatch 'Get-CimInstance' -and $_.CommandLine -notmatch 'follow_' }).Count -gt 0 }
function Invoke-RivalStep([string]$name, [string[]]$cliArgs, [string]$module = "rivals.cli", [string]$cfg = $CFG, [string]$dir = "D:\treeroute\rivals_build") {
    for ($try = 1; $try -le 3; $try++) {
        Log ("START {0} : {1} {2}  (try {3}; free RAM GB {4:N1}; free D: GB {5:N1})" -f $name, $module, ($cliArgs -join ' '), $try, ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB), (FreeGB))
        Push-Location $dir
        $out = & py -3.9 -B -m $module @cliArgs --config $cfg 2>&1 | ForEach-Object { $l = "$_"; Add-Content -Encoding utf8 -Path $LOG -Value $l; $l }
        $code = $LASTEXITCODE
        Pop-Location
        Log "END $name exit $code"
        if ($code -eq 0) { return }
        $ram = ($out | Where-Object { $_ -match 'GiB is available \(watchdog' }).Count -gt 0
        if (-not ($ram -and $cliArgs[0] -in @('refit', 'tune') -and $try -lt 3)) { break }
        Log "RAM guard refusal in ${name}: retrying in a fresh process in 60 s (finished work is skipped)"
        Start-Sleep -Seconds 60
    }
    Log "STOPPED at $name (exit $code). Send this log to the agent."; exit 1
}
if ((Get-Command Invoke-RivalStep -ErrorAction SilentlyContinue).CommandType -ne "Function") { Log "STOPPED: Invoke-RivalStep does not resolve to the script function"; exit 1 }

Log "waiting for the human pre-signing runner to finish, then 5 quiet minutes"
while (@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'follow_human_pre' -and $_.CommandLine -notmatch 'Get-CimInstance' }).Count -gt 0) { Start-Sleep -Seconds 120 }
$hl = Get-ChildItem D:\treeroute\rivals_build\logs_owner\follow_human_*.log | Sort-Object LastWriteTime | Select-Object -Last 1
Log ("human runner ended; its last line: " + (Get-Content $hl.FullName -Tail 1))
$quiet = 0
while ($quiet -lt 5) { if (Busy) { $quiet = 0 } else { $quiet++ }; Start-Sleep -Seconds 60 }
if (Test-Path "$OUT\board.md") { Log "NDVI board already exists: $OUT\board.md"; exit 0 }

foreach ($L in 0, 6, 12) {
    if (-not (Test-Path "$EXP\lead_$L\export_manifest.json")) {
        if ((FreeGB) -lt 25) { Log ("PAUSED before the lead-$L export: D: has {0:N1} GB free (needs ~22 GB). Free disk (section 7), then run this again." -f (FreeGB)); exit 1 }
        Invoke-RivalStep "ndvi export $L" @("export", "--run", $RUN, "--package", "$ENG\datasets\ndvi", "--lead", "$L", "--resume")
    }
    Invoke-RivalStep "human slim ndvi $L" @("slim", "--run", $RUN, "--export", "$EXP\lead_$L") "rivals_human.cli" $HCFG "D:\treeroute\human_rivals_build\human"
    if ($L -eq 0) {
        if (-not (Test-Path "$OUT\board.json")) { Invoke-RivalStep "ndvi init" @("init", "--run", $RUN, "--export", "$EXP\lead_0", "--out", "D:\treeroute\rivals") }
        if (-not (Test-Path "$OUT\picks.json.lock.json")) {
            Invoke-RivalStep "ndvi probe 0" @("probe", "--out", $OUT, "--lead", "0")
            Invoke-RivalStep "ndvi tune" @("tune", "--out", $OUT, "--resume")
            Invoke-RivalStep "ndvi lock" @("lock", "--out", $OUT)
        } else { Log "picks already locked: probe, tune and lock skipped" }
    }
    Invoke-RivalStep "ndvi refit $L" @("refit", "--out", $OUT, "--lead", "$L", "--resume")
    if (-not (Test-Path "$OUT\board_lead_$L.csv")) { Invoke-RivalStep "ndvi score $L" @("score", "--out", $OUT, "--lead", "$L") } else { Log "lead $L already scored" }
}
Invoke-RivalStep "ndvi board" @("board", "--out", $OUT)
Log "NDVI BOARD DONE: $OUT\board.md"
Log ("free D: GB at the end: {0:N1}. Next: Part A signature (owner), then the human boards and the join." -f (FreeGB))
exit 0
