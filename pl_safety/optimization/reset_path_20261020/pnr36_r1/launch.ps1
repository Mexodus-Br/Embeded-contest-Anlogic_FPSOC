# One demand-started task, zero triggers; no recurrence or deployment.
$ErrorActionPreference = 'Stop'
$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$buildPath = Join-Path $workspaceRoot 'pl_safety/build/rtl_path36'
$taskName = 'Codex-PL36-PnR-20261020-R1'
if (!(Test-Path -LiteralPath (Join-Path $buildPath 'run.tcl'))) { throw 'Prepare the independent complete project first' }
if ((Test-Path -LiteralPath (Join-Path $buildPath 'run.log')) -or (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'launch.json'))) { throw 'Refuse duplicate launch' }
$pythonPath = (Get-Command python -CommandType Application | Select-Object -First 1).Source
$pythonWindowless = Join-Path (Split-Path $pythonPath) 'pythonw.exe'
if (!(Test-Path -LiteralPath $pythonWindowless)) { throw 'Windowless Python runtime missing' }
$service = New-Object -ComObject Schedule.Service
$service.Connect()
$folder = $service.GetFolder('\')
try { $existing = $folder.GetTask($taskName) } catch { $existing = $null }
if ($existing) { throw 'Task name exists; refusing overwrite' }
$definition = $service.NewTask(0)
$userName = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$definition.RegistrationInfo.Description = 'One requested candidate36 full synthesis/place/route; 16 threads; no triggers; no bitgen; self-cleans definition.'
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
$action.Arguments = '-u "' + (Join-Path $PSScriptRoot 'worker.py') + '"'
$action.WorkingDirectory = $workspaceRoot
$registered = $folder.RegisterTaskDefinition($taskName, $definition, 2, $userName, $null, 3, $null)
@{ task_name=$taskName; triggers=0; launched_at=[DateTimeOffset]::Now.ToString('o'); hashes_computed=$false } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'launch.json') -Encoding utf8
$null = $registered.Run($null)
Write-Output ('Launched: ' + $taskName)
