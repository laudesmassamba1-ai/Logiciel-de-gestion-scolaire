"""Connexion SQLite, schema et donnees initiales."""
import hashlib
import sqlite3

from config import DB_PATH, DEFAULT_ACCOUNTS, DEFAULT_MATIERES, DOCS_DIR, VILLE_DEFAUT, PAYS_DEFAUT

SCHEMA = """
CREATE TABLE IF NOT EXISTS utilisateurs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_complet TEXT NOT NULL,
    username    TEXT NOT NULL UNIQUE,
    email       TEXT,
    telephone   TEXT,
    password    TEXT NOT NULL,
    role        TEXT NOT NULL,
    actif       INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    last_login  TEXT
);

CREATE TABLE IF NOT EXISTS classes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nom       TEXT NOT NULL,
    niveau    TEXT,
    capacite  INTEGER NOT NULL DEFAULT 50,
    salle     TEXT,
    titulaire TEXT
);

CREATE TABLE IF NOT EXISTS matieres (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT NOT NULL UNIQUE,
    coefficient REAL NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS eleves (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    matricule          TEXT NOT NULL UNIQUE,
    nom                TEXT NOT NULL,
    prenom             TEXT NOT NULL,
    sexe               TEXT,
    date_naissance     TEXT,
    lieu_naissance     TEXT,
    classe_id          INTEGER,
    ecole_provenance   TEXT,
    pere_nom           TEXT,
    pere_tel           TEXT,
    mere_nom           TEXT,
    mere_tel           TEXT,
    tuteur_nom         TEXT,
    tuteur_tel         TEXT,
    adresse            TEXT,
    check_acte         INTEGER NOT NULL DEFAULT 0,
    check_photos       INTEGER NOT NULL DEFAULT 0,
    check_bulletin     INTEGER NOT NULL DEFAULT 0,
    statut             TEXT NOT NULL DEFAULT 'Inscrit',
    date_inscription   TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    FOREIGN KEY (classe_id) REFERENCES classes (id)
);

CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    eleve_id    INTEGER NOT NULL,
    matiere_id  INTEGER NOT NULL,
    periode     TEXT NOT NULL,
    devoir1     REAL,
    devoir2     REAL,
    composition REAL,
    UNIQUE (eleve_id, matiere_id, periode),
    FOREIGN KEY (eleve_id) REFERENCES eleves (id),
    FOREIGN KEY (matiere_id) REFERENCES matieres (id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    date           TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    reference      TEXT NOT NULL,
    beneficiaire   TEXT,
    motif          TEXT,
    categorie      TEXT,
    montant        REAL NOT NULL,
    type           TEXT NOT NULL CHECK (type IN ('entree', 'sortie')),
    mode_reglement TEXT
);

CREATE TABLE IF NOT EXISTS planning (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    classe_id  INTEGER NOT NULL,
    jour       TEXT NOT NULL,
    creneau    TEXT NOT NULL,
    matiere    TEXT,
    salle      TEXT,
    UNIQUE (classe_id, jour, creneau),
    FOREIGN KEY (classe_id) REFERENCES classes (id)
);

CREATE TABLE IF NOT EXISTS connexions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    utilisateur_id INTEGER NOT NULL,
    date_connexion TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs (id)
);

CREATE TABLE IF NOT EXISTS personnel (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_complet TEXT NOT NULL,
    fonction   TEXT,
    telephone  TEXT,
    email      TEXT,
    salaire    REAL NOT NULL DEFAULT 0,
    statut     TEXT NOT NULL DEFAULT 'Contrat'
);

CREATE TABLE IF NOT EXISTS parametres (
    cle   TEXT PRIMARY KEY,
    valeur TEXT
);
"""


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class Database:
    """Wrapper SQLite : connection unique et initialisation au premier acces."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        self._initialized = False

    def connect(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self):
        if self._initialized:
            return
        conn = self.connect()
        try:
            conn.executescript(SCHEMA)
            self._seed(conn)
            conn.commit()
        finally:
            conn.close()
        self._initialized = True

    def _seed(self, conn):
        cur = conn.execute("SELECT COUNT(*) FROM utilisateurs")
        if cur.fetchone()[0] == 0:
            for acc in DEFAULT_ACCOUNTS:
                conn.execute(
                    """INSERT INTO utilisateurs
                       (nom_complet, username, email, telephone, password, role, actif)
                       VALUES (?, ?, ?, ?, ?, ?, 1)""",
                    (acc["nom_complet"], acc["username"], acc["email"],
                     acc["telephone"], hash_password(acc["password"]), acc["role"]),
                )

        for nom in DEFAULT_MATIERES:
            conn.execute(
                "INSERT OR IGNORE INTO matieres (nom) VALUES (?)", (nom,))

        conn.execute(
            "INSERT OR IGNORE INTO parametres (cle, valeur) VALUES (?, ?)",
            ("signataire_nom", ""))
        conn.execute(
            "INSERT OR IGNORE INTO parametres (cle, valeur) VALUES (?, ?)",
            ("signataire_titre", ""))
        conn.execute(
            "INSERT OR IGNORE INTO parametres (cle, valeur) VALUES (?, ?)",
            ("ville", VILLE_DEFAUT))
        conn.execute(
            "INSERT OR IGNORE INTO parametres (cle, valeur) VALUES (?, ?)",
            ("pays", PAYS_DEFAUT))
        conn.execute(
            "INSERT OR IGNORE INTO parametres (cle, valeur) VALUES (?, ?)",
            ("frais_scolarite", "25000"))

        if conn.execute("SELECT COUNT(*) FROM personnel").fetchone()[0] == 0:
            conn.executemany(
                """INSERT INTO personnel (nom_complet, fonction, telephone, email, salaire, statut)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    ("M. Jean Makosso", "Enseignant Francais", "+242 06 521 3344", "j.makosso@ecole.cg", 150000, "Contrat"),
                    ("Mme Clarisse Ngoma", "Enseignante Mathematiques", "+242 05 447 5566", "c.ngoma@ecole.cg", 160000, "Contrat"),
                    ("M. Aristide Moukala", "Comptable", "+242 06 778 8899", "a.moukala@ecole.cg", 120000, "CDI"),
                ),
            )

    # --- helpers d'execution ---
    def query(self, sql, params=()):
        conn = self.connect()
        try:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def query_one(self, sql, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql, params=()):
        conn = self.connect()
        try:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def executemany(self, sql, seq_params):
        conn = self.connect()
        try:
            conn.executemany(sql, seq_params)
            conn.commit()
        finally:
            conn.close()
