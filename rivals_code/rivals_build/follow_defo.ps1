# follow_defo.ps1 -- the agent's runner for the defo common-rival board (RIVALS_OWNER_COMMANDS.md section 5), 2026-10-22.
# Waits until no rivals.cli / engine process has run for 5 minutes in a row (so it never collides with a command you run
# yourself), then runs every step; each step is resumable, so running this again continues where it stopped.
# It stops at the first failure, and before refit lead 1 if D: has less than 9 GB free (then delete the lead-0 fit-set
# copies, section 7, and run this again). It deletes nothing. Log: logs_owner\follow_defo_<stamp>.log
$ErrorActionPreference = 'Continue'
Set-Location D:\treeroute\rivals_build
$CFG = "D:\treeroute\rivals_build\rivals_production.yaml"
$ENG = "C:\Users\<user>\Desktop\data set for reserch paper\engine"
$stamp = Get-Date -Format yyyyMMdd_HHmmss
$LOG = "D:\treeroute\rivals_build\logs_owner\follow_defo_$stamp.log"
function Log([string]$m) { $line = "[$(Get-Date -Format s)] $m"; Add-Content -Encoding utf8 -Path $LOG -Value $line; Write-Host $line }
function FreeGB { (Get-PSDrive D).Free / 1GB }
function Busy { @(Get-CimInstance Win32_Process | Where-Object { ($_.CommandLine -match 'rivals\.cli' -or $_.CommandLine -match '-m treeroute' -or $_.CommandLine -match 'smoke_run\.py') -and $_.CommandLine -notmatch 'Get-CimInstance' -and $_.CommandLine -notmatch 'follow_' }).Count -gt 0 }
function Step([string]$name, [string[]]$cliArgs) {
    # A refit holds the earlier learners' fit-set copies in memory until the process ends, so a later learner can hit
    # the harness RAM guard ("... GiB is available (watchdog"). A fresh process skips the finished learners (--resume,
    # same hash) and frees that memory: retry such a refusal up to 2 times. Any other failure stops.
    for ($try = 1; $try -le 3; $try++) {
        Log ("START {0} : rivals.cli {1}  (try {2}; free RAM GB {3:N1}; free D: GB {4:N1})" -f $name, ($cliArgs -join ' '), $try, ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB), (FreeGB))
        $out = & py -3.9 -B -m rivals.cli @cliArgs --config $CFG 2>&1 | ForEach-Object { $l = "$_"; Add-Content -Encoding utf8 -Path $LOG -Value $l; $l }
        $code = $LASTEXITCODE
        Log "END $name exit $code"
        if ($code -eq 0) { return }
        $ram = ($out | Where-Object { $_ -match 'GiB is available \(watchdog' }).Count -gt 0
        if (-not ($ram -and $cliArgs[0] -eq 'refit' -and $try -lt 3)) { break }
        Log "RAM guard refusal in ${name}: retrying in a fresh process in 60 s (finished learners are skipped)"
        Start-Sleep -Seconds 60
    }
    Log "STOPPED at $name (exit $code). Send this log to the agent."; exit 1
}
Log "waiting for 5 quiet minutes (no other rivals/engine process)"
$quiet = 0
while ($quiet -lt 5) { if (Busy) { $quiet = 0 } else { $quiet++ }; Start-Sleep -Seconds 60 }

$RUN = "D:\treeroute\runs\defo\headline\20261017_d71c61f4"
$OUT = "D:\treeroute\rivals\defo\20261017_d71c61f4"
$EXP = "D:\treeroute\rival_export\defo\20261017_d71c61f4"
if (Test-Path "$OUT\board.md") { Log "defo board already exists: $OUT\board.md"; exit 0 }
if (-not (Test-Path "$EXP\lead_1\export_manifest.json") -and (FreeGB) -lt 24) { Log ("STOPPED: D: has {0:N1} GB free; the defo export + lead-0 copies need ~15 GB and lead 1 another ~6.7 GB" -f (FreeGB)); exit 1 }
if (-not (Test-Path "$EXP\lead_1\export_manifest.json")) {
    Step "defo export" @("export", "--run", $RUN, "--package", "$ENG\datasets\defo", "--lead", "all", "--resume")
}
if (-not (Test-Path "$OUT\board.json")) { Step "defo init" @("init", "--run", $RUN, "--export", "$EXP\lead_0", "--out", "D:\treeroute\rivals") }
if (-not (Test-Path "$OUT\picks.json.lock.json")) {          # picks are written once: after the lock, skip these
    Step "defo probe 0" @("probe", "--out", $OUT, "--lead", "0")
    Step "defo tune" @("tune", "--out", $OUT, "--resume")
    Step "defo lock" @("lock", "--out", $OUT)
} else { Log "picks already locked: probe, tune and lock skipped" }
Step "defo refit 0" @("refit", "--out", $OUT, "--lead", "0", "--resume")
if (-not (Test-Path "$OUT\board_lead_0.csv")) { Step "defo score 0" @("score", "--out", $OUT, "--lead", "0") } else { Log "lead 0 already scored" }
if ((FreeGB) -lt 9) { Log ("PAUSED before refit 1: D: has {0:N1} GB free. Delete the defo lead-0 fit-set copies (section 7), then run this script again." -f (FreeGB)); exit 1 }
Step "defo refit 1" @("refit", "--out", $OUT, "--lead", "1", "--resume")
if (-not (Test-Path "$OUT\board_lead_1.csv")) { Step "defo score 1" @("score", "--out", $OUT, "--lead", "1") } else { Log "lead 1 already scored" }
Step "defo board" @("board", "--out", $OUT)
Log "DEFO BOARD DONE: $OUT\board.md"
Log ("free D: GB at the end: {0:N1}. Next (owner): human slim of defo BEFORE deleting its export; then free disk (section 7) and run NDVI (section 6b)." -f (FreeGB))
exit 0
