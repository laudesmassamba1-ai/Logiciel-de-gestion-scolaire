import sqlite3
import uuid


DB_NAME = "cache_local.db"


# ============================================================
# CONNEXION À LA BASE
# ============================================================

def get_connection():
    connection = sqlite3.connect(DB_NAME)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# ============================================================
# INITIALISATION DE LA BASE
# ============================================================

def init_database():

    connection = get_connection()
    cursor = connection.cursor()

    # ========================================================
    # DONNÉES DE RÉFÉRENCE (en lecture seule, synchronisées
    # depuis le serveur — pas concernées par la file d'attente)
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cycle (
            id INTEGER PRIMARY KEY,
            nom TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classe (
            id INTEGER PRIMARY KEY,
            nom TEXT NOT NULL,
            cycle_id INTEGER NOT NULL,
            FOREIGN KEY (cycle_id) REFERENCES cycle(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matiere (
            id INTEGER PRIMARY KEY,
            nom TEXT NOT NULL
        )
    """)

    # ========================================================
    # ELEVE — cache local, aligné sur les champs de l'API
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eleve (
            id INTEGER PRIMARY KEY,
            uuid_client TEXT UNIQUE NOT NULL,
            matricule TEXT NOT NULL,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            sexe TEXT NOT NULL,
            date_naissance TEXT,
            lieu_naissance TEXT,
            adresse TEXT,
            nom_parent TEXT,
            redoublant TEXT NOT NULL DEFAULT '0',
            statut TEXT,
            classe_id INTEGER NOT NULL,
            telephone_parent TEXT,
            inscription_id INTEGER,
            FOREIGN KEY (classe_id) REFERENCES classe(id)
        )
    """)

    # ========================================================
    # FILE D'ATTENTE DE SYNCHRONISATION (générique — sert à
    # TOUTES les opérations : élève, paiement, note, présence...)
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_attente_synchro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT NOT NULL,
            methode TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uuid_client TEXT
        )
    """)

    connection.commit()
    connection.close()

    print("Base de données locale initialisée avec succès.")


# Alias pour compatibilité avec le code existant qui appelle "initialiser_base"
initialiser_base = init_database


# ============================================================
# DONNÉES DE RÉFÉRENCE PAR DÉFAUT (cycles et classes)
# À charger une fois, ou à recevoir du serveur plus tard
# ============================================================

def insert_cycles():
    connection = get_connection()
    cursor = connection.cursor()
    cycles = [
        (1, "prescolaire"), (2, "primaire"), (3, "college"), (4, "lycee"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO cycle (id, nom) VALUES (?, ?)", cycles
    )
    connection.commit()
    connection.close()
    print("Données des cycles chargées.")


def insert_classes():
    connection = get_connection()
    cursor = connection.cursor()
    classes = [
        (1, "P1", 1), (2, "P2", 1), (3, "P3", 1),
        (4, "CP1", 2), (5, "CP2", 2), (6, "CE1", 2), (7, "CE2", 2),
        (8, "CM1", 2), (9, "CM2", 2),
        (10, "6E", 3), (11, "5E", 3), (12, "4E", 3), (13, "3E", 3),
        (14, "SECOND TROIS COMMUNS", 4), (15, "PREMIERE TROIS COMMUNS", 4),
        (16, "TERMINALE TROIS COMMUNS", 4),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO classe (id, nom, cycle_id) VALUES (?, ?, ?)",
        classes,
    )
    connection.commit()
    connection.close()
    print("Données des classes chargées.")


# ============================================================
# ENREGISTRER UN ÉLÈVE DANS LE CACHE LOCAL
# (appelé juste après l'avoir mis en file d'attente, pour que
# l'interface puisse l'afficher tout de suite, sans attendre
# la synchro)
# ============================================================

def enregistrer_eleve_local(uuid_client, eleve_dict, inscription_id=None):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO eleve (
            uuid_client, matricule, nom, prenom, sexe, date_naissance,
            lieu_naissance, adresse, nom_parent, redoublant, statut,
            classe_id, telephone_parent, inscription_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        eleve_dict.get("classe_id"),
        eleve_dict.get("telephone_parent"),
        inscription_id,
    ))

    connection.commit()
    connection.close()


if __name__ == "__main__":
    init_database()
    insert_cycles()
    insert_classes()
    print("Initialisation terminée.")