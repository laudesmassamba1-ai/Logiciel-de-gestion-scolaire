import sqlite3
import uuid


DB_NAME = "cache_local.db"


def get_connection():
    connection = sqlite3.connect(DB_NAME)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

# TABLES DE RÉFÉRENCE — miroir LECTURE SEULE (rafraîchies
# depuis MySQL via sync_pull.py, jamais modifiées localement)

TABLES_REFERENCE_SQL = {
    "cycle": """
        CREATE TABLE IF NOT EXISTS cycle (
            id INTEGER PRIMARY KEY,
            nom TEXT NOT NULL
        )
    """,
    "classe": """
        CREATE TABLE IF NOT EXISTS classe (
            id INTEGER PRIMARY KEY,
            nom TEXT NOT NULL,
            cycle_id INTEGER NOT NULL,
            FOREIGN KEY (cycle_id) REFERENCES cycle(id)
        )
    """,
    "matiere": """
        CREATE TABLE IF NOT EXISTS matiere (
            id INTEGER PRIMARY KEY,
            nom TEXT NOT NULL
        )
    """,
    "annee_scolaire": """
        CREATE TABLE IF NOT EXISTS annee_scolaire (
            id INTEGER PRIMARY KEY,
            libelle TEXT NOT NULL,
            date_debut TEXT,
            date_fin TEXT,
            est_active INTEGER DEFAULT 0
        )
    """,
    "enseignant": """
        CREATE TABLE IF NOT EXISTS enseignant (
            id INTEGER PRIMARY KEY,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            sexe TEXT,
            telephone TEXT,
            email TEXT,
            statut TEXT
        )
    """,
    "programme": """
        CREATE TABLE IF NOT EXISTS programme (
            id INTEGER PRIMARY KEY,
            classe_id INTEGER,
            matiere_id INTEGER,
            enseignant_id INTEGER,
            coefficient INTEGER DEFAULT 1
        )
    """,
    "tarif_scolarite": """
        CREATE TABLE IF NOT EXISTS tarif_scolarite (
            id INTEGER PRIMARY KEY,
            classe_id INTEGER,
            annee_scolaire_id INTEGER,
            frais_inscription REAL,
            montant_pension REAL
        )
    """,
    "utilisateur": """
        CREATE TABLE IF NOT EXISTS utilisateur (
            id INTEGER PRIMARY KEY,
            matricule TEXT,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            telephone TEXT,
            email TEXT,
            identifiant TEXT,
            mot_de_passe TEXT DEFAULT '',
            role TEXT,
            statut TEXT,
            updated_at TEXT
        )
    """,
}
# TABLES D'ACTION — celles qui ont un uuid_client côté MySQL.
# id local = AUTOINCREMENT (temporaire, tant que non synchronisé).
# Une fois la synchro faite, sync_pull.py remplace ces lignes
# temporaires par la vraie ligne serveur (même uuid_client).

TABLES_ACTION_SQL = {
    "eleve": """
        CREATE TABLE IF NOT EXISTS eleve (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_serveur INTEGER,
            uuid_client TEXT UNIQUE NOT NULL,
            matricule TEXT UNIQUE NOT NULL,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            sexe TEXT NOT NULL,
            date_naissance TEXT,
            lieu_naissance TEXT,
            adresse TEXT,
            nom_parent TEXT,
            redoublant TEXT NOT NULL DEFAULT '0',
            statut TEXT,
            telephone_parent TEXT,
            est_supprime INTEGER DEFAULT 0
        )
    """,
    "inscription": """
        CREATE TABLE IF NOT EXISTS inscription (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_serveur INTEGER,
            uuid_client TEXT UNIQUE,
            eleve_local_id INTEGER,
            eleve_id_serveur INTEGER,
            classe_id INTEGER NOT NULL,
            annee_scolaire_id INTEGER,
            statut TEXT DEFAULT 'actif',
            FOREIGN KEY (classe_id) REFERENCES classe(id)
        )
    """,
    "note": """
        CREATE TABLE IF NOT EXISTS note (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_serveur INTEGER,
            uuid_client TEXT UNIQUE,
            inscription_id INTEGER NOT NULL,
            matiere_id INTEGER NOT NULL,
            type_evaluation TEXT NOT NULL,
            note REAL NOT NULL,
            note_sur INTEGER DEFAULT 20,
            date_evaluation TEXT,
            trimestre TEXT,
            FOREIGN KEY (matiere_id) REFERENCES matiere(id)
        )
    """,
    "paiement": """
        CREATE TABLE IF NOT EXISTS paiement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_serveur INTEGER,
            uuid_client TEXT UNIQUE,
            inscription_id INTEGER NOT NULL,
            type_frais TEXT NOT NULL,
            montant REAL NOT NULL,
            date_paiement TEXT,
            mode_paiement TEXT,
            trimestre TEXT,
            mois TEXT
        )
    """,
    "presences": """
        CREATE TABLE IF NOT EXISTS presences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_serveur INTEGER,
            uuid_client TEXT UNIQUE,
            eleve_id_serveur INTEGER,
            classe_id INTEGER NOT NULL,
            date_presence TEXT,
            statut TEXT NOT NULL,
            justifie TEXT DEFAULT 'Non',
            FOREIGN KEY (classe_id) REFERENCES classe(id)
        )
    """,
}

