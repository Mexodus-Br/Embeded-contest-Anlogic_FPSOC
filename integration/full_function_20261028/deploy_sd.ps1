$ErrorActionPreference = 'Stop'
$taskRoot = 'D:\Works\Embedded_contest\dev\integration\full_function_20261028'
$privateDirectory = Join-Path $taskRoot 'artifacts\private-rollback'
$exitFile = Join-Path $taskRoot 'artifacts\sd-deploy-20261029-01.exit'
if (Test-Path -LiteralPath $exitFile) { throw 'Preserve prior deployment attempt' }
New-Item -ItemType Directory -Path $privateDirectory -Force | Out-Null
$userSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
& icacls.exe $privateDirectory '/inheritance:r' '/grant:r' "*${userSid}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Private backup ACL failed' }
& 'C:\Users\boru\AppData\Local\Programs\Python\Python310\python.exe' (Join-Path $taskRoot 'deploy_sd.py') `
    --disk 1 `
    --unique-id 'USBSTOR\DISK&VEN_RSUER&PROD_RTSUERLUN0&REV_1.00\0000:LAPTOP-JS7E5LFJ' `
    --bytes 31299993600 `
    --image (Join-Path $taskRoot 'artifacts\release-r1\sdcard.img') `
    --sha256 '3340b2dd9a58d99ba2bc5004b498ca8705cabb451f69393e401ec0bee7d5edc5' `
    --root-partuuid '3201cd3a-02' `
    --log (Join-Path $taskRoot 'artifacts\sd-deploy-20261029-01.log') `
    --backup (Join-Path $privateDirectory 'live-f330c1cf-before-full-function-r1.img')
$deploymentExit = $LASTEXITCODE
Set-Content -LiteralPath $exitFile -Value $deploymentExit
exit $deploymentExit
