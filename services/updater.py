"""Verification et installation des mises a jour, a distance.

Deux sources, dans l'ordre de priorite :
  1. Le serveur central de l'ecole (option B) : si la synchronisation est
     active et que l'endpoint /mise-a-jour/etat est configure, la version
     imposee et les paquets sont servis en LAN (fonctionne sans Internet).
  2. Les GitHub Releases du projet (option A) : le repo est public, donc
     n'importe quel poste peut interroger l'API sans cle.

Flux cote utilisateur (propose par ui/updater_ui.py) :
  au lancement de l'application, on verifie silencieusement ; si une version
  plus recente existe, une boite demande « oui ou non » ; si oui, on
  telecharge (empreinte SHA-256 verifiee quand fournie) puis on installe.

Installation selon le support :
  - Windows Setup (Inno)  -> script .bat silencieux apres fermeture de l'app ;
  - Windows onefile       -> remplacement du fichier par script .bat ;
  - Linux .deb            -> pkexec dpkg -i apres fermeture de l'app ;
  - Linux AppImage        -> remplacement direct du fichier (aucun droit).

Les donnees (base, documents, parametres) vivent dans data_dir() et ne sont
JAMAIS touchees par une installation : une mise a jour ne perd rien.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import httpx

from core.config import APP_VERSION, SYNC_ACTIVE, API_BASE_URL, data_dir

REPO = "laudesmassamba1-ai/Logiciel-de-gestion-scolaire"
API_GITHUB = f"https://api.github.com/repos/{REPO}/releases/latest"
# Les petits appels (metadonnees JSON) deverts un delai court ; le
# TELEchargement des paquets (plusieurs dizaines de Mo) doit tolerer les
# connexions lentes : on n'abandonne qu'apres a peu pres 15 minutes sans
# aucun octet recu (ReadTimeout), avec une ouverture a 30 s.
_DELAI_NET = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
_DELAI_CONNEXION = 30.0
_DELAI_LECTURE = 900.0


# ---------------------------------------------------------------- versions

def version_cle(texte) -> tuple | None:
    """'v1.6.2' / '1.6.2' -> (1, 6, 2). Renvoie None si non semver."""
    if not texte:
        return None
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", str(texte).strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def plus_recente(candidate, courante: str = APP_VERSION) -> bool:
    """True si candidate est une version strictement superieure a courante."""
    a = version_cle(candidate)
    b = version_cle(courante)
    return bool(a and b and a > b)


def _version_texte(tuple_version) -> str:
    return ".".join(str(x) for x in tuple_version)


# ---------------------------------------------------------------- plateforme

def est_appimage() -> bool:
    """True si CETTE application tourne depuis un fichier .AppImage.

    Une AppImage montee via FUSE ne fait PAS finir sys.argv[0] par
    '.appimage' (le binaire execute est AppRun) : la variable d'environnement
    APPIMAGE, renseignee par le runtime AppImage, est la source fiable.
    """
    try:
        if (os.environ.get("APPIMAGE") or "").strip():
            return True
        return (sys.argv[0] or "").lower().endswith(".appimage")
    except Exception:
        return False


def _paquet_attendu(version_texte: str) -> str:
    """Nom du paquet pertinent pour cette machine et cette version."""
    systeme = (sys.platform or "").lower()
    if systeme.startswith("win"):
        return f"GestionScolaire-Setup-{version_texte}.exe"
    if est_appimage():
        return f"GestionScolaire-{version_texte}.AppImage"
    return f"gestion-scolaire_{version_texte}_amd64.deb"


def _choisir_asset(assets, version_texte: str):
    """Choisit l'asset GitHub adapte : Setup (Windows), deb ou AppImage."""
    attendu = _paquet_attendu(version_texte)
    for asset in assets:
        if (asset.get("name") or "") == attendu:
            return asset
    # Repli raisonnable : fichier onefile Windows si le Setup manque.
    if (sys.platform or "").lower().startswith("win"):
        for asset in assets:
            if (asset.get("name") or "") == "GestionScolaire.exe":
                return asset
    return None


def _sha256_depuis_assets(assets, nom_fichier: str):
    """Lit l'empreinte SHA-256 dans un asset 'SHA256SUMS.txt' s'il existe."""
    for asset in assets:
        if (asset.get("name") or "").lower() != "sha256sums.txt":
            continue
        try:
            rep = httpx.get(asset.get("browser_download_url", ""),
                            timeout=_DELAI_NET,
                            headers={"User-Agent": "GestionScolaire-Updater"})
            rep.raise_for_status()
        except Exception:
            return None
        for ligne in rep.text.splitlines():
            parties = ligne.split()
            if len(parties) >= 2:
                nom = parties[-1].lstrip("*")
                if nom == nom_fichier:
                    return parties[0].strip().lower()
    return None