FILE_ATTENTE_SQL = """
    CREATE TABLE IF NOT EXISTS file_attente_synchro (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        endpoint TEXT NOT NULL,
        methode TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        uuid_client TEXT
    )
"""


def init_database():
    connection = get_connection()
    cursor = connection.cursor()

    for sql in TABLES_REFERENCE_SQL.values():
        cursor.execute(sql)
    for sql in TABLES_ACTION_SQL.values():
        cursor.execute(sql)
    cursor.execute(FILE_ATTENTE_SQL)

    connection.commit()
    connection.close()
    print("Base de données locale initialisée avec succès (13 tables + file d'attente).")


initialiser_base = init_database

NOMS_TABLES_REFERENCE = list(TABLES_REFERENCE_SQL.keys())
NOMS_TABLES_ACTION = list(TABLES_ACTION_SQL.keys())

# DONNÉES DE RÉFÉRENCE PAR DÉFAUT — juste pour pouvoir tester
# hors ligne avant la toute première synchro. Le pull (sync_pull.py)
# écrasera ces valeurs avec les vraies données serveur dès que
# possible (INSERT OR REPLACE), donc aucun risque de conflit.

def charger_donnees_par_defaut():
    connection = get_connection()
    cursor = connection.cursor()

    cycles = [(1, "prescolaire"), (2, "primaire"), (3, "college"), (4, "lycee")]
    cursor.executemany("INSERT OR IGNORE INTO cycle (id, nom) VALUES (?, ?)", cycles)

    classes = [
        (1, "P1", 1), (2, "P2", 1), (3, "P3", 1),
        (4, "CP1", 2), (5, "CP2", 2), (6, "CE1", 2), (7, "CE2", 2),
        (8, "CM1", 2), (9, "CM2", 2),
        (10, "6E", 3), (11, "5E", 3), (12, "4E", 3), (13, "3E", 3),
        (14, "SECOND TROIS COMMUNS", 4), (15, "PREMIERE TROIS COMMUNS", 4),
        (16, "TERMINALE TROIS COMMUNS", 4),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO classe (id, nom, cycle_id) VALUES (?, ?, ?)", classes
    )

    connection.commit()
    connection.close()
    print("Données de référence par défaut chargées (cycles + classes).")

# ÉCRITURE LOCALE IMMÉDIATE — pour que l'interface affiche
# tout de suite ce qui vient d'être créé hors ligne, sans
# attendre la synchro.

