# Amigurumi AI v0.7.2 — Release Checklist

## Automated/source checks
- [x] Core benchmark remains closed
- [x] UI `[object Object]` rendering bug fixed
- [x] Compiled `parts` contract normalized to displayable strings
- [x] Empty Pattern/Assembly states made explicit
- [x] 36/36 automated tests passing
- [x] JavaScript syntax check passing
- [x] Version aligned 0.7.2

## Required Windows validation
- [ ] Build with `packaging/build_windows.ps1`
- [ ] Confirm `dist/AmigurumiAI.exe`
- [ ] Confirm `dist/AmigurumiAI-Updater.exe`
- [ ] Confirm `dist/installer/AmigurumiAI-Setup-0.7.2.exe`
- [ ] Install/update on Windows
- [ ] Launch application
- [ ] Run real image/text generation
- [ ] Confirm parts render as readable labels (no `[object Object]`)
- [ ] Confirm Pattern tab contains generated instructions
- [ ] Confirm Assemblaggio tab contains instructions
- [ ] Confirm core pipeline returns PASS/REVIEW as expected

## Release gate
The product is not marked distributable until the new Windows UI verification passes.
