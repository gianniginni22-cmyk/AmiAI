from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
ROOT = Path(SPECPATH).parent
hiddenimports = collect_submodules('cv2') + collect_submodules('numpy') + ['webview.platforms.winforms','webview.platforms.cef','webview.platforms.qt','webview.platforms.gtk']
datas=[(str(ROOT/'app'/'static'),'app/static')]+collect_data_files('cv2', include_py_files=False)
a=Analysis([str(ROOT/'desktop.py')], pathex=[str(ROOT)], binaries=[], datas=datas, hiddenimports=hiddenimports, hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='AmigurumiAI',debug=False,bootloader_ignore_signals=False,strip=False,upx=True,console=False,icon=str(ROOT/'packaging'/'icon.ico') if (ROOT/'packaging'/'icon.ico').exists() else None)
# Separate updater executable.
b=Analysis([str(ROOT/'app'/'updater.py')], pathex=[str(ROOT)], binaries=[], datas=[], hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz2=PYZ(b.pure)
updater=EXE(pyz2,b.scripts,b.binaries,b.datas,[],name='AmigurumiAI-Updater',debug=False,bootloader_ignore_signals=False,strip=False,upx=True,console=False)
