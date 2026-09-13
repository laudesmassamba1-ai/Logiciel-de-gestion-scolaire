import datetime
import hashlib
import hmac
import os
import sqlite3
from contextlib import contextmanager

from core.config import DB_PATH, DEFAULT_MATIERES, DOCS_DIR, VILLE_DEFAUT, PAYS_DEFAUT


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
    titulaire TEXT,
    cycle_id  INTEGER,
    FOREIGN KEY (cycle_id) REFERENCES cycles (id)
);

CREATE TABLE IF NOT EXISTS matieres (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT NOT NULL UNIQUE,
    coefficient REAL NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS cycles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS annees_scolaires (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    libelle    TEXT NOT NULL,
    date_debut TEXT,
    date_fin   TEXT,
    est_active INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tarifs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    classe_id     INTEGER,
    type_frais    TEXT NOT NULL,
    montant       REAL NOT NULL DEFAULT 0,
    annee_scolaire TEXT,
    FOREIGN KEY (classe_id) REFERENCES classes (id)
);

CREATE TABLE IF NOT EXISTS paiements (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    inscription_id INTEGER,
    eleve_id       INTEGER NOT NULL,
    montant        REAL NOT NULL DEFAULT 0,
    mode_reglement TEXT,
    type_frais     TEXT,
    date_paiement  TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    annee_scolaire TEXT,
    trimestre      TEXT,
    FOREIGN KEY (eleve_id) REFERENCES eleves (id)
);

CREATE TABLE IF NOT EXISTS programmes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    classe_id     INTEGER NOT NULL,
    matiere_id    INTEGER NOT NULL,
    enseignant_id INTEGER,
    coefficient   REAL NOT NULL DEFAULT 1,
    UNIQUE (classe_id, matiere_id),
    FOREIGN KEY (classe_id) REFERENCES classes (id),
    FOREIGN KEY (matiere_id) REFERENCES matieres (id)
);

CREATE TABLE IF NOT EXISTS presences (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    eleve_id   INTEGER NOT NULL,
    classe_id  INTEGER,
    date       TEXT NOT NULL,
    statut     TEXT NOT NULL DEFAULT 'Present',
    motif      TEXT,
    UNIQUE (eleve_id, date),
    FOREIGN KEY (eleve_id) REFERENCES eleves (id)
);

CREATE TABLE IF NOT EXISTS eleves (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid_client        TEXT UNIQUE,
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
    redoublant         INTEGER NOT NULL DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS file_attente_synchro (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint     TEXT NOT NULL,
    method       TEXT NOT NULL,
    payload      TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    status       TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'FAILED')),
    uuid_client  TEXT
);

