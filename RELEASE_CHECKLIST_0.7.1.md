# Amigurumi AI v0.7.1 — Release Checklist

## Automated/source checks completed
- [x] Core benchmark closed
- [x] 35/35 automated tests passing
- [x] APP_VERSION = 0.7.1
- [x] Inno Setup version = 0.7.1
- [x] Per-user install (`{localappdata}`)
- [x] `PrivilegesRequired=lowest`
- [x] Separate updater executable configured
- [x] Installer output name = `AmigurumiAI-Setup-0.7.1.exe`

## Required Windows validation
- [ ] Build with `packaging/build_windows.ps1`
- [ ] Confirm `dist/AmigurumiAI.exe`
- [ ] Confirm `dist/AmigurumiAI-Updater.exe`
- [ ] Confirm `dist/installer/AmigurumiAI-Setup-0.7.1.exe`
- [ ] Install on a clean Windows user/environment
- [ ] Launch application from Start Menu
- [ ] Configure API key locally
- [ ] Run one real image/text generation
- [ ] Confirm core pipeline returns PASS/REVIEW as expected
- [ ] Confirm uninstall removes application cleanly
- [ ] Optional: perform real updater E2E test with HTTPS manifest

## Release gate
The product is **not marked distributable until the Windows checklist passes**. No further core feature work is required for the release gate.
