$ErrorActionPreference = 'Stop'
$psRoot = Split-Path -Parent $PSScriptRoot
$psBinary = Join-Path $psRoot 'build\partner\native\ps_server.exe'
$psStateFile = Join-Path $psRoot '.cache\launcher.json'
if (-not (Test-Path -LiteralPath $psStateFile)) { Write-Output 'No service started by this folder.'; exit 0 }
$psSaved = Get-Content -LiteralPath $psStateFile -Raw -Encoding UTF8 | ConvertFrom-Json
$psProcess = Get-Process -Id $psSaved.pid -ErrorAction SilentlyContinue
if ($psProcess) {
    if ($psProcess.Path -ne $psBinary -or $psProcess.StartTime.ToUniversalTime().Ticks.ToString() -ne $psSaved.start_ticks) {
        throw 'Process identity changed; no process was stopped.'
    }
    Stop-Process -Id $psProcess.Id
    $psProcess.WaitForExit()
}
Remove-Item -LiteralPath $psStateFile
Write-Output 'PS simulation service stopped.'
