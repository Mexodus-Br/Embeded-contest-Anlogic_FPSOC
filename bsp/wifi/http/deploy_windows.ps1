param([switch]$Elevated)
$ErrorActionPreference='Stop'
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$python='C:\Users\boru\AppData\Local\Programs\Python\Python310\python.exe'
$admin=[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    if ($Elevated) { throw 'Administrator elevation failed' }
    $process=Start-Process -FilePath powershell.exe -Verb RunAs -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$PSCommandPath+'"'),'-Elevated') -PassThru
    $process.WaitForExit()
    exit $process.ExitCode
}
# Authorization and identity belong ONLY to the new card examined 2026-10-19.
# A future deployment must refresh this identity; never treat disk 1 as permanent.
$disk=Get-Disk -Number 1
$identity='USBSTOR\DISK&VEN_RSUER&PROD_RTSUERLUN0&REV_1.00\0000:LAPTOP-JS7E5LFJ'
if ($disk.UniqueId -ne $identity -or $disk.Size -ne 31708938240 -or $disk.BusType -ne 'USB' -or $disk.IsBoot -or $disk.IsSystem) { throw 'Current authorized SD identity changed' }
Set-Location -LiteralPath $workspace
try {
    & $python bsp/scripts/write_sd_windows.py --disk 1 --unique-id $identity --bytes 31708938240 --image bsp/artifacts/wifi-http-20261019/sdcard.img --sha256 03a1ad579677026833863d3335e8d76d21074acb7c1dc577eb2594ba16e5bb65 --root-partuuid 70d791a8-02 --log bsp/evidence/wifi-http-sd-20261019-01.log
    $result=$LASTEXITCODE
} catch {
    $_ | Out-String | Set-Content -Encoding UTF8 bsp/evidence/wifi-http-sd-20261019-launch-error.txt
    $result=1
}
$result | Set-Content bsp/evidence/wifi-http-sd-20261019-exit.txt
exit $result
