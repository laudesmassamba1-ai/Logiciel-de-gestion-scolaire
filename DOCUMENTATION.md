# DOCUMENTATION COMPLETE DU LOGICIEL DE GESTION SCOLAIRE

**Version documentee : 1.2.0** — Python 3 + PyQt5 + SQLite
**Contexte : Republique du Congo (Brazzaville)** — Devise : FCFA — Indicatif : +242

Ce document decrit chaque fichier du projet, son role, et comment tout
s'emboite pour former l'application. Les numeros de lignes correspondent au
code source actuel (branche `exe`).

---

## SOMMAIRE

1. [Vue d'ensemble](#1-vue-densemble)
2. [Arborescence complete du projet](#2-arborescence-complete-du-projet)
3. [Architecture et demarrage](#3-architecture-et-demarrage)
4. [Point d'entree : main.py](#4-point-dentree--mainpy)
5. [Configuration : config.py](#5-configuration--configpy)
6. [Couche donnees : database/db.py](#6-couche-donnees--databasedbpy)
7. [Depots : models/repositories.py](#7-depots--modelsrepositoriespy)
8. [Services : services/](#8-services--services)
9. [Couche presentation : le dossier views/](#9-couche-presentation--le-dossier-views)
10. [Fichiers .ui](#10-fichiers-ui)
11. [Base de donnees SQLite : schema complet](#11-base-de-donnees-sqlite--schema-complet)
12. [Roles et permissions](#12-roles-et-permissions)
13. [Construction des executables](#13-construction-des-executables)
14. [Guide d'utilisation par role](#14-guide-dutilisation-par-role)
15. [Depannage et questions frequentes](#15-depannage-et-questions-frequentes)
16. [Historique des versions](#16-historique-des-versions)

---

## 1. Vue d'ensemble

Le logiciel **Gestion Scolaire** est une application de bureau autonome pour un
etablissement scolaire congolais. Elle couvre :

- la **gestion des eleves** (inscription, reinscription, matricule automatique,
  dossier complet) ;
- la **gestion des classes** (capacite, salle, titulaire) ;
- la **saisie des notes** et la **generation de bulletins** ;
- l'**emploi du temps** (planning hebdomadaire) ;
- la **caisse** (recettes / depenses, solde, export CSV) ;
- la **gestion des comptes utilisateurs** (3 roles) ;
- la **gestion du personnel** (RH, salaires, paie) ;
- la **generation de documents** (bulletins, recus, certificats, paie,
  rapports RH, emploi du temps) au format **HTML** ouverts dans le navigateur ;
- des **dashboards** par role avec graphiques (barres, camemberts) dessines
  sans aucune dependance externe grace a `QPainter`.

### Caracteristiques techniques

| Element | Valeur |
|---|---|
| Langage | Python 3 |
| Interface graphique | PyQt5 (5.15.11) |
| Base de donnees | SQLite (fichier `ecole.db`) |
| Backend optionnel | API REST FastAPI (`http://127.0.0.1:8000`) pour enrichir les indicateurs (voir section 8.2) |
| Mode hors ligne | L'app fonctionne completement sans l'API : bascule sur la base locale |
| Empaquetage | PyInstaller **one-file** sur Linux et Windows |
| Dependances | `PyQt5==5.15.11` et `requests==2.32.3` (voir `requirements.txt`) |

### Ou sont stockees les donnees ?

- En developpement : dossier `data/` a la racine du projet.
- En executable : dossier `data/` **a cote de l'executable** (voir
  `config.data_dir()`).

---

## 2. Arborescence complete du projet

```
Logiciel-de-gestion-scolaire/
│
├── main.py                      # Point d'entree : HighDPI + demarrage (66 lignes)
├── config.py                    # Constantes + feuille de style (118 lignes)
├── requirements.txt             # PyQt5==5.15.11 + requests==2.32.3
├── .gitignore                   # venv/, .venv/, __pycache__/, *.db, build/, dist/, dist_win/, exe-win/, data/, GestionScolaire.spec
│
├── build_win.spec               # Spec PyInstaller WINDOWS (one-file + manifeste DPI)
├── win_dpi_manifest.xml         # Manifeste <dpiAware>true</dpiAware> pour Windows
│
├── .github/workflows/
│   └── build_windows.yml        # Workflow GitHub Actions : build de l'exe Windows
│
├── database/
│   ├── __init__.py              # Importe l'instance partagee de la base
│   └── db.py                    # Connexion SQLite, schema, donnees initiales (234 lignes)
│
├── models/
│   ├── __init__.py              # Importe l'instance partagee des depots
│   └── repositories.py          # Toutes les requetes metier (300 lignes)
│
├── services/
│   ├── __init__.py              # Vide
│   ├── api.py                   # Client de l'API FastAPI + repli local (386 lignes)
│   ├── auth.py                  # Connexion, mots de passe, permissions (69 lignes)
│   └── reports.py               # Documents HTML (bulletins, certificats, paie) (193 lignes)
│
├── views/
│   ├── __init__.py              # Vide
│   ├── loader.py                # Chargement des .ui + responsivite (26 lignes)
│   ├── login_view.py            # Fenetre de connexion (125 lignes)
│   ├── main_view.py             # Fenetre principale, sidebar, statut API (191 lignes)
│   ├── pages.py                 # Toutes les pages et dialogues metier (1455 lignes)
│   ├── widgets.py               # Graphiques QPainter + formats monetaires (176 lignes)
│   │
│   └── ui_files/                # Interfaces .ui (Qt Designer)
│       ├── main.ui              # Fenetre principale (sidebar + QStackedWidget)
│       ├── dashboards/          # dashboard_admin.ui, dashboard_directeur.ui,
│       │                        # dashboard_gestionnaire.ui
│       ├── eleves/              # eleves.ui (liste) + inscription.ui (dossier)
│       ├── classes/             # classes.ui + classe_dialog.ui
│       ├── notes/               # notes.ui (saisie + bulletins)
│       ├── planning/            # planning.ui (emploi du temps)
│       ├── caisse/              # caisse.ui (recettes / depenses)
│       ├── comptes/             # comptes.ui + compte_dialog.ui
│       └── parametres/          # parametres.ui (en-tete des documents)
│
├── data/                        # CREE A L'EXECUTION (base + documents)
│   ├── ecole.db                 # La base SQLite
│   └── documents/               # HTML generes (bulletins, recus, etc.)
│
├── dist/GestionScolaire         # Executable Linux (one-file)
├── dist_win/                    # Executable Windows (one-file, via GitHub Actions)
├── build/                       # Travail intermediaire PyInstaller (nettoyable)
└── .venv/                       # Environnement virtuel de developpement
```

## 3. Architecture et demarrage

L'application suit une architecture en **3 couches**, sans framework :

```
+------------------------------------------------------------+
|  COUCHE PRESENTATION  (views/)                             |
|  login_view.py -> main_view.py -> pages.py -> widgets.py   |
|  fichiers .ui (views/ui_files)                             |
+------------------------------+-----------------------------+
                               | importe / appelle
+------------------------------v-----------------------------+
|  COUCHE SERVICES  (services/)                              |
|  auth.py (connexion, permissions)                          |
|  api.py (client API REST + repli local)                    |
|  reports.py (documents HTML)                               |
+------------------------------+-----------------------------+
                               | utilise
+------------------------------v-----------------------------+
|  COUCHE DONNEES  (models/ + database/)                     |
|  models/repositories.py (requetes metier)                  |
|  database/db.py (connexion, schema, seed)                  |
|  SQLite : data/ecole.db                                    |
+------------------------------------------------------------+
```

### Demarrage pas a pas

1. `python main.py` est execute.
2. `main()` (main.py:44) :
   - configure le **HighDPI** (`_setup_high_dpi`, main.py:16) ;
   - choisit une police vectorielle (`_pick_base_font`, main.py:24) ;
   - installe `_excepthook` (main.py:35) : boite de dialogue au lieu d'un
     crash silencieux en executable ;
   - cree l'application Qt et applique `APP_STYLESHEET` (config.py:29) ;
   - appelle `db.init_db()` -> creation des tables + donnees initiales ;
   - ouvre la **fenetre de connexion** `LoginDialog` ;
   - si la connexion reussit -> ouvre `MainWindow` en plein ecran ;
   - sinon -> quitte.

### Navigation dans la fenetre principale

- `MainWindow` charge `main.ui` : une **sidebar** de boutons et un
  `QStackedWidget` pour le contenu.
- `_wire_nav()` (main_view.py:128) affiche uniquement les boutons autorises
  pour le role connecte.
- `_build_pages()` (main_view.py:138) construit chaque page autorisee dans un
  `QWidget` entoure d'une `QScrollArea`, et l'ajoute au `QStackedWidget`. En
  cas d'erreur, un libelle rouge s'affiche au lieu de faire planter l'app.
- `navigate(page)` (main_view.py:173) bascule la page, appelle son `refresh()`
  et coche le bouton actif.

### Rafraichissement

Chaque page expose `page.refresh = refresh`. A chaque navigation,
`MainWindow.navigate` appelle `refresh()` pour recharger les donnees depuis la
base. Les pages restent en memoire et se rafraichissent a la demande.

---

## 4. Point d'entree : `main.py`

```
main.py (66 lignes)
```

| Ligne | Element | Role |
|---|---|---|
| 16-22 | `_setup_high_dpi()` | Rendu net sur les ecrans Windows 100/125/150/200 % (variables d'environnement Qt posees avant `QApplication`). |
| 24-33 | `_pick_base_font()` | Police vectorielle presente sur le systeme (`APP_FONT_FAMILY`, puis fallbacks), sinon police generique. |
| 35-42 | `_excepthook(...)` | En executable, une exception non geree affiche une boite « Erreur inattendue » avec le detail. |
| 44-63 | `main()` | Orchestration complete du demarrage (voir section 3). |
| 65-66 | garde | `if __name__ == "__main__": main()` |

---

## 5. Configuration : `config.py`

```
config.py (118 lignes)
```

Module importe partout : constantes, chemins, feuille de style.

### Constantes principales

| Constante | Valeur | Ligne | Role |
|---|---|---|---|
| `APP_NAME` | `"Gestion Scolaire"` | 6 | Titre de l'application |
| `APP_VERSION` | `"1.2.0"` | 7 | Version affichee sur l'ecran de connexion |
| `APP_FONT_FAMILY` / `APP_FONT_FALLBACK` / `APP_FONT_SIZE` | `"Segoe UI"` / tuples / 10 | 14-16 | Police et taille du texte |
| `API_BASE_URL` | `"http://127.0.0.1:8000"` | 19 | Adresse du backend FastAPI (optionnel) |
| `API_TIMEOUT` | `3.0` | 20 | Delai d'attente avant bascule sur la base locale |
| `PAYS_DEFAUT` / `VILLE_DEFAUT` | `"Republique du Congo"` / `"Brazzaville"` | 23-24 | Valeurs par defaut des documents |
| `INDICATIF_TEL` / `DEVISE` | `"+242"` / `"FCFA"` | 25-26 | Contexte congolais |
| `APP_STYLESHEET` | CSS Qt | 29-46 | Feuille de style globale de l'app |
| `ROLES` | `("admin", "directeur", "gestionnaire")` | 49 | Roles possibles |
| `ROLE_LABELS` | `{"admin": "Administrateur", ...}` | 51 | Libelles affiches |
| `PERIODES` | `("1er Trimestre", ...)` | 58 | Periodes de notes |
| `JOURS` | `("Lundi", ..., "Samedi")` | 60 | Jours du planning |
| `CRENEAUX` | 8 creneaux | 62 | Horaires des cours |
| `DEFAULT_ACCOUNTS` | 3 comptes | 94 | Comptes crees au premier lancement (voir section 11) |
| `DEFAULT_MATIERES` | 8 matieres | 107 | Francais, Maths, Anglais, HG, SVT, PC, Educ. civique, Informatique |

### Fonctions de chemins

| Fonction | Ligne | Role |
|---|---|---|
| `resource_path(relative)` | 74 | Chemin vers les donnees **empaquetees** dans l'executable (`_MEIPASS`), sinon racine du projet. |
| `data_dir()` | 80 | Dossier **ecrivable** ou vit la base : a cote de l'executable, sinon racine du projet. Cree `data/` si besoin. |

### Constantes de chemins

| Constante | Ligne |
|---|---|
| `UI_DIR` (dossier des .ui) | 89 |
| `DB_PATH` (fichier `data/ecole.db`) | 90 |
| `DOCS_DIR` (dossier `data/documents/`) | 91 |

En fin de module, `os.makedirs(data_dir(), exist_ok=True)` garantit que le
dossier `data/` existe des le chargement de `config`.

---

## 6. Couche donnees : `database/db.py`

```
database/db.py (234 lignes)
```

### Fonctions et schema

| Element | Ligne | Role |
|---|---|---|
| `SCHEMA` | 7 | Script SQL de creation des tables (voir section 11). |
| `hash_password(password)` | 121 | Retourne le hash `sha256` hexadecimal. **Les mots de passe ne sont jamais stockes en clair.** |

### Classe `Database` (singleton)

Une seule instance partagee par toute l'app.

| Methode | Ligne | Role |
|---|---|---|
| `__new__` | 129 | Retourne l'unique instance |
| `__init__` | 134 | Prepare le dossier des documents, pose `_initialized = False` |
| `connect()` | 139 | Ouvre une connexion SQLite (`row_factory = Row` -> dictionnaires), active `PRAGMA foreign_keys = ON`. Une connexion par operation. |
| `init_db()` | 147 | Execute `SCHEMA` puis `_seed`, une seule fois. |
| `_seed(conn)` | 160 | Comptes par defaut (si aucun utilisateur), matieres, parametres, 3 membres de personnel de base. |
| `query(sql, params)` | 204 | SELECT -> liste de dictionnaires. |
| `query_one(sql, params)` | 213 | Premier enregistrement ou `None`. |
| `execute(sql, params)` | 218 | INSERT/UPDATE/DELETE, commit, retourne `lastrowid`. |
| `executemany(sql, seq)` | 228 | Execution en lot, commit. |

> Le `_seed` cree uniquement les donnees de base (comptes, matieres,
> parametres, personnel). Les eleves, transactions et notes sont saisis par
> l'utilisateur dans l'application.

---

## 7. Depots : `models/repositories.py`

```
models/repositories.py (300 lignes)
```

La classe `Repositories` regroupe **toutes les requetes metier**. Elle est
importee partout sous l'alias `repos` (`from models import repos`).

### Helper

| Fonction | Ligne | Role |
|---|---|---|
| `_gen_reference(prefix)` | 9 | Reference unique de transaction `REC-XXXXXXXX` / `DEP-XXXXXXXX`. |

### Methodes par domaine

**Classes & matieres**

| Methode | Ligne | Role |
|---|---|---|
| `classes()` | 15 | Toutes les classes + effectif reel (COUNT sur `eleves`), triees par nom. |
| `classe_by_id(id)` | 20 | Une classe. |
| `add_classe(...)` | 23 | Insere une classe. |
| `update_classe(...)` | 28 | Modifie une classe. |
| `delete_classe(id)` | 33 | Supprime d'abord ce qui depend de la classe (eleves, planning), puis la classe. |
| `matieres()` | 39 | Toutes les matieres triees. |
| `add_matiere(nom)` | 42 | Ajoute une matiere (IGNORE si doublon). |

**Eleves**

| Methode | Ligne | Role |
|---|---|---|
| `eleves(classe_id, statut, recherche)` | 45 | Liste filtree (classe, statut, texte) avec `classe_nom` via LEFT JOIN. |
| `eleve_by_id(id)` | 63 | Un eleve. |
| `eleve_by_matricule(m)` | 66 | Un eleve par matricule (reinscription). |
| `add_eleve(data)` | 69 | Insere un eleve ; genere le matricule si absent. |
| `update_eleve(id, data)` | 87 | Met a jour le dossier. |
| `delete_eleve(id)` | 98 | Supprime notes puis eleve. |
| `next_matricule()` | 102 | Prochain matricule `ELEV{annee}{NNNN}` a partir du dernier existant. |

**Notes**

| Methode | Ligne | Role |
|---|---|---|
| `notes_for(classe_id, matiere_id, periode)` | 118 | Notes d'une classe x matiere x periode (avec matricule et nom). |
| `save_note(...)` | 127 | Insere ou met a jour (UPSERT) sur `(eleve_id, matiere_id, periode)`. |

**Caisse**

| Methode | Ligne | Role |
|---|---|---|
| `transactions(type, recherche, dates)` | 137 | Liste filtree, tri date DESC. |
| `add_transaction(...)` | 158 | Insere avec reference auto `REC-...`/`DEP-...`. |
| `delete_transaction(id)` | 167 | Supprime. |
| `caisse_totals()` | 170 | Somme des entrees, des sorties, solde. |
| `export_transactions_csv(path)` | 180 | CSV separe par `;` avec BOM (`utf-8-sig`) pour Excel. |

**Comptes utilisateurs**

| Methode | Ligne | Role |
|---|---|---|
| `utilisateurs(role, recherche)` | 189 | Liste (sans le hash de mot de passe). |
| `add_compte(...)` | 203 | Cree un compte ; username derive de l'email. |
| `update_compte(...)` | 210 | Modifie identite/email/telephone/role/actif. |
| `toggle_compte(id, actif)` | 216 | Active/desactive. |
| `reset_password(id, hash)` | 219 | Remplace le mot de passe. |
| `delete_compte(id)` | 222 | Supprime connexions puis compte. |

**Planning**

| Methode | Ligne | Role |
|---|---|---|
| `planning_for(classe_id)` | 226 | Dictionnaire `{(jour, creneau): entree}`. |
| `save_planning(classe_id, entries)` | 232 | Remplace tout le planning d'une classe. |

**Personnel**

| Methode | Ligne | Role |
|---|---|---|
| `personnel(recherche)` | 238 | Liste du personnel. |
| `add_personnel(...)` | 247 | Ajoute. |
| `update_personnel(...)` | 253 | Modifie. |
| `delete_personnel(id)` | 259 | Supprime. |
| `masse_salariale()` | 262 | Somme des salaires. |
| `enseignants()` | 266 | Personnel dont la fonction contient « Enseignant ». |

**Parametres**

| Methode | Ligne | Role |
|---|---|---|
| `parametres()` | 269 | Dictionnaire cle -> valeur. |
| `set_parametre(cle, valeur)` | 274 | Upsert d'un parametre. |
| `delete_parametres()` | 279 | Reinitialise signataire, titre, ville. |

**Statistiques du dashboard**

| Methode | Ligne | Role |
|---|---|---|
| `stats_dashboard()` | 284 | Total eleves, inscriptions du jour, encaissements du jour, dossiers incomplets. |

---

## 8. Services : `services/`

### 8.1 `services/auth.py` (69 lignes) — connexion et permissions

**Classe `AuthService`**

| Methode | Ligne | Role |
|---|---|---|
| `login(username, password)` | 10 | Recherche par username **ou** email ; verifie activite puis mot de passe (hash) ; met a jour `last_login` et journalise la connexion. Retourne `(user, None)` ou `(None, message)`. |
| `change_password(user_id, old, new)` | 27 | Verifie l'ancien mot de passe puis met a jour. |
| `random_password()` | 36 | Mot de passe temporaire aleatoire (12 caracteres hexa). |
| `derniere_connexions(limit=20)` | 40 | Journal des connexions (nom, role, date). |

**Classe `RoleAuthorizer`** (permissions par role)

- `NAV` (ligne 48) : pages autorisees par role :
  - `admin` : `dashboard`, `comptes` ;
  - `directeur` : `dashboard`, `eleves`, `classes`, `notes`, `planning`,
    `caisse`, `personnel`, `parametres` ;
  - `gestionnaire` : `dashboard`, `eleves`, `classes`, `notes`, `planning`,
    `caisse`.
- `allowed(page)` (60) : la page est-elle autorisee ?
- `can_edit(page)` (64) : qui peut saisir ? `comptes` -> seul admin ;
  sinon -> le gestionnaire oui, les autres non.

### 8.2 `services/api.py` (386 lignes) — client de l'API FastAPI

L'app peut afficher les indicateurs depuis un backend REST FastAPI
(`http://127.0.0.1:8000`). Si l'API est hors ligne, elle **bascule
automatiquement sur la base locale** : l'utilisateur ne voit aucune erreur.

| Element | Ligne | Role |
|---|---|---|
| `ApiError` | 11 | Exception interne (jamais exposee a l'interface). |
| `_request(method, path, **kwargs)` | 16 | Envoie une requete HTTP et normalise `(donnees, erreur)`. Toutes les erreurs reseau sont interceptees. |
| `_CacheDispo` | 41 | Memorise pendant 5 s si l'API repond (evite de tester a chaque appel). |
| `api_disponible(force=False)` | 57 | L'API est-elle joignable ? |
| `ApiClient` | 64 | Un client par domaine : eleves/classes, paiements, enseignants, notes, presences, annees scolaires. Chaque methode renvoie `(donnees, erreur)`. |
| `client` | 386 | Instance unique utilisee par les dashboards. |

Exemples de methodes : `total_eleves()`, `eleve_recherche(...)`,
`total_montant_paiement()`, `paiements()`, `enseignants()`, `ajouter_eleve(...)`.

La barre d'etat de la fenetre principale affiche l'etat de la connexion :
**« API : connectee »** ou **« API : hors ligne (mode local) »**
(main_view.py:113-118).

### 8.3 `services/reports.py` (193 lignes) — documents HTML

Tous les documents sont generes en **HTML** dans `DOCS_DIR` puis **ouverts
dans le navigateur** (`QDesktopServices.openUrl`). Pas de dependance PDF.

| Element | Ligne | Role |
|---|---|---|
| `STYLE` | 9 | CSS des documents (tableaux bordes, en-tete vert `#047857`). |
| `_open_in_browser(path)` | 19 | Ouvre un fichier local dans le navigateur. |
| `_write(title, body, filename)` | 25 | Ecrit le HTML complet et l'ouvre. |
| `_entete_doc()` | 34 | En-tete generique (nom du logiciel, pays/ville, date). |
| `export_eleves_csv(eleves)` | 45 | CSV (`;`, BOM) dans `data/`. |
| `bulletins(classe_id, periode)` | 59 | Bulletins d'une classe. Moyenne par matiere : `(d1 + d2 + 2xcomp) / 4`, moyenne generale ponderee. |
| `recu_paiement(...)` | 98 | Recu de paiement. |
| `certificat_scolarite(eleve, params)` | 117 | Certificat avec le signataire (parametres). |
| `paie()` | 137 | Bulletins de paie du mois + masse salariale. |
| `rapport_rh()` | 152 | Rapport RH mensuel. |
| `planning(classe)` | 165 | Emploi du temps d'une classe. |
| `_appreciation(moyenne)` | 181 | Mention : >=16 Excellent, >=14 Tres bien, >=12 Bien, >=10 Assez bien, >=8 Passable, sinon Insuffisant. |

---

## 9. Couche presentation : le dossier `views/`

### 9.1 `views/loader.py` (26 lignes)

| Fonction | Ligne | Role |
|---|---|---|
| `_make_responsive(widget)` | 8 | Applique `QSizePolicy.Expanding` **uniquement a la page racine** (volontaire : l'expansion forcee sur les enfants etire les boutons en blocs geants). |
| `load_ui(relative_path, widget=None)` | 18 | Charge un `.ui` via `PyQt5.uic.loadUi`, rend la page responsive. |
| `apply_ui(relative_path, widget)` | 24 | Applique un `.ui` a un widget existant (MainWindow, dialogues). |

### 9.2 `views/main_view.py` (191 lignes)

| Element | Ligne | Role |
|---|---|---|
| `NAV_PAGES` | 9 | Correspondance `bouton sidebar -> page` (dashboard, eleves, caisse, classes, notes, planning, personnel, parametres, comptes). |
| `DASHBOARD_BUILDERS` | 21 | `role -> fabrique de dashboard` (admin/directeur/gestionnaire). |
| `BUILDERS` | 27 | `page -> fabrique` (eleves, caisse, classes, notes, planning, personnel, parametres, comptes). |

Classe `MainWindow(QMainWindow)` (ligne 39) :

| Methode | Ligne | Role |
|---|---|---|
| `__init__(user)` | 40 | Stocke l'utilisateur, cree `PageContext`, applique `main.ui`, remplit les labels, cree le label de statut API, cable la navigation, construit les pages, navigue vers `dashboard`. |
| `_refresh_api_status()` | 106 | Interroge `api.api_disponible()` et met a jour le label de la barre d'etat. |
| `logout()` | 123 | Confirme puis ferme la fenetre. |
| `_wire_nav()` | 128 | Affiche les boutons autorises, masque les autres. |
| `_build_pages()` | 138 | Construit les pages autorisees dans des `QScrollArea` ; toute erreur affiche un libelle rouge. |
| `navigate(page_name)` | 173 | Bascule la page, appelle `refresh()`, coche le bouton. |

### 9.3 `views/login_view.py` (125 lignes)

| Element | Ligne | Role |
|---|---|---|
| `PRIMARY` / `PRIMARY_DARK` | 11-12 | Couleurs du bouton de connexion (`#047857` / `#065f46`). |
| `_Gradient(QFrame)` | 15 | Arriere-plan en degrade peint via `QPainter.paintEvent`. |
| `LoginDialog(QDialog)` | 25 | Dialogue de connexion 700x540. |
| `_build()` | 34 | Construit l'interface **en code** : carte blanche arrondie, champs nom/mot de passe, bouton degrade, rappel des comptes de test. |
| `_do_login()` | 112 | Appelle `auth.login`, affiche l'erreur si besoin, sinon stocke `self.user` et `accept()`. |

### 9.4 `views/pages.py` (1455 lignes) — les pages metier

C'est le cœur de l'interface. Chaque fabrique suit le meme contrat :
`fabrique(page, ctx)` remplit le widget `page`, connecte les signaux et expose
`page.refresh`.

**Contexte commun**

| Element | Ligne | Role |
|---|---|---|
| `PageContext` | 22 | Wrapper : `user`, `role`, `authorizer`, `navigate`, `can_edit(page)`. |

**Utilitaires**

| Fonction | Ligne | Role |
|---|---|---|
| `_btn(text, callback, style)` | 33 | Bouton compact (hauteur max 28 px, curseur main). |
| `_simple_btn_style(...)` | 42 | Style de bouton discret (fond clair, bordure). |
| `_money_edit(...)` | 46 | Champ montant en FCFA. |
| `_today_fr()` | 55 | Date du jour en francais. |
| `_fill_combos(combo, items)` | 62 | Remplit une combo. |

**Dashboards**

| Fabrique | Ligne | Role |
|---|---|---|
| `dashboard_admin` | 69 | KPIs des comptes (actifs, inactifs), dernieres connexions, actions rapides (nouveau compte, reinitialiser un mot de passe). |
| `dashboard_directeur` | 99 | Masse salariale, enseignants (API), taux de scolarite (API), graphiques (tresorerie 6 mois, effectifs par classe, personnel), validations (classes sans titulaire -> double-clic), actions (paie, rapport RH, auditer la caisse, recrutement). |
| `dashboard_gestionnaire` | 204 | KPIs (eleves, inscriptions du jour, encaissements du jour, dossiers incomplets), activite recente, dossiers incomplets, graphique des statuts, actions rapides (inscrire, recette, depense, certificat). |
| `_directeur_charts()` | 175 | Donnees des graphiques du directeur (6 mois, 6 premieres classes). |
| `_replace_layout(layout, widget)` | 195 | Remplace le contenu d'un layout par un graphique. |

Les KPIs des dashboards utilisent l'API **quand elle est disponible** (ex.
`total_eleves`, `total_montant_paiement`, `total_enseignant`), sinon les
valeurs de la base locale.

**Page Eleves**

| Element | Ligne | Role |
|---|---|---|
| `eleves(page, ctx)` | 269 | Tableau des eleves. **Par defaut, une classe est preselectionnee** (la premiere) ; l'option « Toutes les classes » reste disponible. Filtres classe/statut/recherche, boutons Modifier/Supprimer par ligne, double-clic pour modifier, export CSV, 4 KPIs recalcules sur la classe choisie. |
| `open_inscription_dialog(parent, ctx, eleve=None)` | 348 | Dialogue d'inscription (1000x780) : apercu du matricule, **reinscription** par recherche de matricule, classe (creation a la volee), dossier complet (naissance, parents, adresse, documents), montant verse + mode de reglement (encaisse automatiquement, recu imprimable). |
| `_parse_money(text)` | 531 | Parse un montant saisi (espaces, virgules, « FCFA »). |

**Page Classes**

| Element | Ligne | Role |
|---|---|---|
| `classes(page, ctx)` | 538 | Tableau des classes (nom, effectif, capacite, titulaire, salle) ; alerte rouge quand la classe est pleine ; recherche ; 4 KPIs. |
| `open_classe_dialog(parent, ctx, classe=None, on_created=None)` | 606 | Creer/modifier une classe (nom, niveau, capacite, salle, titulaire). |

**Page Notes**

| Element | Ligne | Role |
|---|---|---|
| `notes(page, ctx)` | 654 | Saisie par classe x matiere x periode : tableau editable, moyenne `(d1+d2+2xcomp)/4` et appreciation calculees en direct, bornage 0-20, ajout de matiere, generation des bulletins. Les boutons de saisie sont masques si le role ne peut pas saisir. |
| `_appreciation(moyenne)` | 800 | Mention locale (identique a `reports._appreciation`). |

**Page Planning**

| Element | Ligne | Role |
|---|---|---|
| `PlanningCellDialog` | 813 | Dialogue pour affecter matiere + salle a une case. |
| `planning(page, ctx)` | 845 | Grille jours (6 colonnes) x creneaux (8 lignes). Mode edition : double-clic pour affecter, « Enregistrer le Planning » reecrit tout. Bouton d'impression -> HTML. |

**Page Caisse**

| Element | Ligne | Role |
|---|---|---|
| `caisse(page, ctx)` | 959 | Tableau des transactions filtre par type, recherche et dates (mois courant par defaut). Colonnes Entree/Sortie separees, total entrees, total sorties, solde. Export CSV. Boutons Recette/Depense masques si le role ne saisit pas. |
| `open_transaction_dialog(parent, ctx, type_trans)` | 1037 | Saisie motif, beneficiaire, montant, categorie, mode de reglement. |

**Page Comptes (admin)**

| Element | Ligne | Role |
|---|---|---|
| `comptes(page, ctx)` | 1083 | Tableau des comptes (nom, email, role, actif), filtres, actions par ligne (Activer/Desactiver, Mdp, Supprimer), 4 KPIs. |
| `open_compte_dialog(parent, ctx, compte=None)` | 1148 | Creer/modifier un compte ; mot de passe temporaire genere et affiche. |
| `open_change_password_dialog(parent, user)` | 1194 | Changer son propre mot de passe. |
| `open_reset_password_dialog(parent, ctx)` | 1223 | Reinitialiser le mot de passe d'un compte non-admin. |

**Page Personnel**

| Element | Ligne | Role |
|---|---|---|
| `personnel(page, ctx)` | 1249 | Tableau du personnel construit **en code** (nom, fonction, telephone, email, salaire), recherche, « + Nouvel Employe ». |
| `open_personnel_dialog(parent, ctx, employe=None)` | 1320 | Creer/modifier un employe (fonction, salaire, statut Contrat/CDI/Vacataire/Stage). |

**Certificat**

| Element | Ligne | Role |
|---|---|---|
| `open_certificat_dialog(parent)` | 1366 | Dialogue **filtre par classe** : choisir la classe puis l'eleve, et genere le certificat de scolarite. |

**Parametres**

| Element | Ligne | Role |
|---|---|---|
| `parametres(page, ctx)` | 1403 | Signataire (nom/titre), ville, pays + images (bandeau haut/bas, signature) copiees dans `DOCS_DIR`. Bouton supprimer la configuration. |

### 9.5 `views/widgets.py` (176 lignes) — graphiques et formats

| Element | Ligne | Role |
|---|---|---|
| `CHART_COLORS` | 8 | Palette de couleurs des graphiques. |
| `_color(i)` | 13 | Couleur par index (cycle sur la palette). |
| `fmt_money(montant)` | 17 | `1 234 567 FCFA` (separateur d'espace). |
| `fmt_money_short(montant)` | 24 | Sans le suffixe « FCFA ». |
| `_BaseChart(QWidget)` | 28 | Base commune des graphiques (marge, titre, anti-aliasing). |
| `SimpleBarChart` | 70 | Histogramme (valeurs au-dessus des barres, echelle Y). `set_data(labels, values)`. |
| `SimplePieChart` | 117 | Camembert (pourcentages, legende). `set_data(labels, values)`. |

---

## 10. Fichiers `.ui`

Les interfaces sont definies dans `views/ui_files/` et chargees par
`apply_ui`. Les fichiers reellement utilises :

| Fichier | Charge par | Role |
|---|---|---|
| `main.ui` | `main_view.py:83` | Fenetre principale (sidebar + stackedWidget + labels + bouton deconnexion). |
| `dashboards/dashboard_admin.ui` | `pages.py:70` | Accueil admin. |
| `dashboards/dashboard_directeur.ui` | `pages.py:100` | Accueil directeur. |
| `dashboards/dashboard_gestionnaire.ui` | `pages.py:205` | Accueil gestionnaire. |
| `eleves/eleves.ui` | `pages.py:270` | Liste des eleves. |
| `eleves/inscription.ui` | `pages.py:352` | Dossier d'inscription. |
| `classes/classes.ui` | `pages.py:539` | Liste des classes. |
| `classes/classe_dialog.ui` | `pages.py:610` | Dialogue classe. |
| `notes/notes.ui` | `pages.py:655` | Saisie des notes. |
| `planning/planning.ui` | `pages.py:846` | Emploi du temps. |
| `caisse/caisse.ui` | `pages.py:960` | Caisse. |
| `comptes/comptes.ui` | `pages.py:1084` | Liste des comptes. |
| `comptes/compte_dialog.ui` | `pages.py:1152` | Dialogue compte. |
| `parametres/parametres.ui` | `pages.py:1404` | Parametres des documents. |

---

## 11. Base de donnees SQLite : schema complet

Fichier : `data/ecole.db`. Cree par `SCHEMA` (db.py:7).

### Tables

**`utilisateurs`** — comptes de connexion

| Colonne | Type | Contrainte |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| nom_complet | TEXT | NOT NULL |
| username | TEXT | NOT NULL UNIQUE |
| email | TEXT | — |
| telephone | TEXT | — |
| password | TEXT | NOT NULL (hash sha256) |
| role | TEXT | NOT NULL |
| actif | INTEGER | NOT NULL DEFAULT 1 |
| created_at | TEXT | DEFAULT datetime('now','localtime') |
| last_login | TEXT | — |

**`classes`** : id, nom (NOT NULL), niveau, capacite (INTEGER DEFAULT 50),
salle, titulaire

**`matieres`** : id, nom (TEXT NOT NULL UNIQUE), coefficient (REAL DEFAULT 1)

**`eleves`** : id, matricule (UNIQUE), nom (NOT NULL), prenom (NOT NULL),
sexe, date_naissance, lieu_naissance, classe_id (FK -> classes),
ecole_provenance, pere_nom, pere_tel, mere_nom, mere_tel, tuteur_nom,
tuteur_tel, adresse, check_acte / check_photos / check_bulletin (INTEGER
DEFAULT 0), statut (TEXT DEFAULT 'Inscrit'), date_inscription (TEXT DEFAULT
date('now','localtime'))

**`notes`** : id, eleve_id (FK), matiere_id (FK), periode (TEXT),
devoir1 / devoir2 / composition (REAL), **UNIQUE(eleve_id, matiere_id, periode)**

**`transactions`** : id, date (DEFAULT aujourd'hui), reference (NOT NULL),
beneficiaire, motif, categorie, montant (REAL NOT NULL),
type (CHECK IN ('entree','sortie')), mode_reglement

**`planning`** : id, classe_id (FK), jour (TEXT), creneau (TEXT), matiere,
salle, **UNIQUE(classe_id, jour, creneau)**

**`connexions`** : id, utilisateur_id (FK), date_connexion (DEFAULT maintenant)
-> journal d'audit des connexions.

**`personnel`** : id, nom_complet (NOT NULL), fonction, telephone, email,
salaire (REAL DEFAULT 0), statut (DEFAULT 'Contrat')

**`parametres`** : cle (TEXT PK), valeur (TEXT) -> paires cle/valeur
(`signataire_nom`, `signataire_titre`, `ville`, `pays`, `frais_scolarite`,
`bandeau_haut`, `bandeau_bas`, `signature`).

### Comptes par defaut (crees au premier lancement)

| Nom | Identifiant | Mot de passe | Role |
|---|---|---|---|
| Administrateur Systeme | admin | admin123 | admin |
| Directeur de l'Ecole | directeur | directeur123 | directeur |
| Gestionnaire Scolaire | gestionnaire | gestionnaire123 | gestionnaire |

> **A changer** des la mise en production reelle.

---

## 12. Roles et permissions

| Action | admin | directeur | gestionnaire |
|---|---|---|---|
| Voir le dashboard | OUI (comptes) | OUI | OUI |
| Gerer les comptes | OUI | NON | NON |
| Gerer les eleves | NON | consulter | saisir |
| Gerer les classes | NON | consulter | saisir |
| Saisir les notes | NON | NON | OUI |
| Gerer le planning | NON | consulter | saisir |
| Caisse (recettes/depenses) | NON | NON | OUI |
| Personnel / RH | NON | OUI (paie, rapports) | NON |
| Parametres des documents | NON | OUI | NON |

- Navigation : `RoleAuthorizer.NAV` (auth.py:48) — les boutons de la sidebar
  sont masques selon le role (main_view.py:128).
- Saisie : `RoleAuthorizer.can_edit` (auth.py:64) — les boutons d'ajout et de
  modification sont masques quand le role ne peut pas saisir.

---

## 13. Construction des executables

### Executable Linux

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/pyinstaller --noconfirm --clean --onefile --windowed \
  --name GestionScolaire \
  --add-data "views/ui_files:views/ui_files" \
  main.py
```

Sortie : `dist/GestionScolaire` (one-file, sans console). Les `.ui` sont
embarques via `--add-data`. Hidden imports : `PyQt5.uic`, `PyQt5.uic.plugins`,
`PyQt5.QtSql`.

### Executable Windows (via GitHub Actions)

Le workflow `.github/workflows/build_windows.yml` construit l'exe Windows sur
chaque `push` vers la branche `exe` :

1. `checkout` du code ;
2. `setup-python` 3.11 ;
3. installation de `requirements.txt` + `pyinstaller` ;
4. `pyinstaller --noconfirm --clean build_win.spec` (one-file, sans console) ;
5. depose de `dist/GestionScolaire.exe` comme **artefact** de la run.

L'artefact est telechargeable depuis la page Actions du depot GitHub
(`Actions -> Build Windows Executable -> Artifact`).

### Spec Windows (`build_win.spec`)

`build_win.spec` construit un **one-file** nomme `GestionScolaire.exe`, sans
console, en embarquant `views/ui_files` et le manifeste DPI.

### Manifeste DPI Windows (`win_dpi_manifest.xml`)

Le manifeste declare `<dpiAware>true</dpiAware>`. Il est **embarque dans
l'exe** par `build_win.spec` (`EXE(manifest=...)`). Combine au
`_setup_high_dpi` de main.py, il rend le texte net sur les ecrans Windows
100/125/150/200 %.

> Le fichier n'est pas signe : Windows SmartScreen peut afficher un
> avertissement au premier lancement (« Informations supplementaires ->
> Executer quand meme »).

### Verification apres build

- Lancer l'executable : il doit rester vivant et creer `data/ecole.db`.
- Windows : tester avec `QT_SCALE_FACTOR=1.25` pour simuler un ecran 125 %.

---

## 14. Guide d'utilisation par role

### Connexion

Identifiants de test : `admin/admin123`, `directeur/directeur123`,
`gestionnaire/gestionnaire123` (rappeles sur l'ecran de connexion).

### Gestionnaire (saisie quotidienne)

1. **Inscription** : dashboard -> « Inscrire » -> remplir le dossier (nom,
   prenom obligatoires, classe obligatoire) -> montant verse eventuel -> recu
   imprimable. Reinscription : saisir le matricule -> « Rechercher ».
2. **Eleves** : la liste s'ouvre sur la **premiere classe** ; changer la
   classe avec la liste deroulante ou choisir « Toutes les classes ». Les
   chiffres (KPIs) se mettent a jour sur la classe choisie.
3. **Classes** : creer/modifier (nom, niveau, capacite, salle, titulaire).
4. **Notes** : choisir classe, matiere, periode -> « Charger » -> saisir ->
   « Enregistrer les notes ». Moyenne et appreciation calculees en direct.
5. **Planning** : choisir la classe -> « Modifier » -> double-cliquer sur une
   case pour affecter matiere/salle -> « Enregistrer le Planning ».
6. **Caisse** : « + Recette » / « + Depense ». Filtres par type, texte et
   dates. Export CSV.
7. **Certificat** : dashboard -> « Certificat » -> choisir la **classe** puis
   l'**eleve** -> « Generer ».

### Directeur (supervision)

- Dashboard : masse salariale, taux de scolarite, graphiques, validations
  (classes sans titulaire -> double-clic pour affecter), actions « Paie »,
  « Rapport RH », « Auditer la caisse ».
- Consulte eleves/classes/notes/planning/caisse/personnel/parametres **sans
  pouvoir saisir** (les boutons d'edition sont masques).
- Parametres : renseigne le signataire (nom/titre), la ville, le pays et les
  images d'en-tete/signature des documents.

### Admin (comptes uniquement)

- Dashboard : comptes actifs/inactifs, dernieres connexions.
- Page Comptes : creer un compte (mot de passe temporaire affiche),
  activer/desactiver, reinitialiser le mot de passe, supprimer.
- Ne voit ni les eleves, ni la caisse, ni les notes (sidebar reduite).

### Documents generes (HTML ouverts dans le navigateur)

Bulletins (page Notes), recu de paiement (inscription), certificat de
scolarite, paie + rapport RH (dashboard directeur), emploi du temps (planning).
Les fichiers sont stockes dans `data/documents/`.

---

## 15. Depannage et questions frequentes

| Probleme | Cause / solution |
|---|---|
| L'executable ne s'ouvre pas / crashe silencieusement | Lancer depuis un terminal pour voir l'erreur, ou lire la boite « Erreur inattendue » du `_excepthook`. |
| L'API FastAPI n'est pas lancee | L'app affiche « API : hors ligne (mode local) » dans la barre d'etat et fonctionne quand meme sur la base locale. |
| Les chiffres du dashboard semblent differents | Sans API, les indicateurs viennent de la base locale ; avec API, ils viennent du serveur. C'est le comportement attendu. |
| « Module not found » en build | `hiddenimports` necessaires : `PyQt5.uic`, `PyQt5.uic.plugins`, `PyQt5.QtSql`. |
| Texte flou sur Windows | Verifier que le manifeste est embarque et que `_setup_high_dpi` est execute avant `QApplication`. |
| Boutons / champs geants | Ne jamais forcer `QSizePolicy.Expanding` sur les enfants d'une page (voir `_make_responsive`). |
| Base ecrasee / perdue | `data/ecole.db` vit a cote de l'exe. Sauvegarder ce fichier. |
| Fichier CSV illisible dans Excel | Le CSV utilise `;` et un BOM (`utf-8-sig`) — compatible Excel francophone. |
| SmartScreen bloque l'exe Windows | L'exe n'est pas signe : « Informations supplementaires -> Executer quand meme ». |
| Documents HTML generes | Ils s'ouvrent dans le navigateur par defaut ; ranges dans `data/documents/`. |

---

## 16. Historique des versions

| Version | Contenu |
|---|---|
| 1.0.x | Prototype : API FastAPI + prototype web. |
| 1.1.x | Bascule desktop PyQt5 + SQLite, architecture a 3 couches. |
| 1.2.x | **Version actuelle** : pages metier completes, dashboards par role, client API FastAPI avec repli local, filtre des eleves par classe par defaut, certificat filtrable, exe Windows construit via GitHub Actions, exe Linux one-file. Code nettoye : tous les docstrings supprimes, commentaires courts en francais. |

---

*Fin de la documentation. Les references de lignes correspondent au code
source de la version 1.2.0 (branche `exe`).*
