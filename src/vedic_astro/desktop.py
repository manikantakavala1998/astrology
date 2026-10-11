"""Desktop app entry point: the local FastAPI app in its own window.

This is what the packaged VedicAstro.exe runs. Nothing about the astrology
engine or the web UI changes - uvicorn is started in-process on a loopback
port and a chromeless browser window is pointed at it, so the app behaves
exactly as it does in a browser while launching like a normal desktop
application.

WHY NOT pywebview: pywebview's Windows backend goes through pythonnet, which
needs a .NET runtime on the machine. That is an invisible prerequisite - the
app ran fine on a developer machine with .NET Framework 4.8 installed and
died on a clean machine with "Failed to resolve
Python.Runtime.Loader.Initialize". Microsoft Edge ships with every supported
build of Windows 10 and 11, and its --app mode gives a window with no address
bar or tabs for free, so using it removes a whole class of "works here, not
there" failure instead of asking users to install .NET.

Three further details exist because of real failure modes rather than taste:

1. A free port is chosen at runtime instead of hardcoding 8000. A stale
   server left listening on a fixed port silently serves outdated code.
2. A single-instance lock. Double-clicking the icon twice would otherwise
   start a second server and a second window over the same data.
3. A dedicated browser profile directory. Without it, Edge hands the URL to
   an already-running Edge process and immediately exits, so the app would
   think its window had closed and shut the server down underneath it.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
import winreg
import webbrowser
from pathlib import Path

import uvicorn

from vedic_astro.web.app import app

WINDOW_SIZE = (1440, 920)

# An arbitrary high loopback port used purely as a mutex: holding it open for
# the life of the process is what makes "already running" detectable. It is
# never listened to for HTTP.
_SINGLE_INSTANCE_PORT = 49731
_SERVER_START_TIMEOUT = 30.0
# A browser that exits faster than this never really opened a window.
_WINDOW_MIN_LIFETIME = 3.0


def _ensure_std_streams() -> None:
    """Give sys.stdout/sys.stderr real file objects when there is no console.

    PyInstaller sets both to None in a windowed build. Library code that
    merely *probes* them then dies: uvicorn's log formatter calls
    sys.stdout.isatty() to decide whether to colourise, which raised
    AttributeError on NoneType, failed logging's dictConfig, and aborted
    uvicorn before it ever bound its socket - so the app sat there alive
    with no window and no server. Pointing the streams at the null device
    fixes this class of failure rather than this one instance of it.
    """
    for name in ("stdout", "stderr"):
        if getattr(sys, name, None) is None:
            try:
                setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
            except OSError:
                pass


def _data_dir() -> Path:
    """Per-user writable directory for this app's own files. Not the install
    folder: that may sit under Program Files, where a normal user cannot
    write."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    path = Path(base) / "VedicAstro"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _report_fatal(summary: str, detail: str = "") -> None:
    """Tell the user why the app is not opening, and leave a log behind.

    This exists because the app is built windowed (console=False), which
    means sys.stdout and sys.stderr are None and `print` is a silent no-op.
    Without this, any startup failure looks identical to the app doing
    nothing at all - which is exactly how a missing .NET runtime went
    unnoticed until someone ran it on a clean machine. MessageBoxW is used
    rather than a GUI toolkit so that this path cannot itself fail for want
    of a dependency.
    """
    log_path = None
    try:
        log_path = _data_dir() / "startup-error.log"
        log_path.write_text(
            f"{summary}\n\n{detail}".strip() + "\n", encoding="utf-8"
        )
    except OSError:
        log_path = None

    message = summary
    if log_path is not None:
        message += f"\n\nTechnical details were saved to:\n{log_path}"
    try:
        # 0x10 = MB_ICONERROR
        ctypes.windll.user32.MessageBoxW(None, message, "Vedic Astro", 0x10)
    except Exception:
        pass


_SESSION_FILE = "session.port"


def _write_session_port(port: int) -> None:
    try:
        (_data_dir() / _SESSION_FILE).write_text(str(port), encoding="utf-8")
    except OSError:
        pass


def _read_session_port() -> int | None:
    try:
        return int((_data_dir() / _SESSION_FILE).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _clear_session_port() -> None:
    try:
        (_data_dir() / _SESSION_FILE).unlink(missing_ok=True)
    except OSError:
        pass


def _acquire_single_instance_lock() -> socket.socket | None:
    """The bound socket on success, or None when another instance holds it."""
    lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # No SO_REUSEADDR: the point is for the second bind to fail.
        lock.bind(("127.0.0.1", _SINGLE_INSTANCE_PORT))
    except OSError:
        lock.close()
        return None
    return lock


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _wait_until_serving(port: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.5)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.1)
    return False


