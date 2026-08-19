import sqlite3
import uuid


DB_NAME = "cache_local.db"


# ============================================================
# CONNEXION À LA BASE
# ============================================================

def get_connection():
    connection = sqlite3.connect(DB_NAME)

    # Activation des clés étrangères SQLite
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# ============================================================
# INITIALISATION DE LA BASE
# ============================================================

def init_database():

    connection = get_connection()
    cursor = connection.cursor()

    # ========================================================
    # TABLE CYCLE
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cycle (
            id INTEGER PRIMARY KEY,
            nom TEXT NOT NULL
        )
    """)

    # ========================================================
    # TABLE CLASSE
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classe (
            id INTEGER PRIMARY KEY,
            nom TEXT NOT NULL,
            cycle_id INTEGER NOT NULL,
            FOREIGN KEY (cycle_id) REFERENCES cycle(id)
        )
    """)

    # ========================================================
    # TABLE ELEVE
    # ========================================================
    #
    # Structure alignée sur l'API de ton collègue.
    #
    # API :
    # matricule
    # nom
    # prenom
    # sexe
    # date_naissance
    # lieu_naissance
    # adresse
    # nom_parent
    # redoublant
    # statut
    # classe_id
    # telephone_parent
    #
    # + uuid_client pour la synchronisation offline.
    #

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
            FOREIGN KEY (classe_id) REFERENCES classe(id)
        )
    """)

    # ========================================================
    # TABLE FILE D'ATTENTE DE SYNCHRONISATION
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

    # ========================================================
    # MIGRATION DE L'ANCIENNE TABLE ELEVE
    # ========================================================
    #
    # Si l'ancienne table eleve existe avec :
    # quartier
    # ancien_eleve
    # parent_situation
    #
    # on effectue une migration vers la nouvelle structure.
    #

    cursor.execute("PRAGMA table_info(eleve)")
    colonnes_eleve = [colonne[1] for colonne in cursor.fetchall()]

    ancienne_structure = (
        "quartier" in colonnes_eleve
        or "ancien_eleve" in colonnes_eleve
    )

    if ancienne_structure:

        print("Ancienne structure eleve détectée.")
        print("Migration vers la nouvelle structure...")

        # Nouvelle table temporaire
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS eleve_nouveau (
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
                FOREIGN KEY (classe_id) REFERENCES classe(id)
            )
        """)

        # Récupération des anciennes données
        cursor.execute("""
            SELECT
                id,
                nom,
                prenom,
                sexe,
                date_naissance,
                lieu_naissance,
                quartier,
                nom_parent,
                statut,
                classe_id,
                telephone_parent,
                ancien_eleve
            FROM eleve
        """)

        anciens_eleves = cursor.fetchall()

        for eleve in anciens_eleves:

            (
                ancien_id,
                nom,
                prenom,
                sexe,
                date_naissance,
                lieu_naissance,
                quartier,
                nom_parent,
                statut,
                classe_id,
                telephone_parent,
                ancien_eleve
            ) = eleve

            # UUID unique pour la synchronisation
            nouvel_uuid = str(uuid.uuid4())

            # Matricule temporaire pour les anciens élèves
            matricule = f"LOCAL-{ancien_id}"

            # Conversion ancien_eleve -> redoublant
            redoublant = "1" if ancien_eleve == 1 else "0"

            cursor.execute("""
                INSERT OR IGNORE INTO eleve_nouveau (
                    id,
                    uuid_client,
                    matricule,
                    nom,
                    prenom,
                    sexe,
                    date_naissance,
                    lieu_naissance,
                    adresse,
                    nom_parent,
                    redoublant,
                    statut,
                    classe_id,
                    telephone_parent
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ancien_id,
                nouvel_uuid,
                matricule,
                nom,
                prenom,
                sexe,
                date_naissance,
                lieu_naissance,
                quartier,
                nom_parent,
                redoublant,
                statut,
                classe_id,
                telephone_parent
            ))

        # Suppression de l'ancienne table
        cursor.execute("DROP TABLE eleve")

        # Renommage de la nouvelle table
        cursor.execute("""
            ALTER TABLE eleve_nouveau
            RENAME TO eleve
        """)

        print("Migration de la table eleve terminée.")

    # ========================================================
    # MIGRATION FILE D'ATTENTE
    # ========================================================

    cursor.execute("""
        PRAGMA table_info(file_attente_synchro)
    """)

    colonnes_queue = [
        colonne[1]
        for colonne in cursor.fetchall()
    ]

    if "uuid_client" not in colonnes_queue:

        cursor.execute("""
            ALTER TABLE file_attente_synchro
            ADD COLUMN uuid_client TEXT
        """)

        print(
            "Colonne uuid_client ajoutée "
            "à file_attente_synchro."
        )

    connection.commit()
    connection.close()

    print("Base de données initialisée avec succès.")


# ============================================================
# INSERTION DES CYCLES
# ============================================================

def insert_cycles():

    connection = get_connection()
    cursor = connection.cursor()

    cycles = [
        (1, "prescolaire"),
        (2, "primaire"),
        (3, "college"),
        (4, "lycee")
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO cycle (
            id,
            nom
        )
        VALUES (?, ?)
    """, cycles)

    connection.commit()
    connection.close()

    print("Données des cycles chargées.")


# ============================================================
# INSERTION DES CLASSES
# ============================================================

