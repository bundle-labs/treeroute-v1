# follow_hboards.ps1 -- the human-rival boards after the Part A signature (Part 617; HUMAN_OWNER_COMMANDS.txt steps 7-8),
# 2026-10-25. Coral / defo / PM2.5 / NDVI boards, then the one rival table (fire joined as pending, Part B). Stops at the
# first failure; the coral picks must equal the DRY pass. Deletes nothing. Log: logs_ownerollow_hboards_<stamp>.log
$ErrorActionPreference = 'Continue'
# GUARD (2026-10-23): the step function was once named H, which PowerShell resolves to its built-in alias for
# Get-History, so every step silently ran Get-History and the script printed DONE. Refuse unless the name
# resolves to THIS script's function.
Set-Location D:\treeroute\human_rivals_build\human
$env:PYTHONDONTWRITEBYTECODE = "1"
$HCFG = "D:\treeroute\human_rivals_build\human\human_rivals_production.yaml"
$HDRY = "D:\treeroute\human_rivals_build\human\human_rivals_DRY.yaml"
$CORAL = "D:\treeroute\runs\coral\headline\20261020_f3b8e3da"
$DEFO  = "D:\treeroute\runs\defo\headline\20261017_d71c61f4"
$PM    = "D:\treeroute\runs\pm25\headline\20261007_74e67609"
$EXP   = "D:\treeroute\rival_export"
$DEFO_BOARD = "D:\treeroute\rivals\defo\20261017_d71c61f4\board.md"
$LOG = "D:\treeroute\rivals_build\logs_owner\follow_hboards_$(Get-Date -Format yyyyMMdd_HHmmss).log"
$script:STEPS_RUN = 0
function Log([string]$m) { $line = "[$(Get-Date -Format s)] $m"; Add-Content -Encoding utf8 -Path $LOG -Value $line; Write-Host $line }
function Busy { @(Get-CimInstance Win32_Process | Where-Object { ($_.CommandLine -match 'rivals\.cli' -or $_.CommandLine -match 'rivals_human\.cli' -or $_.CommandLine -match '-m treeroute' -or $_.CommandLine -match 'smoke_run\.py') -and $_.CommandLine -notmatch 'Get-CimInstance' -and $_.CommandLine -notmatch 'follow_' }).Count -gt 0 }
function Stop-OrphanWorkers {
    # multiprocessing workers whose parent process is gone (a parent stopped by the RAM watchdog leaves them idle,
    # and on 2026-10-23 they held the old pipe open so the runner hung for hours). Only orphans are stopped.
    Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'multiprocessing\.spawn' -and $_.CommandLine -match 'parent_pid=(\d+)' } | ForEach-Object {
        $pp = [int]([regex]::Match($_.CommandLine, 'parent_pid=(\d+)').Groups[1].Value)
        if (-not (Get-Process -Id $pp -ErrorAction SilentlyContinue)) {
            Stop-Process -Id $_.ProcessId -Force -Confirm:$false -ErrorAction SilentlyContinue
            Log "stopped orphan worker $($_.ProcessId) (its parent $pp is gone)"
        }
    }
}
function Invoke-HumanStep([string]$name, [string[]]$cliArgs, [string]$cfg = $HCFG) {
    Log ("START {0} : rivals_human.cli {1}  (free RAM GB {2:N1}; free D: GB {3:N1})" -f $name, ($cliArgs -join ' '), ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB), ((Get-PSDrive D).Free/1GB))
    # wait for the PROCESS to exit (not for its output pipe to close: orphaned workers kept that open), output to files
    $tmp = Join-Path $env:TEMP ("hstep_" + [guid]::NewGuid().ToString("N"))
    $argv = @("-3.9", "-B", "-m", "rivals_human.cli") + $cliArgs + @("--config", $cfg) | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }
    $p = Start-Process -FilePath "py" -ArgumentList $argv -NoNewWindow -PassThru -WorkingDirectory (Get-Location).Path -RedirectStandardOutput "$tmp.out" -RedirectStandardError "$tmp.err"
    $null = $p.Handle
    $p.WaitForExit()
    $code = $p.ExitCode
    foreach ($f in "$tmp.out", "$tmp.err") { if (Test-Path $f) { Get-Content $f | ForEach-Object { Add-Content -Encoding utf8 -Path $LOG -Value "$_" }; Remove-Item $f -ErrorAction SilentlyContinue } }
    Stop-OrphanWorkers
    Log "END $name exit $code"
    $script:STEPS_RUN++
    if ($code -ne 0) { Log "STOPPED at $name (exit $code). Send this log to the agent."; exit 1 }
}

