# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['reference_manager_qt.py'],
    pathex=['D:\\anaconda\\Library\\bin'],
    binaries=[('D:\\anaconda\\Library\\bin\\sqlite3.dll', '.'), ('D:\\anaconda\\Library\\bin\\libcrypto-3-x64.dll', '.'), ('D:\\anaconda\\Library\\bin\\libssl-3-x64.dll', '.'), ('D:\\anaconda\\Library\\bin\\libmpdec-4.dll', '.'), ('D:\\anaconda\\Library\\bin\\liblzma.dll', '.'), ('D:\\anaconda\\Library\\bin\\libbz2.dll', '.'), ('D:\\anaconda\\Library\\bin\\zlib.dll', '.'), ('D:\\anaconda\\Library\\bin\\Qt5Core_conda.dll', '.'), ('D:\\anaconda\\Library\\bin\\Qt5Gui_conda.dll', '.'), ('D:\\anaconda\\Library\\bin\\Qt5Widgets_conda.dll', '.'), ('D:\\anaconda\\Library\\bin\\Qt5PrintSupport_conda.dll', '.'), ('D:\\anaconda\\Library\\bin\\Qt5Svg_conda.dll', '.'), ('D:\\anaconda\\Library\\bin\\Qt5DBus_conda.dll', '.'), ('D:\\anaconda\\Library\\bin\\libpng16.dll', '.'), ('D:\\anaconda\\Library\\bin\\libjpeg.dll', '.'), ('D:\\anaconda\\Library\\bin\\freetype.dll', '.'), ('D:\\anaconda\\Library\\bin\\icuuc73.dll', '.'), ('D:\\anaconda\\Library\\bin\\icuin73.dll', '.'), ('D:\\anaconda\\Library\\bin\\icudt73.dll', '.'), ('D:\\anaconda\\Library\\bin\\zstd.dll', '.'), ('D:\\anaconda\\Library\\bin\\libzstd.dll', '.'), ('D:\\anaconda\\Library\\bin\\pcre2-8.dll', '.'), ('D:\\anaconda\\Library\\bin\\brotlicommon.dll', '.'), ('D:\\anaconda\\Library\\bin\\brotlidec.dll', '.'), ('D:\\anaconda\\Library\\bin\\brotlienc.dll', '.'), ('D:\\anaconda\\Library\\bin\\ffi.dll', '.'), ('D:\\anaconda\\Library\\bin\\ffi-8.dll', '.')],
    datas=[('app_icon.ico', '.')],
    hiddenimports=['pythoncom', 'pywintypes', 'win32gui', 'win32con', 'win32com.shell.shell', 'win32com.shell.shellcon'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6', 'PySide6_Addons', 'PySide6_Essentials', 'shiboken6', 'cryptography', 'numpy', 'PIL', 'lxml', 'yaml'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ReferenceManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon=['app_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ReferenceManager',
)
