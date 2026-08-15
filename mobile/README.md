# Version mobile (APK) — Gestion Scolaire

Application mobile **responsive** du logiciel de gestion scolaire, construite
avec **Kivy**. Elle réutilise le backend partagé du dépôt (base SQLite,
`core/`, `database/`, `repositories/`, `services/`) : une seule source de
vérité, aucune duplication de la logique métier.

## Structure

```
mobile/
├── main.py                    # point d'entrée (ajoute le backend au sys.path)
├── requirements.txt           # dépendances pour lancer en local (desktop)
├── buildozer.spec             # configuration du build APK (buildozer)
├── scripts/build_apk.sh       # prépare la source et lance buildozer
└── app/
    ├── main.py                # classe Kivy App (navigation login -> accueil)
    ├── theme.py               # couleurs (même charte que la version desktop)
    ├── utils.py               # formatage, grilles adaptatives (responsive)
    ├── widgets.py             # composants réutilisables (StatCard, ListItem...)
    └── screens/
        ├── login_screen.py        # connexion (services.auth)
        ├── home_screen.py         # accueil + tiroir de navigation selon le rôle
        ├── dashboard_screen.py    # indicateurs, effectifs, paiements récents
        ├── eleves_screen.py       # liste + recherche + ajout
        ├── eleve_detail_screen.py # fiche élève + solde
        ├── classes_screen.py      # liste des classes -> élèves
        ├── caisse_screen.py       # entrées / sorties / solde
        ├── placeholder_screen.py  # pages pas encore portées sur mobile
        └── forms.py               # formulaires popup (élève, opération)
```

## Lancer en local (desktop, pour développer)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Sur desktop, une fenêtre 430x900 simule un téléphone. Les données sont lues
dans `data/ecole.db` (partagées avec la version desktop). Sur Android, les
données sont écrites dans le stockage privé de l'application
(`GS_DATA_DIR` -> `core/config.data_dir()`).

## Construire l'APK

Prérequis (Debian/Ubuntu) :

```bash
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool \
    pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake \
    libffi-dev libssl-dev
pip install buildozer cython
```

Puis :

```bash
cd mobile
./scripts/build_apk.sh
```

L'APK (debug) est produit dans `mobile/bin/` :
`GestionScolaire-1.2.0-arm64-v8a-debug.apk`.

- Le premier build télécharge Android SDK/NDK dans `~/.buildozer` (plusieurs
  centaines de Mo, un peu long).
- `scripts/build_apk.sh` régénère `mobile/build_src/` (backend partagé + app
  Kivy) pour que l'APK soit toujours synchronisé avec le dépôt.

## État d'avancement

Pages portées sur mobile : tableau de bord, élèves (liste/recherche/ajout/
fiche), classes, caisse. Les autres pages (notes, présences, planning,
personnel, tarifs, paiements, paramètres, comptes) affichent pour l'instant
un écran « arrive bientôt » dans le tiroir de navigation ; elles peuvent être
portées une à une en suivant le même patron (`home_screen._make_page` +
`PAGE_LABELS` + `IMPLEMENTED`).