# ------------------------------------------------------------------- sources

def cible_serveur() -> dict | None:
    """Option B : consigne du serveur central de l'ecole (`/mise-a-jour/etat`).

    Ne reporte rien si la synchronisation est desactivee, si le serveur ne
    repond pas, si aucune consigne n'est activee ou si elle n'est pas plus
    recente que la version locale.
    """
    if not SYNC_ACTIVE:
        return None
    try:
        from api.client import _request
        data, err = _request("GET", "/mise-a-jour/etat")
        if err or not isinstance(data, dict) or not data.get("actif"):
            return None
        version = str(data.get("version") or "")
        if not plus_recente(version):
            return None
        nom = _paquet_attendu(_version_texte(version_cle(version)))
        # Le directeur peut nommer des paquets differents sur le depot.
        nom_serveur = ""
        systeme = (sys.platform or "").lower()
        if systeme.startswith("win"):
            nom_serveur = str(data.get("paquet_windows") or "")
        else:
            nom_serveur = str(data.get("paquet_linux") or "")
        nom_fichier = nom_serveur or nom
        sha_map = data.get("sha256") if isinstance(data.get("sha256"), dict) else {}
        url = API_BASE_URL.rstrip("/") + "/mise-a-jour/paquet/" + nom_fichier
        return {
            "source": "serveur",
            "version": version_cle(version),
            "version_texte": _version_texte(version_cle(version)),
            "nom_fichier": nom_fichier,
            "url": url,
            "sha256": sha_map.get(nom_fichier) if nom_fichier in sha_map else None,
            "obligatoire": bool(data.get("obligatoire")),
        }
    except Exception:
        return None


def cible_github() -> dict | None:
    """Option A : derniere release publique sur GitHub.

    Silencieux en cas d'echec (hors ligne, limite d'API...) -> None.
    """
    try:
        rep = httpx.get(
            API_GITHUB, timeout=_DELAI_NET,
            headers={"Accept": "application/vnd.github+json",
                     "User-Agent": "GestionScolaire-Updater"})
        rep.raise_for_status()
        release = rep.json()
    except Exception:
        return None
    tag = str(release.get("tag_name") or "")
    if not plus_recente(tag):
        return None
    version = version_cle(tag)
    version_texte = _version_texte(version)
    assets = release.get("assets") or []
    asset = _choisir_asset(assets, version_texte)
    if not asset:
        return None
    nom = str(asset.get("name") or "")
    return {
        "source": "github",
        "version": version,
        "version_texte": version_texte,
        "nom_fichier": nom,
        "url": str(asset.get("browser_download_url") or ""),
        "sha256": _sha256_depuis_assets(assets, nom),
        "obligatoire": False,
    }


def verifier_mise_a_jour() -> dict | None:
    """Retourne les infos de la mise a jour disponible, sinon None.

    Le serveur central prime (l'ecole peut imposer/diffuser) ; a defaut on
    consulte GitHub. N'importe quel echec reseau reste silencieux.
    """
    cible = cible_serveur()
    if cible is not None:
        return cible
    return cible_github()


# -------------------------------------------------------------- telechargement

def dossier_mises_a_jour() -> Path:
    dossier = data_dir() / "mises_a_jour"
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


def telecharger(infos: dict, progression=None):
    """Telecharge le paquet dans data_dir()/mises_a_jour et verifie le SHA.

    progression(recu, total) est appelee avec des octets (total 0 si inconnu).
    Retourne (chemin, None) ou (None, message_erreur).
    """
    dossier = dossier_mises_a_jour()
    nom = infos.get("nom_fichier") or "paquet"
    # Evite toute injection de chemin.
    nom = Path(nom).name
    destination = dossier / nom
    tmp = destination.with_suffix(destination.suffix + ".part")
    try:
        with httpx.stream("GET", infos["url"],
                          timeout=httpx.Timeout(
                              connect=_DELAI_CONNEXION, read=_DELAI_LECTURE,
                              write=_DELAI_CONNEXION, pool=_DELAI_CONNEXION),
                          follow_redirects=True,
                          headers={"User-Agent": "GestionScolaire-Updater"}) as rep:
            rep.raise_for_status()
            total = int(rep.headers.get("content-length") or 0)
            recu = 0
            with open(tmp, "wb") as fichier:
                for bloc in rep.iter_bytes(65536):
                    fichier.write(bloc)
                    recu += len(bloc)
                    if progression:
                        try:
                            progression(recu, total)
                        except Exception:
                            pass
        os.replace(tmp, destination)
    except httpx.ReadTimeout:
        try:
            tmp.unlink()
        except OSError:
            pass
        return None, ("Telechargement interrompu : la connexion est trop lente "
                      "ou coupee. Verifiez votre Internet puis reessayez.")
    except Exception as exc:
        try:
            tmp.unlink()
        except OSError:
            pass
        return None, f"Telechargement echoue : {exc}"
    sha = infos.get("sha256")
    if sha:
        try:
            calcule = hashlib.sha256(destination.read_bytes()).hexdigest()
        except OSError as exc:
            return None, f"Lecture du paquet impossible : {exc}"
        if calcule.lower() != str(sha).lower():
            try:
                destination.unlink()
            except OSError:
                pass
            return None, "Empreinte SHA-256 invalide : le paquet est corrompu."
    return str(destination), None


