# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['daily_planner.py'],
    pathex=[],
    binaries=[],
    datas=[('commands.db', '.')],
    hiddenimports=['PyQt5', 'sqlite3', 'zhipuai', 'json', 'asyncio', 'pydantic.json_schema', 'pydantic.networks', 'pydantic.types', 'pydantic.validators', 'pydantic.fields'],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DailyPlanner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity='-',
    entitlements_file=None,
    icon=['app_icon.icns'],
)
app = BUNDLE(
    exe,
    name='DailyPlanner.app',
    icon='app_icon.icns',
    bundle_identifier=None,
)
