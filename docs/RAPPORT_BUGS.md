# RAPPORT DE BUGS — Gestion Scolaire

> Registre des bugs découverts et corrigés lors des campagnes de tests
> fonctionnels (session 2026-09-09). Format par bug :
> **Symptôme → Cause profonde → Correctif → Statut.**

## Mode d'emploi des tests

- Suite automatique : `python -m pytest tests server -q`
- Exercices fonctionnels (dans `/tmp/opencode/`) :
  - `exerciser_routes.py` : toutes les routes serveur sur SQLite local
  - `exerciser_routes_mysql.py` : mêmes routes contre un **vrai MySQL 8**
    (conteneur `gs_mysql`, port 3307, base `gs_multi`)
  - `exerciser_desktop.py` : 80 opérations des repositories bureau
  - `exerciser_services.py` : 28 services (auth, backup, rapports, PDF, sync)
- Serveur MySQL de test : `docker exec gs_mysql mysql -uroot -pgs_root_pwd -e
  "DROP DATABASE IF EXISTS gs_multi; CREATE DATABASE gs_multi CHARACTER SET
  utf8mb4 COLLATE utf8mb4_unicode_ci;"`

## Bugs corrigés

### BUG-01 — Route `GET /bulletin` renvoyait des moyennes fausses / bugguées

- **Contexte** : mode serveur (SQLite et MySQL), consultation du bulletin.
- **Symptôme** : `/bulletin/{nom}/{prenom}/{trimestre}` : erreurs de jointure
  (colonne `eleve_id` inexistante dans `inscription`), moyenne jamais trouvée
  ou plantage sur `fetchone()["moyenne"]` quand aucun résultat.
- **Cause profonde** :
  - `inscription.eleve_id = %s` remplacé par un `eleve.id = %s` incohérent ;
  - les moyennes utilisaient `note.programme_id` (colonne inexistante) au lieu
    de joindre `note.matiere_id = programme.matiere_id` ;
  - filtre `type_evaluation` non robuste (pas de `LOWER`, devoirs inclassés) ;
  - aucun garde sur `fetchone()` retournant `None`.
- **Correctif** (`server/main.py`, route `GET /bulletin`) :
  - jointure via `inscription.eleve_id` ;
  - moyennes par `note.matiere_id = programme.matiere_id` ;
  - `LOWER(type_evaluation) LIKE 'devoir%'` pour les devoirs,
    `LOWER(type_evaluation) = 'composition'` pour la composition ;
  - `moyenne = resultat["moyenne"] if resultat else None`.
- **Statut** : CORRIGÉ — testé SQLite (122/122) et MySQL (122/122).

### BUG-02 — `_definir_parametre` (compat) cassait SQLite

- **Contexte** : route `POST /parametre` (surface bureau, `server/compat.py`,
  branche `gestion_scolaire_api`).
- **Symptôme** : en mode SQLite, `ON DUPLICATE KEY UPDATE` → erreur de syntaxe ;
  le paramètre n'était jamais enregistré.
- **Cause profonde** : SQL « MySQL-only » exécuté contre SQLite.
- **Correctif** (`server/compat.py::_definir_parametre`) : upsert portable —
  `SELECT` puis `INSERT` ou `UPDATE` selon la présence de la clé.
- **Statut** : CORRIGÉ.

### BUG-03 — `compat.connexion()` en erreur systématique sur MySQL (50 KO)

- **Contexte** : mode MySQL réel (serveur hôte multi-utilisateurs).
- **Symptôme** : TOUTES les routes compat (eleves, paiements, presences,
  tarifs…) renvoyaient 500 `AttributeError: module 'mysql' has no attribute
  'connect'`. 50 des 50 premiers KO venaient de là.
- **Cause profonde** : `import mysql.connector` puis appel `mysql.connect(...)`
  au lieu de `mysql.connector.connect(...)` dans `server/compat.py`.
- **Correctif** : `mysql.connect(` → `mysql.connector.connect(`.
- **Statut** : CORRIGÉ — c'était la cause racine de la moitié des erreurs
  MySQL avant l'exercice.

