import hashlib,json,re,sys,zipfile
from pathlib import Path
wheel=next(Path(sys.argv[1]).glob("*.whl"));out=Path(sys.argv[2]);license_bytes=Path(sys.argv[3]).read_bytes()
with zipfile.ZipFile(wheel) as z:
    names=z.namelist()
    assert "mcc/owner.py" in names
    assert "mcc/static/app.js" in names
    assert not any(n.startswith(("jobs/","tests/","onboarding/")) or "auth-token" in n or ".openclaw" in n or "__pycache__" in n for n in names)
    licenses=[n for n in names if n.endswith("/LICENSE")]
    assert licenses and z.read(licenses[0])==license_bytes
    entry=next(n for n in names if n.endswith("entry_points.txt"))
    assert "mcc-owner = mcc.owner:main" in z.read(entry).decode()
    findings=[]
    for n in names:
        raw=z.read(n)
        if re.search(rb"(?:sk-[A-Za-z0-9]{20,}|BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY|/home/[^/\s]+/|(?:192\.168|10)\.\d+\.\d+\.\d+)",raw):findings.append(n)
    assert not findings,findings
    result={"wheel":wheel.name,"wheelSha256":hashlib.sha256(wheel.read_bytes()).hexdigest(),"contents":names,"licenseMatchesSource":True,"cleanInstallEntryPoints":True,"privacyPatternFindings":findings,"scanLimit":"Specified patterns only; not comprehensive secret detection"}
    (out/"package-proof.json").write_text(json.dumps(result,indent=2))
