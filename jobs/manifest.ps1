function SourceInventory {
  return @(Get-ChildItem -Force -File -Recurse | Where-Object { $relative=$_.FullName.Substring((Get-Location).Path.Length+1).Replace('\','/'); -not ($relative.StartsWith('.git/') -or $relative.StartsWith('artifacts/') -or $relative.StartsWith('.missy-') -or $relative -eq 'INPUT_SHA256SUMS' -or $relative -eq 'run.json') } | ForEach-Object { $_.FullName.Substring((Get-Location).Path.Length+1).Replace('\','/') } | Sort-Object)
}
function EvidenceInventory {
  return @(Get-ChildItem artifacts/result -File | Where-Object { $_.Name -ne 'PASS' } | ForEach-Object { 'artifacts/result/'+$_.Name } | Sort-Object)
}
function RequiredEvidence {
  foreach ($name in @('tests.log','UNIT-PASS','source.sha256','toolchain.txt','package-proof.json','package-build.log','package-install.log','package-owner-help.log','package-viewer-help.log','package-bridge-help.log','stock-version.log','stock-help.log','stock-setup-help.log','stock-bootstrap.log','stock-bootstrap-manifest.json','stock-scope.txt','browser-proof.json','browser-authenticated.png','browser.log')) {
    if (-not (Test-Path ('artifacts/result/'+$name))) { throw ('Missing required gate artifact: '+$name) }
  }
  $wheels=@(Get-ChildItem artifacts/result/*.whl);if($wheels.Count -ne 1){throw 'Exactly one wheel required'}
  if(Test-Path artifacts/result/browser-ready.json){throw 'Credential rendezvous must not be collected'}
  if(Test-Path artifacts/result/browser-failure.json){throw 'Failed browser proof cannot pass'}
}
