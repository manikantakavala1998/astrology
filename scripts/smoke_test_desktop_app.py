"""Smoke-test the PACKAGED desktop app, not the dev environment.

A PyInstaller build can succeed and still be broken at runtime, because the
failures that matter here are missing *data* files rather than missing code:

  - pyswisseph is a compiled extension; if it did not bundle, every chart dies.
  - geonamescache / reverse_geocoder / timezonefinder each ship their own data
    files that PyInstaller cannot infer from imports, and without them
    place-of-birth search fails while everything else looks fine.

So this launches the real VedicAstro.exe and drives it over HTTP exactly as
the window does, asserting a chart actually computes end to end.

Usage:
    python scripts/smoke_test_desktop_app.py
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_EXE = _ROOT / "dist" / "VedicAstro" / "VedicAstro.exe"

# Must match desktop.py's mutex port - the app refuses to start a second
# instance, so a leftover window would make this test fail confusingly.
_SINGLE_INSTANCE_PORT = 49731
_STARTUP_TIMEOUT = 90.0

_BIRTH = {
    "birth_date": "1990-06-15",
    "birth_hour": "8",
    "birth_minute": "30",
    "birth_meridiem": "AM",
    "place_name": "Chennai, India",
    "ayanamsha": "lahiri",
    "node_type": "mean",
}


def _instance_already_running() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", _SINGLE_INSTANCE_PORT))
        except OSError:
            return True
    return False


def _find_app_port(pid: int, deadline: float) -> int | None:
    """The app picks its HTTP port at runtime, so it has to be discovered.

    Discovery is restricted to sockets owned by the process we launched. An
    earlier version probed every loopback port and trusted any page that
    looked like this app - which silently tested a leftover uvicorn dev
    server on port 8000 instead of the bundle, reporting all checks green
    while proving nothing about the packaged app. Matching on the PID means a
    dev server can be running and the test still measures the real .exe.
    """
    while time.monotonic() < deadline:
        for port in _candidate_ports(pid):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1) as response:
                    if "astro-root" in response.read(4000).decode("utf-8", "ignore"):
                        return port
            except (urllib.error.URLError, OSError, TimeoutError):
                continue
        time.sleep(1.0)
    return None


def _candidate_ports(pid: int) -> list[int]:
    """Loopback ports listened on by `pid` itself or one of its children."""
    owned = {pid} | _child_pids(pid)
    output = subprocess.run(
        ["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, shell=True
    ).stdout
    ports = set()
    for line in output.splitlines():
        fields = line.split()
        if "LISTENING" not in fields or len(fields) < 5:
            continue
        local, owner = fields[1], fields[-1]
        if not local.startswith("127.0.0.1:") or not owner.isdigit():
            continue
        if int(owner) not in owned:
            continue
        port = local.rsplit(":", 1)[-1]
        if port.isdigit() and int(port) != _SINGLE_INSTANCE_PORT:
            ports.add(int(port))
    return sorted(ports)


def _child_pids(pid: int) -> set[int]:
    """Direct children of `pid`, in case the bootloader re-execs the app."""
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"(Get-CimInstance Win32_Process -Filter 'ParentProcessId={pid}')"
            ".ProcessId -join ','",
        ],
        capture_output=True,
        text=True,
    )
    return {int(part) for part in result.stdout.strip().split(",") if part.strip().isdigit()}


def _check(label: str, condition: bool, detail: str = "") -> bool:
    print(f"  [{'PASS' if condition else 'FAIL'}] {label}{(' - ' + detail) if detail else ''}")
    return condition


def main() -> int:
    if not _EXE.exists():
        raise SystemExit(f"{_EXE} not found - run scripts/build_desktop_app.py first")
    if _instance_already_running():
        raise SystemExit("Vedic Astro is already running - close it before smoke testing")

    print(f"Launching {_EXE} ...")
    process = subprocess.Popen([str(_EXE)])
    try:
        port = _find_app_port(process.pid, time.monotonic() + _STARTUP_TIMEOUT)
        if port is None:
            raise SystemExit(f"app did not serve its UI within {_STARTUP_TIMEOUT:.0f}s")
        print(f"App is serving on port {port} (pid {process.pid})\n")

        base = f"http://127.0.0.1:{port}"
        results = []

        with urllib.request.urlopen(f"{base}/", timeout=20) as response:
            home = response.read().decode("utf-8", "ignore")
        results.append(_check("home page loads", "astro-root" in home))
        results.append(_check("built React bundle referenced", "/static/ui/app.js" in home))

        with urllib.request.urlopen(f"{base}/static/ui/app.js", timeout=20) as response:
            js = response.read()
        results.append(_check("React bundle is served", len(js) > 100_000, f"{len(js) // 1024} KB"))

        # The real test: a full chart. This exercises pyswisseph (positions)
        # AND the geo stack (place -> coordinates -> timezone) together.
        request = urllib.request.Request(
            f"{base}/", data=urllib.parse.urlencode(_BIRTH).encode()
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            chart = response.read().decode("utf-8", "ignore")

        results.append(_check("place search resolved (geo data bundled)", "Chennai" in chart))
        results.append(_check("chart computed (pyswisseph bundled)", "Ascendant" in chart))
        # Note: there is deliberately no panel-bnn check. The backend still
        # computes `bnn` for every chart, but no template renders it - the
        # Bhrigu Nandi Nadi tab is absent from _workspace.html. That is a
        # property of the app's current UI, not of the packaging.
        for tab in ("panel-bcp", "panel-bsp", "panel-padma", "panel-laghu-parashari"):
            results.append(_check(f"{tab} rendered", f'id="{tab}"' in chart))

        print()
        if all(results):
            print(f"All {len(results)} checks passed - the packaged app works.")
            return 0
        print(f"{sum(1 for r in results if not r)} of {len(results)} checks FAILED.")
        return 1
    finally:
        # terminate() alone is not enough: the app opens its window by
        # spawning a separate msedge.exe child, which survives its parent and
        # would be left on screen showing a dead page. /T takes the tree.
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            shell=True,
        )
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
