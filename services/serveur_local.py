"""Gestion du serveur GS integre — sans terminal, multi-plateforme.

L'assistant graphique (et le worker de synchro) utilisent ce module pour :
  - demarrer le serveur FastAPI sur CE poste en mode SQLite
    (aucune installation : la base est un simple fichier) ;
  - l'arreter proprement ;
  - connaitre l'adresse a saisir sur les autres postes de l'ecole.

Windows : le processus est cree SANS fenetre console (CREATE_NO_WINDOW)
et arrete via TerminateProcess. Linux/Mac : nouvelle session (setsid)
pour pouvoir couper tout le groupe.
"""

import os
import signal
import socket
import subprocess
import sys
import time

import httpx

from core.config import PROJECT_ROOT, data_dir, lire_config_sync, ecrire_config_sync

_DELAI_ATTENTE_S = 15

_annonceur = None


def _debuter_annonce(port: int):
    """Annonce la presence du serveur sur le reseau local (broadcast UDP)
    pour que les autres postes le trouvent automatiquement."""
    global _annonceur
    if _annonceur is not None:
        return
    try:
        from services.discovery import AnnonceurServeur
        _annonceur = AnnonceurServeur(port_api=port)
        _annonceur.start()
    except Exception:
        _annonceur = None


def _stopper_annonce():
    global _annonceur
    if _annonceur is not None:
        try:
            _annonceur.stop()
            _annonceur.join(1.0)
        except Exception:
            pass
        _annonceur = None


def port_configure() -> int:
    try:
        return int(lire_config_sync().get("port", 8000))
    except Exception:
        return 8000


def journal_serveur() -> "os.PathLike":
    return data_dir() / "serveur.log"


def pid_enregistre():
    pid = lire_config_sync().get("pid")
    return int(pid) if pid else None


