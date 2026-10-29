# One-shot on-demand task: started by Windows Task Scheduler, not the chat job.
$ErrorActionPreference='Stop'
$workspaceRoot=(Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$launchPath=Join-Path $PSScriptRoot 'launch_r3'
$taskName='Codex-PL16-PnR-20261020-R2'
if (Test-Path $launchPath) { throw 'Existing launch_r3 retained; refusing duplicate launch.' }
$pythonPath='C:/Users/boru/AppData/Local/Programs/Python/Python310/pythonw.exe'
if (!(Test-Path $pythonPath)) { throw 'Missing windowless Python runtime' }
$service=New-Object -ComObject Schedule.Service
$service.Connect()
$folder=$service.GetFolder('\')
$task=$service.NewTask(0)
$userName=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$task.RegistrationInfo.Description='User-requested one-shot PL16 place/route resume; no triggers, no deployment; removes its definition on exit.'
$task.Principal.UserId=$userName
$task.Principal.LogonType=3
$task.Principal.RunLevel=0
$task.Settings.Enabled=$true
$task.Settings.Hidden=$true
$task.Settings.AllowDemandStart=$true
$task.Settings.DisallowStartIfOnBatteries=$false
$task.Settings.StopIfGoingOnBatteries=$false
$task.Settings.ExecutionTimeLimit='PT9H'
$task.Settings.MultipleInstances=2
$task.Settings.Priority=4
$action=$task.Actions.Create(0)
$action.Path=$pythonPath
$action.Arguments='-u "'+(Join-Path $PSScriptRoot 'resume_pnr.py')+'" --attempt r2 --launch-dir launch_r3 --task-name '+$taskName
$action.WorkingDirectory=$workspaceRoot
# No triggers are created; only this explicit Run starts the task.
$registered=$folder.RegisterTaskDefinition($taskName,$task,2,$userName,$null,3,$null)
$null=New-Item -ItemType Directory -Path $launchPath
@{task_name=$taskName;origin='Windows Task Scheduler service';triggers=0;hashes_computed=$false} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $launchPath 'task.json') -Encoding utf8
# Stop only the verified previous attempt before another writer starts.
$oldMeta=Get-Content (Join-Path $PSScriptRoot 'launch_r2/process.json') -Raw | ConvertFrom-Json
$oldProcess=Get-Process -Id $oldMeta.process_id -ErrorAction SilentlyContinue
if ($oldProcess) {
    if ($oldProcess.StartTime.ToUniversalTime().Ticks -ne ([DateTimeOffset]$oldMeta.start_time_utc).UtcDateTime.Ticks) { throw 'Old PID identity changed' }
    $oldInfo=Get-CimInstance Win32_Process -Filter ('ProcessId='+$oldMeta.process_id)
    if (($oldInfo.CommandLine -replace '\\','/') -notmatch '/interlock_candidate16/resume_pnr[.]py') { throw 'Unexpected old driver command' }
    $children=Get-CimInstance Win32_Process -Filter "Name='td_commands_prompt.exe'" |
      Where-Object { $_.ParentProcessId -eq $oldMeta.process_id -and ($_.CommandLine -replace '\\','/') -match '/interlock_route16/resume_pnr_r1[.]tcl' }
    foreach ($child in $children) { Stop-Process -Id $child.ProcessId -ErrorAction Stop }
    for ($i=0;$i -lt 20;$i++) {
        if (!(Get-Process -Id $oldMeta.process_id -ErrorAction SilentlyContinue)) { break }
        Start-Sleep -Milliseconds 250
    }
    if (Get-Process -Id $oldMeta.process_id -ErrorAction SilentlyContinue) { throw 'Old driver did not exit; new task not started' }
}
@{reason='Intentional handoff to one-shot Windows Task Scheduler origin; original driver still in a managed job';hashes_computed=$false} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'launch_r2/interruption.json') -Encoding utf8
$running=$registered.Run($null)
for ($i=0;$i -lt 100;$i++) {
    if (Test-Path (Join-Path $launchPath 'started.json')) { break }
    Start-Sleep -Milliseconds 200
}
$started=Get-Content (Join-Path $launchPath 'started.json') -Raw | ConvertFrom-Json
$process=Get-Process -Id $started.process_id -ErrorAction Stop
@{process_id=$process.Id;start_time_utc=$process.StartTime.ToUniversalTime().ToString('o');task_name=$taskName;origin='Windows Task Scheduler service';hashes_computed=$false} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $launchPath 'process.json') -Encoding utf8
@{attempt='resume_pnr_r2';launch_directory='launch_r3';summary='pl_safety/build/interlock_route16/resume_pnr_r2_summary.json';log='pl_safety/build/interlock_route16/resume_pnr_r2.log'} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'active_run.json') -Encoding utf8
Write-Output ('Windows on-demand task started: '+$taskName+'; driver PID '+$process.Id)
Write-Output ('Task state: '+$running.State+'; triggers: '+$registered.Definition.Triggers.Count)
