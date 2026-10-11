# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Vedic Astro desktop app.

Built as ONEDIR rather than onefile on purpose: the geo datasets below are
large, and onefile re-extracts the whole bundle to a temp directory on every
launch, which would make the app slow to start every single time.

The app resolves its templates, static files and data files through
`Path(__file__).parent`, so those three trees must land at the same relative
paths inside the bundle that they occupy in the source tree - that is what the
`datas` entries below guarantee, and it is why no source changes were needed
to make the app packageable.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

# geonamescache ships four nested city datasets totalling 179 MB, but
# geocode.py constructs GeonamesCache(min_city_population=500), and the
# library resolves exactly one file from that number - cities500.json. The
# other three are strict subsets of it that are never opened, so bundling them
# costs 104 MB for nothing.
_UNUSED_GEONAMES_DATA = {
    "cities1000.json",
    "cities5000.json",
    "cities15000.json",
}

# These ship their own data files (city lists, timezone polygons, coordinate
# grids) that PyInstaller cannot infer from imports alone. Missing any one of
# them breaks place-of-birth search at runtime while the build still succeeds,
# so they are collected wholesale rather than piecemeal.
for package in ("geonamescache", "reverse_geocoder", "timezonefinder", "tzdata"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    if package == "geonamescache":
        package_datas = [
            (source, destination)
            for source, destination in package_datas
            if Path(source).name not in _UNUSED_GEONAMES_DATA
        ]
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

# uvicorn resolves its loop/protocol/lifespan implementations by string name at
# runtime, so static analysis misses them.
hiddenimports += collect_submodules("uvicorn")

# The app's own resources, kept at their source-tree-relative locations.
datas += [
    ("src/vedic_astro/web/static", "vedic_astro/web/static"),
    ("src/vedic_astro/web/templates", "vedic_astro/web/templates"),
    ("src/vedic_astro/data", "vedic_astro/data"),
]

analysis = Analysis(
    ["src/vedic_astro/desktop.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Pillow is build-time only (scripts/build_app_icon.py) and cryptography
    # was installed for a one-off PDF read; neither is imported anywhere under
    # src/, and together they cost ~27 MB. scipy is deliberately NOT excluded -
    # reverse_geocoder really does use scipy.spatial's KD-tree at runtime.
    #
    # webview/pythonnet/clr_loader are excluded deliberately and must stay
    # excluded: pywebview's Windows backend loads .NET through pythonnet, so
    # bundling it reintroduces a hidden .NET runtime prerequisite. The app ran
    # on a machine with .NET Framework 4.8 and failed on a clean one with
    # "Failed to resolve Python.Runtime.Loader.Initialize". desktop.py now
    # opens an Edge --app window instead, which needs no .NET at all.
    excludes=[
        "tkinter",
        "matplotlib",
        "pytest",
        "mypy",
        "PIL",
        "cryptography",
        "webview",
        "pythonnet",
        "clr_loader",
        "clr",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="VedicAstro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # no console window behind the app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="src/vedic_astro/web/static/app.ico",
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="VedicAstro",
)
