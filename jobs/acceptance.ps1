$ErrorActionPreference='Stop'
. ./jobs/manifest.ps1
RequiredEvidence
$receipt=Get-Content artifacts/result/PASS -Raw | ConvertFrom-Json
if ($receipt.schemaVersion -ne 1 -or $receipt.exitCode -ne 0 -or $receipt.run -ne (Split-Path (Get-Location).Path -Leaf)) { throw 'Wrong workload receipt' }
if(@(Compare-Object @($receipt.source.PSObject.Properties.Name | Sort-Object) (SourceInventory)).Count -ne 0){throw 'Source receipt membership incomplete'}
if(@(Compare-Object @($receipt.evidence.PSObject.Properties.Name | Sort-Object) (EvidenceInventory)).Count -ne 0){throw 'Evidence receipt membership incomplete'}
foreach ($p in $receipt.source.PSObject.Properties) { if ($p.Value -ne (Get-FileHash $p.Name -Algorithm SHA256).Hash) { throw 'Source hash mismatch' } }
foreach ($p in $receipt.evidence.PSObject.Properties) { if ($p.Value -ne (Get-FileHash $p.Name -Algorithm SHA256).Hash) { throw 'Evidence hash mismatch' } }
