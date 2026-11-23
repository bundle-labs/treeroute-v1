# follow_human_pre.ps1 -- the agent's runner for the human-rival PRE-SIGNING steps (HUMAN_OWNER_COMMANDS.txt steps 2-4),
# 2026-10-22, ruling AG4: after the defo common board, before NDVI. Reads NO test label (no human test score exists
# before Part A is signed). PM2.5 uses MERRA-2 (ruling AG1): no EAC4 steps. It waits until the defo board exists (or the
# defo runner stopped), then 5 quiet minutes. Stops at the first failure; deletes nothing; every step can be re-run.
# Log: D:\treeroute\rivals_build\logs_owner\follow_human_<stamp>.log
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
$LOG = "D:\treeroute\rivals_build\logs_owner\follow_human_$(Get-Date -Format yyyyMMdd_HHmmss).log"
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
Log "waiting for the defo common board ($DEFO_BOARD)"
while (-not (Test-Path $DEFO_BOARD)) {
    $dl = Get-ChildItem D:\treeroute\rivals_build\logs_owner\follow_defo_*.log -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
    if ($dl -and (Select-String -Path $dl.FullName -Pattern 'STOPPED|PAUSED' -Quiet)) { Log "STOPPED: the defo runner stopped ($($dl.Name)); human steps not started"; exit 1 }
    Start-Sleep -Seconds 120
}
Log "defo board exists; waiting for 5 quiet minutes"
$quiet = 0
while ($quiet -lt 5) { if (Busy) { $quiet = 0 } else { $quiet++ }; Start-Sleep -Seconds 60 }

# ---- step 0: the human tool's full test suite + review tests with the machine free (Part 613: the last full run had
#      27 setup errors, all the toy RAM guard refusing while the defo export held the memory). Any failure stops here.
$stamp = Get-Date -Format yyyyMMdd_HHmmss
New-Item -ItemType Directory -Force D:\treeroute\human_rivals_build\pt\ag | Out-Null
$toolsha = (& py -3.9 -B -c "import sys; sys.path.insert(0,'.'); from rivals_human.common import tool_code_sha; print(tool_code_sha())" 2>$null | Select-Object -Last 1)
$marker = "D:\treeroute\human_rivals_build\pt\ag\tests_passed_$toolsha.txt"
if ($toolsha -and (Test-Path $marker)) { Log "test suite already passed on tool code $($toolsha.Substring(0,16)): skipped" } else {
Log "START full human test suite (basetemp pt\ag\pre_$stamp)"
& py -3.9 -B -m pytest rivals_human/tests tests_builder_b tests_builder_c --basetemp "D:\treeroute\human_rivals_build\pt\ag\pre_$stamp" -q -p no:cacheprovider 2>&1 | ForEach-Object { Add-Content -Encoding utf8 -Path $LOG -Value "$_" }
if ($LASTEXITCODE -ne 0) { Log "STOPPED: the human test suite did not pass (exit $LASTEXITCODE). Send this log to the agent."; exit 1 }
& py -3.9 -B -m pytest -c ..\review_tests\pytest.ini ..\review_tests --basetemp "D:\treeroute\human_rivals_build\pt\ag\prerev_$stamp" -q -p no:cacheprovider 2>&1 | ForEach-Object { Add-Content -Encoding utf8 -Path $LOG -Value "$_" }
if ($LASTEXITCODE -ne 0) { Log "STOPPED: the review tests did not pass (exit $LASTEXITCODE). Send this log to the agent."; exit 1 }
Log "human test suite and review tests passed"
if ($toolsha) { Set-Content -Path $marker -Value "passed $(Get-Date -Format s)" }
}

