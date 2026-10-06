$ErrorActionPreference='Stop'
New-Item -ItemType Directory -Force artifacts/result | Out-Null
$win=(Get-Location).Path
$linux=(& wsl.exe -e wslpath -a $win).Trim()
& wsl.exe -e bash ($linux+'/jobs/test.sh') $linux
if ($LASTEXITCODE -ne 0) { throw 'Unit gate failed' }
& node --check mcc/static/app.js
if ($LASTEXITCODE -ne 0) { throw 'UI syntax failed' }
