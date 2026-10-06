$ErrorActionPreference='Stop'
New-Item -ItemType Directory -Force artifacts/result | Out-Null
$root=(Get-Location).Path
$fixture=Get-ChildItem $env:TEMP -Directory -Filter 'mcc-stock-*' | Sort-Object CreationTime -Descending | Select-Object -First 1
if(-not $fixture){throw 'No isolated completed stock fixture available'}
$stock=$fixture.FullName
$env:PATH=(Join-Path $stock 'node-v26.8.2-win-x64')+';'+$env:PATH
$env:NODE_NO_WARNINGS='1'
$ErrorActionPreference='Continue'
& node jobs/browser.mjs $stock $root ((& wsl.exe -e wslpath -a $root).Trim()) *> artifacts/result/browser.log
$exit=$LASTEXITCODE
$ErrorActionPreference='Stop'
if($exit -ne 0){throw 'Focused browser gate failed; sanitized failure artifact'}