def _port_occupe(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sonde:
        sonde.settimeout(0.5)
        return sonde.connect_ex(("127.0.0.1", port)) == 0


def adresse_locale(port: int) -> str:
    """IP reelle du poste sur le reseau local (pour les autres postes)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sonde:
            sonde.settimeout(0)
            sonde.connect(("8.8.8.8", 80))
            ip = sonde.getsockname()[0]
        if ip and not ip.startswith("127."):
            return f"http://{ip}:{port}"
    except OSError:
        pass
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        for info in infos:
            ip = info[4][0]
            if ip and not ip.startswith("127."):
                return f"http://{ip}:{port}"
    except OSError:
        pass
    return f"http://127.0.0.1:{port}"


def serveur_disponible() -> bool:
    """Vérifie que les dépendances du serveur (uvicorn + fastapi) sont installées."""
    for mod in ("uvicorn", "fastapi"):
        try:
            __import__(mod)
        except ImportError:
            return False
    return True


def _charger_env_serveur():
    """Lit server/.env s'il existe (config MySQL definie par l'hote)."""
    import collections
    chemin = os.path.join(PROJECT_ROOT, "server", ".env")
    valeurs = collections.OrderedDict()
    try:
        with open(chemin, encoding="utf-8") as fichier:
            for ligne in fichier:
                ligne = ligne.strip()
                if not ligne or ligne.startswith("#") or "=" not in ligne:
                    continue
                cle, _, valeur = ligne.partition("=")
                valeurs[cle.strip()] = valeur.strip()
    except OSError:
        pass
    return valeurs


def _config_mysql_presente(environ_fichier) -> bool:
    """MySQL reel quand un mot de passe est defini (server/.env).

    Sinon on retombe en SQLite (« sans installation ») pour un poste seul.
    """
    return bool(environ_fichier.get("GS_DB_PASSWORD"))


def demarrer_serveur(port: int = None, serveur_auto: bool = True):
    """Demarre uvicorn en tache de fond. Retourne (ok, message).

    serveur_auto : si True, le drapeau est persiste dans sync.json pour
    un demarrage automatique au prochain lancement de l'application.
    """
    if port is None:
        port = port_configure()

    if not serveur_disponible():
        return False, (
            "Le serveur ne peut pas demarrer : les paquets « uvicorn » et "
            "« fastapi » ne sont pas installe sur ce poste. Installez-les "
            "avec :  pip install uvicorn fastapi puis relancez.")

    if _port_occupe(port):
        # Quelque chose ecoute deja (serveur deja lance ?) : on teste.
        if api_joignable(port):
            ecrire_config_sync(sync_active=True, port=port,
                               api_url=f"http://127.0.0.1:{port}",
                               serveur_auto=serveur_auto)
            _debuter_annonce(port)
            return True, ("Le serveur repond deja sur le port "
                          f"{port} — synchronisation activee.")
        return False, (f"Le port {port} est occupe par une autre "
                       "application. Choisissez un autre port.")

    env = os.environ.copy()
    env_serveur = _charger_env_serveur()
    if _config_mysql_presente(env_serveur):
        # Mode MySQL reel : on injecte la configuration server/.env dans
        # l'environnement du processus uvicorn (chargee aussi par securite.py).
        for cle, valeur in env_serveur.items():
            if cle not in env or valeur:
                env[cle] = valeur
    else:
        # Mode « sans installation » : SQLite, aucun MySQL requis.
        env["GS_DB_MODE"] = "sqlite"
        env["GS_SQLITE_DIR"] = str(data_dir() / "serveur")
        env.pop("GS_DB_HOST", None)

    options = {}
    if os.name == "nt":
        creation_no_console = 0x08000000          # CREATE_NO_WINDOW
        options["creationflags"] = creation_no_console
    else:
        options["start_new_session"] = True

    try:
        journal = open(journal_serveur(), "a", encoding="utf-8")
        processus = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server.main:app",
             "--host", "0.0.0.0", "--port", str(port)],
            cwd=str(PROJECT_ROOT), env=env,
            stdout=journal, stderr=subprocess.STDOUT,
            **options,
        )
    except Exception as exc:
        return False, f"Impossible de lancer le serveur : {exc}"

    ecrire_config_sync(pid=processus.pid, port=port, sync_active=True,
                       api_url=f"http://127.0.0.1:{port}",
                       serveur_auto=serveur_auto)

    if api_joignable(port):
        _debuter_annonce(port)
        return True, ("Serveur demarre ! Sur les AUTRES postes, saisissez "
                      f"cette adresse : {adresse_locale(port)}")
    return False, ("Le serveur met du temps a demarrer. Consultez le "
                   f"journal : {journal_serveur()}")


def arreter_serveur():
    """Coupe le serveur lance par l'assistant et repasse en autonome.

    Retourne (ok, message).
    """
    pid = pid_enregistre()
    if not pid:
        ecrire_config_sync(pid=None, serveur_auto=False)
        _stopper_annonce()
        return True, "Aucun serveur n'a ete lance depuis cet ordinateur."
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.6)
        message = "Serveur arrete. L'application repasse en mode autonome."
    except ProcessLookupError:
        message = "Le serveur n'etait plus actif."
    except PermissionError:
        message = ("Impossible d'arreter le serveur (droits). "
                   "Fermez-le puis reessayez.")
    except OSError as exc:
        message = f"Arret impossible : {exc}"
    ecrire_config_sync(pid=None, serveur_auto=False)
    _stopper_annonce()
    return True, message


def api_joignable(port: int = None, delai: float = _DELAI_ATTENTE_S) -> bool:
    if port is None:
        port = port_configure()
    fin = time.monotonic() + delai
    url = f"http://127.0.0.1:{port}/annee_scolaire_active"
    while time.monotonic() < fin:
        try:
            rep = httpx.get(url, timeout=1.5)
            if rep.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(0.4)
    return False


def _est_processus_actif(pid: int) -> bool:
    """Vérifie si un processus est encore en vie (portabilité Windows/Linux/Mac)."""
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def demarrer_si_auto():
    """Démarre le serveur automatiquement au lancement de l'application
    si la configuration indique que ce poste est l'hôte avec serveur_auto=True.

    Vérifie d'abord si un serveur est déjà en cours (PID vivant ou port occupé)
    pour ne pas lancer de doublon.
    """
    from core.config import SERVEUR_AUTO, est_hote

    if not SERVEUR_AUTO or not est_hote():
        return False, "Ce poste n'est pas configuré comme hôte avec démarrage automatique."

    if not serveur_disponible():
        return False, (
            "Le serveur ne peut pas démarrer automatiquement : installez "
            "« uvicorn » et « fastapi » (pip install uvicorn fastapi).")

    pid = pid_enregistre()
    if pid and _est_processus_actif(pid):
        return True, "Le serveur est déjà en cours d'exécution."

    port = port_configure()
    if api_joignable(port, delai=1.0):
        return True, "Le serveur répond déjà sur le port {}.".format(port)

    ok, message = demarrer_serveur(port)
    return ok, message
