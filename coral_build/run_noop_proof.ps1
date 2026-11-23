# run_noop_proof.ps1 -- the grid no-op proof for the coral build (BUILD_REPORT.md, step 4a).
#
# What it does, in order, one process at a time:
#   1. checks that each engine folder imports its own treeroute package, and prints both engine hashes;
#   2. runs the smoke of each real grid package (pm25, fire, defo, ndvi in LIVE\datasets) under the LIVE engine
#      (run root noop\old) and then under the build copy (run root noop\new), one after another;
#   3. compares each pair with tools\compare_runs.py (a verbatim copy of D:\treeroute\engine_next\tools\compare_runs.py):
#      every prediction/score file and derived.json byte for byte; every other JSON record after removing only
#      times, pids, paths, engine hashes and fingerprints.
# Both engines get the SAME package folders, so only the engine differs.
# Expected time: about 30-35 minutes (the same 8 smokes took 28 minutes on this machine on 2026-10-19).
# Writes only under D:\treeroute\coral_build\noop (and the engines' own temp dir, cleaned by each run).
# Exit 0 = every pair matches. Exit 1 = a pair differs or a smoke failed. Exit 2 = a precondition failed.
# Every file it writes is UTF-8 (2026-10-19 fix: Tee-Object -Append wrote UTF-16 into the UTF-8 summary under
# Windows PowerShell 5.1; it now uses Add-Content -Encoding utf8 with Write-Host).
#
# Run it from a FRESH PowerShell window (the engine refuses foreign BLAS/OpenMP variables), with games closed:
#   powershell -ExecutionPolicy Bypass -File D:\treeroute\coral_build\run_noop_proof.ps1

$ErrorActionPreference = 'Continue'
$Live    = 'C:\Users\<user>\Desktop\data set for reserch paper\engine'
$Build   = 'D:\treeroute\coral_build\engine'
$Out     = 'D:\treeroute\coral_build\noop'
$Compare = 'D:\treeroute\coral_build\tools\compare_runs.py'
$Packages = @('pm25', 'fire', 'defo', 'ndvi')
$OldRoot = Join-Path $Out 'old'
$NewRoot = Join-Path $Out 'new'
$LogDir  = Join-Path $Out 'logs'

function Stop-Proof([string]$why) {
    Write-Host "STOPPED: $why" -ForegroundColor Red
    exit 2
}

# ---- preconditions -------------------------------------------------------------------------------------------
if (-not (Test-Path $Compare)) { Stop-Proof "compare tool missing: $Compare" }
foreach ($root in @($OldRoot, $NewRoot)) {
    if ((Test-Path $root) -and (Get-ChildItem $root -Force | Select-Object -First 1)) {
        Stop-Proof "$root is not empty. Move it aside (for example to D:\treeroute\coral_build\_moved\noop_<date>) and rerun."
    }
}
foreach ($p in $Packages) {
    if (-not (Test-Path (Join-Path $Live "datasets\$p\dataset.yaml"))) { Stop-Proof "package missing: $Live\datasets\$p" }
}
New-Item -ItemType Directory -Force $OldRoot, $NewRoot, $LogDir | Out-Null

$Summary = Join-Path $Out 'noop_summary.txt'
function Write-Summary([string]$line) {
    # one UTF-8 line into the summary, and the same line on the console (never Tee-Object: UTF-16 in PS 5.1)
    Add-Content -Encoding utf8 -Path $Summary -Value $line
    Write-Host $line
}
"no-op proof started $(Get-Date -Format s)" | Set-Content -Encoding utf8 $Summary

foreach ($pair in @(@('LIVE', $Live), @('BUILD', $Build))) {
    $tag, $dir = $pair
    Push-Location $dir
    $file = (& py -3.9 -c "import treeroute;print(treeroute.__file__)" 2>&1 | Out-String).Trim()
    $hash = (& py -3.9 -c "from treeroute.runs.fingerprint import engine_code_sha256;print(engine_code_sha256())" 2>&1 | Out-String).Trim()
    Pop-Location
    $want = [IO.Path]::GetFullPath((Join-Path $dir 'treeroute\__init__.py'))
    Write-Summary "$tag engine: $file"
    Write-Summary "$tag engine_code_sha256: $hash"
    if ([IO.Path]::GetFullPath($file) -ne $want) { Stop-Proof "$tag imports $file, expected $want" }
}

# ---- smokes, one after another -------------------------------------------------------------------------------
function Invoke-Smoke([string]$tag, [string]$engineDir, [string]$package, [string]$runRoot) {
    $pkgDir = Join-Path $Live "datasets\$package"
    $log = Join-Path $LogDir "$($tag)_$package.log"
    Write-Host "[$(Get-Date -Format HH:mm:ss)] $tag smoke $package -> $runRoot" -ForegroundColor Cyan
    $t0 = Get-Date
    Push-Location $engineDir
    Set-Content -Encoding utf8 -Path $log -Value "$tag smoke $package started $(Get-Date -Format s)"
    & py -3.9 -u -m treeroute smoke $pkgDir --run-root $runRoot 2>&1 | ForEach-Object {
        $line = "$_"
        Add-Content -Encoding utf8 -Path $log -Value $line
        Write-Host $line
    }
    $code = $LASTEXITCODE
    Pop-Location
    $mins = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
    Write-Summary "$tag smoke $package exit $code in $mins min (log $log)"
    return $code
}

$failed = @()
foreach ($p in $Packages) {
    if ((Invoke-Smoke 'old' $Live $p $OldRoot) -ne 0) { $failed += "old smoke $p" }
    if ((Invoke-Smoke 'new' $Build $p $NewRoot) -ne 0) { $failed += "new smoke $p" }
}

# ---- byte comparison -----------------------------------------------------------------------------------------
foreach ($p in $Packages) {
    $a = @(Get-ChildItem (Join-Path $OldRoot "$p\smoke") -Directory -ErrorAction SilentlyContinue)
    $b = @(Get-ChildItem (Join-Path $NewRoot "$p\smoke") -Directory -ErrorAction SilentlyContinue)
    if ($a.Count -ne 1 -or $b.Count -ne 1) {
        Write-Summary "COMPARE ${p}: expected one run folder on each side, found $($a.Count) old and $($b.Count) new"
        $failed += "compare $p (run folders)"
        continue
    }
    Write-Summary "=== COMPARE $p : $($a[0].FullName)  vs  $($b[0].FullName)"
    & py -3.9 $Compare $a[0].FullName $b[0].FullName 2>&1 | ForEach-Object { Write-Summary "$_" }
    if ($LASTEXITCODE -ne 0) { $failed += "compare $p" }
}

if ($failed.Count -eq 0) {
    Write-Summary "RESULT: PASS. All four grid smokes are identical under LIVE and the build copy."
    exit 0
}
Write-Summary "RESULT: FAIL: $($failed -join '; ')"
exit 1
