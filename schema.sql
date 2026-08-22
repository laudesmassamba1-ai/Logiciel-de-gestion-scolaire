-- ============================================================
-- SCHÉMA DE LA BASE DE DONNÉES "ecole"
-- Ordre respecté pour les clés étrangères : tables sans dépendance d'abord
-- ============================================================

-- 1. cycle
CREATE TABLE cycle (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom TEXT NOT NULL
);

-- 2. classe (dépend de cycle)
CREATE TABLE classe (
    id INT AUTO_INCREMENT PRIMARY KEY,
    classe TEXT NOT NULL,
    cycle_id INT NOT NULL,
    FOREIGN KEY (cycle_id) REFERENCES cycle(id)
);

-- 3. annee_scolaire
CREATE TABLE annee_scolaire (
    id INT AUTO_INCREMENT PRIMARY KEY,
    libelle VARCHAR(50) NOT NULL,
    date_debut DATE NOT NULL,
    date_fin DATE NOT NULL,
    est_active TINYINT(1) DEFAULT 0
);

-- 4. matiere
CREATE TABLE matiere (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(100) NOT NULL
);

-- 5. eleve
CREATE TABLE eleve (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    sexe ENUM('M', 'F') NOT NULL,
    date_naissance DATE,
    lieu_naissance VARCHAR(100),
    adresse VARCHAR(255) NOT NULL,
    nom_parent VARCHAR(150) NOT NULL,
    numero_parent VARCHAR(30),
    redoublant ENUM('0', '1') DEFAULT '0',
    statut ENUM('actif', 'inactif', 'exclu') DEFAULT 'actif',
    uuid_client VARCHAR(100),
    est_supprime TINYINT(1) DEFAULT 0
);

-- 6. enseignant
CREATE TABLE enseignant (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    sexe ENUM('M', 'F') NOT NULL,
    date_naissance DATE,
    lieu_naissance VARCHAR(100),
    adresse TEXT,
    telephone VARCHAR(30) NOT NULL,
    email VARCHAR(150),
    diplome VARCHAR(150),
    date_embauche DATE,
    statut ENUM('actif', 'inactif') DEFAULT 'actif'
);

-- 7. inscription (dépend de eleve, classe, annee_scolaire)
CREATE TABLE inscription (
    id INT AUTO_INCREMENT PRIMARY KEY,
    eleve_id INT NOT NULL,
    classe_id INT NOT NULL,
    annee_scolaire_id INT NOT NULL,
    date_inscription TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    statut ENUM('actif', 'abandon', 'transfere') DEFAULT 'actif',
    uuid_client VARCHAR(100),
    FOREIGN KEY (eleve_id) REFERENCES eleve(id),
    FOREIGN KEY (classe_id) REFERENCES classe(id),
    FOREIGN KEY (annee_scolaire_id) REFERENCES annee_scolaire(id)
);

-- 8. programme (dépend de classe, matiere, enseignant)
CREATE TABLE programme (
    id INT AUTO_INCREMENT PRIMARY KEY,
    classe_id INT NOT NULL,
    matiere_id INT NOT NULL,
    enseignant_id INT,
    coefficient INT DEFAULT 1,
    FOREIGN KEY (classe_id) REFERENCES classe(id),
    FOREIGN KEY (matiere_id) REFERENCES matiere(id),
    FOREIGN KEY (enseignant_id) REFERENCES enseignant(id)
);

-- 9. note (dépend de inscription, matiere)
--  Valeurs de l'ENUM type_evaluation à vérifier/ajuster selon la vraie base
CREATE TABLE note (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inscription_id INT NOT NULL,
    matiere_id INT NOT NULL,
    type_evaluation TEXT NOT NULL,
    note DECIMAL(4,2) NOT NULL,
    note_sur INT DEFAULT 20,
    date_evaluation DATE NOT NULL,
    trimestre ENUM('T1', 'T2', 'T3'),
    uuid_client VARCHAR(100),
    FOREIGN KEY (inscription_id) REFERENCES inscription(id),
    FOREIGN KEY (matiere_id) REFERENCES matiere(id)
);

-- 10. paiement (dépend de inscription)
-- ⚠️ Valeurs de l'ENUM type_frais à vérifier/ajuster selon la vraie base
CREATE TABLE paiement (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inscription_id INT NOT NULL,
    type_frais ENUM('Inscription', 'Scolarite', 'Cantine', 'Transport') NOT NULL,
    montant DECIMAL(10,2) NOT NULL,
    date_paiement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mode_paiement ENUM('espece', 'virement', 'mobile_money', 'cheque') DEFAULT 'espece',
    trimestre ENUM('T1', 'T2', 'T3'),
    mois VARCHAR(20),
    uuid_client VARCHAR(100),
    FOREIGN KEY (inscription_id) REFERENCES inscription(id)
);

-- 11. tarif_scolarite (dépend de classe, annee_scolaire)
CREATE TABLE tarif_scolarite (
    id INT AUTO_INCREMENT PRIMARY KEY,
    classe_id INT NOT NULL,
    annee_scolaire_id INT NOT NULL,
    frais_inscription DECIMAL(10,2) NOT NULL,
    montant_pension DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (classe_id) REFERENCES classe(id),
    FOREIGN KEY (annee_scolaire_id) REFERENCES annee_scolaire(id)
);

-- 12. presences (dépend de eleve, classe)
CREATE TABLE presences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    eleve_id INT NOT NULL,
    classe_id INT NOT NULL,
    date_presence TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    statut ENUM('Present', 'Absent', 'En retard') NOT NULL,
    justifie ENUM('Oui', 'Non') DEFAULT 'Non',
    uuid_client VARCHAR(100),
    FOREIGN KEY (eleve_id) REFERENCES eleve(id),
    FOREIGN KEY (classe_id) REFERENCES classe(id)
);

-- 13. utilisateur (aucune dépendance)
CREATE TABLE utilisateur (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    telephone VARCHAR(30) NOT NULL UNIQUE,
    email VARCHAR(150),
    identifiant VARCHAR(100),
    mot_de_passe VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'gestionnaire',
    statut VARCHAR(50) DEFAULT 'actif',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
