# One-shot, user-authorized independent background launch. No hashes/bitgen.
$workspaceRoot=(Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$launchPath=Join-Path $PSScriptRoot 'launch_r1'
if ((Test-Path $launchPath) -or (Test-Path (Join-Path $workspaceRoot 'pl_safety/build/interlock_route16'))) {
    throw 'Existing launch/build retained; do not start a duplicate or overwrite evidence.'
}
foreach ($entry in @(@('interlock_suite_route16_20261020_r1',375),@('interlock_regressions_route16_20261020_r1',33))) {
    $resultPath=Join-Path $workspaceRoot ('pl_safety/evidence/'+$entry[0]+'/result.json')
    $result=Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
    if (!$result.passed -or $result.cases.Count -ne $entry[1]) { throw ('Prerequisite not passed: '+$entry[0]) }
}
$null=New-Item -ItemType Directory -Path $launchPath
$pythonPath='C:/Users/boru/AppData/Local/Programs/Python/Python310/python.exe'
$scriptPath=Join-Path $PSScriptRoot 'background_run.py'
$process=Start-Process -FilePath $pythonPath -ArgumentList @('-u',$scriptPath) -WorkingDirectory $workspaceRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $launchPath 'orchestrator.log') -RedirectStandardError (Join-Path $launchPath 'orchestrator.err') -PassThru
$metadata=@{
    process_id=$process.Id
    start_time_utc=$process.StartTime.ToUniversalTime().ToString('o')
    launched_at_taipei=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(8)).ToString('o')
    script=$scriptPath
    build='interlock_route16'
    independent_hidden_process=$true
    hashes_computed=$false
}
$metadata | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $launchPath 'process.json') -Encoding utf8
Write-Output ('Independent background process launched: '+$process.Id)
Write-Output ('Status script: '+(Join-Path $PSScriptRoot 'status.ps1'))
