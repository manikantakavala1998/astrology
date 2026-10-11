"""Build the Vedic Astro desktop app end to end.

Runs the three steps in the order that matters:

    1. npm run build   - compile the React/Vite UI into web/static/ui
    2. build_app_icon  - regenerate the .ico the window and exe use
    3. pyinstaller     - bundle everything into dist/VedicAstro

Step 1 is part of the build on purpose. The Python bundle just copies whatever
is sitting in web/static/ui, so building the app without rebuilding the UI
first would silently ship a stale frontend - a bug that looks like the backend
is broken and wastes a lot of time to track down.

Usage:
    python scripts/build_desktop_app.py              # full build
    python scripts/build_desktop_app.py --skip-npm   # Python bundle only
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_FRONTEND = _ROOT / "frontend"
_BUILT_UI = _ROOT / "src" / "vedic_astro" / "web" / "static" / "ui"
_DIST = _ROOT / "dist" / "VedicAstro"


def _run(command: list[str], cwd: Path) -> None:
    printable = " ".join(command)
    print(f"\n==> {printable}   (in {cwd})", flush=True)
    # shell=True on Windows so npm/npx resolve through their .cmd shims.
    result = subprocess.run(command, cwd=cwd, shell=(sys.platform == "win32"))
    if result.returncode != 0:
        raise SystemExit(f"failed ({result.returncode}): {printable}")


def _build_frontend() -> None:
    if not (_FRONTEND / "node_modules").exists():
        _run(["npm", "install"], cwd=_FRONTEND)
    _run(["npm", "run", "build"], cwd=_FRONTEND)
    if not (_BUILT_UI / "app.js").exists():
        raise SystemExit(f"frontend build produced no app.js in {_BUILT_UI}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-npm", action="store_true", help="reuse the existing built UI")
    args = parser.parse_args()

    if args.skip_npm:
        if not (_BUILT_UI / "app.js").exists():
            raise SystemExit(f"--skip-npm given but no built UI exists at {_BUILT_UI}")
        print(f"==> skipping npm build, reusing {_BUILT_UI}")
    else:
        _build_frontend()

    _run([sys.executable, str(_ROOT / "scripts" / "build_app_icon.py")], cwd=_ROOT)

    if _DIST.exists():
        shutil.rmtree(_DIST)
    _run([sys.executable, "-m", "PyInstaller", "--noconfirm", "vedic_astro.spec"], cwd=_ROOT)

    executable = _DIST / "VedicAstro.exe"
    if not executable.exists():
        raise SystemExit(f"build finished but {executable} is missing")

    size_mb = sum(f.stat().st_size for f in _DIST.rglob("*") if f.is_file()) / (1024 * 1024)
    print(f"\nBuilt {executable}  ({size_mb:.0f} MB in {_DIST})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
