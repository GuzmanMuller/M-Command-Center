$ErrorActionPreference='Stop'
$root=(Get-Location).Path
$out=Join-Path $root 'artifacts/result'
$stock=Join-Path $env:TEMP ('mcc-stock-'+[Guid]::NewGuid().ToString('N').Substring(0,10))
New-Item -ItemType Directory -Force $stock | Out-Null
$env:HOME=Join-Path $stock 'home'
$env:USERPROFILE=$env:HOME
$env:OPENCLAW_STATE_DIR=Join-Path $stock 'state'
$env:OPENCLAW_CONFIG_PATH=Join-Path $env:OPENCLAW_STATE_DIR 'openclaw.json'
New-Item -ItemType Directory -Force $env:HOME,$env:OPENCLAW_STATE_DIR | Out-Null
'{}' | Set-Content -Encoding Ascii $env:OPENCLAW_CONFIG_PATH
$before=(Get-FileHash $env:OPENCLAW_CONFIG_PATH).Hash
$env:npm_config_cache=Join-Path $stock 'npm-cache'
$env:npm_config_userconfig=Join-Path $stock 'empty-npmrc'
'' | Set-Content $env:npm_config_userconfig
Invoke-WebRequest -UseBasicParsing https://nodejs.org/dist/v26.8.2/node-v26.8.2-win-x64.zip -OutFile (Join-Path $stock 'node.zip')
Invoke-WebRequest -UseBasicParsing https://nodejs.org/dist/v26.8.2/SHASUMS256.txt -OutFile (Join-Path $stock 'node-shasums.txt')
$line=Get-Content (Join-Path $stock 'node-shasums.txt') | Where-Object { $_ -match ' node-v26.8.2-win-x64.zip$' }
if (-not $line -or ($line -split ' ')[0] -ne (Get-FileHash (Join-Path $stock 'node.zip') -Algorithm SHA256).Hash.ToLower()) { throw 'Node distribution hash mismatch' }
& tar.exe -xf (Join-Path $stock 'node.zip') -C $stock
if ($LASTEXITCODE -ne 0) { throw 'Short-path Node extraction failed' }
$env:PATH=(Join-Path $stock 'node-v26.8.2-win-x64')+';'+$env:PATH
Set-Location $stock
$ErrorActionPreference='Continue'
& npm.cmd install --prefix package --ignore-scripts --no-audit --no-fund openclaw@2026.9.8 *> (Join-Path $out 'stock-install.log')
$installExit=$LASTEXITCODE
$ErrorActionPreference='Stop'
if ($installExit -ne 0) { throw 'Stock local install failed' }
$cli=Join-Path $stock 'package/node_modules/openclaw/openclaw.mjs'
$env:NODE_NO_WARNINGS='1'
$ErrorActionPreference='Continue'
& node $cli --version *> (Join-Path $out 'stock-version.log')
if ($LASTEXITCODE -ne 0) { throw 'Stock CLI version failed' }
& node $cli --help *> (Join-Path $out 'stock-help.log')
if ($LASTEXITCODE -ne 0) { throw 'Stock general help failed' }
& node $cli setup --help *> (Join-Path $out 'stock-setup-help.log')
if ($LASTEXITCODE -ne 0) { throw 'Stock setup help failed' }
$ErrorActionPreference='Stop'
if ($before -ne (Get-FileHash $env:OPENCLAW_CONFIG_PATH).Hash) { throw 'Help altered isolated config' }
$workspace=Join-Path $stock 'workspace'
$ErrorActionPreference='Continue'
& node $cli setup --baseline --workspace $workspace *> (Join-Path $out 'stock-bootstrap.log')
if ($LASTEXITCODE -ne 0) { throw 'Stock baseline bootstrap failed' }
$ErrorActionPreference='Stop'
$config=Get-Content $env:OPENCLAW_CONFIG_PATH -Raw | ConvertFrom-Json
if ($config.channels -and @($config.channels.PSObject.Properties).Count -gt 0) { throw 'Fixture unexpectedly configured channels' }
$agentFile=Join-Path $workspace 'AGENTS.md'
if (-not (Test-Path $agentFile)) { throw 'No real stock AGENTS bootstrap' }
$identityHashes=@{};foreach($name in @('SOUL.md','IDENTITY.md','USER.md')){ $file=Join-Path $workspace $name;if(Test-Path $file){$identityHashes[$name]=(Get-FileHash $file).Hash} }
Copy-Item (Join-Path $root 'onboarding/OWNER-INSTRUCTIONS.md') (Join-Path $workspace 'OWNER-INSTRUCTIONS.md')
Add-Content $agentFile '
Synthetic owner-reviewed MCC fixture: read OWNER-INSTRUCTIONS.md. No execution or reviewer authority inferred from this instruction.'
foreach($name in $identityHashes.Keys){if($identityHashes[$name] -ne (Get-FileHash (Join-Path $workspace $name)).Hash){throw 'Persona template changed during adoption'}}
@{version='2026.9.8';node='26.8.2';channelConfigured=$false;modelInvoked=$false;bootstrapFiles=@(Get-ChildItem $workspace -File | ForEach-Object {$_.Name});configSha256=(Get-FileHash $env:OPENCLAW_CONFIG_PATH).Hash;adoptedInstructionSha256=(Get-FileHash (Join-Path $workspace 'OWNER-INSTRUCTIONS.md')).Hash;personaUnchanged=$true} | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $out 'stock-bootstrap-manifest.json')
'Genuine isolated stock baseline/bootstrap and instruction-file adoption mechanics only; no model/channel/adherence proof' | Set-Content (Join-Path $out 'stock-scope.txt')
Set-Location $root
$ErrorActionPreference='Continue'
& node jobs/browser.mjs $stock $root ((& wsl.exe -e wslpath -a $root).Trim()) *> (Join-Path $out 'browser.log')
$browserExit=$LASTEXITCODE
$ErrorActionPreference='Stop'
if ($browserExit -ne 0) { throw 'Browser proof failed; see sanitized stage result' }