### BUG-04 — `DELETE /supprimerEnseignant/{nom}/{prenom}` plantait si absent

- **Symptôme** : `TypeError: 'NoneType' object is not subscriptable` (500)
  quand l'enseignant n'existe pas ; le test d'absence était
  `if id_enseignant == 0` (mort : `fetchone()[0]` plantait avant).
- **Cause profonde** : indexation de `cursor.fetchone()[0]` AVANT le contrôle.
- **Correctif** (`server/main.py::delete_un_enseignant`) : `ligne = fetchone()`,
  `if ligne is None: raise HTTPException(404)`, puis `id = ligne[0]`.
- **Statut** : CORRIGÉ.

### BUG-05 — Valeurs métier du bureau rejetées par les ENUM MySQL

- **Contexte** : le bureau envoie le vocabulaire humain, le schéma MySQL impose
  des ENUM stricts → erreurs `1265 Data truncated for column <col> at row 1`.
- **Symptômes relevés** :
  - `POST /ajout_enseignant` : statut « Enseignant » → ENUM(`actif`,`inactif`) ;
  - `PUT /modifierEnseignant/{id}` : statut « Professeur » ;
  - `POST /ajout_eleve` : statut « Inscrit », mais aussi le paiement lié avec
    `mode_paiement` « Espèces » → ENUM(`espece`,`virement`,`mobile_money`,`cheque`) ;
  - `eleve.redoublant` 0/1 int.
- **Correctif** (normalisation à la frontière `server/main.py` en réutilisant
  les normalisateurs `compat` existants) :
  - `compat._statut_eleve`, `compat._statut_enseignant` (nouveau, miroir du
    premier), `compat._mode_paiement`, `compat._type_frais`, `compat._trimestre` ;
  - helpers `_redoublant_sql` / `_oui_non_sql` pour `redoublant` et
    `presence.justifie` ;
  - appliqués dans `ajouter_eleve`, `modifier_eleve`, `ajouter_enseignant`,
    `put_un_enseignant`, `ajouter_paiement`, `ajouter_presence`.
- **Statut** : CORRIGÉ — MySQL 122/122, SQLite 122/122, pytest 282 passed.

### BUG-06 — `update_eleve` (desktop) : violation NOT NULL en modification

- **Symptôme** : `NOT NULL constraint failed: eleves.redoublant` au MODIF d'un
  élève via le bureau (SQLite).
- **Cause profonde** : l'UPDATE dynamique n'assignait pas les colonnes non
  fournies (dont `redoublant` non nullable sans valeur par défaut).
- **Correctif** (`repositories/eleve_repository.py::update_eleve`) :
  `setdefault` pour `redoublant`, `statut`, `check_acte`, `check_photos`,
  `check_bulletin` avant construction de l'UPDATE.
- **Statut** : CORRIGÉ — 80/80 opérations desktop OK.

## Faux positifs / comportements attendus (pas des bugs)

- **Erreurs FK 1452 dans le harness** : les DELETE métier (`/supprimerClasse`,
  `/supprimerCycle`, `/supprimerEnseignant`) suppriment les parents du seed ;
  les tests suivants qui réutilisaient les mêmes ids échouaient par FK. C'était
  un artefact de séquençage du testeur, corrigé en rejouant la surface bureau
  sur des parents recréés ; le serveur (comme MySQL) refuse correctement de
  créer des programme/paiement/planning sans classes vivantes.

## Résultats de la campagne 2026-09-09

| Cible | Résultat |
|---|---|
| `pytest tests server` | 282 passed |
| Routes serveur (SQLite) | 122/122 OK |
| Routes serveur (MySQL 8 réel, mode hôte/serveur) | 122/122 OK |
| Repositories bureau | 80/80 OK |
| Services (auth, backup, rapports, PDF, sync) | 28/28 OK |
| serveur_local (démarrage/arrêt, port 8427) | OK |
| autostart demarrage (état restauré) | OK |