# Structure finale des vues -- a copier dans views/ui_files/

## Arborescence

```
views/ui_files/
|-- main.ui                          Fenetre principale (sidebar + zone de contenu)
|
|-- dashboards/
|   |-- dashboard_admin.ui           Accueil du role Admin
|   |-- dashboard_directeur.ui       Accueil du role Directeur
|   `-- dashboard_gestionnaire.ui    Accueil du role Gestionnaire
|
|-- eleves/
|   |-- eleves.ui                    Liste + recherche des eleves
|   `-- inscription.ui               Dossier d'inscription complet
|
|-- classes/
|   |-- classes.ui                   Liste des classes
|   `-- classe_dialog.ui             Creer/modifier une classe
|
|-- notes/
|   `-- notes.ui                     Saisie des notes + generation bulletins
|
|-- planning/
|   `-- planning.ui                  Emploi du temps hebdomadaire
|
|-- caisse/
|   `-- caisse.ui                    Encaissements / decaissements
|
|-- comptes/
|   |-- comptes.ui                   Liste des comptes (role Admin)
|   `-- compte_dialog.ui             Creer un compte Directeur/Gestionnaire
|
`-- parametres/
    `-- parametres.ui                En-tete/pied de page des documents
```

Organisation par module plutot que tout a plat : c'est ainsi que
s'organisent la plupart des logiciels de gestion scolaire (chaque
domaine metier -- scolarite, finances, administration -- est un dossier
a part). Ca facilite aussi le travail a plusieurs : chacun peut avancer
dans son dossier sans risquer d'ecraser le travail d'un autre.

## Pourquoi 3 dashboards et pas 1 seul avec des sections cachees

Les 3 roles font des choses fondamentalement differentes au quotidien :
- **Admin** : ne touche jamais aux eleves/classes/notes -- juste les
  comptes et l'acces a l'application
- **Gestionnaire** : saisie quotidienne (inscriptions, notes, caisse)
- **Directeur** : supervision, chiffres cles, validations

Plutot qu'un seul dashboard avec plein de blocs masques selon le role
(fragile, difficile a maintenir), chaque role a sa page d'accueil
dediee. Le controller choisit laquelle charger apres le login :

```python
DASHBOARDS = {
    "admin": "dashboards/dashboard_admin.ui",
    "directeur": "dashboards/dashboard_directeur.ui",
    "gestionnaire": "dashboards/dashboard_gestionnaire.ui",
}
dashboard_path = DASHBOARDS[user.role]
```

## Navigation dans la sidebar (main.ui), par role

```python
NAV_PAR_ROLE = {
    "admin": ["btn_nav_dashboard", "btn_nav_comptes"],
    "directeur": ["btn_nav_dashboard", "btn_nav_eleves", "btn_nav_classes",
                  "btn_nav_notes", "btn_nav_planning", "btn_nav_caisse",
                  "btn_nav_personnel", "btn_nav_parametres"],
    "gestionnaire": ["btn_nav_dashboard", "btn_nav_eleves", "btn_nav_classes",
                      "btn_nav_notes", "btn_nav_planning", "btn_nav_caisse"],
}

def appliquer_nav_role(view, role):
    tous_les_boutons = ["btn_nav_dashboard", "btn_nav_eleves", "btn_nav_classes",
                          "btn_nav_notes", "btn_nav_planning", "btn_nav_caisse",
                          "btn_nav_comptes", "btn_nav_personnel", "btn_nav_parametres"]
    autorises = NAV_PAR_ROLE[role]
    for nom_bouton in tous_les_boutons:
        widget = getattr(view, nom_bouton)
        widget.setVisible(nom_bouton in autorises)
```

## Fusion de l'inscription elevee (doublon resolu)

`inscription_dialog.ui` (version courte, en fenetre modale) et
`inscription_eleve.ui` (dossier complet) faisaient doublon. La version
courte est archivee -- gardez uniquement `eleves/inscription.ui`, le
dossier complet, plus realiste pour un vrai etablissement (contacts
pere ET mere, tuteur, ecole de provenance).

## Regles de saisie par role (rappel)

- **Gestionnaire** : peut inscrire un eleve, creer une classe, saisir
  les notes, encaisser/decaisser
- **Directeur** : consulte tout, valide, exporte -- ne saisit pas
- **Admin** : gere uniquement les comptes, n'a acces a rien d'autre

```python
if user.role == "directeur":
    eleves_view.btn_add_eleve.setVisible(False)        # eleves/eleves.ui
    classes_view.btn_nouvelle_classe.setVisible(False)  # classes/classes.ui
    notes_view.btn_save_notes.setVisible(False)         # notes/notes.ui
    caisse_view.btn_add_expense.setVisible(False)       # caisse/caisse.ui
    caisse_view.btn_add_income.setVisible(False)
```

## CE QUI MANQUE ENCORE (toujours honnete)

- Aucune logique reelle nulle part -- ce sont des maquettes visuelles
- Pas de gestion des matieres ni des enseignants (notes.ui et
  planning.ui en ont besoin pour fonctionner vraiment)
- `login.ui` reste un fichier separe, pas inclus ici
- La grille de `planning.ui` est statique (jours/creneaux fixes dans
  le .ui) -- pas encore editable dynamiquement
- Aucune generation reelle de PDF (bulletins, certificats)
- Le "reset mot de passe" et "dernieres connexions" du dashboard admin
  sont des boutons/zones vides -- aucun systeme d'audit/log n'existe
  encore cote base de donnees
