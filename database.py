import sqlite3

DB_NAME = "local_database.db"


def get_connection():
    """Retourne une connexion active à la base SQLite local."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def initialiser_base():
    """Crée les tables SQLite locales si elles n'existent pas encore."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Table de file d'attente pour la synchronisation hors-ligne
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_attente_synchro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT NOT NULL,
            methode TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            uuid_client TEXT,
            cree_le TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Table Élèves
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eleve (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            prenom TEXT,
            sexe TEXT,
            date_naissance TEXT,
            lieu_naissance TEXT,
            adresse TEXT,
            nom_parent TEXT,
            numero_parent TEXT,
            redoublant TEXT DEFAULT '0',
            statut TEXT DEFAULT 'actif',
            uuid_client TEXT UNIQUE
        )
    """)

    # 3. Table Enseignants
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS enseignant (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            prenom TEXT,
            sexe TEXT,
            date_naissance TEXT,
            lieu_naissance TEXT,
            adresse TEXT,
            telephone TEXT,
            email TEXT,
            diplome TEXT,
            date_embauche TEXT,
            statut TEXT DEFAULT 'actif'
        )
    """)

    # 4. Table Inscriptions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inscription (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            eleve_id INTEGER,
            classe_id INTEGER,
            annee_scolaire_id INTEGER,
            statut TEXT DEFAULT 'actif',
            uuid_client TEXT UNIQUE
        )
    """)

    # 5. Table Paiements
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paiement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inscription_id INTEGER,
            type_frais TEXT,
            montant REAL,
            mode_paiement TEXT,
            trimestre TEXT,
            mois TEXT,
            date_paiement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uuid_client TEXT UNIQUE
        )
    """)

    # 6. Table Notes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS note (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inscription_id INTEGER,
            matiere_id INTEGER,
            type_evaluation TEXT,
            note REAL,
            note_sur REAL DEFAULT 20,
            date_evaluation TEXT,
            trimestre TEXT,
            uuid_client TEXT UNIQUE
        )
    """)

    # 7. Table Présences
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS presences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            eleve_id INTEGER,
            classe_id INTEGER,
            date_presence TEXT,
            statut TEXT DEFAULT 'Present',
            justifie TEXT DEFAULT 'Non',
            uuid_client TEXT UNIQUE
        )
    """)

    # 8. Tables de configuration (Classe, Cycle, Matiere, Programme, Tarif, Utilisateurs)
    cursor.execute("CREATE TABLE IF NOT EXISTS classe (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, cycle_id INTEGER)")
    cursor.execute("CREATE TABLE IF NOT EXISTS cycle (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS matiere (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, code TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS programme (id INTEGER PRIMARY KEY AUTOINCREMENT, classe_id INTEGER, matiere_id INTEGER, enseignant_id INTEGER, coefficient REAL DEFAULT 1)")
    cursor.execute("CREATE TABLE IF NOT EXISTS annee_scolaire (id INTEGER PRIMARY KEY AUTOINCREMENT, libelle TEXT, date_debut TEXT, date_fin TEXT, statut TEXT DEFAULT 'actif')")
    cursor.execute("CREATE TABLE IF NOT EXISTS tarif_scolarite (id INTEGER PRIMARY KEY AUTOINCREMENT, cycle_id INTEGER, type_frais TEXT, montant REAL, annee_scolaire_id INTEGER)")
    cursor.execute("CREATE TABLE IF NOT EXISTS utilisateurs (id INTEGER PRIMARY KEY AUTOINCREMENT, nom_utilisateur TEXT, mot_de_passe_hash TEXT, role TEXT DEFAULT 'utilisateur')")

    conn.commit()
    conn.close()
    print("[DATABASE] SQLite locale initialisée avec toutes les tables.")


if __name__ == "__main__":
    initialiser_base()