from pathlib import Path

project_root = Path(SPECPATH)
icon_path = project_root / 'assets' / 'icon.png'

a = Analysis(
    ['main.py'],
    pathex=[str(project_root), str(project_root / 'server')],
    binaries=[],
    datas=[
        (str(project_root / 'ui' / 'ui_files'), 'ui/ui_files'),
        (str(project_root / 'assets' / 'icon.png'), 'assets') if icon_path.exists() else None,
        (str(project_root / 'server' / 'schema.sql'), 'server'),
        (str(project_root / 'server' / 'schema_sqlite.sql'), 'server'),
    ],
    hiddenimports=[
        'PyQt5.uic',
        'PyQt5.uic.plugins',
        'PyQt5.QtSql',
        # Serveur FastAPI embarqué : référencé par chaîne ("server.main:app")
        # dans services/serveur_local.py, l'analyse statique ne le voit pas.
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.protocols.websockets.wsproto_impl',
        'fastapi',
        'server.main',
        'server.securite',
        'server.compat',
        'server.sqlite_backend',
        # Formes top-level (server/main.py fait `import securite`,
        # `import compat`, `from sqlite_backend import ...` via sys.path).
        'securite',
        'compat',
        'sqlite_backend',
        'services.discovery',
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
