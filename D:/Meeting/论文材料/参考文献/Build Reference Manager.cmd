@echo off
setlocal
cd /d "%~dp0"
set "PATH=D:\anaconda\Library\bin;D:\anaconda;D:\anaconda\Scripts;%PATH%"

if not exist "_reference_manager_qt\papers" mkdir "_reference_manager_qt\papers"

"D:\anaconda\python.exe" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name ReferenceManager ^
  --icon "app_icon.ico" ^
  --version-file "version_info.txt" ^
  --paths "D:\anaconda\Library\bin" ^
  --add-data "app_icon.ico;." ^
  --add-binary "D:\anaconda\Library\bin\sqlite3.dll;." ^
  --add-binary "D:\anaconda\Library\bin\libcrypto-3-x64.dll;." ^
  --add-binary "D:\anaconda\Library\bin\libssl-3-x64.dll;." ^
  --add-binary "D:\anaconda\Library\bin\libmpdec-4.dll;." ^
  --add-binary "D:\anaconda\Library\bin\liblzma.dll;." ^
  --add-binary "D:\anaconda\Library\bin\libbz2.dll;." ^
  --add-binary "D:\anaconda\Library\bin\zlib.dll;." ^
  --add-binary "D:\anaconda\Library\bin\Qt5Core_conda.dll;." ^
  --add-binary "D:\anaconda\Library\bin\Qt5Gui_conda.dll;." ^
  --add-binary "D:\anaconda\Library\bin\Qt5Widgets_conda.dll;." ^
  --add-binary "D:\anaconda\Library\bin\Qt5PrintSupport_conda.dll;." ^
  --add-binary "D:\anaconda\Library\bin\Qt5Svg_conda.dll;." ^
  --add-binary "D:\anaconda\Library\bin\Qt5DBus_conda.dll;." ^
  --add-binary "D:\anaconda\Library\bin\libpng16.dll;." ^
  --add-binary "D:\anaconda\Library\bin\libjpeg.dll;." ^
  --add-binary "D:\anaconda\Library\bin\freetype.dll;." ^
  --add-binary "D:\anaconda\Library\bin\icuuc73.dll;." ^
  --add-binary "D:\anaconda\Library\bin\icuin73.dll;." ^
  --add-binary "D:\anaconda\Library\bin\icudt73.dll;." ^
  --add-binary "D:\anaconda\Library\bin\zstd.dll;." ^
  --add-binary "D:\anaconda\Library\bin\libzstd.dll;." ^
  --add-binary "D:\anaconda\Library\bin\pcre2-8.dll;." ^
  --add-binary "D:\anaconda\Library\bin\brotlicommon.dll;." ^
  --add-binary "D:\anaconda\Library\bin\brotlidec.dll;." ^
  --add-binary "D:\anaconda\Library\bin\brotlienc.dll;." ^
  --add-binary "D:\anaconda\Library\bin\ffi.dll;." ^
  --add-binary "D:\anaconda\Library\bin\ffi-8.dll;." ^
  --hidden-import pythoncom ^
  --hidden-import pywintypes ^
  --hidden-import win32gui ^
  --hidden-import win32con ^
  --hidden-import win32com.shell.shell ^
  --hidden-import win32com.shell.shellcon ^
  --exclude-module PySide6 ^
  --exclude-module PySide6_Addons ^
  --exclude-module PySide6_Essentials ^
  --exclude-module shiboken6 ^
  --exclude-module cryptography ^
  --exclude-module numpy ^
  --exclude-module PIL ^
  --exclude-module lxml ^
  --exclude-module yaml ^
  reference_manager_qt.py

if not exist "dist\ReferenceManager\_reference_manager_qt\papers" mkdir "dist\ReferenceManager\_reference_manager_qt\papers"

echo.
echo Build finished. Share this folder:
echo %~dp0dist\ReferenceManager
echo.
pause
