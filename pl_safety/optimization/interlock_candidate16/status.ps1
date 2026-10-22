# Read-only status. Does not start/stop tools or calculate hashes.
$workspaceRoot=(Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$launchPath=Join-Path $PSScriptRoot 'launch_r1'
$summaryPath=Join-Path $workspaceRoot 'pl_safety/build/interlock_route16/summary.json'
$logPath=Join-Path $workspaceRoot 'pl_safety/build/interlock_route16/run.log'
$realPath=Join-Path $PSScriptRoot 'launch_r1/real_result.json'
$activePath=Join-Path $PSScriptRoot 'active_run.json'
if (Test-Path $activePath) {
    $active=Get-Content -LiteralPath $activePath -Raw | ConvertFrom-Json
    $launchPath=Join-Path $PSScriptRoot $active.launch_directory
    $summaryPath=Join-Path $workspaceRoot $active.summary
    $logPath=Join-Path $workspaceRoot $active.log
    Write-Output ('Active attempt: '+$active.attempt)
}
if (Test-Path $summaryPath) {
    $result=Get-Content -LiteralPath $summaryPath -Raw | ConvertFrom-Json
    if (!$result.passed) {
        Write-Output 'TD flow FAILED / incomplete. Inspect summary.failure and logs.'
        Write-Output $result.failure
    } elseif ($result.timing_pass) {
        Write-Output 'TD flow COMPLETED; original 100MHz route timing target PASSED.'
    } else {
        Write-Output 'TD flow COMPLETED; original 100MHz route timing target FAILED.'
    }
    if ($result.stages) { $result.stages | ConvertTo-Json -Depth 4 }
} else {
    $metadataPath=Join-Path $launchPath 'process.json'
    if (Test-Path $metadataPath) {
        $metadata=Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
        $driver=Get-Process -Id $metadata.process_id -ErrorAction SilentlyContinue
        # PS7 decodes ISO JSON dates into DateTime; PS5 leaves strings.
        # Compare UTC ticks rather than culture-dependent string conversion.
        $expectedStart=([DateTimeOffset]$metadata.start_time_utc).UtcDateTime
        if ($driver -and $driver.StartTime.ToUniversalTime().Ticks -eq $expectedStart.Ticks) {
            Write-Output 'Background driver RUNNING; TD has no completion summary yet.'
        } else {
            Write-Output 'No live original driver and no TD summary: INTERRUPTED or failed to start; not success.'
        }
    } else { Write-Output 'Not launched: no process metadata or TD summary.' }
    if (Test-Path $logPath) {
        Get-Item -LiteralPath $logPath | Select-Object FullName,LastWriteTime,Length
        Get-Content -LiteralPath $logPath -Tail 8
    }
}
if (Test-Path $realPath) {
    $real=Get-Content -LiteralPath $realPath -Raw | ConvertFrom-Json
    if (!$real.completed) { Write-Output 'Real-IP validation RUNNING; completed cases below.' }
    elseif ($real.passed) { Write-Output 'Real-IP validation COMPLETED and PASSED.' }
    else { Write-Output 'Real-IP validation FAILED; inspect real_driver.log and case result.' }
    $real.cases | Format-Table scenario,passed,exit_code,tag -AutoSize
} else { Write-Output 'Real-IP validation has no completed case result yet.' }
$workflowPath=Join-Path $launchPath 'workflow_result.json'
if (Test-Path $workflowPath) {
    $workflow=Get-Content -LiteralPath $workflowPath -Raw | ConvertFrom-Json
    Write-Output ('All background work finished. Timing + validation passed: ' + $workflow.passed)
    Write-Output 'Resource/final database audits and release signoff still require review.'
}
