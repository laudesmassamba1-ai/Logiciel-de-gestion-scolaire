"""Gestion du lancement automatique de l'application au demarrage du systeme.

Fournit une API unifiee pour activer/desactiver le demarrage automatique
selon le systeme d'exploitation :

- Linux : fichier .desktop dans ~/.config/autostart/
- Windows : raccourci .lnk dans le dossier de demarrage
- macOS : fichier .plist dans ~/Library/LaunchAgents/

Utilise le binaire courant (python + script, ou exe genere par build_app.py).
"""

import os
import sys
from pathlib import Path

from core.config import APP_NAME, PROJECT_ROOT


def _executable() -> Path:
    """Retourne le chemin de l'executable a mettre dans le startup."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    return Path(sys.executable)


def _script_demarrage():
    """Arguments/ligne de commande pour lancer l'application."""
    if getattr(sys, "frozen", False):
        return None
    main_py = PROJECT_ROOT / "main.py"
    return [str(_executable()), str(main_py)]


def _fichier_demarrage() -> Path:
    """Chemin canonique du fichier de demarrage selon l'OS."""
    nom = APP_NAME.lower().replace(" ", "-")
    if sys.platform == "win32":
        dossier = Path(os.environ.get(
            "APPDATA",
            str(Path.home() / "AppData" / "Roaming"))
        )
        return dossier / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / f"{nom}.lnk"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "LaunchAgents" / f"com.gestion-scolaire.{nom}.plist"
    else:
        return Path.home() / ".config" / "autostart" / f"{nom}.desktop"


def est_auto_demarrage() -> bool:
    """Retourne True si le lancement automatique est actif."""
    return _fichier_demarrage().exists()


def activer_auto_demarrage() -> bool:
    """Active le demarrage automatique. Retourne True si cela a fonctionne."""
    fichier = _fichier_demarrage()
    exe = _executable()
    nom = APP_NAME.lower().replace(" ", "-")
    fichier.parent.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        try:
            from win32com.client import Dispatch
            shell = Dispatch("WScript.Shell")
            raccourci = shell.CreateShortCut(str(fichier))
            raccourci.Targetpath = str(exe)
            raccourci.WorkingDirectory = str(PROJECT_ROOT)
            raccourci.IconLocation = str(exe)
            raccourci.save()
            return True
        except Exception:
            # Fallback : fichier .bat
            bat = fichier.parent / f"{nom}.bat"
            bat.write_text(f'@echo off\nstart "" "{exe}"\n', encoding="utf-8")
            return bat.exists()

    if sys.platform == "darwin":
        exe_str = str(exe)
        contenu = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>Label</key>
\t<string>com.gestion-scolaire.{nom}</string>
\t<key>ProgramArguments</key>
\t<array>
\t\t<string>{exe_str}</string>
\t</array>
\t<key>RunAtLoad</key>
\t<true/>
</dict>
</plist>"""
        fichier.write_text(contenu, encoding="utf-8")
        return True

    # Linux : fichier .desktop
    exe_str = str(exe)
    main_py = str(PROJECT_ROOT / "main.py")
    if getattr(sys, "frozen", False):
        exec_line = exe_str
    else:
        exec_line = f"{exe_str} {main_py}"
    contenu = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Exec={exec_line}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
    fichier.write_text(contenu, encoding="utf-8")
    return True


def desactiver_auto_demarrage() -> bool:
    """Desactive le lancement automatique. Retourne True si fichier supprime."""
    fichier = _fichier_demarrage()
    try:
        fichier.unlink()
        return True
    except FileNotFoundError:
        return True
    except Exception:
        return False
