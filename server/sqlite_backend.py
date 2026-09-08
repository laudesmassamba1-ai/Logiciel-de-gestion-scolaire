"""Backend SQLite pour le serveur GS (mode "sans installation").

Le serveur d'origine parle a MySQL via mysql.connector (curseur
"dictionnaire", placeholders %s). Ce module fournit la MEME interface
sur un simple fichier SQLite : aucune installation, aucun droit
administrateur, ideal pour une ecole sur un seul poste ou un petit
reseau local.

Active avec GS_DB_MODE=sqlite (c'est ce que fait l'assistant graphique).
"""

import os
import sqlite3
import threading
from pathlib import Path

from fastapi import HTTPException

_SCHEMA_APPLIQUE = False
_VERROU = threading.RLock()


def chemin_base() -> Path:
    """Emplacement du fichier de base, stable et multi-plateforme.

    - GS_SQLITE_DIR : prioritaire (l'assistant graphique le definit).
    - Sinon dossier donnees de l'utilisateur :
        Windows  -> %APPDATA%\\GestionScolaire\\serveur
        Linux/Mac-> ~/.local/share/gestion-scolaire/serveur
    """
    perso = os.environ.get("GS_SQLITE_DIR")
    if perso:
        dossier = Path(perso)
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home()))) / "GestionScolaire"
        dossier = base / "serveur"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
        dossier = base / "gestion-scolaire" / "serveur"
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier / "serveur_gs.db"


def _appliquer_schema(conn):
    global _SCHEMA_APPLIQUE
    if _SCHEMA_APPLIQUE:
        return
    schema = Path(__file__).resolve().parent / "schema_sqlite.sql"
    conn.executescript(schema.read_text(encoding="utf-8"))
    conn.commit()
    _SCHEMA_APPLIQUE = True


class _CurseurSQLite:
    """Imite un curseur mysql.connector.

    - defaut : lignes sqlite3.Row -> accessibles par index (ligne[0])
      comme par nom (ligne["nom"]), comme les tuples MySQL du code
      original ET de la couche compat.
    - dictionary=True : lignes en dictionnaires (compatibilite).
    """

    def __init__(self, conn):
        self._conn = conn
        self._cur = None
        self._dictionnaire = False
        self.rowcount = 0
        self.lastrowid = None

    @property
    def description(self):
        return self._cur.description if self._cur is not None else None

    def execute(self, sql, params=None):
        # NOTE perf : le verrou global est assume. SQLite n'admet qu'un
        # seul redacteur ; un verrou par table n'apporterait rien et le
        # mode mono-poste LAN du serveur reste tres en deca des limites.
        with _VERROU:
            # Les routes compat sont ecrites en dialecte MySQL (%s).
            self._cur = self._conn.cursor()
            self._cur.execute(sql.replace("%s", "?"), params or ())
            self.rowcount = self._cur.rowcount
            self.lastrowid = self._cur.lastrowid
        return self

    def executemany(self, sql, seq):
        with _VERROU:
            self._cur = self._conn.cursor()
            self._cur.executemany(sql.replace("%s", "?"), seq)
            self.rowcount = self._cur.rowcount
        return self

    def _lignes(self):
        if self._cur is None or self._cur.description is None:
            return []
        if self._dictionnaire:
            colonnes = [d[0] for d in self._cur.description]
            return [dict(zip(colonnes, ligne)) for ligne in self._cur.fetchall()]
        return self._cur.fetchall()

    def fetchone(self):
        lignes = self._lignes()
        return lignes[0] if lignes else None

    def fetchall(self):
        return self._lignes()

    def close(self):
        if self._cur is not None:
            self._cur.close()
            self._cur = None


class ConnexionSQLite:
    """Imite la connexion mysql.connector utilisee par compat/main."""

    def __init__(self):
        self._conn = sqlite3.connect(
            str(chemin_base()),
            timeout=15,
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA busy_timeout = 15000")
        _appliquer_schema(self._conn)

    def cursor(self, *args, **kwargs):
        curseur = _CurseurSQLite(self._conn)
        curseur._dictionnaire = bool(kwargs.get("dictionary"))
        return curseur

    def commit(self):
        with _VERROU:
            self._conn.commit()

    def rollback(self):
        with _VERROU:
            self._conn.rollback()

    def close(self):
        with _VERROU:
            try:
                self._conn.commit()
            except Exception:
                pass
            self._conn.close()


def connexion_sqlite():
    """Point d'entree : remplace compat.connexion en mode sqlite."""
    try:
        return ConnexionSQLite()
    except Exception as exc:
        raise HTTPException(status_code=500,
                            detail=f"Base SQLite indisponible : {exc}")
