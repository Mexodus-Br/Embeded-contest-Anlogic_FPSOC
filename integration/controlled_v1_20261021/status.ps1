param([switch]$Json, [ValidateRange(1,100)][int]$Tail = 12)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$runRoot = Join-Path $taskRoot 'hardware'
$logPath = Join-Path $runRoot 'run.log'
if (-not (Test-Path -LiteralPath $logPath)) { throw "Missing run log: $logPath" }
# Read-only: no hashes, device access, process control, or build commands.
$logInfo = Get-Item -LiteralPath $logPath
$lines = @(Get-Content -LiteralPath $logPath -Tail 2500)
$complete = [bool]($lines -match '^INTERLOCK_FULL_TOP_COMPLETE\s*$')
$threadReads = @($lines | Where-Object { $_ -match '^INTERLOCK_TD_THREADS\s+16\s*$' })
$stageLines = @($lines | Where-Object { $_ -match 'Stage [0-9]|RTL_POST_ROUTE_HIGH_|INTERLOCK_FULL_TOP_COMPLETE' })
$processError = $null
try {
    $running = @(Get-CimInstance Win32_Process -OperationTimeoutSec 5 -Filter "Name='td_commands_prompt.exe'" |
        Where-Object { $_.CommandLine -like '*controlled_v1_20261021/hardware/run.tcl*' -or $_.CommandLine -like '*controlled_v1_20261021\hardware\run.tcl*' } |
        Select-Object ProcessId, ParentProcessId, CreationDate)
} catch { $running = @(); $processError = $_.Exception.Message }
$reports = @()
foreach ($name in @('gate.timing','place.timing','route_before_physopt.timing','route.timing','route.area','route.check','route.drc')) {
    $path = Join-Path $runRoot $name
    if (Test-Path -LiteralPath $path) {
        $item = Get-Item -LiteralPath $path
        $reports += [pscustomobject]@{name=$name; bytes=$item.Length; modified=$item.LastWriteTime.ToString('o'); path=$path}
    }
}
$timing = @()
$finalTiming = Join-Path $runRoot 'route.timing'
if (Test-Path -LiteralPath $finalTiming) {
    $timing = @(Select-String -LiteralPath $finalTiming -Pattern 'WNS|TNS|Slack|slack|Setup|Hold|Period' | Select-Object -First 30 | ForEach-Object {$_.Line})
}
$state = if ($complete) {'FLOW_COMPLETE_REVIEW_REQUIRED'} elseif ($running.Count) {'RUNNING'} elseif ($processError) {'PROCESS_UNKNOWN'} else {'STOPPED_OR_NOT_VISIBLE_CHECK_LOG'}
$result = [pscustomobject]@{
    checked_at=(Get-Date).ToString('o'); state=$state; processes=$running; process_query_error=$processError
    log=$logPath; log_modified=$logInfo.LastWriteTime.ToString('o'); log_age_seconds=[math]::Round(((Get-Date)-$logInfo.LastWriteTime).TotalSeconds)
    last_stage=($stageLines | Select-Object -Last 1); completion_marker=$complete
    thread16_readbacks_in_tail=$threadReads.Count; reports=$reports; final_timing_excerpt=$timing
    signoff_pass=$false; boot_chain_generated=$false; board_acceptance='NOT_EXECUTED'
    note='Intermediate WNS is not final STA. Completion requires review of nominal 100MHz constraints, timing, resources and open gates. No motion authorization.'
    log_tail=@($lines | Select-Object -Last $Tail)
}
if ($Json) { $result | ConvertTo-Json -Depth 6; exit }
Write-Output ("State: {0} | checked: {1}" -f $state,$result.checked_at)
Write-Output ("Log updated: {0} | age: {1}s" -f $result.log_modified,$result.log_age_seconds)
Write-Output ("Stage: {0}" -f $result.last_stage)
Write-Output ("TD PID: {0} | 16-thread readbacks in last 2500 lines: {1}" -f (($running.ProcessId) -join ','),$threadReads.Count)
if ($processError) { Write-Output "Process query unavailable: $processError" }
Write-Output 'Reports (existence does not imply approval):'
$reports | Format-Table name,bytes,modified -AutoSize | Out-String | Write-Output
if ($timing.Count) { Write-Output 'Final timing file excerpt (requires completion marker and review):'; $timing | Write-Output }
Write-Output $result.note
Write-Output 'signoff_pass=false; BOOT/SD not generated; board acceptance not executed.'
Write-Output 'Recent log:'
$result.log_tail | Write-Output
