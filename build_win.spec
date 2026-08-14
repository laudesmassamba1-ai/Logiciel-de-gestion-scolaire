# -*- mode: python ; coding: utf-8 -*-
"""Spec PyInstaller WINDOWS (one-file) : construit GestionScolaire.exe autonome.

A executer avec un Python Windows (ex: sous Wine) :
    pyinstaller build_win.spec --noconfirm --clean
"""
from pathlib import Path

project_root = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / 'views' / 'ui_files'), 'views/ui_files'),
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

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='GestionScolaire',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=None,
    # Manifeste DPI : rendu net sur ecrans 100/125/150/200 %.
    # Qt 5.15 ne gere que le DPI systeme (<dpiAware>true</dpiAware>) : declare ici
    # pour eviter l'etirement bitmap de Windows (texte/contours flous) avant meme
    # l'init de Qt.
    manifest=str(project_root / 'win_dpi_manifest.xml'),
)
