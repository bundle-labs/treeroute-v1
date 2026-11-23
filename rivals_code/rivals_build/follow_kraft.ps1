# follow_kraft.ps1 -- the optional Kraft LSTM prep for the NDVI human board (HUMAN_OWNER_COMMANDS.txt step 5, O15),
# owner choice 2026-10-25 (the author's answer, not quoted, ruling AI). Same step runner as follow_human_pre.ps1 (waits for
# the PROCESS, stops orphaned workers). Reads no test label. Deletes nothing. Log: logs_ownerollow_kraft_<stamp>.log
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
$LOG = "D:\treeroute\rivals_build\logs_owner\follow_kraft_$(Get-Date -Format yyyyMMdd_HHmmss).log"
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
Log "waiting for 5 quiet minutes"
$quiet = 0
while ($quiet -lt 5) { if (Busy) { $quiet = 0 } else { $quiet++ }; Start-Sleep -Seconds 60 }
Invoke-HumanStep "O15 manifest monthly_panel" @("manifest", "--product", "monthly_panel")
Invoke-HumanStep "O15 prep kraft_lstm" @("prep", "--run", $NDVI, "--rival", "kraft_lstm")
Invoke-HumanStep "O15 manifest ndvi_kraft_store" @("manifest", "--product", "ndvi_kraft_store")
$sh = & py -3.9 -B -m rivals_human.cli shas --run $NDVI --config $HCFG 2>&1 | Where-Object { $_ -notmatch 'Warning|warn' }
$sh | ForEach-Object { Add-Content -Encoding utf8 -Path $LOG -Value "$_" }
$sh | Set-Content -Encoding utf8 -Path "D:\treeroute\human_rivals_build\SHAS_FOR_PART_A_NDVI_KRAFT.txt"
Log "KRAFT PREP DONE ($($script:STEPS_RUN) steps)"
exit 0
