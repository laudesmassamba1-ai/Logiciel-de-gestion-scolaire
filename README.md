# Logiciel de Gestion Scolaire

Application desktop de gestion scolaire pour les etablissements scolaires en Republique du Congo.

## Fonctionnalites

- **Gestion des eleves** : inscription, modification, recherche, fiches individuelles
- **Gestion des classes** : creation, affectation, cycles et annees scolaires
- **Notes et evaluations** : saisie par matiere/eleve, calcul automatique des moyennes, bulletins
- **Presences** : suivi journalier, marquage rapide (tout present/absent)
- **Planning** : emplois du temps par classe et par creneau
- **Caisse** : transactions entrees/sorties, releves
- **Tarifs et paiements** : frais de scolarite, suivi des paiements par eleve
- **Programmes** : matieres et coefficients par classe
- **Personnel** : gestion des enseignants et personnel administratif
- **Parametres** : configuration de l'ecole, logo, signatures
- **Sauvegarde/Restauration** : backup et restauration de la base de donnees
- **Export PDF** : bulletins, recus, certificats, fiches de paie, plannings
- **Comptes utilisateurs** : authentification securisee, gestion des roles (admin, directeur, gestionnaire)
- **Tableaux de bord** : statistiques et KPI adaptes a chaque role
- **Synchronisation** : file d'attente pour synchronisation avec un serveur distant (optionnel)

## Stack technique

| Composant | Technologie |
|---|---|
| Langage | Python 3.12 |
| Interface | PyQt5 |
| Base de donnees | SQLite3 (WAL mode) |
| PDF | WeasyPrint |
| Architecture | MVC (Repositories / Services / UI) |

## Installation

```bash
# Cloner le depot
git clone <url-du-depot>
cd Logiciel-de-gestion-scolaire

# Creer l'environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Installer les dependances
pip install -r requirements.txt
```

## Lancement

```bash
python main.py
```


## Configuration

Variables d'environnement optionnelles :

| Variable | Description | Defaut |
|---|---|---|
| `GS_API_URL` | URL du serveur de synchronisation | `http://127.0.0.1:8000` |
| `GS_SYNC_ACTIVE` | Activer la synchronisation (`true`/`false`) | `false` |
| `GS_API_TIMEOUT` | Timeout des appels API (secondes) | `2.0` |
| `GS_DATA_DIR` | Repertoire de stockage des donnees | `./data` |

## Tests

```bash
python -m pytest tests/ -v
```

## Serveur de synchronisation (multi-postes)

Le dossier `server/` contient l'API FastAPI + MySQL issue de la branche
`gestion_scolaire_api`. Elle centralise les donnees entre plusieurs postes
d'un meme etablissement : un seul PC fait tourner le serveur, les autres
postes (clients) pointent vers lui via `GS_API_URL`.

### Installation du poste serveur (un seul par etablissement)

```bash
cd server/
pip install -r requirements.txt
# Windows : installe l'API comme service demarrage automatique (NSSM)
setup_service.bat
# Linux / test :
uvicorn main:app --host 0.0.0.0 --port 8000
```

La base MySQL est creee automatiquement au premier demarrage (`schema.sql`).
Configuration optionnelle par variables d'environnement :

| Variable | Description | Defaut |
|---|---|---|
| `GS_DB_HOST` | Hote MySQL | `localhost` |
| `GS_DB_USER` | Utilisateur MySQL | `root` |
| `GS_DB_PASSWORD` | Mot de passe MySQL | - |
| `GS_DB_NAME` | Nom de la base | `ecole` |

Puis ouvrir le port 8000 dans le pare-feu du poste serveur et lui donner
une IP fixe sur le reseau local.

### Postes clients

```bash
set GS_API_URL=http://IP_DU_POSTE_SERVEUR:8000
set GS_SYNC_ACTIVE=true
python main.py
```

L'application reste entierement fonctionnelle hors-ligne : les ecritures
sont enregistrees localement puis synchronisees automatiquement des que le
serveur repond (file d'attente, anti-doublon par `uuid_client`).

### Compatibilite client/serveur

Le serveur expose a la fois ses routes historiques (`/ajout_eleve`,
`/ajout_classe`, ...) et celles utilisees par l'application de bureau
(`/eleve`, `/classe`, `/modifierEleve/{id}`, `/planning`, `/parametre`, ...).
Cette couche d'adaptation vit dans `server/compat.py` ; elle traduit aussi
les champs de l'app bureau vers le schema MySQL (ex : `pere_nom` ->
`nom_parent`). Tests : `cd server && python -m pytest test_compat.py`.

## Build et distribution

### Linux (.deb + AppImage)

```bash
python3 build_app.py
```

Les installateurs sont générés dans le dossier `installers/`.

### Windows (EXE + Inno Setup)

```bash
python build_app.py
```

Les installateurs sont générés dans le dossier `installers/`.


## Structure du projet

```
Logiciel-de-gestion-scolaire/
  main.py                    # Point d'entree
  core/
    config.py                # Configuration, constantes, themes
    network.py               # Client HTTP pour synchronisation
  database/
    db.py                    # Singleton SQLite, schema, migrations
  repositories/              # Couche d'acces aux donnees
  services/                  # Logique metier
    auth.py                  # Authentification et autorisation
    backup.py                # Sauvegarde/Restauration
    pdf_export.py            # Generation PDF
    reports.py               # Rapports HTML
  ui/
    main_view.py             # Fenetre principale et navigation
    login_view.py            # Ecran de connexion
    pages/                   # Pages modulaires
      dashboards.py          # Tableaux de bord
      eleves.py              # Gestion des eleves
      classes_page.py        # Gestion des classes
      notes_page.py          # Notes et evaluations
      presences_page.py      # Presences
      planning_page.py       # Emplois du temps
      caisse_page.py         # Caisse
      comptes_page.py        # Comptes utilisateurs
      personnel_page.py      # Personnel
      parametres_page.py     # Parametres
      cycles_page.py         # Cycles et annees
      tarifs_page.py         # Tarifs
      paiements_page.py      # Paiements
      programmes_page.py     # Programmes
      statistiques_page.py   # Statistiques
    ui_files/                # Fichiers .ui (Qt Designer)
  tests/                     # Tests unitaires (app bureau)
  server/                    # API de synchronisation (FastAPI + MySQL)
    main.py                  # Application FastAPI
    compat.py                # Couche de compatibilite app bureau <-> serveur
    test_compat.py           # Tests de la couche de compatibilite
    schema.sql               # Schema MySQL (cree automatiquement)
    setup_service.bat        # Installation service Windows (NSSM)
```

## Licence

Usage interne - Ecole
