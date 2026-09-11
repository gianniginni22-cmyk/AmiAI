$ErrorActionPreference = "Stop"

# ============================================================
# Amigurumi AI - E2E AUTO-UPDATE TEST
# 0.6.2.2 (patched bootstrap) -> 0.6.2.3
#
# Run from the ROOT of the patched 0.6.2.2 source folder.
# The script intentionally STOPS instead of downgrading an
# already-installed 0.6.2.3, to avoid destructive surprises.
# ============================================================

$ManifestUrl = "https://raw.githubusercontent.com/gianniginni22-cmyk/AmigurumiAI/refs/heads/main/update-manifest.json"
$ExpectedLatest = "0.6.2.3"
$ExpectedInstallerSha256 = "16F208643AB49CC9297B01E1FD7564E54589BF8C4BA64BFF136A47A711DB57DC"
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\Amigurumi AI"
$InstalledExe = Join-Path $InstallDir "AmigurumiAI.exe"
$UpdaterExe = Join-Path $InstallDir "AmigurumiAI-Updater.exe"
$BuildScript = Join-Path $PSScriptRoot "packaging\build_windows.ps1"

function Get-InstalledAmigurumi {
    $roots = @(
        "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall",
        "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall",
        "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    )

    foreach ($root in $roots) {
        if (Test-Path $root) {
            Get-ChildItem $root -ErrorAction SilentlyContinue | ForEach-Object {
                try {
                    $p = Get-ItemProperty $_.PSPath -ErrorAction Stop
                    if ($p.DisplayName -eq "Amigurumi AI") {
                        return [pscustomobject]@{
                            Key             = $_.PSPath
                            DisplayName     = $p.DisplayName
                            DisplayVersion  = [string]$p.DisplayVersion
                            InstallLocation = [string]$p.InstallLocation
                            UninstallString = [string]$p.UninstallString
                        }
                    }
                } catch {}
            }
        }
    }
}

function Wait-Until {
    param(
        [scriptblock]$Condition,
        [int]$TimeoutSeconds = 60,
        [int]$IntervalMilliseconds = 500,
        [string]$Description = "condizione"
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (& $Condition) { return $true }
        Start-Sleep -Milliseconds $IntervalMilliseconds
    }

    Write-Warning "Timeout: $Description"
    return $false
}

Write-Host ""
Write-Host "=== Amigurumi AI - TEST AUTO-UPDATE 0.6.2.2 -> 0.6.2.3 ===" -ForegroundColor Cyan
Write-Host ""

# 1) Source check
if (-not (Test-Path $BuildScript)) {
    throw "Non trovo $BuildScript. Esegui questo script dalla root del sorgente 0.6.2.2 patched."
}

Write-Host "[1/7] Verifico il manifest pubblico..." -ForegroundColor Yellow
$manifest = Invoke-RestMethod -Uri $ManifestUrl -TimeoutSec 15
if ([string]$manifest.version -ne $ExpectedLatest) {
    throw "Manifest inatteso: versione = '$($manifest.version)', attesa '$ExpectedLatest'."
}
if ([string]$manifest.sha256 -ne $ExpectedInstallerSha256) {
    throw "Manifest inatteso: SHA256 = '$($manifest.sha256)', attesa '$ExpectedInstallerSha256'."
}
if (-not ([string]$manifest.installer_url).StartsWith("https://")) {
    throw "installer_url non HTTPS."
}
Write-Host "  OK: manifest -> $($manifest.version)" -ForegroundColor Green
Write-Host "  SHA256 installer -> $($manifest.sha256)" -ForegroundColor DarkGray

# 2) Existing installation safety check
Write-Host ""
Write-Host "[2/7] Controllo l'installazione corrente..." -ForegroundColor Yellow
$installed = Get-InstalledAmigurumi
if ($installed) {
    Write-Host "  Versione installata: $($installed.DisplayVersion)"
    Write-Host "  Percorso: $($installed.InstallLocation)"
    if ($installed.DisplayVersion -eq "0.6.2.3") {
        throw "0.6.2.3 e gia installato. Per evitare un downgrade automatico, interrompo qui."
    }
}

# 3) Build patched 0.6.2.2
Write-Host ""
Write-Host "[3/7] Build del bootstrap 0.6.2.2..." -ForegroundColor Yellow
$env:AMIGURUMI_UPDATE_MANIFEST = $ManifestUrl

& $BuildScript

$BuiltExe = Join-Path $PSScriptRoot "dist\AmigurumiAI.exe"
$BuiltUpdater = Join-Path $PSScriptRoot "dist\AmigurumiAI-Updater.exe"
$BuiltInstaller = Join-Path $PSScriptRoot "dist\installer\AmigurumiAI-Setup-0.6.2.2.exe"

if (-not (Test-Path $BuiltExe)) { throw "Manca dist\AmigurumiAI.exe" }
if (-not (Test-Path $BuiltUpdater)) { throw "Manca dist\AmigurumiAI-Updater.exe" }
if (-not (Test-Path $BuiltInstaller)) { throw "Manca installer 0.6.2.2: $BuiltInstaller" }

Write-Host "  EXE OK:      $((Get-Item $BuiltExe).Length) bytes" -ForegroundColor Green
Write-Host "  Updater OK:  $((Get-Item $BuiltUpdater).Length) bytes" -ForegroundColor Green
Write-Host "  Installer OK:$((Get-Item $BuiltInstaller).Length) bytes" -ForegroundColor Green

# 4) Install 0.6.2.2 silently (does not auto-launch because [Run] has skipifsilent)
# Force-refresh the updater so an older 0.6.2.2 installation cannot leave a stale EXE.
Write-Host ""
Write-Host "[4/7] Preparo l'installazione pulita del bootstrap 0.6.2.2..." -ForegroundColor Yellow
if (Test-Path $UpdaterExe) {
    Write-Host "  Rimuovo updater precedente: $UpdaterExe" -ForegroundColor DarkGray
    Remove-Item $UpdaterExe -Force -ErrorAction Stop
}

Start-Process -FilePath $BuiltInstaller `
    -ArgumentList "/VERYSILENT","/SUPPRESSMSGBOXES","/NORESTART" `
    -Wait

$ok22 = Wait-Until -TimeoutSeconds 30 -Description "installazione 0.6.2.2" -Condition {
    $x = Get-InstalledAmigurumi
    return ($x -and $x.DisplayVersion -eq "0.6.2.2" -and (Test-Path $InstalledExe))
}
if (-not $ok22) {
    $x = Get-InstalledAmigurumi
    throw "Non riesco a confermare l'installazione 0.6.2.2. Versione rilevata: $($x.DisplayVersion)"
}

$x = Get-InstalledAmigurumi
Write-Host "  OK: installato $($x.DisplayVersion) in $InstallDir" -ForegroundColor Green

# Verify that the installer actually deployed the freshly-built updater.
if (-not (Test-Path $UpdaterExe)) {
    throw "Installer 0.6.2.2 non ha installato AmigurumiAI-Updater.exe: $UpdaterExe"
}
$builtUpdaterHash = (Get-FileHash $BuiltUpdater -Algorithm SHA256).Hash.ToUpperInvariant()
$installedUpdaterHash = (Get-FileHash $UpdaterExe -Algorithm SHA256).Hash.ToUpperInvariant()
Write-Host "  Updater build SHA256:     $builtUpdaterHash" -ForegroundColor DarkGray
Write-Host "  Updater installato SHA256:$installedUpdaterHash" -ForegroundColor DarkGray
if ($builtUpdaterHash -ne $installedUpdaterHash) {
    throw "Updater installato diverso da quello appena compilato. Build=$builtUpdaterHash Installed=$installedUpdaterHash"
}
Write-Host "  Updater diagnostico OK." -ForegroundColor Green

# 5) Start installed 0.6.2.2 - this is the real bootstrap path
Write-Host ""
Write-Host "[5/7] Avvio l'EXE installato 0.6.2.2..." -ForegroundColor Yellow
if (-not (Test-Path $UpdaterExe)) {
    throw "Updater non presente nell'installazione: $UpdaterExe"
}

# Remove stale temp update files from previous tests.
Get-ChildItem $env:TEMP -Filter "AmigurumiAI-update-*.exe" -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

Start-Process -FilePath $InstalledExe

# 6) Observe updater download
Write-Host ""
Write-Host "[6/7] Attendo il download/verifica SHA dell'updater..." -ForegroundColor Yellow
$downloaded = Wait-Until -TimeoutSeconds 90 -IntervalMilliseconds 1000 `
    -Description "AmigurumiAI-update-*.exe in TEMP" -Condition {
        $files = Get-ChildItem $env:TEMP -Filter "AmigurumiAI-update-*.exe" -ErrorAction SilentlyContinue |
            Where-Object { $_.Length -gt 1000000 } |
            Sort-Object LastWriteTime -Descending
        return ($null -ne $files -and $files.Count -gt 0)
    }

if ($downloaded) {
    $tempInstaller = Get-ChildItem $env:TEMP -Filter "AmigurumiAI-update-*.exe" -ErrorAction SilentlyContinue |
        Where-Object { $_.Length -gt 1000000 } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    Write-Host "  DOWNLOAD OK: $($tempInstaller.FullName)" -ForegroundColor Green
    Write-Host "  Dimensione:   $($tempInstaller.Length) bytes" -ForegroundColor DarkGray

    $actualSha = (Get-FileHash $tempInstaller.FullName -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($actualSha -ne $ExpectedInstallerSha256) {
        throw "SHA256 del file scaricato NON CORRISPONDE: $actualSha"
    }
    Write-Host "  SHA256 OK:    $actualSha" -ForegroundColor Green
} else {
    $logPath = Join-Path $env:TEMP "AmigurumiAI-updater.log"
    if (Test-Path $logPath) {
        Write-Host "  LOG UPDATER:" -ForegroundColor DarkYellow
        Get-Content $logPath -Tail 40 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
    } else {
        Write-Host "  Nessun log updater trovato in $logPath" -ForegroundColor DarkYellow
    }
    throw "L'updater non ha lasciato un file temporaneo verificabile entro 90 secondi."
}

# 7) Final verification: installed version must become 0.6.2.3
Write-Host ""
Write-Host "[7/7] Attendo l'installazione automatica di 0.6.2.3..." -ForegroundColor Yellow
$ok23 = Wait-Until -TimeoutSeconds 120 -IntervalMilliseconds 1000 `
    -Description "versione installata 0.6.2.3" -Condition {
        $x = Get-InstalledAmigurumi
        return ($x -and $x.DisplayVersion -eq "0.6.2.3" -and (Test-Path $InstalledExe))
    }

if (-not $ok23) {
    $x = Get-InstalledAmigurumi
    throw "AUTO-UPDATE NON CONFERMATO. Versione finale rilevata: $($x.DisplayVersion)"
}

$final = Get-InstalledAmigurumi
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  TEST AUTO-UPDATE SUPERATO" -ForegroundColor Green
Write-Host "  Da:       0.6.2.2" -ForegroundColor Green
Write-Host "  A:        $($final.DisplayVersion)" -ForegroundColor Green
Write-Host "  Percorso: $InstallDir" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

# Show final process state if it is still running.
Get-Process AmigurumiAI -ErrorAction SilentlyContinue |
    Select-Object Id, Path |
    Format-Table -AutoSize

Write-Host "TEST COMPLETATO. Verifica Amigurumi AI, poi chiudi questa finestra." -ForegroundColor Cyan
