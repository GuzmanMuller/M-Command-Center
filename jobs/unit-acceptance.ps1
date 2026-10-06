$ErrorActionPreference='Stop'
if (-not (Test-Path artifacts/result/UNIT-PASS)) { throw 'No fresh unit pass' }
Get-FileHash artifacts/result/tests.log -Algorithm SHA256