if ((Get-Command Invoke-HumanStep -ErrorAction SilentlyContinue).CommandType -ne "Function") { Log "STOPPED: Invoke-HumanStep does not resolve to the script function"; exit 1 }
$NDVI = "D:\treeroute\runs\ndvi\headline\20261016_d1de3158"
$FIRE = "D:\treeroute\runs\fire\headline\20261017_869d1f38"
$HB = "D:\treeroute\rivals_human"
$EAC4_DECISION = "ruling AG1: MERRA-2 is the P row (PLAN R2); CAMS EAC4 not obtained"
Log "human boards after the Part A signature (Part 617, 2026-10-25); waiting for 5 quiet minutes"
$quiet = 0
while ($quiet -lt 5) { if (Busy) { $quiet = 0 } else { $quiet++ }; Start-Sleep -Seconds 60 }
function Invoke-Board([string]$tag, [string]$run, [string]$out, [int[]]$leads, [string[]]$initExtra, [string[]]$lockExtra, [string]$dryPicks) {
    if (-not (Test-Path "$out\human_board.json")) { Invoke-HumanStep "$tag init" (@("init", "--run", $run) + $initExtra) }
    if (-not (Test-Path "$out\human_picks.json.lock.json")) {
        Invoke-HumanStep "$tag tune" @("tune", "--out", $out, "--resume")
        Invoke-HumanStep "$tag lock" (@("lock", "--out", $out) + $lockExtra)
    } else { Log "$tag picks already locked" }
    if ($dryPicks) {
        $sha = (& py -3.9 -B -c "import json,sys; sys.path.insert(0,'.'); from rivals_human import lockfile as LK; print(LK.picks_content_sha(json.load(open(r'$out\human_picks.json'))['picks']))" 2>$null | Select-Object -Last 1)
        Log "$tag picks content $sha (DRY pass $dryPicks)"
        if ($sha -ne $dryPicks) { Log "STOPPED: $tag picks differ from the DRY pass (HUMAN_OWNER_COMMANDS step 7 check). Send this log to the agent."; exit 1 }
    }
}
function Invoke-Leads([string]$tag, [string]$out, [int[]]$leads) {
    foreach ($L in $leads) { Invoke-HumanStep "$tag refit $L" @("refit", "--out", $out, "--lead", "$L", "--resume") }
    foreach ($L in ($leads | Sort-Object -Descending)) { Invoke-HumanStep "$tag refs $L" @("refs", "--out", $out, "--lead", "$L") }
    foreach ($L in $leads) { Invoke-HumanStep "$tag score $L" @("score", "--out", $out, "--lead", "$L") }
    Invoke-HumanStep "$tag board" @("board", "--out", $out)
}
# coral
$HOUT = "$HB\coral\20261020_f3b8e3da"
Invoke-Board "coral" $CORAL $HOUT @(0, 183, 365) @() @() "ebef5359f26e9e314d445f496c5d00f78c32abc3e7cc228b4f7fa745e2b8ae5a"
Invoke-Leads "coral" $HOUT @(0, 183, 365)
# defo (stage-test prep after the lock)
$HOUT = "$HB\defo\20261017_d71c61f4"
Invoke-Board "defo" $DEFO $HOUT @(0, 1) @() @() ""
Invoke-HumanStep "defo prep test" @("prep", "--run", $DEFO, "--rival", "vt0007_shipped", "--stage", "test")
Invoke-HumanStep "manifest defo_vt0007_prep (test)" @("manifest", "--product", "defo_vt0007_prep")
foreach ($R in "vt0007_shipped", "vt0007_cal", "vt0007_frozen2019") {
    Invoke-HumanStep "adapt $R test" @("adapt", "--run", $DEFO, "--rival", $R, "--lead", "all", "--stage", "test")
    Invoke-HumanStep "check $R" @("check", "--run", $DEFO, "--rival", $R)
}
Invoke-Leads "defo" $HOUT @(0, 1)
# pm25 (ruling AG1: MERRA-2 is the P row; the EAC4 rows are locked out by the recorded decision)
$HOUT = "$HB\pm25\20261007_74e67609"
Invoke-Board "pm25" $PM $HOUT @(0, 6, 12) @("--allow-waiting") @("--without", "eac4_lag1", "eac4_same", "eac4_lag1_placebo", "--decision", $EAC4_DECISION) ""
Invoke-Leads "pm25" $HOUT @(0, 6, 12)
# ndvi
$HOUT = "$HB\ndvi\20261016_d1de3158"
Invoke-Board "ndvi" $NDVI $HOUT @(0, 6, 12) @() @() ""
Invoke-Leads "ndvi" $HOUT @(0, 6, 12)
# one rival table (fire = Part B, pending)
Invoke-HumanStep "join" @("join", "--runs", $CORAL, $DEFO, $PM, $NDVI, "--pending", $FIRE, "--part", "617")
Log "HUMAN BOARDS AND JOIN DONE ($($script:STEPS_RUN) steps): D:\treeroute\rivals_table\<stamp>\RIVALS_TABLE.md"
exit 0
