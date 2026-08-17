import os
import shutil
import subprocess
import sys
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / 'dist'
BUILD_DIR = ROOT / 'build'
ASSETS_DIR = ROOT / 'assets'
ICON_PATH = ASSETS_DIR / 'icon.ico'
PNG_PATH = ASSETS_DIR / 'icon.png'
SPEC_PATH = ROOT / 'build_win.spec'
LINUX_SPEC_PATH = ROOT / 'build_linux.spec'
ISS_PATH = ROOT / 'setup_gestion_scolaire.iss'
INSTALLER_DIR = ROOT / 'installers'
APP_DIR_NAME = 'GestionScolaire'
EXE_NAME = 'GestionScolaire.exe'
LINUX_APP_DIR_NAME = 'gestion-scolaire'
LINUX_EXE_NAME = 'gestion-scolaire'
DEB_NAME = 'gestion-scolaire'


def _version() -> str:
    text = (ROOT / 'core' / 'config.py').read_text(encoding='utf-8')
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'APP_VERSION':
                    return str(ast.literal_eval(node.value))
    return '1.0.0'


def _ensure_icon() -> Path:
    if ICON_PATH.exists() and PNG_PATH.exists():
        return ICON_PATH
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter
    app = QGuiApplication([])
    size = 256
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor('#047857'))
    painter.drawRoundedRect(0, 0, size, size, size // 5, size // 5)
    painter.setPen(QColor('white'))
    painter.setFont(QFont('Segoe UI', 100, QFont.Bold))
    painter.drawText(image.rect(), Qt.AlignCenter, 'GS')
    painter.end()
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    saved = image.save(str(ICON_PATH), 'ICO') and image.save(str(PNG_PATH), 'PNG')
    painter = None
    image = None
    app.quit()
    app = None
    if not saved:
        sys.exit("Erreur : impossible de creer les icones assets/icon.ico et assets/icon.png")
    return ICON_PATH


def _run(cmd: list) -> None:
    print('> ' + ' '.join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True)


def _pyinstaller(spec: Path) -> None:
    _run([
        sys.executable, '-m', 'PyInstaller',
        str(spec),
        '--noconfirm', '--clean',
        '--distpath', str(DIST_DIR),
        '--workpath', str(BUILD_DIR),
    ])


def _find_iscc() -> Path | None:
    from_env = os.environ.get('ISCC_PATH')
    if from_env and Path(from_env).exists():
        return Path(from_env)
    candidates = [
        r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
        r'C:\Program Files\Inno Setup 6\ISCC.exe',
        r'C:\Program Files (x86)\Inno Setup 5\ISCC.exe',
        r'C:\Program Files\Inno Setup 5\ISCC.exe',
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return path
    return shutil.which('iscc') or shutil.which('ISCC.exe')


def _find_signtool() -> Path | None:
    from_env = os.environ.get('SIGNTOOL_PATH')
    if from_env and Path(from_env).exists():
        return Path(from_env)
    return shutil.which('signtool')


def _sign_target(path: Path, signtool: Path) -> None:
    pfx = os.environ.get('SIGN_PFX')
    password = os.environ.get('SIGN_PASSWORD')
    if not pfx or not password:
        print('Signature ignoree : definissez SIGN_PFX et SIGN_PASSWORD')
        return
    timestamp = os.environ.get('SIGN_TIMESTAMP', 'http://timestamp.digicert.com')
    cmd = [
        str(signtool), 'sign', '/f', pfx, '/p', password,
        '/fd', 'SHA256', '/tr', timestamp, '/td', 'SHA256',
        str(path),
    ]
    _run(cmd)


def _build_installer() -> None:
    iscc = _find_iscc()
    if not iscc:
        print('ISCC introuvable : installation de l\'installeur sautee.')
        return
    cmd = [str(iscc), str(ISS_PATH), '/DMyAppVersion=' + _version()]
    _run(cmd)


def _build_deb() -> None:
    if shutil.which('dpkg-deb') is None:
        print('dpkg-deb introuvable : paquet .deb non cree.')
        return
    version = _version()
    stage = BUILD_DIR / 'deb_stage'
    if stage.exists():
        shutil.rmtree(stage)
    opt = stage / 'opt' / LINUX_APP_DIR_NAME
    shutil.copytree(DIST_DIR / LINUX_APP_DIR_NAME, opt)
    _write_script(stage / 'usr' / 'bin' / 'gestion-scolaire', '#!/bin/sh\nexec /opt/gestion-scolaire/gestion-scolaire "$@"\n')
    desktop = stage / 'usr' / 'share' / 'applications' / 'gestion-scolaire.desktop'
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text(
        '[Desktop Entry]\n'
        'Type=Application\n'
        'Version=1.0\n'
        'Name=Gestion Scolaire\n'
        'Comment=Application de gestion scolaire\n'
        'Exec=gestion-scolaire\n'
        'Icon=gestion-scolaire\n'
        'Terminal=false\n'
        'Categories=Education;\n'
        'StartupWMClass=gestion-scolaire\n', encoding='utf-8')
    icon_dir = stage / 'usr' / 'share' / 'icons' / 'hicolor' / '256x256' / 'apps'
    icon_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PNG_PATH, icon_dir / 'gestion-scolaire.png')
    _write_script(stage / 'DEBIAN' / 'postinst',
                  '#!/bin/sh\nset -e\n'
                  'if command -v update-desktop-database >/dev/null 2>&1; then\n'
                  '    update-desktop-database /usr/share/applications >/dev/null 2>&1 || true\n'
                  'fi\nexit 0\n')
    control = stage / 'DEBIAN' / 'control'
    control.parent.mkdir(parents=True, exist_ok=True)
    control.write_text(
        'Package: {}\n'
        'Version: {}\n'
        'Section: education\n'
        'Priority: optional\n'
        'Architecture: amd64\n'
        'Depends: libxcb-xinerama0, libxkbcommon-x11-0, libegl1, libxcb-cursor0,'
        ' libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0,'
        ' libxcb-render-util0, libxcb-xfixes0, libxcb-shape0\n'
        'Maintainer: Gestion Scolaire\n'
        'Homepage: https://github.com/laudesmassamba1-ai/Logiciel-de-gestion-scolaire\n'
        'Description: Application de gestion scolaire\n'
        ' Gestion des eleves, notes, finances, planning et presences.\n'.format(DEB_NAME, version),
        encoding='utf-8')
    postrm = stage / 'DEBIAN' / 'postrm'
    _write_script(postrm,
                  '#!/bin/sh\nset -e\n'
                  'if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then\n'
                  '    if command -v update-desktop-database >/dev/null 2>&1; then\n'
                  '        update-desktop-database /usr/share/applications >/dev/null 2>&1 || true\n'
                  '    fi\n'
                  '    rm -rf /opt/gestion-scolaire/data 2>/dev/null || true\n'
                  'fi\nexit 0\n')
    INSTALLER_DIR.mkdir(parents=True, exist_ok=True)
    deb_path = INSTALLER_DIR / '{}_{}_{}.deb'.format(DEB_NAME, version, 'amd64')
    _run(['dpkg-deb', '--build', '--root-owner-group', str(stage), str(deb_path)])


def _write_script(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    path.chmod(0o755)


def _build_windows() -> None:
    _pyinstaller(SPEC_PATH)
    exe = DIST_DIR / APP_DIR_NAME / EXE_NAME
    signtool = _find_signtool()
    if signtool:
        _sign_target(exe, signtool)
    _build_installer()
    setup = next(INSTALLER_DIR.glob('*.exe'), None) if INSTALLER_DIR.exists() else None
    if setup and signtool:
        _sign_target(setup, signtool)


def _build_linux() -> None:
    _pyinstaller(LINUX_SPEC_PATH)
    _build_deb()


def main() -> None:
    _ensure_icon()
    if sys.platform == 'win32':
        _build_windows()
    else:
        _build_linux()
    print('Build termine.')


if __name__ == '__main__':
    main()