def insert_classes():

    connection = get_connection()
    cursor = connection.cursor()

    classes = [
        (1, "P1", 1),
        (2, "P2", 1),
        (3, "P3", 1),
        (4, "CP1", 2),
        (5, "CP2", 2),
        (6, "CE1", 2),
        (7, "CE2", 2),
        (8, "CM1", 2),
        (9, "CM2", 2),
        (10, "6E", 3),
        (11, "5E", 3),
        (12, "4E", 3),
        (13, "3E", 3),
        (14, "SECOND TROIS COMMUNS", 4),
        (15, "PREMIERE TROIS COMMUNS", 4),
        (16, "TERMINALE TROIS COMMUNS", 4)
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO classe (
            id,
            nom,
            cycle_id
        )
        VALUES (?, ?, ?)
    """, classes)

    connection.commit()
    connection.close()

    print("Données des classes chargées.")


# ============================================================
# INSERTION DES ELEVES
# ============================================================

def insert_eleves():

    connection = get_connection()
    cursor = connection.cursor()

    eleves = [

        (
            3,
            str(uuid.uuid4()),
            "LOCAL-3",
            "malonga",
            "junior",
            "M",
            "02-01-2007",
            "brazzaville",
            "mayanga",
            "nkenzo davy",
            "0",
            "actif",
            15,
            "0697299896"
        ),

        (
            4,
            str(uuid.uuid4()),
            "LOCAL-4",
            "nkenzo",
            "nelfride",
            "F",
            "02-01-2011",
            "brazzaville",
            "mayanga",
            "nkenzo davy",
            "0",
            "actif",
            13,
            "0697299896"
        ),

        (
            5,
            str(uuid.uuid4()),
            "LOCAL-5",
            "malela",
            "oman",
            "M",
            "02-01-2006",
            "brazzaville",
            "mayanga",
            "malela davy",
            "0",
            "actif",
            16,
            "0698299896"
        ),

        (
            6,
            str(uuid.uuid4()),
            "LOCAL-6",
            "malela",
            "bat",
            "M",
            "02-01-2005",
            "brazzaville",
            "mayanga",
            "malela davy",
            "0",
            "actif",
            16,
            "0698299896"
        ),

        (
            7,
            str(uuid.uuid4()),
            "LOCAL-7",
            "nkenzo",
            "sterling",
            "M",
            "02-11-2007",
            "brazzaville",
            "barrage",
            "nkenzo ella",
            "0",
            "",
            16,
            "068275047"
        ),

        (
            8,
            str(uuid.uuid4()),
            "LOCAL-8",
            "massamba",
            "",
            "",
            "",
            "",
            "",
            "",
            "1",
            "",
            13,
            ""
        ),

        (
            9,
            str(uuid.uuid4()),
            "LOCAL-9",
            "massamba",
            "laudes",
            "M",
            "12-12-2007",
            "benin",
            "kinsoudi",
            "nkenzo josias",
            "0",
            "",
            13,
            "067923680"
        ),

        (
            10,
            str(uuid.uuid4()),
            "LOCAL-10",
            "nkenzo",
            "junior",
            "M",
            "04-10-2008",
            "brazzaville",
            "usine",
            "nkenzo davy",
            "0",
            "actif",
            16,
            "string"
        ),

        (
            11,
            str(uuid.uuid4()),
            "LOCAL-11",
            "nkenzo",
            "osias",
            "M",
            "21-02-2013",
            "brazzaville",
            "usine",
            "nkenzo adonay",
            "0",
            "actif",
            13,
            "05555555"
        ),

        (
            12,
            str(uuid.uuid4()),
            "LOCAL-12",
            "nkenzo",
            "isaac",
            "M",
            "21-02-2013",
            "brazzaville",
            "usine",
            "nkenzo adonay",
            "0",
            "actif",
            13,
            "05555555"
        ),

        (
            13,
            str(uuid.uuid4()),
            "LOCAL-13",
            "malonga",
            "salem",
            "M",
            "16-01-2013",
            "brazzaville",
            "usine",
            "malonga blandin",
            "0",
            "actif",
            13,
            "05558555"
        ),

        (
            14,
            str(uuid.uuid4()),
            "LOCAL-14",
            "malonga",
            "josias",
            "M",
            "12-12-2006",
            "brazzaville",
            "bilouki",
            "malonga patrick",
            "0",
            "",
            16,
            "06XXXXXX"
        ),

        (
            15,
            str(uuid.uuid4()),
            "LOCAL-15",
            "malonga",
            "josias",
            "M",
            "12-12-2006",
            "brazzaville",
            "bilouki",
            "malonga patrick",
            "0",
            "",
            16,
            "06XXXXXX"
        ),

        (
            16,
            str(uuid.uuid4()),
            "LOCAL-16",
            "KOUASSI",
            "Jean",
            "M",
            "2012-05-14",
            "Brazzaville",
            "Centre-ville",
            "KOUASSI Paul",
            "0",
            "actif",
            16,
            "+242060000000"
        )
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO eleve (
            id,
            uuid_client,
            matricule,
            nom,
            prenom,
            sexe,
            date_naissance,
            lieu_naissance,
            adresse,
            nom_parent,
            redoublant,
            statut,
            classe_id,
            telephone_parent
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, eleves)

    connection.commit()
    connection.close()

    print("Données des élèves chargées.")


# ============================================================
# EXECUTION DIRECTE DU SCRIPT
# ============================================================

if __name__ == "__main__":

    init_database()
    insert_cycles()
    insert_classes()
    insert_eleves()

    print("Initialisation terminée.")