@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ROOT=%CD%"
set "PS1=%ROOT%\packaging\build_windows.ps1"

echo ===============================================
echo   Amigurumi AI - Creazione Setup 0.7.2
echo ===============================================
echo.
echo Cartella progetto: %ROOT%
echo.

if not exist "%PS1%" (
  echo ERRORE: struttura pacchetto non corretta.
  echo File mancante: %PS1%
  echo.
  echo IMPORTANTE: estrai completamente lo ZIP prima di avviare questo file.
  pause
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
if errorlevel 1 (
  echo.
  echo ERRORE: compilazione fallita.
  pause
  exit /b 1
)

if exist "%ROOT%\dist\installer\AmigurumiAI-Setup-0.7.2.exe" (
  echo.
  echo ===============================================
  echo   INSTALLER 0.7.2 CREATO CON SUCCESSO
  echo ===============================================
  echo.
  echo Percorso:
  echo %ROOT%\dist\installer\AmigurumiAI-Setup-0.7.2.exe
  echo.
  start "" explorer.exe "%ROOT%\dist\installer"
  exit /b 0
)

echo.
echo ERRORE: il Setup 0.7.2 non e' stato creato.
echo Controlla l'errore mostrato sopra.
pause
exit /b 1