def enregistrer_eleve_local(uuid_client, eleve_dict, classe_id, annee_scolaire_id=None):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO eleve (
            uuid_client, matricule, nom, prenom, sexe, date_naissance,
            lieu_naissance, adresse, nom_parent, redoublant, statut,
            telephone_parent
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        uuid_client,
        eleve_dict.get("matricule"),
        eleve_dict.get("nom"),
        eleve_dict.get("prenom"),
        eleve_dict.get("sexe"),
        eleve_dict.get("date_naissance"),
        eleve_dict.get("lieu_naissance"),
        eleve_dict.get("adresse"),
        eleve_dict.get("nom_parent"),
        eleve_dict.get("redoublant", "0"),
        eleve_dict.get("statut"),
        eleve_dict.get("telephone_parent"),
    ))
    eleve_local_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO inscription (
            uuid_client, eleve_local_id, classe_id, annee_scolaire_id, statut
        ) VALUES (?, ?, ?, ?, 'actif')
    """, (uuid_client, eleve_local_id, classe_id, annee_scolaire_id))

    connection.commit()
    connection.close()

# UPSERT GÉNÉRIQUE — utilisé par sync_pull.py pour rafraîchir
# le cache local à partir des données reçues de MySQL.

def upsert_reference(nom_table, colonnes, lignes):
    """
    lignes : liste de tuples, dans l'ordre exact de `colonnes`.
    La 1ère colonne doit toujours être `id`.
    """
    if not lignes:
        return

    connection = get_connection()
    cursor = connection.cursor()

    placeholders = ", ".join(["?"] * len(colonnes))
    colonnes_str = ", ".join(colonnes)

    cursor.executemany(
        f"INSERT OR REPLACE INTO {nom_table} ({colonnes_str}) VALUES ({placeholders})",
        lignes,
    )

    connection.commit()
    connection.close()


def remplacer_temp_par_serveur(nom_table, uuid_client, id_serveur):
    """
    Une fois qu'une ligne créée hors ligne (id local temporaire)
    est confirmée par le serveur, on met à jour la ligne locale
    avec son véritable id_serveur via son uuid_client.
    """
    if not uuid_client or not id_serveur:
        return
    
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"UPDATE {nom_table} SET id_serveur = ? WHERE uuid_client = ? AND (id_serveur IS NULL OR id_serveur = '')",
            (id_serveur, uuid_client),
        )
        connection.commit()
    except Exception as e:
        print(f"[DB ERROR] Échec du remappage pour {nom_table} (uuid: {uuid_client}) : {e}")
    finally:
        connection.close()


def upsert_action_row(nom_table, id_serveur, uuid_client, colonnes_valeurs):
    """
    Upsert complet pour une table d'action, à partir d'une ligne
    venant du serveur MySQL. Gère 3 cas :
      1. La ligne existe déjà en local avec ce id_serveur -> on met à jour
      2. La ligne existe en local en tant que ligne TEMPORAIRE (créée hors
         ligne, retrouvée par son uuid_client) -> on la complète avec le
         vrai id_serveur
      3. La ligne n'existe pas du tout en local (créée directement côté
         serveur, ou par un autre poste client) -> on l'insère pour de vrai

    uuid_client peut être None (ligne créée hors du mécanisme de synchro,
    par exemple directement dans Workbench) : on génère alors un
    identifiant technique interne pour respecter la contrainte UNIQUE.
    """
    if uuid_client is None:
        uuid_client = f"SERVEUR-{nom_table}-{id_serveur}"

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(f"SELECT id FROM {nom_table} WHERE id_serveur = ?", (id_serveur,))
    ligne = cursor.fetchone()

    if ligne is None:
        cursor.execute(f"SELECT id FROM {nom_table} WHERE uuid_client = ?", (uuid_client,))
        ligne = cursor.fetchone()

    colonnes = list(colonnes_valeurs.keys())
    valeurs = list(colonnes_valeurs.values())

    if ligne:
        set_clause = ", ".join(f"{c} = ?" for c in colonnes)
        cursor.execute(
            f"UPDATE {nom_table} SET {set_clause}, id_serveur = ?, uuid_client = ? WHERE id = ?",
            (*valeurs, id_serveur, uuid_client, ligne[0]),
        )
    else:
        toutes_colonnes = colonnes + ["id_serveur", "uuid_client"]
        toutes_valeurs = valeurs + [id_serveur, uuid_client]
        placeholders = ", ".join(["?"] * len(toutes_colonnes))
        cursor.execute(
            f"INSERT INTO {nom_table} ({', '.join(toutes_colonnes)}) VALUES ({placeholders})",
            toutes_valeurs,
        )

    connection.commit()
    connection.close()


if __name__ == "__main__":
    init_database()
    charger_donnees_par_defaut()
    print("Tables de référence :", NOMS_TABLES_REFERENCE)
    print("Tables d'action :", NOMS_TABLES_ACTION)