CREATE TABLE IF NOT EXISTS ia_memoire (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    type       TEXT NOT NULL DEFAULT 'qa' CHECK (type IN ('qa', 'fait')),
    question   TEXT NOT NULL,
    reponse    TEXT NOT NULL,
    usage      INTEGER NOT NULL DEFAULT 0,
    appris_le  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_ia_memoire_question ON ia_memoire (question);
"""


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return salt.hex() + ":" + h.hex()


def verify_password(password: str, stored: str) -> bool:
    if ":" in stored:
        salt_hex, h_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(h.hex(), h_hex)
    return hmac.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), stored)

class Database:

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
        conn = sqlite3.connect(str(DB_PATH), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn


    def init_db(self):
        if self._initialized:
            return
        conn = self.connect()
        try:
            conn.executescript(SCHEMA)
            self._migrate(conn)
            self._seed(conn)
            conn.commit()
        finally:
            conn.close()
        self._initialized = True


    def _migrate(self, conn):
        cols = [r[1] for r in conn.execute("PRAGMA table_info(classes)")]
        if "cycle_id" not in cols:
            conn.execute("ALTER TABLE classes ADD COLUMN cycle_id INTEGER")

        eleve_cols = [r[1] for r in conn.execute("PRAGMA table_info(eleves)")]
        if "uuid_client" not in eleve_cols:
            conn.execute("ALTER TABLE eleves ADD COLUMN uuid_client TEXT")
        if "redoublant" not in eleve_cols:
            conn.execute("ALTER TABLE eleves ADD COLUMN redoublant INTEGER NOT NULL DEFAULT 0")

        queue_cols = [r[1] for r in conn.execute("PRAGMA table_info(file_attente_synchro)")]
        if "uuid_client" not in queue_cols:
            conn.execute("ALTER TABLE file_attente_synchro ADD COLUMN uuid_client TEXT")

        # Chaque ecriture de caisse est rattachee a l'annee scolaire active :
        # indispensable a la coherence comptable quand l'annee change.
        trans_cols = [r[1] for r in conn.execute("PRAGMA table_info(transactions)")]
        if "annee_scolaire" not in trans_cols:
            conn.execute("ALTER TABLE transactions ADD COLUMN annee_scolaire TEXT")

        # Chaque paiement d'eleve cree desormais une ecriture de caisse
        # (type 'entree') liee par paiement_id. La Caisse ne lit que la table
        # transactions : sans ce rattachement, un encaissement enregistre
        # dans Paiements n'apparait jamais en Caisse. Cette migration cree
        # a posteriori les ecritures manquantes pour les paiements deja
        # enregistres (idempotente : rien si l'ecriture existe deja).
        if "paiement_id" not in trans_cols:
            conn.execute("ALTER TABLE transactions ADD COLUMN paiement_id INTEGER")
            conn.execute(
                """INSERT INTO transactions
                       (date, reference, beneficiaire, motif, categorie, montant,
                        type, mode_reglement, annee_scolaire, paiement_id)
                   SELECT COALESCE(p.date_paiement, date('now', 'localtime')),
                          'REC-' || upper(hex(randomblob(4))),
                          TRIM(e.prenom || ' ' || e.nom),
                          COALESCE(p.type_frais, 'Paiement'),
                          COALESCE(p.type_frais, 'Autres'),
                          p.montant,
                          'entree',
                          p.mode_reglement,
                          p.annee_scolaire,
                          p.id
                     FROM paiements p
                     JOIN eleves e ON e.id = p.eleve_id
                     WHERE NOT EXISTS (
                         SELECT 1 FROM transactions t WHERE t.paiement_id = p.id)""")


    def _seed(self, conn):
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
        conn.execute(
            "INSERT OR IGNORE INTO parametres (cle, valeur) VALUES (?, ?)",
            ("dernier_utilisateur_id", ""))

        if conn.execute("SELECT COUNT(*) FROM annees_scolaires").fetchone()[0] == 0:
            year = datetime.date.today().year
            conn.execute(
                """INSERT INTO annees_scolaires (libelle, date_debut, date_fin, est_active)
                   VALUES (?, ?, ?, 1)""",
                (f"{year}-{year + 1}", f"{year}-09-01", f"{year + 1}-06-30"))

        def _cycle_id(nom, description):
            row = conn.execute("SELECT id FROM cycles WHERE nom = ?", (nom,)).fetchone()
            if row:
                return row[0]
            conn.execute("INSERT INTO cycles (nom, description) VALUES (?, ?)",
                         (nom, description))
            return conn.execute("SELECT id FROM cycles WHERE nom = ?", (nom,)).fetchone()[0]

        for nom, description in [("Prescolaire", "Cycle Prescolaire"),
                                  ("Primaire", "Cycle Primaire"),
                                  ("College", "Cycle College"),
                                  ("Lycee", "Cycle Lycee")]:
            _cycle_id(nom, description)

        if conn.execute("SELECT COUNT(*) FROM classes").fetchone()[0] == 0:
            cycle_ids = {}
            for nom in ("Prescolaire", "Primaire", "College", "Lycee"):
                row = conn.execute("SELECT id FROM cycles WHERE nom = ?", (nom,)).fetchone()
                if row:
                    cycle_ids[nom] = row[0]
            classes_def = [
                ("P1", "Prescolaire"), ("P2", "Prescolaire"), ("P3", "Prescolaire"),
                ("CP1", "Primaire"), ("CP2", "Primaire"),
                ("CE1", "Primaire"), ("CE2", "Primaire"),
                ("CM1", "Primaire"), ("CM2", "Primaire"),
                ("6eme", "College"), ("5eme", "College"),
                ("4eme", "College"), ("3eme", "College"),
                ("2nde", "Lycee"), ("1ere", "Lycee"), ("Terminale", "Lycee"),
            ]
            for nom_classe, cycle_nom in classes_def:
                cid = cycle_ids.get(cycle_nom)
                conn.execute(
                    "INSERT INTO classes (nom, cycle_id) VALUES (?, ?)",
                    (nom_classe, cid))


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


    @contextmanager
    def transaction(self):
        """Contexte transactionnel : commit si tout reussit, rollback sinon.

        with db.transaction() as t:
            t.execute("DELETE ...")
            t.execute("INSERT ...")
        """
        conn = self.connect()

        class _Txn:
            def execute(self_, sql, params=()):
                return conn.execute(sql, params)

            def close(self_):
                pass

        txn = _Txn()
        try:
            yield txn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


    def enqueue(self, method, endpoint, payload, uuid_client=None):
        # Dédoublonnage : un double-clic ou une revalidation ne doit pas
        # empiler deux fois la meme operation en attente.
        existe = self.query_one(
            """SELECT id FROM file_attente_synchro
               WHERE status = 'PENDING' AND method = ? AND endpoint = ?
                 AND payload = ?""",
            (method, endpoint, payload))
        if existe:
            return existe["id"]
        return self.execute(
            """INSERT INTO file_attente_synchro (endpoint, method, payload, status, uuid_client)
               VALUES (?, ?, ?, 'PENDING', ?)""",
            (endpoint, method, payload, uuid_client))


    def dequeue_pending(self, limit=50):
        # PENDING *et* FAILED : un echec temporaire (serveur injoignable le
        # temps de la resolution, reference pas encore arrivee) est rejoue
        # au cycle suivant, sans jamais rester bloque silencieusement.
        return self.query(
            """SELECT * FROM file_attente_synchro
               WHERE status IN ('PENDING', 'FAILED')
               ORDER BY id LIMIT ?""", (limit,))


    def mark_queue_done(self, queue_id):
        self.execute("DELETE FROM file_attente_synchro WHERE id = ?", (queue_id,))


    def mark_queue_failed(self, queue_id):
        self.execute(
            "UPDATE file_attente_synchro SET status = 'FAILED' WHERE id = ?",
            (queue_id,))