# ---- step 2: coral slim, manifests, coral index tables, the coral TUNE-ONLY DRY pass
foreach ($L in 0, 183, 365) { Invoke-HumanStep "O1 slim coral $L" @("slim", "--run", $CORAL, "--export", "$EXP\coral\20261020_f3b8e3da\lead_$L") }
foreach ($P in "coral_sst_npz", "crw_climatology", "crw_outlook", "coral_store_20261020") { Invoke-HumanStep "O4 manifest $P" @("manifest", "--product", $P) }
Invoke-HumanStep "D6 manifest verify" @("manifest", "--product", "noaa_crw_dhw_sitedays", "--verify")
Invoke-HumanStep "D4 manifest verify" @("manifest", "--product", "gadm36_defo42", "--verify")
foreach ($P in "merra2_aer_monthly", "pm25_static_cells", "ndvi_static_cells") { Invoke-HumanStep "O5 manifest $P" @("manifest", "--product", $P) }
Invoke-HumanStep "O7 adapt crw_dhw" @("adapt", "--run", $CORAL, "--rival", "crw_dhw", "--lead", "all")
Invoke-HumanStep "O8 adapt crw_outlook" @("adapt", "--run", $CORAL, "--rival", "crw_outlook", "--lead", "all")
Invoke-HumanStep "check crw_dhw" @("check", "--run", $CORAL, "--rival", "crw_dhw")
Invoke-HumanStep "check crw_outlook" @("check", "--run", $CORAL, "--rival", "crw_outlook")
$DOUT = "D:\treeroute\rivals_human_dry\coral\20261020_f3b8e3da"
if (-not (Test-Path "$DOUT\human_board.json")) { Invoke-HumanStep "O9 DRY init" @("init", "--run", $CORAL, "--dry") $HDRY } else { $script:STEPS_RUN++ }
if (-not (Test-Path "$DOUT\human_picks.json.lock.json")) {     # the lock is write-once
    Invoke-HumanStep "O9 DRY tune" @("tune", "--out", $DOUT, "--resume") $HDRY
    Invoke-HumanStep "O9 DRY lock" @("lock", "--out", $DOUT) $HDRY
} else { Log "O9 DRY picks already locked: tune and lock skipped"; $script:STEPS_RUN += 2 }
$sha = & py -3.9 -B -c "import json,sys; sys.path.insert(0,'.'); from rivals_human import lockfile as LK; print(LK.picks_content_sha(json.load(open(r'$DOUT\human_picks.json'))['picks']))" 2>&1
Log "O9 DRY picks content sha: $sha"

# ---- step 3: PM2.5 slim + MERRA-2 index tables (ruling AG1: no EAC4)
foreach ($L in 0, 6, 12) { Invoke-HumanStep "O2 slim pm25 $L" @("slim", "--run", $PM, "--export", "$EXP\pm25\20261007_74e67609\lead_$L") }
foreach ($R in "merra2_lag1", "merra2_same", "merra2_lag1_placebo") { Invoke-HumanStep "O12 adapt $R" @("adapt", "--run", $PM, "--rival", $R, "--lead", "0") }

# ---- step 4: defo manifests, the stage-train prep (~6 GB RAM, alone), defo slim + train-side index tables
foreach ($P in "hansen_gfc_v1_13", "defo_target", "defo_static") { Invoke-HumanStep "O6 manifest $P" @("manifest", "--product", $P) }
foreach ($L in 0, 1) { Invoke-HumanStep "O3 slim defo $L" @("slim", "--run", $DEFO, "--export", "$EXP\defo\20261017_d71c61f4\lead_$L") }   # the prep reads the slim (2026-10-23)
Invoke-HumanStep "O10 defo prep train" @("prep", "--run", $DEFO, "--rival", "vt0007_shipped", "--stage", "train")
Invoke-HumanStep "manifest defo_vt0007_prep" @("manifest", "--product", "defo_vt0007_prep")
foreach ($R in "vt0007_shipped", "vt0007_cal", "vt0007_frozen2019") {
    Invoke-HumanStep "adapt $R train" @("adapt", "--run", $DEFO, "--rival", $R, "--lead", "all", "--stage", "train")
    Invoke-HumanStep "check $R" @("check", "--run", $DEFO, "--rival", $R)
}
if ($script:STEPS_RUN -lt 30) { Log "STOPPED: only $($script:STEPS_RUN) steps ran (expected 37-38); not DONE"; exit 1 }
Log "HUMAN PRE-SIGNING STEPS 2-4 DONE ($($script:STEPS_RUN) steps). Next: NDVI common board (owner frees disk first, section 7), NDVI slims, then Part A signature."
Log ("free D: GB at the end: {0:N1}" -f ((Get-PSDrive D).Free/1GB))
exit 0
