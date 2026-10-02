# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for TA-app. Build with:

    pyinstaller TA-app.spec

Produces a ONEDIR build (a folder of files, not a single .exe) on every
platform - see the long comment further down for why that's the safer
default here. This spec is written to run correctly on Windows, macOS,
and Linux; PyInstaller itself does NOT cross-compile, so the actual
output you get always matches whatever OS you run this command on - a
Windows machine can only build a Windows binary, a Mac can only build a
Mac one, and so on. Building all three means running this spec on all
three (see .github/workflows/build.yml for doing that automatically).

Requires pyinstaller itself (pip install pyinstaller) - that's a build
tool, not a runtime dependency, so it doesn't belong in requirements.txt
alongside things like openpyxl/fpdf2/matplotlib that the app actually
imports while running.
"""
import os
import sys

block_cipher = None

# SPECPATH is injected automatically by PyInstaller into this file's
# namespace - the absolute path of the folder this .spec file lives in.
# Building datas/pathex from it (rather than a relative path) means this
# spec works correctly regardless of what directory `pyinstaller` is
# invoked from.
PROJECT_ROOT = SPECPATH

a = Analysis(
    ['main.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        # Bundled, read-only resources - see config.py's RESOURCE_DIRECTORY
        # docstring for why these specifically need to be reachable via
        # sys._MEIPASS/next-to-the-exe rather than the writable data base.
        # The destination (second element) matches config.py's own
        # "assets/fonts" / "assets/logo" path construction, so nothing
        # else needs to change for these to be found correctly once frozen,
        # on any of the three platforms.
        (os.path.join(PROJECT_ROOT, 'assets', 'fonts'), os.path.join('assets', 'fonts')),
        (os.path.join(PROJECT_ROOT, 'assets', 'logo'), os.path.join('assets', 'logo')),
    ],
    hiddenimports=[
        # matplotlib's Tk backend is loaded dynamically (by name, as a
        # string) rather than via a normal import statement, so
        # PyInstaller's static analysis can miss it without this. Needed
        # identically on all three platforms.
        'matplotlib.backends.backend_tkagg',
        # Uncomment if you installed fpdf2's optional text-shaping extra
        # (`pip install "fpdf2[text-shaping]"`) for correct Persian/Arabic
        # letter joining and right-to-left order - see
        # ExportService._configure_pdf_font()'s docstring. Leaving this
        # commented out is fine either way; PyInstaller will just bundle
        # whatever's actually importable, and the app already degrades
        # gracefully (readable-but-unshaped Persian text) if this isn't
        # installed at all.
        # 'uharfbuzz',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Icons are the one piece of this spec that genuinely differs per
# platform, not just cosmetically:
# - Windows: EXE()'s icon= wants a .ico file, which assets/logo/icon.ico
#   already is - used directly below.
# - macOS: the equivalent is a .icns file, which this project doesn't
#   have yet (only .ico/.png exist). Passing a .ico there wouldn't apply
#   correctly, and depending on the PyInstaller version could error
#   outright rather than just being ignored - so this is skipped
#   entirely on macOS until a real .icns is added. The app still runs
#   fine without one; it just uses the OS's generic app icon.
# - Linux: EXE() has no concept of an embedded icon at all - there's
#   nothing to set here regardless.
icon_path = None
if sys.platform.startswith('win'):
    icon_path = os.path.join(PROJECT_ROOT, 'assets', 'logo', 'icon.ico')

# ---- ONEDIR (recommended default, on every platform) ----
# A folder (dist/TA-app/) containing the executable alongside its
# dependencies and the bundled assets, rather than one single-file
# binary. This is the safer choice for this app specifically: a onefile
# build re-extracts its bundled contents to a temporary folder on every
# launch, which (a) adds a startup delay, and (b) can fail outright on a
# locked-down machine (e.g. a university lab computer where the
# student/TA account can't write to the system temp directory) - a
# failure mode that's easy to never see while testing on your own
# machine and then hit for the first time on exactly the computer you
# can't easily debug. A onedir build sidesteps both issues entirely:
# nothing is extracted at runtime, since everything already sits right
# next to the executable.
#
# config.py's BASE_DIRECTORY/RESOURCE_DIRECTORY split (see its module
# docstring) was written to work correctly either way, so if you want a
# single-file build instead on a given platform, delete the
# EXE()/COLLECT() pair below and replace it with:
#
#   exe = EXE(
#       pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
#       name='TA-app', debug=False, strip=False, upx=True, console=False,
#       icon=icon_path,
#   )

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TA-app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # no console window behind the GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TA-app',
)

# macOS only: wraps the onedir output into a proper double-clickable
# TA-app.app bundle. Without this step, a onedir build on macOS is just
# a folder with a raw Unix executable inside it - it runs, but it isn't
# a normal-looking Mac app. BUNDLE() is a no-op on Windows/Linux (it's
# simply not invoked there), so this doesn't affect those platforms.
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='TA-app.app',
        icon=None,  # would be a .icns path here too, once one exists
        bundle_identifier=None,
    )