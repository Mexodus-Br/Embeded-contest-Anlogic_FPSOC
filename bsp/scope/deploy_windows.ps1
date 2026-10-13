$ErrorActionPreference='Stop'
$taskRoot='D:\Works\Embedded_contest\dev'
$pythonPath='C:\Users\boru\AppData\Local\Programs\Python\Python310\python.exe'
$imagePath=Join-Path $taskRoot 'bsp\artifacts\scope-release-final\output\release\sdcard.img'
$logPath=Join-Path $taskRoot 'bsp\evidence\scope-sd-windows-write-20261013-01.log'
if (Test-Path -LiteralPath $logPath) { throw 'Evidence already exists; do not overwrite it' }
$arguments=@(
    (Join-Path $taskRoot 'bsp\scripts\write_sd_windows.py'),
    '--disk','1','--unique-id','USBSTOR\DISK&VEN_RSUER&PROD_RTSUERLUN0&REV_1.00\0000:LAPTOP-JS7E5LFJ',
    '--bytes','31299993600','--image',$imagePath,
    '--sha256','66d1b0cff5e56db5b8572eb879a3d9781e25c1028fa3168c2ec6142e6e3a6ff6',
    '--root-partuuid','8aea5f8d-02','--log',$logPath
)
$quotedArguments=($arguments | ForEach-Object { '"'+$_+'"' }) -join ' '
$process=Start-Process -FilePath $pythonPath -ArgumentList $quotedArguments -Verb RunAs -WindowStyle Hidden -PassThru
Write-Output ('SD_WRITER_STARTED_PID='+$process.Id)
$process.WaitForExit()
Write-Output ('SD_WRITER_EXIT='+$process.ExitCode)
if ($process.ExitCode -ne 0) { throw 'SD writer failed; inspect raw log before further action' }