# Set by the server thread when it dies, so the main thread can report the
# real reason instead of a generic timeout.
_server_error: str | None = None


def _serve(port: int) -> None:
    global _server_error
    try:
        uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        ).run()
    except BaseException:
        # Including BaseException on purpose: this runs on a thread whose
        # exceptions would otherwise be written to a sys.stderr that is None
        # in a windowed build, and so lost entirely.
        _server_error = traceback.format_exc()


# Windows records where each browser is actually installed here, which is
# authoritative: guessing at Program Files misses per-user installs, machines
# with a relocated Program Files, and anything installed somewhere unusual.
# Getting this wrong is not cosmetic - it is the difference between the app
# opening its own window and dumping the user into a browser tab.
_APP_PATHS_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"


def _browser_from_registry(executable: str) -> Path | None:
    views = (
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_64KEY),
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_32KEY),
        (winreg.HKEY_CURRENT_USER, 0),
    )
    for root, view in views:
        try:
            with winreg.OpenKey(
                root, _APP_PATHS_KEY + "\\" + executable, 0, winreg.KEY_READ | view
            ) as key:
                value, _ = winreg.QueryValueEx(key, None)
        except OSError:
            continue
        candidate = Path(str(value).strip().strip('"'))
        if candidate.is_file():
            return candidate
    return None


def _browser_from_known_paths(relative: Path) -> Path | None:
    bases = (
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("LOCALAPPDATA", ""),
    )
    for base in bases:
        if not base:
            continue
        candidate = Path(base) / relative
        if candidate.is_file():
            return candidate
    return None


def _find_chromium_browser() -> Path | None:
    """Edge first (part of Windows 10/11), then Chrome."""
    wanted = (
        ("msedge.exe", Path("Microsoft") / "Edge" / "Application" / "msedge.exe"),
        ("chrome.exe", Path("Google") / "Chrome" / "Application" / "chrome.exe"),
    )
    for executable, relative in wanted:
        found = _browser_from_registry(executable) or _browser_from_known_paths(relative)
        if found is not None:
            return found
    return None


# Chromium opens its welcome/first-run pages in a brand new profile unless
# told not to, which would put an "Introduction" window in front of the app.
_QUIET_BROWSER_FLAGS = (
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-sync",
    "--disable-features=msEdgeWelcomePage,msEdgeFirstRunExperience,msImplicitSignin",
    "--no-service-autorun",
    "--disable-background-networking",
    "--disable-default-apps",
)


def _profiles_root() -> Path:
    return _data_dir() / "window-profiles"


def _new_profile_dir() -> Path:
    """A browser profile belonging to this launch alone.

    This is the whole reason the app can be trusted to open. Chromium keys
    its single-instance lock on the profile directory: hand it a directory
    some other process already owns and it forwards the URL to that process
    and exits immediately with status 0. Leftover Edge helper processes - the
    kind a hard kill of this app strands - own exactly that directory, so a
    shared profile meant the browser could exit instantly, the app would
    read that as "the window was closed", and clicking the icon would do
    nothing at all with no error anywhere. A directory unique to this
    process cannot be owned by anyone else, so the browser we start is
    always the browser we can wait on.
    """
    path = _profiles_root() / f"session-{os.getpid()}"
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sweep_old_profiles(keep: Path) -> None:
    """Delete profiles stranded by earlier launches that were killed before
    they could clean up after themselves."""
    try:
        children = list(_profiles_root().iterdir())
    except OSError:
        return
    for child in children:
        if child != keep:
            shutil.rmtree(child, ignore_errors=True)


def _spawn_browser(
    url: str, profile: Path
) -> tuple[subprocess.Popen[bytes] | None, Path | None]:
    browser = _find_chromium_browser()
    if browser is None:
        return None, None

    width, height = WINDOW_SIZE
    process = subprocess.Popen(
        [
            str(browser),
            f"--app={url}",
            f"--user-data-dir={profile}",
            f"--window-size={width},{height}",
            *_QUIET_BROWSER_FLAGS,
        ]
    )
    return process, browser


