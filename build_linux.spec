from pathlib import Path

project_root = Path(SPECPATH)
icon_path = project_root / 'assets' / 'icon.png'

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / 'ui' / 'ui_files'), 'ui/ui_files'),
        (str(project_root / 'assets' / 'icon.png'), 'assets') if icon_path.exists() else None,
    ],
    hiddenimports=[
        'PyQt5.uic',
        'PyQt5.uic.plugins',
        'PyQt5.QtSql',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

a.datas = [d for d in a.datas if d is not None]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='gestion-scolaire',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,
    icon=str(icon_path) if icon_path.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=True,
    name='gestion-scolaire',
)
