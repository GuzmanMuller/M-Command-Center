$ErrorActionPreference='Stop'
& wsl.exe -e python3 --version
if ($LASTEXITCODE -ne 0) { throw 'POSIX Python required' }