def _browser_processes_using(profile: Path) -> int:
    """How many browser processes are still using this launch's profile.

    Needed because the process we spawn is not always the process that ends
    up owning the window: Chromium may hand off to a freshly started browser
    process and let the original exit within a second. Waiting only on the
    process we spawned would then look like an instant failure even though
    the window is up. The profile directory is unique to this launch, so any
    browser using it is ours.
    """
    query = (
        "@(Get-CimInstance Win32_Process -Filter \"Name='msedge.exe' or "
        "Name='chrome.exe'\" -ErrorAction SilentlyContinue | Where-Object "
        f"{{ $_.CommandLine -like '*{profile.name}*' }}).Count"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", query],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return int(result.stdout.strip() or 0)
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0


def _run_window(url: str, sweep: bool = True) -> tuple[bool, str]:
    """Show the app window, blocking until the user closes it.

    Returns (shown, diagnostic). `shown` is False when no window could be
    kept open, so the caller falls back to the default browser; the
    diagnostic says why, because "it opened in your browser instead" is
    useless to anyone trying to work out what went wrong on a machine we
    cannot inspect.
    """
    profile = _new_profile_dir()
    if sweep:
        # Only safe for the instance holding the single-instance lock: a
        # second instance sweeping would delete the profile belonging to
        # the window the user is looking at.
        _sweep_old_profiles(keep=profile)

    window, browser = _spawn_browser(url, profile)
    if window is None:
        shutil.rmtree(profile, ignore_errors=True)
        return False, (
            "No Chromium browser was found. Looked in the Windows App Paths "
            "registry for msedge.exe and chrome.exe, and in Program Files, "
            "Program Files (x86) and LOCALAPPDATA."
        )

    opened_at = time.monotonic()
    try:
        window.wait()
        lifetime = time.monotonic() - opened_at

        if lifetime < _WINDOW_MIN_LIFETIME:
            # It may have handed off rather than failed - check before
            # concluding anything.
            still_running = _browser_processes_using(profile)
            if still_running:
                while _browser_processes_using(profile):
                    time.sleep(2.0)
                return True, ""
            return False, (
                f"{browser} exited after {lifetime:.1f}s without opening a "
                "window, and left no browser process using this session's "
                "profile."
            )

        return True, ""
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def _attach_to_running_instance() -> int:
    """Show the app when its icon is clicked while it is already running.

    Every other desktop application brings itself up when you click its icon
    again; answering with "already running" and quitting is a bug, not a
    safeguard. It is worst right after the app has fallen back to the
    default browser, because the process is then alive with no window of its
    own and the icon would be permanently dead.
    """
    port = _read_session_port()
    if port is None or not _wait_until_serving(port, timeout=3.0):
        _report_fatal(
            "Vedic Astro is already running, but is not responding.\n\n"
            "Open Task Manager, end the task named VedicAstro, then start "
            "the app again."
        )
        return 1

    url = f"http://127.0.0.1:{port}/"
    shown, _ = _run_window(url, sweep=False)
    if not shown:
        webbrowser.open(url)
    return 0


def main() -> int:
    _ensure_std_streams()

    lock = _acquire_single_instance_lock()
    if lock is None:
        return _attach_to_running_instance()

    try:
        port = _find_free_port()
        threading.Thread(target=_serve, args=(port,), daemon=True).start()

        if not _wait_until_serving(port, _SERVER_START_TIMEOUT):
            _report_fatal(
                "Vedic Astro could not start its calculation engine.",
                _server_error
                or f"The engine did not begin serving within {_SERVER_START_TIMEOUT:.0f}s "
                "and reported no error.",
            )
            return 1

        _write_session_port(port)
        url = f"http://127.0.0.1:{port}/"
        shown, reason = _run_window(url)
        if shown:
            return 0

        # No usable Chromium window. Open the page in the default browser and
        # keep serving: there is no window process to wait on, so the user
        # closes this process themselves. Better a browser tab than nothing.
        webbrowser.open(url)
        _report_fatal(
            "Vedic Astro could not open its own window, so it opened in your "
            "web browser instead.\n\nThe app is still running at " + url + "\n\n"
            "Leave this running while you use it.",
            reason,
        )
        threading.Event().wait()
        return 0
    finally:
        _clear_session_port()
        lock.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException:
        _report_fatal(
            "Vedic Astro hit an unexpected error while starting up.",
            traceback.format_exc(),
        )
        raise SystemExit(1)
