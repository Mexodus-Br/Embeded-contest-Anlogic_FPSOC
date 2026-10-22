# Read-only status query; optional -Watch. Ctrl+C stops only the query.
param(
    [switch]$Watch,
    [ValidateRange(1,60)][int]$IntervalSeconds = 5,
    [ValidateRange(0,100)][int]$Tail = 8
)
$ErrorActionPreference = 'Stop'
$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$buildPath = Join-Path $workspaceRoot 'pl_safety/build/reset21_physopt_high_r1'

function Show-RunStatus {
    Write-Output ('Time: ' + [DateTimeOffset]::Now.ToString('yyyy-MM-dd HH:mm:ss zzz'))
    Write-Output 'Run: reset21_physopt_high_r1; phys_opt -post_route -effort high'
    $resultPath = Join-Path $buildPath 'result.json'
    $statePath = Join-Path $buildPath 'state.json'
    $logPath = Join-Path $buildPath 'run.log'
    if (!(Test-Path -LiteralPath $statePath)) {
        Write-Output 'State: NOT_STARTED'
        return $false
    }
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    if (Test-Path -LiteralPath $resultPath) {
        $result = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
        Write-Output ('State: ' + $(if ($result.flow_completed) { 'COMPLETED' } else { 'FAILED' }))
        Write-Output ('Completed: ' + $result.completed_at)
        if ($result.flow_completed) {
            Write-Output ('Setup: {0} -> {1} ns; delta {2} ns' -f $result.before.setup_ns,$result.after.setup_ns,$result.setup_delta_ns)
            Write-Output ('Hold: {0} -> {1} ns' -f $result.before.hold_ns,$result.after.hold_ns)
            Write-Output ('Timing target setup > 1ns and hold >= 0: ' + $result.timing_target_met)
            Write-Output ('Slice: {0} -> {1}; FF: {2} -> {3}; ERAM: {4} -> {5}' -f $result.resources_before.slice,$result.resources_after.slice,$result.resources_before.slice_reg,$result.resources_after.slice_reg,$result.resources_before.eram,$result.resources_after.eram)
        } else { Write-Output $result.failure }
        Write-Output ('Result: ' + $resultPath)
    } else {
        $worker = if ($state.worker_pid) { Get-Process -Id $state.worker_pid -ErrorAction SilentlyContinue } else { $null }
        $tdProcess = if ($state.td_pid) { Get-Process -Id $state.td_pid -ErrorAction SilentlyContinue } else { $null }
        # A reused PID must not be reported as this run's live TD process.
        if ($tdProcess -and $tdProcess.ProcessName -ne 'td_commands_prompt') { $tdProcess = $null }
        if ($tdProcess -and $state.td_started_at_utc) {
            $expected = [DateTimeOffset]::Parse($state.td_started_at_utc).UtcDateTime
            if ([Math]::Abs(($tdProcess.StartTime.ToUniversalTime() - $expected).TotalSeconds) -gt 5) { $tdProcess = $null }
        }
        # Restricted shells can hide a process outside their own job. Query
        # the independent task as well, instead of falsely declaring it dead.
        $taskRunning = $false
        $taskState = 'unavailable'
        try {
            $scheduler = New-Object -ComObject Schedule.Service
            $scheduler.Connect()
            $scheduledTask = $scheduler.GetFolder('\').GetTask($state.task_name)
            $taskState = [string]$scheduledTask.State
            $taskRunning = $scheduledTask.State -eq 4
        } catch { }
        Write-Output ('State: ' + $(if ($tdProcess -or $taskRunning) { 'RUNNING' } elseif ($worker) { 'STARTING / FINALIZING' } elseif ($state.phase -eq 'prepared') { 'PREPARED' } else { 'PROCESS_NOT_VISIBLE_OR_STOPPED; inspect log/task' }))
        Write-Output ('Phase: ' + $state.phase + '; worker PID: ' + $state.worker_pid + '; TD PID: ' + $state.td_pid)
        Write-Output ('Independent task state: ' + $taskState + ' (4 = running)')
        if ($tdProcess) {
            Write-Output ('TD CPU seconds: {0:N1}; elapsed: {1}' -f $tdProcess.CPU,((Get-Date)-$tdProcess.StartTime).ToString('hh\:mm\:ss'))
        }
    }
    if (Test-Path -LiteralPath $logPath) {
        $log = Get-Content -LiteralPath $logPath -Raw
        $threadReadback = $log -match 'PHYSOPT_HIGH_THREADS 16' -and $log -match 'Number of Thread = 16'
        $highEntered = $log.Contains('start command "phys_opt -post_route -effort high"')
        Write-Output ('16 threads read back: ' + $threadReadback + '; HIGH command entered: ' + $highEntered)
        Write-Output ('Log updated: ' + (Get-Item -LiteralPath $logPath).LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'))
        Write-Output ('Log: ' + $logPath)
        if ($Tail -gt 0) { Get-Content -LiteralPath $logPath -Tail $Tail }
    }
    return (Test-Path -LiteralPath $resultPath)
}

do {
    $lines = @(Show-RunStatus)
    # The function's final boolean is internal; the preceding lines are output.
    $finished = $lines[-1]
    if ($lines.Count -gt 1) { $lines[0..($lines.Count-2)] | Write-Output }
    if (!$Watch -or $finished) { break }
    Start-Sleep -Seconds $IntervalSeconds
    Write-Output ''
} while ($true)
