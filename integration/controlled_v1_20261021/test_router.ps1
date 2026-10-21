param([string]$Tag = 'seven-router-powershell')
$ErrorActionPreference = 'Stop'
if ($Tag -notmatch '^[A-Za-z0-9_-]+$') { throw 'Invalid tag' }
$taskRoot = $PSScriptRoot
$repoRoot = Split-Path (Split-Path $taskRoot -Parent) -Parent
Push-Location $repoRoot
try {
    python integration/controlled_v1_20261021/test_router.py --prepare-only --tag $Tag
    if ($LASTEXITCODE -ne 0) { throw 'Preparation failed' }
    $caseRoot = "integration/controlled_v1_20261021/evidence/$Tag"
    # This Windows Icarus requires execution outside the restricted sandbox.
    iverilog -g2005 -I integration/controlled_v1_20261021/hardware/gp -I integration/controlled_v1_20261021/hardware -s tb_router -o "$caseRoot/test.vvp" integration/controlled_v1_20261021/hardware/gp/safety_axi_lite_seven_way.v "$caseRoot/tb.v" *> "$caseRoot/compile.log"
    if ($LASTEXITCODE -ne 0) { throw 'Compilation failed; preserve log' }
    vvp "$caseRoot/test.vvp" *> "$caseRoot/simulation.log"
    if ($LASTEXITCODE -ne 0) { throw 'Simulation failed; preserve log' }
    $sim = Get-Content "$caseRoot/simulation.log" -Raw
    if ($sim -notmatch 'PASS seven-way A33 response ownership checks=460') { throw 'Missing pass marker' }
    @{passed=$true;checks=460;hashes_computed=$false;launcher='PowerShell'} | ConvertTo-Json | Set-Content "$caseRoot/result.json"
    Write-Output $sim
} finally { Pop-Location }
