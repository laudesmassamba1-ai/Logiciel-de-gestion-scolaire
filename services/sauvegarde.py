"""Sauvegarde automatique des bases de donnees (app + serveur).

Le PC hote est la source de verite : si son disque lache ou si l'ordinateur
est vole, tout est perdu sans copie. Ce module copie regulierement les bases
dans un dossier dedie, avec rotation sur 30 jours, et tient un journal.

Fichiers sauvegardes par copie :
  - la base de l'application (data_dir()/ecole.db) ;
  - la base du serveur integre (data_dir()/serveur/serveur_gs.db, mode
    SQLite « sans installation », WAL).

Restauration : voir la procedure dans docs/SUIVI_PROJET.md (session XXII).
"""

import csv
import sqlite3
import threading
from datetime import date, datetime
from pathlib import Path

_VERROU = threading.Lock()
ROTATION = 30


def _dossier() -> Path:
    from core.config import data_dir
    dossier = data_dir() / "sauvegardes"
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


def sources_db():
    """[(nom, chemin)] pour chaque base presente sur ce poste."""
    from core.config import data_dir
    resultat = []
    base_app = data_dir() / "ecole.db"
    if base_app.exists():
        resultat.append(("ecole", base_app))
    base_serveur = data_dir() / "serveur" / "serveur_gs.db"
    if base_serveur.exists():
        resultat.append(("serveur_gs", base_serveur))
    return resultat


def _copier(chemin: Path, destination: Path) -> bool:
    """Copie consistante d'une base SQLite (API backup, compatible WAL).

    Si l'API ne fonctionne pas (base creee par une autre version), repli sur
    une copie de fichiers (+ -wal/-shm si presents)."""
    try:
        src = sqlite3.connect(str(chemin), timeout=15)
        dst = sqlite3.connect(str(destination), timeout=15)
        try:
            src.backup(dst)
            return True
        finally:
            dst.close()
            src.close()
    except Exception:
        # Repli : copie brute, WAL inclus.
        try:
            import shutil
            shutil.copy2(chemin, destination)
            for suffixe in ("-wal", "-shm"):
                lat = Path(str(chemin) + suffixe)
                if lat.exists():
                    shutil.copy2(lat, Path(str(destination) + suffixe))
            return True
        except OSError:
            return False


def _journaliser(raison, nom, destination: Path, ok: bool):
    ligne = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), raison, nom,
             str(destination.name) if ok else "echec",
             str(destination.stat().st_size) if ok and destination.exists() else "0",
             "ok" if ok else "erreur"]
    try:
        with open(_dossier() / "journal.csv", "a", newline="", encoding="utf-8") as f:
            csv.writer(f, delimiter=";").writerow(ligne)
    except OSError:
        pass


def _rotationner(nom_base: str):
    """Ne garde que les ROTATION sauvegardes les plus recentes par base."""
    try:
        fichiers = sorted(_dossier().glob(f"{nom_base}-*.db"))
    except OSError:
        return
    for trop in fichiers[:-ROTATION]:
        try:
            trop.unlink()
            for suffixe in ("-wal", "-shm"):
                lat = Path(str(trop) + suffixe)
                if lat.exists():
                    lat.unlink()
        except OSError:
            pass


def sauvegarder_maintenant(raison="manuel") -> dict:
    """Copie toutes les bases presentes dans le dossier sauvegardes."""
    with _VERROU:
        enregistres = []
        for nom, chemin in sources_db():
            moment = datetime.now().strftime("%Y%m%d-%H%M%S")
            destination = _dossier() / f"{nom}-{moment}-{raison}.db"
            ok = _copier(chemin, destination)
            _journaliser(raison, nom, destination, ok)
            if ok:
                enregistres.append(str(destination))
                _rotationner(nom)
        return {"fichiers": enregistres, "n": len(enregistres)}


def _une_sauvegarde_aujourdhui() -> bool:
    aujourdhui = date.today().strftime("%Y%m%d")
    try:
        for base, _ in sources_db():
            if not list(_dossier().glob(f"{base}-{aujourdhui}-*")):
                return False
    except OSError:
        return False
    return True


def sauvegarder_si_quotidien():
    """Effectue la sauvegarde quotidienne si elle n'a pas deja eu lieu."""
    if not sources_db() or _une_sauvegarde_aujourdhui():
        return None
    return sauvegarder_maintenant("quotidienne")