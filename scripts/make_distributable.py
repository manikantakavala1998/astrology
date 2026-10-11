"""Package the built app for installing on another Windows PC.

Produces dist/VedicAstro-windows.zip containing the whole application folder
plus a self-contained installer script. The target machine needs nothing
preinstalled - no Python, no Node, no internet.

On the other PC the flow is:
    1. copy the .zip across and extract it anywhere
    2. double-click "Install Vedic Astro.bat" inside the extracted folder
    3. the app's icon appears on the Desktop and in the Start Menu

The installer .bat is written here rather than shipped as a static file
because it has to locate itself at runtime (%~dp0): the folder can be
extracted anywhere, so the shortcut target cannot be known in advance.

Usage:
    python scripts/make_distributable.py
"""

from __future__ import annotations

import zipfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_APP_DIR = _ROOT / "dist" / "VedicAstro"
_ZIP_PATH = _ROOT / "dist" / "VedicAstro-windows.zip"

_INSTALLER_NAME = "Install Vedic Astro.bat"
_UNINSTALLER_NAME = "Uninstall Vedic Astro.bat"

# %~dp0 is the folder this .bat lives in, with a trailing backslash - that is
# what lets the extracted folder sit anywhere on the target machine.
_INSTALLER_BAT = r"""@echo off
setlocal
set "APPDIR=%~dp0"
set "TARGET=%APPDIR%VedicAstro.exe"

if not exist "%TARGET%" (
  echo ERROR: VedicAstro.exe not found next to this script.
  echo Make sure you extracted the whole folder, not just this file.
  pause
  exit /b 1
)

echo Installing Vedic Astro shortcuts...
powershell -NoProfile -NonInteractive -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "foreach ($dir in @([Environment]::GetFolderPath('Desktop'), (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'))) {" ^
  "  $lnk = $ws.CreateShortcut((Join-Path $dir 'Vedic Astro.lnk'));" ^
  "  $lnk.TargetPath = '%TARGET%';" ^
  "  $lnk.WorkingDirectory = '%APPDIR%';" ^
  "  $lnk.IconLocation = '%TARGET%,0';" ^
  "  $lnk.Description = 'Vedic Astro - offline Vedic astrology chart engine';" ^
  "  $lnk.Save();" ^
  "  Write-Host ('  created ' + (Join-Path $dir 'Vedic Astro.lnk')) }"

echo.
echo Done. Look for the Vedic Astro icon on your Desktop.
echo Keep this folder where it is - deleting it will break the shortcut.
pause
"""

_UNINSTALLER_BAT = r"""@echo off
setlocal
echo Removing Vedic Astro shortcuts...
powershell -NoProfile -NonInteractive -Command ^
  "foreach ($dir in @([Environment]::GetFolderPath('Desktop'), (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'))) {" ^
  "  $lnk = Join-Path $dir 'Vedic Astro.lnk';" ^
  "  if (Test-Path $lnk) { Remove-Item $lnk; Write-Host ('  removed ' + $lnk) } }"
echo.
echo Shortcuts removed. Delete this folder to finish uninstalling.
pause
"""

_README = """Vedic Astro - offline Vedic astrology chart engine
==================================================

REQUIREMENTS
  Windows 10 or 11, 64-bit. Nothing else - no Python, no .NET, no
  internet connection. Every calculation runs locally on this machine.

  The app draws its window using Microsoft Edge, which is part of
  Windows 10 and 11, so there is nothing to install. If Edge has been
  removed from the PC the app still works - it opens in whichever
  browser is the default instead of in its own window.

INSTALL
  1. Extract this whole folder anywhere you like
     (for example C:\\Program Files\\VedicAstro or your Desktop).
  2. Double-click "Install Vedic Astro.bat".
  3. The Vedic Astro icon appears on your Desktop and in the Start Menu.

"WINDOWS PROTECTED YOUR PC" - THIS IS EXPECTED
  The first time you run it, Windows may show a blue box saying
  "Windows protected your PC" or "unrecognized app".

  That appears because the app is not code-signed (a signing certificate
  is a paid yearly subscription), NOT because anything is wrong with it.

  To continue: click "More info", then "Run anyway".

  Your antivirus may flag it for the same reason. Applications built
  this way - Python bundled into a single .exe - commonly trigger that
  false positive. If it gets quarantined, allow it in your antivirus.

FIRST LAUNCH
  The app takes a few seconds to open the first time while it loads its
  place-name database. Later launches are quicker.

  If nothing seems to happen, wait ten seconds before clicking again -
  the window only opens once the engine is ready.

IMPORTANT
  Keep this folder where you put it. The shortcut points at
  VedicAstro.exe inside it, so moving or deleting the folder breaks the
  icon. To move the app, move the folder and run the installer again.

IF SOMETHING GOES WRONG
  The app explains itself rather than failing silently. If it cannot
  start, or cannot open its own window, it shows a message box and
  writes the reason to:

    %LOCALAPPDATA%\VedicAstro\startup-error.log

  Send that file on and it will say exactly what happened.

  One message is normal rather than broken: "could not open its own
  window, so it opened in your web browser instead". The app is fully
  working in that case - it is only the window frame that it could not
  build, because it found no Microsoft Edge or Google Chrome installed.

UNINSTALL
  Run "Uninstall Vedic Astro.bat", then delete this folder.
"""


def main() -> int:
    if not (_APP_DIR / "VedicAstro.exe").exists():
        raise SystemExit(
            f"{_APP_DIR / 'VedicAstro.exe'} not found - run scripts/build_desktop_app.py first"
        )

    (_APP_DIR / _INSTALLER_NAME).write_text(_INSTALLER_BAT, encoding="utf-8")
    (_APP_DIR / _UNINSTALLER_NAME).write_text(_UNINSTALLER_BAT, encoding="utf-8")
    (_APP_DIR / "README.txt").write_text(_README, encoding="utf-8")

    files = sorted(path for path in _APP_DIR.rglob("*") if path.is_file())
    raw_bytes = sum(path.stat().st_size for path in files)

    print(f"Zipping {len(files)} files ({raw_bytes / 1024 / 1024:.0f} MB) ...")
    _ZIP_PATH.unlink(missing_ok=True)
    with zipfile.ZipFile(_ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            archive.write(path, Path("VedicAstro") / path.relative_to(_APP_DIR))

    zipped_mb = _ZIP_PATH.stat().st_size / 1024 / 1024
    print(f"\nWrote {_ZIP_PATH}  ({zipped_mb:.0f} MB zipped)")
    print("Copy that one file to the other PC, extract it, run the installer .bat inside.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
