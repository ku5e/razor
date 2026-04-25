# razor.spec
from PyInstaller.utils.hooks import collect_data_files
import platform

block_cipher = None

datas = collect_data_files("customtkinter")

a = Analysis(
    ["timer.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "playsound",
        "plyer.platforms.win.notification",
        "plyer.platforms.macosx.notification",
        "plyer.platforms.linux.notification",
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="razor",
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
    icon="razor.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="razor",
)

# Mac: wrap in .app bundle
if platform.system() == "Darwin":
    app = BUNDLE(
        coll,
        name="Razor.app",
        icon="razor.ico",
        bundle_identifier="com.ku5e.razor",
        info_plist={
            "NSHighResolutionCapable": True,
            "LSUIElement": True,  # hides from Dock (floating widget behavior)
        },
    )
