"""Put the Vedic Astro icon on the Desktop and in the Start Menu.

Creates ordinary Windows .lnk shortcuts pointing at the built
dist/VedicAstro/VedicAstro.exe, so the app launches the way any other
installed application does - double-click the icon, the window opens.

Nothing is written outside the current user's own Desktop and Start Menu
folders, and re-running simply overwrites the two shortcuts.

Usage:
    python scripts/install_shortcuts.py
    python scripts/install_shortcuts.py --remove
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_EXE = _ROOT / "dist" / "VedicAstro" / "VedicAstro.exe"
_SHORTCUT_NAME = "Vedic Astro.lnk"


def _desktop_dir() -> Path:
    """Windows' real Desktop, which is NOT always ~/Desktop.

    With OneDrive's "back up my Desktop" enabled - the default on many
    machines - the actual Desktop is ~/OneDrive/Desktop, while a stale empty
    ~/Desktop usually still exists. Writing to the latter puts the icon
    somewhere the user never sees, so ask Windows instead of guessing."""
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "[Environment]::GetFolderPath('Desktop')",
        ],
        capture_output=True,
        text=True,
    )
    resolved = result.stdout.strip()
    return Path(resolved) if resolved else Path(os.path.expanduser("~")) / "Desktop"


def _shortcut_locations() -> list[Path]:
    start_menu = (
        Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    )
    return [_desktop_dir() / _SHORTCUT_NAME, start_menu / _SHORTCUT_NAME]


def _create(target: Path, shortcut: Path) -> None:
    """Windows has no shortcut API in the stdlib, so this goes through the
    WScript.Shell COM object via PowerShell - no extra dependency needed."""
    script = f"""
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut('{shortcut}')
$link.TargetPath = '{target}'
$link.WorkingDirectory = '{target.parent}'
$link.IconLocation = '{target},0'
$link.Description = 'Vedic Astro - offline Vedic astrology chart engine'
$link.Save()
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"could not create {shortcut}: {result.stderr.strip()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remove", action="store_true", help="delete the shortcuts instead")
    args = parser.parse_args()

    if sys.platform != "win32":
        raise SystemExit("this installer is Windows-only")

    if args.remove:
        for shortcut in _shortcut_locations():
            if shortcut.exists():
                shortcut.unlink()
                print(f"removed {shortcut}")
            else:
                print(f"not present: {shortcut}")
        return 0

    if not _EXE.exists():
        raise SystemExit(f"{_EXE} not found - run scripts/build_desktop_app.py first")

    for shortcut in _shortcut_locations():
        shortcut.parent.mkdir(parents=True, exist_ok=True)
        _create(_EXE, shortcut)
        print(f"created {shortcut}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