# ------------------------------------------------------ depot du serveur (B)

def dossier_depot_serveur() -> Path:
    dossier = data_dir() / "mises_a_jour_paquets"
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


def deposer_paquet(source) -> dict:
    """Copie un paquet d'installation dans le depot du serveur central.

    Retourne {"nom", "chemin", "sha256"} ; leve OSError en cas d'echec.
    """
    source = Path(source)
    if not source.exists():
        raise OSError("Fichier introuvable.")
    destination = dossier_depot_serveur() / source.name
    shutil.copy2(source, destination)
    sha = hashlib.sha256(destination.read_bytes()).hexdigest()
    return {"nom": source.name, "chemin": str(destination), "sha256": sha}


def fichier_consigne() -> Path:
    return data_dir() / "mise_a_jour.json"


def lire_consigne() -> dict:
    try:
        return json.loads(fichier_consigne().read_text(encoding="utf-8"))
    except Exception:
        return {}


def ecrire_consigne(version: str, nom_paquet: str = "", obligatoire: bool = False,
                    sha256=None) -> None:
    """Active la consigne de version du serveur central (endpoint /etat).

    `sha256` : dict {"<nom du paquet>": "<empreinte hex>"} utilise par les
    postes pour verifier l'integrite du paquet telecharge depuis le depot.
    """
    consigne = lire_consigne()
    consigne.update({"actif": bool(version), "version": version,
                     "obligatoire": bool(obligatoire)})
    if nom_paquet:
        consigne["paquet_linux"] = nom_paquet
        consigne["paquet_windows"] = nom_paquet
    if sha256:
        consigne["sha256"] = dict(sha256)
    else:
        consigne.pop("sha256", None)
    tmp = fichier_consigne().with_suffix(".json.tmp")
    tmp.write_text(json.dumps(consigne, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    os.replace(tmp, fichier_consigne())


def desactiver_consigne() -> None:
    """Desactive la consigne et purge tout ce qui nombrait encore une version."""
    try:
        fichier_consigne().unlink(missing_ok=True)
    except OSError:
        pass
    ecrire_consigne("", "", obligatoire=False)


# ----------------------------------------------------------------- installation

def _style_script() -> tuple:
    """(fin de ligne, encodage) selon la plateforme des scripts d'install."""
    if os.name == "nt":
        # cmd.exe ne lit pas l'UTF-8 : cp1252 couvre l'ANSI francais courant.
        return "\r\n", "cp1252"
    return "\n", "utf-8"


def _ecrire_script(nom: str, lignes, shell: bool) -> Path:
    dossier = dossier_mises_a_jour()
    chemin = dossier / nom
    fin, encodage = _style_script()
    texte = fin.join(lignes) + fin
    chemin.write_bytes(texte.encode(encodage))
    if shell and os.name != "nt":
        chemin.chmod(0o755)
    return chemin


def _lancer_detache(commande) -> None:
    """Lance un processus d'installation deconnecte de l'application."""
    options = {}
    if os.name == "nt":
        options["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    else:
        options["start_new_session"] = True
    subprocess.Popen(commande, cwd=str(dossier_mises_a_jour()), **options)


def _script_windows_setup(chemin_paquet: str) -> Path:
    """BAT : attend la fermeture de l'app puis lance le Setup en silencieux."""
    lignes = [
        "@echo off",
        "setlocal",
        "title Mise a jour - Gestion Scolaire",
        ":attente",
        'tasklist /FI "IMAGENAME eq gestion-scolaire.exe" 2>NUL '
        '| find /I "gestion-scolaire.exe" >NUL',
        "if errorlevel 1 goto instal",
        "timeout /t 2 /nobreak >NUL",
        "goto attente",
        ":instal",
        f'"{chemin_paquet}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART',
        "exit",
    ]
    return _ecrire_script("maj_setup.bat", lignes, shell=False)


def _script_windows_onefile(chemin_paquet: str, cible: str) -> Path:
    """BAT : attend la fermeture, remplace l'exe et relance l'application."""
    lignes = [
        "@echo off",
        "setlocal",
        "title Mise a jour - Gestion Scolaire",
        ":attente",
        'tasklist /FI "IMAGENAME eq gestion-scolaire.exe" 2>NUL '
        '| find /I "gestion-scolaire.exe" >NUL',
        "if errorlevel 1 goto instal",
        "timeout /t 2 /nobreak >NUL",
        "goto attente",
        ":instal",
        f'copy /Y "{chemin_paquet}" "{cible}" >NUL',
        f'start "" "{cible}"',
        "exit",
    ]
    return _ecrire_script("maj_onefile.bat", lignes, shell=False)


def _script_linux_deb(chemin_paquet: str) -> Path:
    """SH : attend la fermeture de l'app, installe via pkexec, relance."""
    lignes = [
        "#!/bin/sh",
        "# Installation de la mise a jour - Gestion Scolaire",
        "# Attend la fermeture complete de l'application (chemin /opt).",
        'while pgrep -f "/opt/gestion-scolaire/gestion-scolaire" >/dev/null 2>&1; do',
        "    sleep 2",
        "done",
        "# Fenetre d'autorisation systeme (polkit).",
        f'pkexec /usr/bin/dpkg -i "{chemin_paquet}"',
        'if [ -x /opt/gestion-scolaire/gestion-scolaire ]; then',
        "    nohup /opt/gestion-scolaire/gestion-scolaire >/dev/null 2>&1 &",
        "fi",
    ]
    return _ecrire_script("maj.sh", lignes, shell=True)


def remplacer_appimage(chemin_paquet: str) -> None:
    """Remplace atomiquement l'AppImage en cours d'execution (aucun droit).

    La cible est l'archive .AppImage (variable APPIMAGE du runtime) ou, a
    defaut, le binaire en cours d'execution — jamais l'overlay FUSE monté.
    """
    cible = Path(os.environ.get("APPIMAGE") or sys.argv[0]).resolve()
    tmp = cible.with_name(cible.name + ".maj.tmp")
    shutil.copy2(chemin_paquet, tmp)
    os.replace(tmp, cible)
    try:
        os.chmod(cible, 0o755)
    except OSError:
        pass


def installer(chemin_paquet: str, infos: dict):
    """Declenche l'installation. Retourne (action, message).

    action = 'fermer' : l'application doit se fermer, un script detache
                        poursuit l'installation (et eventuellement la relance).
    action = 'fait'   : deja installe (AppImage), actif au prochain demarrage.
    """
    systeme = (sys.platform or "").lower()
    nom = Path(chemin_paquet).name.lower()

    # Coherence paquet / plateforme : ne jamais appliquer le mauvais format.
    if not est_appimage():
        if systeme.startswith("win") and not nom.endswith(".exe"):
            return ("erreur",
                    f"Le paquet {nom!r} n'est pas un fichier Windows (.exe). "
                    "Deposez le paquet Windows sur le depot central.")
        if systeme.startswith("linux") and not (
                nom.endswith(".deb") or nom.endswith(".appimage")):
            return ("erreur",
                    f"Le paquet {nom!r} n'est pas un paquet Linux "
                    "(.deb ou .AppImage). Deposez le bon paquet sur le depot "
                    "central.")

    if est_appimage():
        try:
            remplacer_appimage(chemin_paquet)
        except OSError as exc:
            return ("erreur", f"Impossible de remplacer l'AppImage : {exc}")
        return ("fait",
                "Mise a jour installee. Elle sera active au prochain demarrage.")

    if systeme.startswith("win"):
        if "setup" in nom.lower():
            script = _script_windows_setup(chemin_paquet)
            _lancer_detache([str(script)])
            return ("fermer",
                    "L'application va se fermer pour installer la mise a jour "
                    "(installation silencieuse). Relancez-la depuis son "
                    "raccourci ensuite.")
        cible = os.path.abspath(sys.executable)
        script = _script_windows_onefile(chemin_paquet, cible)
        _lancer_detache([str(script)])
        return ("fermer",
                "L'application va se fermer pour appliquer la mise a jour, "
                "puis se relancera automatiquement.")

    # Linux : paquet .deb
    script = _script_linux_deb(chemin_paquet)
    _lancer_detache(["/bin/sh", str(script)])
    return ("fermer",
            "L'application va se fermer pour installer la mise a jour. "
            "Une autorisation systeme peut etre demandee, puis "
            "l'application se relancera automatiquement.")


def blocage_obligatoire(infos: dict) -> bool:
    """True si une consigne serveur rend la mise a jour obligatoire."""
    return bool(infos and infos.get("source") == "serveur"
                and infos.get("obligatoire"))