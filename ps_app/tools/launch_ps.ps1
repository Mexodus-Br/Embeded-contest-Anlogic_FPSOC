param([switch]$NoBrowser, [switch]$SimulationInjection, [ValidateRange(0,65535)][int]$Port = 0)
$ErrorActionPreference = 'Stop'
$psRoot = Split-Path -Parent $PSScriptRoot
$psBinary = Join-Path $psRoot 'build\partner\native\ps_server.exe'
$psToken = Join-Path $psRoot '.cache\ps-token'
$psStateFile = Join-Path $psRoot '.cache\launcher.json'
$psProcess = $null
$psSaved = $null
if (Test-Path -LiteralPath $psStateFile) {
    $psSaved = Get-Content -LiteralPath $psStateFile -Raw -Encoding UTF8 | ConvertFrom-Json
    $psCandidate = Get-Process -Id $psSaved.pid -ErrorAction SilentlyContinue
    if ($psCandidate -and $psCandidate.Path -eq $psBinary -and
        $psCandidate.StartTime.ToUniversalTime().Ticks.ToString() -eq $psSaved.start_ticks) {
        if ($Port -ne 0 -and $Port -ne $psSaved.port) {
            throw 'This folder already has a running service. Stop it before changing its port.'
        }
        $psProcess = $psCandidate
        $Port = [int]$psSaved.port
    }
}
if (-not $psProcess) {
    if (-not (Test-Path -LiteralPath $psBinary)) { throw 'Build with python tools/build_ps.py --server first.' }
    $psUsedPorts = @([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | ForEach-Object { $_.Port })
    if ($Port -eq 0) {
        $psAvailable = @(18083..18102 | Where-Object { $_ -notin $psUsedPorts })
        if ($psAvailable.Count -eq 0) { throw 'No free port in 18083..18102. Supply -Port with an available port.' }
        $Port = $psAvailable[0]
    }
    if ($Port -le 1024 -or $Port -in $psUsedPorts) { throw "Port $Port is unavailable. Supply another -Port." }
    New-Item -ItemType Directory -Force -Path (Join-Path $psRoot '.cache') | Out-Null
    $psProcess = Start-Process -FilePath $psBinary -ArgumentList '--backend', 'simulation', '--allow-simulation-injection', $SimulationInjection.IsPresent.ToString().ToLowerInvariant(), '--port', $Port -WorkingDirectory $psRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $psRoot '.cache\ps-server.log') -RedirectStandardError (Join-Path $psRoot '.cache\ps-server-error.log')
    @{ pid = $psProcess.Id; port = $Port; start_ticks = $psProcess.StartTime.ToUniversalTime().Ticks.ToString() } | ConvertTo-Json | Set-Content -LiteralPath $psStateFile -Encoding UTF8
}
$psUrl = "http://127.0.0.1:$Port"
$psHealth = $null
for ($psAttempt=0; $psAttempt -lt 40; $psAttempt++) {
    if ($psProcess.HasExited) { throw 'PS service failed to start. See .cache/ps-server-error.log.' }
    try { $psHealth = Invoke-RestMethod -Uri ($psUrl + '/api/health') -TimeoutSec 2 } catch { $psHealth = $null }
    if ($psHealth -and $psHealth.app -eq 'ps-simulation') { break }
    Start-Sleep -Milliseconds 150
}
if (-not $psHealth -or $psHealth.app -ne 'ps-simulation') { throw 'PS service did not respond.' }
if (-not $NoBrowser) {
    $psSecret = (Get-Content -LiteralPath $psToken -Raw -Encoding UTF8).Trim()
    # Fragment is consumed by app.js and removed before authentication.
    Start-Process ($psUrl + '/#token=' + $psSecret)
    $psSecret = $null
}
Write-Output $psUrl
