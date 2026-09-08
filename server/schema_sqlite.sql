-- ============================================================
-- Schema SQLite du serveur GS (mode "sans installation").
-- Utilise quand GS_DB_MODE=sqlite : aucun MySQL a installer,
-- la base est un simple fichier dans le dossier de donnees.
-- Converti de schema.sql (MySQL) : ENUM->TEXT, AUTO_INCREMENT->
-- AUTOINCREMENT, index separes.
-- ============================================================

CREATE TABLE IF NOT EXISTS cycle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS classe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classe TEXT NOT NULL,
    cycle_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS annee_scolaire (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    libelle TEXT NOT NULL,
    date_debut TEXT NOT NULL,
    date_fin TEXT NOT NULL,
    est_active INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS matiere (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eleve (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    sexe TEXT NOT NULL,
    date_naissance TEXT,
    lieu_naissance TEXT,
    adresse TEXT NOT NULL,
    nom_parent TEXT NOT NULL,
    numero_parent TEXT,
    redoublant TEXT DEFAULT '0',
    statut TEXT DEFAULT 'actif',
    uuid_client TEXT,
    est_supprime INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS enseignant (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    sexe TEXT NOT NULL,
    date_naissance TEXT,
    lieu_naissance TEXT,
    adresse TEXT,
    telephone TEXT NOT NULL,
    email TEXT,
    diplome TEXT,
    date_embauche TEXT,
    statut TEXT DEFAULT 'actif'
);

CREATE TABLE IF NOT EXISTS inscription (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    eleve_id INTEGER NOT NULL,
    classe_id INTEGER NOT NULL,
    annee_scolaire_id INTEGER NOT NULL,
    date_inscription TEXT DEFAULT CURRENT_TIMESTAMP,
    statut TEXT DEFAULT 'actif',
    uuid_client TEXT
);

CREATE TABLE IF NOT EXISTS programme (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classe_id INTEGER NOT NULL,
    matiere_id INTEGER NOT NULL,
    enseignant_id INTEGER,
    coefficient INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS note (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inscription_id INTEGER NOT NULL,
    matiere_id INTEGER NOT NULL,
    type_evaluation TEXT NOT NULL,
    note REAL NOT NULL,
    note_sur INTEGER DEFAULT 20,
    date_evaluation TEXT NOT NULL,
    trimestre TEXT,
    uuid_client TEXT
);

CREATE TABLE IF NOT EXISTS paiement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inscription_id INTEGER NOT NULL,
    type_frais TEXT NOT NULL,
    montant REAL NOT NULL,
    date_paiement TEXT DEFAULT CURRENT_TIMESTAMP,
    mode_paiement TEXT DEFAULT 'espece',
    trimestre TEXT,
    mois TEXT,
    uuid_client TEXT
);

CREATE TABLE IF NOT EXISTS tarif_scolarite (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classe_id INTEGER NOT NULL,
    annee_scolaire_id INTEGER NOT NULL,
    frais_inscription REAL NOT NULL,
    montant_pension REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS presences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    eleve_id INTEGER NOT NULL,
    classe_id INTEGER NOT NULL,
    date_presence TEXT DEFAULT CURRENT_TIMESTAMP,
    statut TEXT NOT NULL,
    justifie TEXT DEFAULT 'Non',
    uuid_client TEXT
);

CREATE TABLE IF NOT EXISTS utilisateur (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    telephone TEXT NOT NULL UNIQUE,
    email TEXT,
    identifiant TEXT,
    mot_de_passe TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'gestionnaire',
    statut TEXT DEFAULT 'actif',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS parametre (
    cle TEXT PRIMARY KEY,
    valeur TEXT
);

CREATE TABLE IF NOT EXISTS planning (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classe_id INTEGER NOT NULL,
    jour TEXT NOT NULL,
    creneau TEXT NOT NULL,
    matiere TEXT,
    salle TEXT
);

CREATE TABLE IF NOT EXISTS caisse_transaction (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference TEXT,
    beneficiaire TEXT,
    motif TEXT,
    categorie TEXT,
    montant REAL NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('entree', 'sortie')),
    mode_reglement TEXT,
    date TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    horodatage TEXT DEFAULT CURRENT_TIMESTAMP,
    utilisateur_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    adresse_ip TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_date ON audit_log(horodatage);
