$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } else { 'python' }
if ($python -eq 'py') { py -3 -m venv .venv } else { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m unittest discover -s tests
if ($LASTEXITCODE -ne 0) { throw 'Die Kernprüfungen sind fehlgeschlagen.' }
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --icon icon.ico --name '8M-Foto-Karaoke' app.py
if ($LASTEXITCODE -ne 0) { throw 'Die portable Datei konnte nicht erstellt werden.' }
Write-Host 'Portable Datei: dist\8M-Foto-Karaoke.exe'
$iscc = @(
  "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($iscc) { & $iscc installer.iss; if ($LASTEXITCODE -ne 0) { throw 'Der Installer-Bau ist fehlgeschlagen.' }; Write-Host 'Installer: dist\8M-Foto-Karaoke-Setup.exe' }
else { Write-Host 'Für den Installer zusätzlich Inno Setup 6 installieren und installer.iss kompilieren.' }
