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
  tests/                     # Tests unitaires
```

## Licence

Usage interne - Ecole
