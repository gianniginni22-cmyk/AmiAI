$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m pip install --upgrade pip
python -m pip install -r requirements-desktop.txt
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
if (Test-Path build) { Remove-Item build -Recurse -Force }
python -m PyInstaller packaging/AmigurumiAI.spec --clean
if (-not (Test-Path dist\AmigurumiAI.exe)) { throw "PyInstaller non ha creato dist/AmigurumiAI.exe" }
Write-Host "Exe creato in dist/AmigurumiAI.exe"
$ISCC = Get-Command iscc.exe -ErrorAction SilentlyContinue
if (-not $ISCC) {
  $candidates = @(
    "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe"
  )
  foreach ($candidate in $candidates) {
    if (Test-Path $candidate) { $ISCC = @{ Source = $candidate }; break }
  }
}
if ($ISCC) {
  Write-Host "Inno Setup trovato: $($ISCC.Source)"
  & $ISCC.Source /Q packaging/AmigurumiAI.iss
  if ($LASTEXITCODE -ne 0) { throw "Inno Setup ha restituito il codice $LASTEXITCODE" }
  if (-not (Test-Path dist\installer\AmigurumiAI-Setup-0.7.3.exe)) { throw "Inno Setup non ha creato il Setup 0.7.3" }
  Write-Host "Installer creato in dist/installer/AmigurumiAI-Setup-0.7.3.exe"
} else {
  throw "Inno Setup 7 non trovato. Installa Inno Setup e rilancia questo script."
}
