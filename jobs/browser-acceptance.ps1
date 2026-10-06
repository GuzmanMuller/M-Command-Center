$ErrorActionPreference='Stop'
$p=Get-Content artifacts/result/browser-proof.json -Raw | ConvertFrom-Json
if($p.elapsedMs -gt 5000 -or -not $p.logoutRevoked -or -not $p.crashStaleObserved -or -not $p.corruptionStaleObserved){throw 'Browser criteria failed'}
Get-FileHash artifacts/result/browser-proof.json
