$ErrorActionPreference='Stop'
. ./jobs/manifest.ps1
New-Item -ItemType Directory -Force artifacts/result | Out-Null
Remove-Item artifacts/result/PASS -ErrorAction SilentlyContinue
$files=SourceInventory
$hashes=@{};foreach($file in $files){$hashes[$file]=(Get-FileHash $file -Algorithm SHA256).Hash}
$win=(Get-Location).Path
$linux=(& wsl.exe -e wslpath -a $win).Trim()
& wsl.exe -e bash ($linux+'/jobs/test.sh') $linux
if ($LASTEXITCODE -ne 0) { throw 'Test workload failed' }
& node --check mcc/static/app.js
if ($LASTEXITCODE -ne 0) { throw 'UI syntax failed' }
& node --check jobs/browser.mjs
if ($LASTEXITCODE -ne 0) { throw 'Browser harness syntax failed' }
& wsl.exe -e bash ($linux+'/jobs/package.sh') $linux
if ($LASTEXITCODE -ne 0) { throw 'Clean wheel gate failed' }
& ./jobs/stock.ps1
if(@(Compare-Object $files (SourceInventory)).Count -ne 0){throw 'Source membership changed'}
foreach($file in $files){if($hashes[$file] -ne (Get-FileHash $file -Algorithm SHA256).Hash){throw 'Source changed during validation'}}
RequiredEvidence
$evidence=@{};foreach($file in (EvidenceInventory)){$evidence[$file]=(Get-FileHash $file -Algorithm SHA256).Hash}
@{schemaVersion=1;source=$hashes;evidence=$evidence;exitCode=0;run=(Split-Path (Get-Location).Path -Leaf)} | ConvertTo-Json -Depth 4 | Set-Content artifacts/result/PASS
