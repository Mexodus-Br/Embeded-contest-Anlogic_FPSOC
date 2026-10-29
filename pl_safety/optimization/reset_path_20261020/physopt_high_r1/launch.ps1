# One explicit run, no schedule/recurrence; independent of the chat process.
$ErrorActionPreference = 'Stop'
$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$buildPath = Join-Path $workspaceRoot 'pl_safety/build/reset21_physopt_high_r1'
$taskName = 'Codex-PL21-PhysOptHigh-20261020-R1'
$pythonPath = (Get-Command python -CommandType Application | Select-Object -First 1).Source
$pythonWindowless = Join-Path (Split-Path $pythonPath) 'pythonw.exe'
if (!(Test-Path -LiteralPath $pythonWindowless)) { throw 'Windowless Python runtime missing' }
if (Test-Path -LiteralPath $buildPath) { throw 'Attempt already exists; refusing overwrite or duplicate start' }
& $pythonPath (Join-Path $PSScriptRoot 'worker.py') --prepare-only
if ($LASTEXITCODE -ne 0) { throw 'Independent project preparation failed' }

$service = New-Object -ComObject Schedule.Service
$service.Connect()
$folder = $service.GetFolder('\')
try { $existing = $folder.GetTask($taskName) } catch { $existing = $null }
if ($existing) { throw 'Task name already exists; refusing to overwrite' }
$definition = $service.NewTask(0)
$userName = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$definition.RegistrationInfo.Description = 'One user-requested TD phys_opt post-route HIGH run; 16 threads, no triggers, no deployment, self-cleans definition.'
$definition.Principal.UserId = $userName
$definition.Principal.LogonType = 3
$definition.Principal.RunLevel = 0
$definition.Settings.Enabled = $true
$definition.Settings.Hidden = $true
$definition.Settings.AllowDemandStart = $true
$definition.Settings.DisallowStartIfOnBatteries = $false
$definition.Settings.StopIfGoingOnBatteries = $false
$definition.Settings.ExecutionTimeLimit = 'PT9H'
$definition.Settings.MultipleInstances = 2
$action = $definition.Actions.Create(0)
$action.Path = $pythonWindowless
$action.Arguments = '-u "' + (Join-Path $PSScriptRoot 'worker.py') + '" --task-name ' + $taskName
$action.WorkingDirectory = $workspaceRoot
$registered = $folder.RegisterTaskDefinition($taskName, $definition, 2, $userName, $null, 3, $null)
@{ task_name=$taskName; origin='Windows Task Scheduler'; triggers=0; hashes_computed=$false;
   launched_at_taipei=[DateTimeOffset]::Now.ToString('o') } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $buildPath 'launch.json') -Encoding utf8
$null = $registered.Run($null)
Write-Output ('Launched one-shot hidden task: ' + $taskName)
Write-Output ('Status: & "' + (Join-Path $PSScriptRoot 'status.ps1') + '"')
