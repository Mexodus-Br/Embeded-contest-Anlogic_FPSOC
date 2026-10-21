$ErrorActionPreference='Stop'
$taskRoot='D:\Works\Embedded_contest\dev'
$pythonPath='C:\Users\boru\AppData\Local\Programs\Python\Python310\python.exe'
$imagePath=Join-Path $taskRoot 'bsp\artifacts\motor3125\sdcard.img'
$rollbackPath=Join-Path $taskRoot 'bsp\artifacts\scope-release-final\output\release\sdcard.img'
$logPath=Join-Path $taskRoot 'bsp\evidence\motor3125-sd-windows-20261021-01.log'
$uniqueId='USBSTOR\DISK&VEN_RSUER&PROD_RTSUERLUN0&REV_1.00\0000:LAPTOP-JS7E5LFJ'
$imageHash='f9fbe564a5cec7662c2fd9267f5ce437db0d5f3097e6e41eef73f4ef573b17a3'
if (Test-Path -LiteralPath $logPath) { throw 'Evidence exists; preserve this attempt and use a separately reviewed new log path' }
if ((Get-FileHash -LiteralPath $imagePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $imageHash) { throw 'Candidate image identity mismatch' }
if ((Get-FileHash -LiteralPath $rollbackPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne '66d1b0cff5e56db5b8572eb879a3d9781e25c1028fa3168c2ec6142e6e3a6ff6') { throw 'Rollback image identity mismatch' }
$targets=@(Get-Disk | Where-Object { $_.UniqueId -eq $uniqueId -and $_.FriendlyName -eq 'Generic- SD/MMC/MS PRO' -and $_.Size -eq 31299993600 -and $_.BusType -eq 'USB' -and -not $_.IsBoot -and -not $_.IsSystem -and -not $_.IsReadOnly -and -not $_.IsOffline })
if ($targets.Count -ne 1) { throw 'Expected one previously authorized, non-system SD card; target identity is ambiguous' }
$targetDisk=$targets[0]
Write-Output ('VERIFIED_TARGET_DISK='+$targetDisk.Number+' SIZE='+$targetDisk.Size+' WRITE_RANGE=0..536870911')
$arguments=@(
    (Join-Path $taskRoot 'bsp\scripts\write_sd_windows.py'),
    '--disk',[string]$targetDisk.Number,'--unique-id',$uniqueId,
    '--bytes','31299993600','--image',$imagePath,'--sha256',$imageHash,
    '--root-partuuid','f330c1cf-02','--log',$logPath
)
$quotedArguments=($arguments | ForEach-Object { '"'+$_+'"' }) -join ' '
$process=Start-Process -FilePath $pythonPath -ArgumentList $quotedArguments -Verb RunAs -WindowStyle Hidden -PassThru
Write-Output ('SD_WRITER_STARTED_PID='+$process.Id)
$process.WaitForExit()
Write-Output ('SD_WRITER_EXIT='+$process.ExitCode)
if ($process.ExitCode -ne 0) { throw 'SD write/readback failed; retain evidence and stop' }
