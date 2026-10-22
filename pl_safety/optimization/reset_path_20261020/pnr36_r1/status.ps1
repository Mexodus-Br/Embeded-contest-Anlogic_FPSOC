# Read-only query. Ctrl+C exits the query and leaves TD running.
param([switch]$Watch, [ValidateRange(1,60)][int]$IntervalSeconds=5, [ValidateRange(0,100)][int]$Tail=8)
$ErrorActionPreference='Stop'
$workspaceRoot=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$buildPath=Join-Path $workspaceRoot 'pl_safety/build/rtl_path36'
function Show-RunStatus {
    Write-Output ('Time: '+[DateTimeOffset]::Now.ToString('yyyy-MM-dd HH:mm:ss zzz'))
    Write-Output 'Run: rtl_path36; full synthesis -> place -> route; original 10ns final constraints'
    $statePath=Join-Path $PSScriptRoot 'state.json'
    $resultPath=Join-Path $PSScriptRoot 'result.json'
    $summaryPath=Join-Path $buildPath 'route_summary.json'
    $logPath=Join-Path $buildPath 'run.log'
    $finished=$false
    if (Test-Path -LiteralPath $resultPath) {
        $r=Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
        $finished=$true
        Write-Output ('State: '+$(if ($r.flow_completed) {'COMPLETED'} else {'FAILED'}))
        Write-Output ('Completed: '+$r.completed_at)
        if ($r.flow_completed) {
            foreach ($stage in @('gate','place','route')) {
                $t=$r.stages.$stage
                Write-Output ('{0}: setup {1} ns; hold {2} ns' -f $stage,$t.setup_ns,$t.hold_ns)
            }
            Write-Output ('Final setup > 1ns / hold >= 0 target: '+$r.timing_target_met)
            Write-Output ('LUT6 {0}; Slice {1}; Slice FF {2}; PAD FF {3}; ERAM {4}; DSP {5}; IO {6}' -f $r.resources.lut6,$r.resources.slice,$r.resources.slice_ff,$r.resources.pad_ff,$r.resources.eram,$r.resources.dsp,$r.resources.io)
        } else { Write-Output $r.failure }
        Write-Output 'Production signoff: NOT GRANTED'
        Write-Output ('Result: '+$resultPath)
    } elseif (Test-Path -LiteralPath $statePath) {
        $s=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        $taskState='unavailable';$running=$false
        try {
            $scheduler=New-Object -ComObject Schedule.Service
            $scheduler.Connect()
            $taskState=$scheduler.GetFolder('\').GetTask($s.task_name).State
            $running=$taskState -eq 4
        } catch { }
        Write-Output ('State: '+$(if ($running) {'RUNNING'} else {'PROCESS_NOT_VISIBLE_OR_STOPPED; inspect log/task'}))
        Write-Output ('Worker PID: {0}; builder PID: {1}; independent task state: {2} (4=running)' -f $s.worker_pid,$s.builder_pid,$taskState)
        $processPath=Join-Path $buildPath 'process.json'
        if (Test-Path -LiteralPath $processPath) {
            $p=Get-Content -LiteralPath $processPath -Raw | ConvertFrom-Json
            $td=Get-Process -Id $p.td_pid -ErrorAction SilentlyContinue
            if ($td -and $td.ProcessName -eq 'td_commands_prompt') {
                $expected=[DateTimeOffset]::Parse($p.td_started_at_utc).UtcDateTime
                if ([Math]::Abs(($td.StartTime.ToUniversalTime()-$expected).TotalSeconds) -lt 5) {
                    Write-Output ('TD PID {0}; CPU seconds {1:N1}; elapsed {2}' -f $td.Id,$td.CPU,((Get-Date)-$td.StartTime).ToString('hh\:mm\:ss'))
                }
            }
        }
    } else { Write-Output 'State: NOT_STARTED' }
    if (Test-Path -LiteralPath $logPath) {
        $log=Get-Content -LiteralPath $logPath -Raw
        $readback=($log -match 'INTERLOCK_TD_THREADS 16') -and ($log -match 'Number of Thread = 16')
        $phase=if ($log -match 'INTERLOCK_FULL_TOP_COMPLETE') {'finished; checking reports'} elseif ($log -match 'start command "route"') {'route'} elseif ($log -match 'start command "place"') {'place'} else {'synthesis / preparation'}
        Write-Output ('Phase: '+$phase+'; 16 threads read back: '+$readback)
        Write-Output ('Log updated: '+(Get-Item -LiteralPath $logPath).LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'))
        Write-Output ('Log: '+$logPath)
        Write-Output 'Live log slack is intermediate; only final route summary decides the timing target.'
        if ($Tail -gt 0) { Get-Content -LiteralPath $logPath -Tail $Tail }
    } elseif (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'builder.log')) {
        Get-Content -LiteralPath (Join-Path $PSScriptRoot 'builder.log') -Tail $Tail
    }
    return $finished
}
do {
    $lines=@(Show-RunStatus)
    $finished=$lines[-1]
    if ($lines.Count -gt 1) { $lines[0..($lines.Count-2)] | Write-Output }
    if (!$Watch -or $finished) { break }
    Start-Sleep -Seconds $IntervalSeconds
    Write-Output ''
} while ($true)
