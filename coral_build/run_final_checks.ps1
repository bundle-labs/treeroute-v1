# run_final_checks.ps1 -- the owner's last checks of the coral build before the install (RULING_V_REPORT.md).
#
# What it does, in order, one heavy process at a time:
#   1. moves D:\treeroute\coral_build\noop aside to D:\treeroute\coral_build\_moved\noop_<timestamp> (a move, never a
#      delete), and also moves aside an old pt\full folder and an old fullsuite.xml (pytest would empty pt\full);
#   2. runs D:\treeroute\coral_build\run_noop_proof.ps1: the four grid smokes (pm25, fire, defo, ndvi) under LIVE and
#      under the build copy, then a byte comparison of each pair (about 30-35 min);
#   3. runs the one full test suite of the build copy from D:\treeroute\coral_build\engine (about 45 min):
#        py -3.9 -m pytest -q -p no:cacheprovider --basetemp D:\treeroute\coral_build\pt\full
#                          --junitxml D:\treeroute\coral_build\fullsuite.xml
#   4. prints one final line: the proof's RESULT line and the suite counts (read from fullsuite.xml).
# Expected time: about 75-80 minutes in all.
# Every log write is UTF-8 (Set-Content / Add-Content -Encoding utf8; no Tee-Object, which writes UTF-16 in PS 5.1).
# Writes only under D:\treeroute\coral_build (and the engines' own temp dir, cleaned by each run).
# The suite runs even when the proof fails, so both results are known; a failed proof still means: do not install.
# Exit 0 = proof PASS and the suite ran (read its counts: some old failures are expected). Exit 1 = proof not PASS.
# Exit 2 = a precondition failed.
#
# Run it from a FRESH PowerShell window (the engine refuses foreign BLAS/OpenMP variables), with games closed:
#   powershell -ExecutionPolicy Bypass -File D:\treeroute\coral_build\run_final_checks.ps1

$ErrorActionPreference = 'Continue'
$Root    = 'D:\treeroute\coral_build'
$Build   = Join-Path $Root 'engine'
$Noop    = Join-Path $Root 'noop'
$Moved   = Join-Path $Root '_moved'
$Proof   = Join-Path $Root 'run_noop_proof.ps1'
$PtFull  = Join-Path $Root 'pt\full'
$Junit   = Join-Path $Root 'fullsuite.xml'
$Stamp   = Get-Date -Format 'yyyyMMdd_HHmmss'
$Log     = Join-Path $Root "final_checks_$Stamp.log"
$SuiteLog = Join-Path $Root "fullsuite_$Stamp.log"

function Write-Log([string]$line) {
    # one UTF-8 line into the run log, and the same line on the console
    Add-Content -Encoding utf8 -Path $Log -Value $line
    Write-Host $line
}

function Stop-Checks([string]$why) {
    Write-Log "STOPPED: $why"
    exit 2
}

function Move-Aside([string]$path, [string]$name) {
    # move, never delete; refuse if the destination exists
    if (-not (Test-Path $path)) { return }
    $dest = Join-Path $Moved "$($name)_$Stamp"
    if (Test-Path $dest) { Stop-Checks "$dest exists; not overwriting it" }
    New-Item -ItemType Directory -Force $Moved | Out-Null
    Move-Item -LiteralPath $path -Destination $dest -ErrorAction Stop
    Write-Log "moved $path -> $dest"
}

Set-Content -Encoding utf8 -Path $Log -Value "final checks started $(Get-Date -Format s)"

# ---- preconditions -------------------------------------------------------------------------------------------
foreach ($f in @($Proof, (Join-Path $Build 'treeroute\__init__.py'))) {
    if (-not (Test-Path $f)) { Stop-Checks "missing: $f" }
}
$busy = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'treeroute (smoke|run|plan)' -or $_.CommandLine -match '-m pytest' })
$busy = @($busy | Where-Object { $_.ProcessId -ne $PID })
if ($busy.Count -gt 0) {
    Stop-Checks "another engine or pytest process is running (pid $($busy[0].ProcessId)); one heavy job at a time"
}

# ---- 1. move the old outputs aside ---------------------------------------------------------------------------
try {
    Move-Aside $Noop 'noop'
    Move-Aside $PtFull 'pt_full'
    Move-Aside $Junit 'fullsuite_xml'
} catch {
    Stop-Checks "a move failed: $($_.Exception.Message)"
}

# ---- 2. the grid no-op proof ---------------------------------------------------------------------------------
Write-Log "[$(Get-Date -Format HH:mm:ss)] no-op proof: $Proof"
$t0 = Get-Date
& powershell -NoProfile -ExecutionPolicy Bypass -File $Proof
$proofCode = $LASTEXITCODE
Write-Log "no-op proof exit $proofCode in $([math]::Round(((Get-Date) - $t0).TotalMinutes, 1)) min"

$Summary = Join-Path $Noop 'noop_summary.txt'
$resultLine = 'RESULT: (no summary file)'
if (Test-Path $Summary) {
    $bytes = [IO.File]::ReadAllBytes($Summary)
    $found = $null
    foreach ($enc in @([Text.Encoding]::UTF8, [Text.Encoding]::Unicode)) {    # UTF-8 now; UTF-16 kept as a fallback
        $hit = ($enc.GetString($bytes) -split "`r?`n") | Where-Object { $_ -match 'RESULT:' } | Select-Object -Last 1
        if ($hit) { $found = $hit.Trim([char[]]@([char]0xFEFF, [char]32, [char]0)); break }
    }
    if ($found) { $resultLine = $found } else { $resultLine = 'RESULT: (no RESULT line in the summary)' }
}
Write-Log "proof: $resultLine"

# ---- 3. the one full suite -----------------------------------------------------------------------------------
Write-Log "[$(Get-Date -Format HH:mm:ss)] full suite from $Build (log $SuiteLog)"
Set-Content -Encoding utf8 -Path $SuiteLog -Value "full suite started $(Get-Date -Format s)"
$t1 = Get-Date
Push-Location $Build
& py -3.9 -m pytest -q -p no:cacheprovider --basetemp $PtFull --junitxml $Junit 2>&1 | ForEach-Object {
    $line = "$_"
    Add-Content -Encoding utf8 -Path $SuiteLog -Value $line
    Write-Host $line
}
$suiteCode = $LASTEXITCODE
Pop-Location
Write-Log "full suite exit $suiteCode in $([math]::Round(((Get-Date) - $t1).TotalMinutes, 1)) min"

$counts = 'suite: no junit file'
if (Test-Path $Junit) {
    try {
        [xml]$x = Get-Content -Raw -Encoding UTF8 $Junit
        $suites = @($x.SelectNodes('//testsuite'))
        $tests = 0; $fail = 0; $err = 0; $skip = 0
        foreach ($s in $suites) {
            $tests += [int]$s.tests; $fail += [int]$s.failures; $err += [int]$s.errors; $skip += [int]$s.skipped
        }
        $passed = $tests - $fail - $err - $skip
        $counts = "suite: $passed passed, $fail failed, $err errors, $skip skipped of $tests (pytest exit $suiteCode)"
        $names = @($x.SelectNodes('//testcase[failure or error]') | ForEach-Object { "$($_.classname)::$($_.name)" })
        foreach ($n in $names) { Write-Log "  failed: $n" }
    } catch {
        $counts = "suite: junit file unreadable ($($_.Exception.Message)); pytest exit $suiteCode"
    }
}

# ---- 4. one final line ---------------------------------------------------------------------------------------
Write-Log "FINAL: proof $resultLine | $counts | log $Log"
if ($resultLine -match 'RESULT: PASS') { exit 0 }
exit 1
