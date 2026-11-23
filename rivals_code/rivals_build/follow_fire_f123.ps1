# follow_fire_f123.ps1 -- the agent's runner for Part B steps F1-F3 (HUMAN_OWNER_COMMANDS_partB.txt section 2), 2026-10-26,
# after ruling AJ. Dot-sources the setup block copied verbatim from that file (fire_setup_partB.ps1), then runs F1 (slim
# fire leads 0/6/12), F2 (manifests fire_static_cells, fire_target_2018), F3 (refs label store + T-F18). No test score.
# Log: logs_owner\follow_fire_f123_<stamp>.log
$LOG = "D:\treeroute\rivals_build\logs_owner\follow_fire_f123_$(Get-Date -Format yyyyMMdd_HHmmss).log"
Start-Transcript -Path $LOG -Append | Out-Null
try {
    . D:\treeroute\rivals_build\fire_setup_partB.ps1
    foreach ($f in "Invoke-FireStepF1", "Invoke-FireStepF2", "Invoke-FireStepF3") {
        if ((Get-Command $f -ErrorAction SilentlyContinue).CommandType -ne "Function") { throw "STOP: $f does not resolve to the setup-block function" }
    }
    Write-Host "[$(Get-Date -Format s)] F1 start"; Invoke-FireStepF1
    Write-Host "[$(Get-Date -Format s)] F2 start"; Invoke-FireStepF2
    Write-Host "[$(Get-Date -Format s)] F3 start"; Invoke-FireStepF3
    Write-Host "[$(Get-Date -Format s)] FIRE F1-F3 DONE"
    $code = 0
} catch {
    Write-Host "[$(Get-Date -Format s)] $($_.Exception.Message)"
    $code = 1
} finally { Stop-Transcript | Out-Null }
exit $code
