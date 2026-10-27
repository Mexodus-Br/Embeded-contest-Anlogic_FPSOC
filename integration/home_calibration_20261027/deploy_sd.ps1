param([switch]$Elevated)
$ErrorActionPreference='Stop'
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$python='C:\Users\boru\AppData\Local\Programs\Python\Python310\python.exe'
$admin=[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    if ($Elevated) { throw 'Administrator elevation failed' }
    $process=Start-Process -FilePath powershell.exe -Verb RunAs -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$PSCommandPath+'"'),'-Elevated') -PassThru
    $process.WaitForExit()
    exit $process.ExitCode
}
Set-Location -LiteralPath $workspace
# Human authorization applies to this current card, 2026-10-27, only.
$disk=Get-Disk -Number 1
$identity='USBSTOR\DISK&VEN_RSUER&PROD_RTSUERLUN0&REV_1.00\0000:LAPTOP-JS7E5LFJ'
if ($disk.UniqueId -ne $identity -or $disk.FriendlyName -ne 'Generic- SD/MMC/MS PRO' -or $disk.Size -ne 31708938240 -or $disk.BusType -ne 'USB' -or $disk.IsBoot -or $disk.IsSystem -or $disk.IsReadOnly -or $disk.IsOffline) { throw 'Current authorized SD identity changed' }
$private=Join-Path $PSScriptRoot 'artifacts/private-rollback'
New-Item -ItemType Directory -Path $private -ErrorAction Stop | Out-Null
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
& icacls.exe $private /inheritance:r /grant:r ('*'+$sid+':(OI)(CI)F') '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Cannot secure private rollback directory' }
try {
 & $python integration/home_calibration_20261027/deploy_sd.py --disk 1 --unique-id $identity --bytes 31708938240 --image integration/home_calibration_20261027/artifacts/release-r2/sdcard.img --sha256 335a509643f57fe6753c5f596fc7e7f0d84cff7b9c8febc584fcc6779e85f69d --root-partuuid a61e22d5-02 --backup integration/home_calibration_20261027/artifacts/private-rollback/wifi-http-live-70d791a8-before-home-r2.img --log integration/home_calibration_20261027/artifacts/sd-deploy-20261027-01.log
 $result=$LASTEXITCODE
} catch {
 $_ | Out-String | Set-Content -Encoding UTF8 (Join-Path $PSScriptRoot 'artifacts/sd-deploy-launch-error.txt')
 $result=1
}
$result | Set-Content (Join-Path $PSScriptRoot 'artifacts/sd-deploy-exit.txt')
exit $result
