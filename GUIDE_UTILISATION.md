# GUIDE D'UTILISATION COMPLET — LOGICIEL DE GESTION SCOLAIRE

**Version du logiciel : 1.2.0 (interface)** — Technologie : Python 3 + PyQt5 + SQLite
**Contexte : Republique du Congo (Brazzaville)** — Devise : FCFA — Indicatif : +242

Ce guide vous accompagne pas a pas dans l'utilisation quotidienne du logiciel Gestion Scolaire : installation, connexion, chaque module detaille champ par champ, cas d'usage reels, situations particulieres et resolution des problemes.

---

## 1. A propos de ce guide

### 1.1 Objectif
Ce guide a ete redige pour les trois profils d'utilisateurs du logiciel : **l'administrateur**, **le directeur** et **le gestionnaire**. Il explique, dans le moindre detail :

- comment installer et demarrer le logiciel ;
- comment se connecter et comprendre les differents roles ;
- comment utiliser chaque ecran du logiciel, champ par champ ;
- les cas d'usage concrets de la vie d'un etablissement scolaire (rentree, inscription, notes, caisse, paie...) ;
- les situations particulieres et comment les resoudre.

### 1.2 Comment lire ce guide
- Les **sections 1 a 5** presentent le logiciel, l'installation et l'interface generale.
- Les **sections 6 a 13** detailent chaque module (eleves, classes, notes, emploi du temps, caisse, personnel, parametres, documents).
- Les **sections 14 a 17** couvrent les cas d'usage, le depannage et les bonnes pratiques.

Les libelles de boutons, de champs et les messages affiches par le logiciel sont reproduits exactement tels qu'ils apparaissent a l'ecran.

### 1.3 Vocabulaire utilise
| Terme | Signification |
|---|---|
| FCFA | Francs CFA, la devise utilisee dans tout le logiciel |
| Matricule | Numero unique attribue a chaque eleve (ex. `ELEV20260001`) |
| Trimestre | Periode d'evaluation : 1er, 2eme ou 3eme |
| Statut | Situation d'un eleve : Inscrit, Pre-inscrit, Inactif (historiquement : Transfert, Exclu) |
| Recette | Argent qui entre dans la caisse (encaissement) |
| Depense | Argent qui sort de la caisse (decaissement) |
| Solde | Difference entre les entrees et les sorties |

---

## 2. Le logiciel en un coup d'oeil

### 2.1 Presentation
Le logiciel **Gestion Scolaire** est une application de bureau autonome destinee a un etablissement scolaire congolais. Elle fonctionne sur un seul poste, sans connexion Internet, et stocke toutes ses donnees dans un fichier local.

Elle couvre l'ensemble de la vie scolaire :

- **les eleves** : inscription, reinscription, dossier complet (acte de naissance, photos, bulletin), matricule automatique ;
- **les classes** : creation, capacite, salle, professeur titulaire ;
- **les notes** : saisie par matiere et par trimestre, generation des bulletins ;
- **l'emploi du temps** : planning hebdomadaire par classe ;
- **la caisse** : recettes et depenses, solde, export CSV ;
- **les comptes utilisateurs** : 3 roles (administrateur, directeur, gestionnaire) ;
- **le personnel** : gestion des salaries et des salaires (RH) ;
- **les documents** : bulletins, recus de paiement, certificats de scolarite, bulletins de paie, rapports RH, emplois du temps, au format HTML.

### 2.2 Fonctionnalites principales

| Domaine | Ce que fait le logiciel |
|---|---|
| Eleves | Inscription / reinscription, dossier complet, matricule automatique `ELEV2026XXXX`, recherche, filtres, export CSV |
| Classes | 26 classes sur 13 niveaux (CI a Terminale), capacite, titulaire, salle, alerte « classe complete » |
| Notes | Saisie bornee 0 a 20, moyenne automatique, appreciation, bulletins imprimables |
| Emploi du temps | Grille hebdomadaire (6 jours, 8 creneaux) par classe, impression |
| Caisse | Recettes et depenses, categories, modes de reglement, solde, export CSV, audit |
| Personnel & RH | Fiches salaries, salaires, bulletin de paie, rapport RH mensuel |
| Comptes | Creation / desactivation / reinitialisation de mots de passe |
| Parametres | Nom et titre du signataire, ville, pays, bandeaux et signature des documents |
| Documents | Bulletins, recus, certificats, paie, rapport RH, emplois du temps en HTML |

### 2.3 Les donnees du logiciel
Toutes les donnees sont enregistrees dans un dossier `data/` situe **a cote du programme** :

| Fichier | Contenu |
|---|---|
| `data/ecole.db` | La base de donnees complete (eleves, classes, notes, caisse, comptes, personnel...) |
| `data/documents/` | Tous les documents generes (bulletins, recus, certificats, paie...) au format HTML |

Au premier lancement, le logiciel cree une base **quasi vierge** : les 3 comptes par defaut, les 8 matieres, les parametres et 3 membres du personnel de depart. Les eleves, classes et operations de caisse sont saisis par vos soins dans l'application. Pour repartir d'une base vierge, voir la section 15.4.

---

## 3. Installation et premier demarrage

### 3.1 Installation sous Windows (recommandee)
1. **Telechargez** le fichier executable `GestionScolaire.exe`.
2. Placez-le dans le dossier de votre choix (ex. `C:\GestionScolaire\`).
3. **Double-cliquez** sur `GestionScolaire.exe` : aucune installation n'est necessaire.
4. Au premier lancement, le logiciel cree automatiquement le dossier `data/` a cote de l'executable, avec la base de donnees `ecole.db` et le dossier `documents/`.

> Aucune connection Internet n'est requise pour faire fonctionner le logiciel. L'antivirus Windows peut demander une autorisation au premier lancement : acceptez.

### 3.2 Lancement depuis le code source (Linux)
1. Ouvrez un terminal dans le dossier du projet.
2. Creez l'environnement virtuel et installez les dependances :
```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```
3. Lancez le logiciel :
```bash
venv/bin/python main.py
```

### 3.3 Premier demarrage
Au premier lancement, le logiciel effectue automatiquement :

1. la **creation de la base de donnees** `data/ecole.db` ;
2. l'insertion des **comptes par defaut** (admin, directeur, gestionnaire) ;
3. l'insertion des **8 matieres** de base (Francais, Mathematiques, Anglais, Histoire-Geographie, SVT, Physique-Chimie, Education Civique, Informatique) ;
4. l'insertion des **parametres** de l'etablissement (ville : Brazzaville, pays : Republique du Congo, frais de scolarite : 25 000 FCFA).

L'ecran de connexion s'affiche alors.

### 3.4 Mise a jour du logiciel
Pour mettre a jour le logiciel :

1. **Fermez** le logiciel.
2. **Sauvegardez** le dossier `data/` (c'est lui qui contient vos donnees).
3. Remplacez l'executable par la nouvelle version.
4. Relancez : vos donnees sont conservees car la base `data/ecole.db` n'est pas modifiee.

> Regle d'or : l'executable change, mais le dossier `data/` reste celui de votre etablissement.

---

## 4. Connexion et comptes

### 4.1 L'ecran de connexion
Au demarrage, un ecran de connexion s'affiche avec un fond degrade vert et une carte blanche. Il contient :

- le titre **GESTION SCOLAIRE** et la mention **Connexion - v1.2.0** ;
- un champ **Identifiant** ;
- un champ **Mot de passe** (masque) ;
- le bouton **Se connecter**.

La touche **Entree** du clavier declenche egalement la connexion.

### 4.2 Les comptes par defaut
Le logiciel est livre avec trois comptes de demonstration :

| Nom complet | Identifiant | Mot de passe | Role |
|---|---|---|---|
| Administrateur Systeme | admin | admin123 | Administrateur |
| Directeur de l'Ecole | directeur | directeur123 | Directeur |
| Gestionnaire Scolaire | gestionnaire | gestionnaire123 | Gestionnaire |

Ces rappels sont affiches directement en bas de l'ecran de connexion.

> **Securite** : changez ces mots de passe des la premiere utilisation (voir section 4.5).

### 4.3 Se connecter
1. Saisissez votre **identifiant** (le nom d'utilisateur OU l'adresse email du compte).
2. Saisissez votre **mot de passe**.
3. Cliquez sur **Se connecter**.

Cas particuliers :

| Situation | Message affiche |
|---|---|
| Champ vide | « Veuillez saisir l'identifiant et le mot de passe. » |
| Identifiant ou mot de passe faux | « Identifiant ou mot de passe incorrect. » |
| Compte desactive | « Ce compte est desactive. Contactez l'administrateur. » |

### 4.4 Les roles et leurs droits
Le logiciel distingue **trois roles**. Chaque connexion ouvre une fenetre dont la navigation est adaptee au role : les boutons des pages non autorisees sont simplement masques.

| Page | Administrateur | Directeur | Gestionnaire |
|---|---|---|---|
| Tableau de bord | Oui (administration) | Oui (direction) | Oui (journee) |
| Liste des Eleves | — | Oui | Oui |
| Classes | — | Oui | Oui |
| Notes et Bulletins | — | Oui (consultation) | Oui (saisie) |
| Emploi du Temps | — | Oui | Oui |
| Gestion Caisse | — | Oui (audit, lecture) | Oui (saisie) |
| Personnel & RH | — | Oui | Oui |
| Parametres Etablissement | — | Oui | — |
| Gestion des Comptes | Oui | — | — |

**En resume :** le **gestionnaire** saisit (eleves, caisse, notes) ; le **directeur** supervise et pilote (consultation + parametres + RH) ; l'**administrateur** gere uniquement les comptes d'acces et la connexion.

### 4.5 Changer son mot de passe
Le bouton **Changer mon mot de passe** est accessible dans la fenetre principale. La boite de dialogue demande :

- **Ancien mot de passe** ;
- **Nouveau mot de passe** ;
- **Confirmer** (saisie du nouveau mot de passe une seconde fois).

Messages possibles :
- « Les nouveaux mots de passe ne correspondent pas. »
- « Ancien mot de passe incorrect. »
- « Mot de passe mis a jour. »

### 4.6 Gestion des comptes (role administrateur uniquement)
La page **Gestion des Comptes** permet a l'administrateur de gerer les acces des directeurs et gestionnaires. Elle affiche le nombre total de comptes, de directeurs, de gestionnaires et de comptes inactifs, ainsi qu'un tableau avec les colonnes : Nom, Email, Role, Statut (Actif/Inactif), Date de creation, Actions.

**Creer un compte :**
1. Cliquez sur **+ Nouveau Compte**.
2. Renseignez : **Nom** (ex. Jean Dupont), **Email** (ex. exemple@ecole.com), **Telephone** (ex. 01 23 45 67 89), **Role** (Gestionnaire ou Directeur).
3. Cochez **Compte actif des la creation** si le compte doit etre utilisable immediatement.
4. Cliquez sur **Creer le compte**.
5. Le logiciel genere automatiquement : l'**identifiant** (la partie avant le `@` de l'email) et un **mot de passe temporaire aleatoire**, qui s'affiche dans une fenetre. **Notez-le** et transmettez-le au nouvel utilisateur.

> Un compte administrateur ne peut pas etre cree depuis le logiciel : il n'existe que le compte `admin` par defaut.

**Activer / desactiver un compte :** cliquez sur **Activer** ou **Desactiver** dans la ligne du compte. Un compte desactive ne peut plus se connecter (« Ce compte est desactive. Contactez l'administrateur. »).

**Reinitialiser un mot de passe :** cliquez sur **Mdp** (couleur ambre). Le logiciel propose un nouveau mot de passe aleatoire et demande confirmation. Un message « Mot de passe reinitialise. » confirme l'operation. Transmettez le nouveau mot de passe a l'utilisateur.

**Supprimer un compte :** cliquez sur **Supprimer**. La suppression est immediate (les historiques de connexions du compte sont egalement supprimes).

**Rechercher / filtrer :** utilisez la zone de recherche (« Rechercher par nom ou email... ») et le filtre par role (« Tous les roles », « Directeur », « Gestionnaire »), puis **Filtrer**.

### 4.7 Se deconnecter
Le bouton **Se deconnecter** (en bas de la barre laterale) ferme la session apres confirmation « Voulez-vous vraiment vous deconnecter ? » et ramene a l'ecran de connexion.

---

## 5. Comprendre l'interface

### 5.1 La fenetre principale
Apres connexion, la fenetre principale s'ouvre **en plein ecran** avec le titre « Gestion Scolaire - {nom complet de l'utilisateur} ». Elle se compose de :

1. **une barre laterale** a gauche : logo « Gestion Scolaire », boutons de navigation (visibles selon votre role), nom et role de l'utilisateur connecte, bouton **Se deconnecter** ;
2. **une zone centrale** : la page active (tableau de bord ou module) ;
3. **une barre d'etat** en bas : « Connecte comme {role} », « Page active : {page} », et un indicateur de connexion au serveur de statistiques : **« API : connectee »** ou **« API : hors ligne (mode local) »**. En mode hors ligne, tout fonctionne normalement avec les donnees locales.

### 5.2 La barre laterale (navigation)

| Bouton | Page ouverte |
|---|---|
| Tableau de bord | Le tableau de bord adapte a votre role |
| Liste des Eleves | Gestion des eleves |
| Gestion Caisse | Recettes, depenses, solde |
| Classes | Gestion des classes |
| Notes et Bulletins | Saisie des notes et bulletins |
| Emploi du Temps | Planning hebdomadaire |
| Personnel && RH | Salaries et salaires |
| Parametres Etablissement | Configuration des documents |
| Gestion des Comptes | Comptes utilisateurs (admin) |

Le bouton de la page active reste encoche. Le clic sur un bouton bascule immediatement la page et actualise son contenu.

### 5.3 Le tableau de bord selon le role

**Administrateur — « Administration du Systeme »** (Gestion des comptes et de l'acces) :
- indicateurs : comptes actifs, directeurs actifs, gestionnaires actifs, comptes inactifs ;
- liste des 20 dernieres connexions (date, nom, role) ;
- boutons : **+ Nouveau Compte**, **Voir tous les comptes**, **Reinitialiser un mot de passe**.

**Directeur — « Tableau de Bord - Direction Generale »** (Pilotage strategique) :
- indicateurs : masse salariale mensuelle, nombre d'enseignants, demandes en attente, taux de recouvrement des frais de scolarite ;
- 3 graphiques : flux de tresorerie sur 6 mois, effectifs des classes, repartition du personnel par fonction ;
- tableau des **validations en attente** (classes sans titulaire) : double-cliquez sur une ligne pour ouvrir la page Classes et affecter un titulaire ;
- boutons : **Gerer le Personnel**, **+ Nouveaux Contrats / Enseignants**, **Valider les Bulletins de Paie**, **Exporter Rapport RH Mensuel**, **Auditer les Entrees / Sorties Caisse**.

**Gestionnaire — « Bonjour, Gestionnaire »** (Resume de la journee) :
- date du jour en francais ;
- indicateurs : effectif total, inscriptions du jour, encaissements du jour, dossiers incomplets ;
- liste des 8 dernieres transactions (date, motif, +/- montant) ;
- liste des **dossiers incomplets** (eleves auxquels il manque l'acte de naissance, les photos ou le bulletin) ;
- graphique de repartition des eleves par statut ;
- boutons d'action rapide : **+ Inscrire un Eleve**, **+ Nouvelle Recette**, **+ Nouvelle Depense**, **Imprimer un Certificat**.
---

## 6. Gestion des eleves

### 6.1 La liste des eleves
La page **Gestion des Eleves** affiche : Total Eleves, Pre-inscriptions, Eleves Actifs, Eleves Inactifs, ainsi qu'un tableau avec les colonnes : Matricule, Nom et Prenom, Classe, Sexe, Date Naissance, Contact Parent, Statut, Actions (boutons Modifier bleu / Supprimer rouge).

**Filtres disponibles :**
- **classe** : « Toutes les classes » ou une classe precise. **La liste s'ouvre par defaut sur la premiere classe** (pour une lecture plus lisible) ; choisissez « Toutes les classes » pour voir l'effectif complet ;
- **statut** : « Tous les statuts », « Inscrit », « Pre-inscrit », « Inactif » ;
- **recherche** : saisissez un nom, un prenom ou un matricule (« Rechercher par nom, prenom ou matricule... »).

Les 4 chiffres en haut (Total Eleves, Pre-inscriptions, Eleves Actifs, Eleves Inactifs) se recalculent sur la **classe choisie**. Le bouton **Filtrer** applique les criteres ; le tableau se recharge aussi automatiquement a chaque modification des criteres.

**Actions sur une ligne :**
- **Double-clic** sur une ligne : ouvre le dossier complet de l'eleve (modification) ;
- **Modifier** (bleu) : ouvre le formulaire de modification ;
- **Supprimer** (rouge) : supprime l'eleve (apres confirmation « Supprimer l'eleve {prenom} {nom} ? »). Les notes de l'eleve sont supprimees en meme temps.

**Exporter la liste :** le bouton **Exporter la Liste** genere un fichier `eleves_AAAAMMJJ.csv` (colonne « ; », compatible Excel) contenant : Matricule, Nom, Prenom, Sexe, Date Naissance, Classe, Contact Tuteur, Statut. Le fichier s'ouvre automatiquement.

### 6.2 Inscrire un nouvel eleve
Cliquez sur **Inscrire un Eleve** (page Eleves) ou **+ Inscrire un Eleve** (tableau de bord gestionnaire). Le formulaire **Dossier d'Inscription** s'ouvre. Champs :

| Champ | Details |
|---|---|
| Nouvelle Inscription / Reinscription | Choisissez **Nouvelle Inscription** |
| Nom de famille | **Obligatoire** (placeholder « Nom de famille * ») |
| Prenoms | **Obligatoire** |
| Sexe | Masculin / Feminin |
| Date de naissance | Au format AAAA-MM-JJ |
| Lieu de naissance | Facultatif |
| Classe | Choisissez la classe, ou creez-en une avec **+ Classe** |
| Etablissement de provenance | Facultatif (ancien etablissement) |
| Pere (nom, telephone) | Facultatif |
| Mere (nom, telephone) | Facultatif |
| Tuteur Legal / Contact d'urgence | Nom du tuteur (placeholder « Tuteur Legal / Contact d'urgence * ») |
| Tel Principal Tuteur | Telephone du tuteur, pour les notifications (placeholder « Tel Principal Tuteur (Notif WhatsApp) * ») |
| Adresse de la famille | Facultative |
| Acte de naissance (Copie certifiee) | Case a cocher si le document est fourni |
| 2 Photos d'identite recentes | Case a cocher |
| Dernier bulletin de notes | Case a cocher |
| Montant verse (Droits / Acompte) | Montant encaisse a l'inscription (peut rester a 0) |
| Mode de reglement | Especes / Mobile Money (MTN / Moov) / Cheque / Virement |

**Matricule automatique :** le logiciel affiche en vert le matricule qui sera attribue : format `ELEV{annee}{numero}` (ex. `ELEV20260001`).

**Enregistrer :** cliquez sur **Enregistrer & Imprimer Recu**.

Regles et messages :

| Situation | Comportement |
|---|---|
| Nom ou prenom absent | « Le nom et le prenom sont obligatoires. » |
| Aucune classe choisie | « Selectionnez une classe (ou creez-en une). » |
| Montant verse > 0 | Une transaction **Recette** est creee : motif « Droits de scolarite - inscription », categorie « Inscription », beneficiaire `{prenom} {nom}`, mode choisi |
| Inscription enregistree | Message « Eleve inscrit. Matricule : ... » puis question « Eleve inscrit. Matricule : ...\n{montant} encaisse.\nImprimer le recu ? » |
| Cliquez **Oui** | Le recu de paiement s'ouvre dans le navigateur (« RECU DE PAIEMENT ») |
| Cliquez **Non** | Le recu n'est pas imprime |

Le statut de l'eleve est **« Pre-inscrit »** lors d'une nouvelle inscription (statut « Inscrit » lors d'une reinscription).

### 6.3 Reinscrire un eleve
1. Dans le formulaire d'inscription, choisissez **Reinscription**.
2. Saisissez le **matricule** de l'eleve (« Matricule (reinscription) ») et cliquez sur **Rechercher**.
3. Le formulaire se **preremplit** automatiquement avec les informations de l'eleve et affiche « Reinscription de {prenom} {nom} ». La recherche se desactive.
4. Verifiez / corrigez les informations, saisissez le cas echeant le montant verse, puis **Enregistrer & Imprimer Recu**.

Message si le matricule est inconnu : « Aucun eleve trouve avec le matricule {matricule}. »

### 6.4 Modifier le dossier d'un eleve
- Double-cliquez sur la ligne de l'eleve, ou cliquez sur **Modifier**.
- Le formulaire s'ouvre avec le titre « Modifier - {prenom} {nom} ».
- Le champ **Montant verse** et le **mode de reglement** sont desactives en mode modification (les operations de caisse se font dans la page Caisse).
- Le bouton devient **Enregistrer les Modifications**. Un message « {prenom} {nom} mis a jour. » confirme.

### 6.5 Supprimer un eleve
Cliquez sur **Supprimer** dans la ligne de l'eleve. Confirmez avec « Supprimer l'eleve {prenom} {nom} ? ». Les notes de l'eleve sont supprimees en cascade.

### 6.6 Les statuts d'un eleve
- **Inscrit** : eleve inscrit pour l'annee en cours (le statut devient « Inscrit » apres une reinscription) ;
- **Pre-inscrit** : nouvelle inscription enregistree ;
- **Inactif** : eleve qui ne frequente plus (filtre « Inactif ») ;
- Historiquement, la base d'exemple peut contenir des eleves **Transfert** ou **Exclu** : ils apparaissent dans la liste avec leur statut d'origine.

> Conseil : pour un eleve qui quitte l'ecole, mettez a jour son dossier (ex. mention dans le nom, ou statut inactif) plutot que de le supprimer, afin de conserver l'historique des paiements et notes.

---

## 7. Gestion des classes

### 7.1 La liste des classes
La page **Gestion des Classes** affiche : TOTAL CLASSES, EFFECTIF TOTAL, CLASSES COMPLETES, SANS TITULAIRE, ainsi qu'un tableau avec les colonnes : Nom de la Classe, Niveau, Effectif, Capacite Max, Titulaire, Salle, Actions (Modifier / Supprimer).

**Recherche / filtre :** saisissez un nom de classe (« Rechercher par nom de classe... ») ou choisissez un niveau (« Tous les niveaux » + niveaux).

**Alerte « classe complete » :** lorsque l'effectif atteint ou depasse la capacite maximale, la cellule **Effectif devient rouge** avec le message « Classe complete ». Inscrivez plutot les nouveaux eleves dans une autre classe, ou augmentez la capacite (voir 7.2).

**Affecter un titulaire :** double-cliquez sur la ligne de la classe (ou **Modifier**) et choisissez le titulaire dans la liste.

### 7.2 Creer ou modifier une classe
Cliquez sur **+ Classe** (page Classes, ou bouton **+ Classe** du formulaire d'inscription). La boite de dialogue **Nouvelle Classe** demande :

| Champ | Details |
|---|---|
| Nom de la classe | **Obligatoire** (ex. 6eme A) |
| Niveau | 6eme, 5eme, 4eme, 3eme, 2nde, 1ere, Terminale, CI, CP, CE1... |
| Capacite maximale | Nombre maximal d'eleves (defaut 50) |
| Salle | Facultatif (ex. Salle 12) |
| Titulaire | « -- A affecter plus tard -- » ou un membre du personnel |

Message si le nom manque : « Le nom de la classe est obligatoire. »

En modification, le bouton devient **Enregistrer la classe**.

### 7.3 Supprimer une classe
Cliquez sur **Supprimer** : confirmation « Supprimer la classe {nom} et ses eleves ? ». La suppression efface **les eleves de la classe et l'emploi du temps de la classe**. A n'utiliser qu'apres avoir verifie que les eleves concernes n'ont plus de donnees utiles.

---

## 8. Notes et bulletins

### 8.1 Le principe
Les notes sont saisies **par classe, par matiere et par trimestre**. Chaque eleve a, pour chaque matiere et chaque trimestre : **Devoir 1 /20**, **Devoir 2 /20** et **Composition /20**. La moyenne est calculee automatiquement.

### 8.2 Saisir les notes
1. Ouvrez la page **Notes et Bulletins**.
2. Choisissez : la **classe**, la **matiere** (ex. Mathematiques) et la **periode** (« 1er Trimestre », « 2eme Trimestre », « 3eme Trimestre »).
3. Cliquez sur **Charger les Eleves** : le tableau se remplit (colonnes Matricule, Nom et Prenom, Devoir 1 /20, Devoir 2 /20, Composition /20, Moyenne, Appreciation).
4. Saisissez les notes (uniquement des nombres de 0 a 20) :
   - une valeur hors de 0-20 est automatiquement ramenee dans les bornes ;
   - un texte non numerique est efface.
5. La **Moyenne** se calcule en direct : moyenne = `(Devoir 1 + Devoir 2 + 2 × Composition) / 4`.
6. Cliquez sur **Enregistrer les Notes**. Message final : « {n} notes enregistrees. »

**Important :** l'enregistrement est un enregistrement/ecrasement par eleve, matiere et trimestre : resaisir une note pour le meme eleve/matiere/trimestre **remplace** l'ancienne valeur.

**Ajouter une matiere :** si une matiere manque, cliquez sur **+ Matiere**, saisissez son nom dans la boite « Nouvelle matiere », validez. La matiere est alors disponible dans la liste.

> Seul le **gestionnaire** peut saisir les notes. Le **directeur** consulte en lecture seule (le bouton Enregistrer est masque).

### 8.3 Generer les bulletins
1. Choisissez la **classe** et la **periode**.
2. Cliquez sur **Generer les Bulletins** (message si classe manquante : « Choisissez une classe. »).
3. Le fichier `bulletins_{classe}_{trimestre}.html` s'ouvre dans votre navigateur.

Chaque bulletin affiche :
- pour chaque matiere : Devoir 1, Devoir 2, Composition et la **moyenne de la matiere** ;
- la **moyenne generale** : somme des (moyenne × coefficient de la matiere) divisee par la somme des coefficients ;
- l'**appreciation** selon le bareme.

**Bareme d'appreciation :**

| Moyenne | Appreciation |
|---|---|
| 16 et plus | Excellent |
| 14 a 16 | Tres bien |
| 12 a 14 | Bien |
| 10 a 12 | Assez bien |
| 8 a 10 | Passable |
| Moins de 8 | Insuffisant |

Le bulletin peut etre imprime depuis le navigateur (Ctrl+P) ou sauvegarde en PDF.

---

## 9. Emploi du temps

### 9.1 La grille hebdomadaire
La page **Emploi du Temps** affiche le planning d'une classe sur 6 jours (Lundi a Samedi) et 8 creneaux :

| Creneau | Horaire |
|---|---|
| 1 | 07h30 - 08h20 |
| 2 | 08h20 - 09h10 |
| 3 | 09h10 - 10h00 |
| — | **10h00 - 10h20 (Pause)** |
| 4 | 10h20 - 11h10 |
| 5 | 11h10 - 12h00 |
| — | **12h00 - 13h30 (Pause dejeuner)** |
| 6 | 13h30 - 14h20 |

Chaque cellule contient la matiere et la salle : `Matiere (Salle)`. Les creneaux de pause ne sont pas modifiables.

### 9.2 Modifier le planning
1. Choisissez la **classe** (message « Choisissez d'abord une classe. » si aucune).
2. Cliquez sur **Modifier** (le bouton devient **Enregistrer le Planning**).
3. **Double-cliquez** sur une cellule a remplir.
4. Dans la fenetre « {jour} - {creneau} », choisissez la matiere (« -- Libre -- » pour laisser vide) et la **salle**, puis OK.
5. Repetez pour chaque cellule, puis cliquez sur **Enregistrer le Planning**. Message : « Emploi du temps enregistre. »

### 9.3 Imprimer le planning
Cliquez sur **Imprimer** : le fichier `planning_{classe}.html` s'ouvre dans le navigateur avec la grille complete (creneau × jours). Imprimez-le ou sauvegardez-le en PDF depuis le navigateur.

---

## 10. Gestion de la caisse

### 10.1 La page Caisse
La page **Gestion de la Caisse** affiche :
- **Total des Entrees**, **Total des Sorties** et **Solde Actuel Caisse** ;
- un tableau des transactions : Date, Reference, Beneficiaire / Eleve, Motif / Libelle, Categorie, Entree, Sortie, Actions (Supprimer).

Le montant est place dans la colonne Entree ou Sortie selon le type de transaction.

### 10.2 Filtrer et rechercher
- **type** : « Toutes les transactions », « Recettes uniquement », « Depenses uniquement » ;
- **periode** : date de debut et date de fin (le logiciel affiche par defaut le **mois en cours**) ;
- **recherche** : « Rechercher un eleve, un motif, une reference... ».

Cliquez sur **Filtrer** pour appliquer.

### 10.3 Enregistrer une recette (encaissement)
1. Cliquez sur **Nouvelle Recette** (ou **+ Nouvelle Recette** sur le tableau de bord gestionnaire).
2. Renseignez :
   - **Motif** (placeholder « Ex: Droits de scolarite, Fournitures... ») — si vide, le motif sera « Sans motif » ;
   - **Beneficiaire / Eleve** (ex. nom de l'eleve ou du payeur) — si vide, « - » ;
   - **Montant** (en FCFA, minimum 1) ;
   - **Categorie** : Scolarite, Inscription, Tenues, Autres ;
   - **Mode** : Especes, Mobile Money (MTN / Moov), Cheque / Virement.
3. Cliquez sur **Valider**. La reference est generee automatiquement : `REC-XXXXXXXX` (ex. `REC-3F9A22B1`). Message : « Transaction enregistree. »

> Lors d'une **inscription avec montant verse**, une recette est creee automatiquement (motif « Droits de scolarite - inscription », categorie « Inscription »).

### 10.4 Enregistrer une depense (decaissement)
1. Cliquez sur **Nouvelle Depense**.
2. Renseignez : **Motif**, **Beneficiaire / fournisseur**, **Montant**, **Categorie** (Fournitures, Salaires, Entretien, Transport, Autres), **Mode** (Especes, Virement, Cheque).
3. **Valider**. Reference automatique `DEP-XXXXXXXX`. Message : « Transaction enregistree. »

### 10.5 Supprimer une transaction
Cliquez sur **Supprimer** dans la ligne : confirmation « Supprimer cette transaction ? ». **Attention** : si la transaction provient d'une inscription, la supprimer ne modifie pas le dossier de l'eleve, mais le solde de la caisse change.

### 10.6 Exporter la caisse en CSV
1. Cliquez sur **Exporter CSV**.
2. Choisissez l'emplacement et le nom du fichier (defaut `transactions.csv`).
3. Le fichier (separateur « ; », compatible Excel) contient : Date, Reference, Beneficiaire, Motif, Categorie, Type, Montant, Mode. Message : « Exporte vers {chemin} ».

### 10.7 L'audit par le directeur
Le directeur accede a la caisse **en lecture seule** : il voit les totaux, le detail et peut exporter, mais les boutons Nouvelle Recette / Nouvelle Depense sont masques. C'est le dispositif de controle : seule la personne chargee de la caisse (gestionnaire) saisit, le directeur verifie.

---

---

## 11. Personnel & RH

### 11.1 La page Personnel & RH
La page **Personnel & RH** (accessibles au directeur et au gestionnaire) presente la liste des salaries avec les colonnes : Nom complet, Fonction, Telephone, Email, Salaire, Actions (Modifier / Supprimer).

Une zone de recherche (« Rechercher un membre du personnel... ») filtre la liste au fil de la saisie.

### 11.2 Ajouter un employe
Cliquez sur **+ Nouvel Employe** (ou **+ Nouveaux Contrats / Enseignants** sur le tableau de bord du directeur). La boite **Nouvel Employe** demande :

| Champ | Details |
|---|---|
| Nom complet | **Obligatoire** |
| Fonction | Ex. Enseignant Mathematiques |
| Telephone | Facultatif |
| Email | Facultatif |
| Salaire | Montant mensuel en FCFA |
| Statut | Contrat, CDI, Vacataire, Stage |

Message si le nom manque : « Le nom est obligatoire. »

### 11.3 Modifier ou supprimer un employe
- **Modifier** : ouvre le formulaire prerempli (bouton **Modifier Employe**).
- **Supprimer** : confirmation « Supprimer {nom_complet} ? ».

### 11.4 Valider les bulletins de paie
Cliquez sur **Valider les Bulletins de Paie** (tableau de bord directeur). Le logiciel genere le fichier `paie.html`, ouvert dans le navigateur, contenant pour chaque employe : Nom, Fonction, Statut, Salaire, puis la **masse salariale mensuelle** (total des salaires) en pied de tableau. Le titre porte le mois et l'annee en clair.

### 11.5 Exporter le rapport RH mensuel
Cliquez sur **Exporter Rapport RH Mensuel** (tableau de bord directeur). Le fichier `rapport_rh.html` s'ouvre dans le navigateur : effectif total, nombre d'enseignants et tableau Nom / Fonction / Telephone / Statut.

---

## 12. Parametres de l'etablissement

La page **Parametres Etablissement** (accessibles au directeur uniquement) configure l'en-tete des documents imprimes (recus, certificats, bulletins...).

### 12.1 Les champs
| Champ | Utilisation |
|---|---|
| Nom du signataire | Ex. M. Jean Makosso |
| Titre du signataire | Ex. Directeur General |
| Ville de la lettre | Ex. Brazzaville |
| Pays | Ex. Republique du Congo |

### 12.2 Les images des documents
Le bouton **Televerser** (trois boutons : bandeau d'en-tete, bandeau bas de page, image de signature) permet de choisir une image (PNG, JPG, JPEG) sur le disque. Le fichier est copie dans le dossier des documents avec un horodatage, et la mention « {image} choisi : {nom du fichier} » s'affiche.

### 12.3 Enregistrer ou supprimer
- **Mettre a jour la configuration** : enregistre les changements. Message « Configuration enregistree. »
- **Supprimer la configuration** : apres confirmation « Supprimer la configuration ? », efface le signataire, le titre et la ville. Message « Configuration supprimee. »

> Valeurs par defaut installees : signataire « M. Jean Makosso » (Directeur General), ville « Brazzaville », pays « Republique du Congo », frais de scolarite « 25000 » FCFA.

---

## 13. Les documents generes

Tous les documents sont generes au format **HTML** dans le dossier `data/documents/` et s'ouvrent automatiquement dans votre navigateur web. Depuis le navigateur, vous pouvez les **imprimer** (Ctrl+P) ou les **sauvegarder en PDF**.

| Document | Comment le generer | Fichier |
|---|---|---|
| Recu de paiement | Inscription avec montant verse, ou saisie d'une recette en caisse | `recu_{matricule}_{reference}.html` |
| Bulletin scolaire | Notes et Bulletins → **Generer les Bulletins** | `bulletins_{classe}_{trimestre}.html` |
| Certificat de scolarite | Tableau de bord gestionnaire → **Imprimer un Certificat**, choisir la **classe** puis l'**eleve**, **Generer** | `certificat_{matricule}.html` |
| Bulletin de paie | Tableau de bord directeur → **Valider les Bulletins de Paie** | `paie.html` |
| Rapport RH mensuel | Tableau de bord directeur → **Exporter Rapport RH Mensuel** | `rapport_rh.html` |
| Emploi du temps | Emploi du Temps → **Imprimer** | `planning_{classe}.html` |
| Liste des eleves | Liste des Eleves → **Exporter la Liste** | `eleves_AAAAMMJJ.csv` |
| Caisse | Caisse → **Exporter CSV** | `transactions.csv` |

Le **certificat de scolarite** reprend la formule « Nous, soussignes... », l'identite de l'eleve (nom, matricule, date et lieu de naissance), le tableau Classe / Statut / Date d'inscription, et les informations du signataire definies dans les Parametres.

---

## 14. Cas d'usage (scenarios de la vie reelle)

### 14.1 Cas n° 1 : preparer la rentree scolaire
1. **Creer les classes** : page **Classes** → **+ Classe** pour chaque classe de l'annee (ex. 6eme A, 6eme B, 5eme A...), avec niveau, capacite et salle.
2. **Affecter les titulaires** : modifier chaque classe pour choisir son titulaire parmi le personnel (ou **+ Nouvel Employe** pour recruter).
3. **Inscrire les eleves** : page **Eleves** → **Inscrire un Eleve**, un par un (ou reinscription avec le matricule de l'annee precedente). Saisissez le montant verse pour encaisser les droits a l'inscription et imprimer les recus.
4. **Verifier les dossiers** : le tableau de bord du gestionnaire signale les **dossiers incomplets** (acte, photos ou bulletin manquant) : recontactez les familles pour completer.
5. **Construire l'emploi du temps** : page **Emploi du Temps** → **Modifier** → remplissez les cellules de chaque classe → **Enregistrer le Planning** → **Imprimer** pour afficher en classe.

### 14.2 Cas n° 2 : inscrire un eleve en cours d'annee
1. Page **Eleves** → **Inscrire un Eleve** → onglet **Nouvelle Inscription**.
2. Renseignez l'identite (nom et prenom obligatoires), choisissez la classe (attention a la capacite : une cellule rouge signifie **classe complete**).
3. Cochez les documents fournis (acte, photos, bulletin), saisissez le montant verse et le mode de reglement.
4. **Enregistrer & Imprimer Recu** : le matricule est attribue automatiquement, le recu s'ouvre.
5. L'eleve apparait dans la liste avec le statut **Pre-inscrit**. Pensez ensuite a saisir ses notes dans chaque matiere (section 8).

### 14.3 Cas n° 3 : reinscrire un ancien eleve
1. **Inscrire un Eleve** → onglet **Reinscription**.
2. Saisissez le **matricule** et **Rechercher** : le dossier se preremplit.
3. Confirmez les informations et enregistrez. Le statut passe a **Inscrit**, l'historique de l'eleve est conserve.

### 14.4 Cas n° 4 : encaisser les frais de scolarite
1. Page **Caisse** → **Nouvelle Recette** (ou **+ Nouvelle Recette** du tableau de bord).
2. Motif : « Droits de scolarite - mois de ... », beneficiaire : nom de l'eleve, montant, categorie **Scolarite**, mode de reglement.
3. **Valider** : la reference `REC-...` est creee, le solde augmente.
4. Pour un recu papier : le **recu de paiement** est genere au moment de l'inscription (lorsqu'un montant est verse). Pour un paiement isole effectue plus tard, la transaction reste **tracable** par sa reference (`REC-...`) : conservez la reference pour vos echanges avec la famille. Le cas echeant, vous pouvez retrouver ou regenerer un recu en passant par une inscription avec montant verse.

### 14.5 Cas n° 5 : clore un trimestre
1. Saisissez les notes de chaque matiere et chaque classe (section 8).
2. **Generer les Bulletins** classe par classe : le fichier s'ouvre dans le navigateur.
3. Imprimez ou sauvegardez les bulletins en PDF, puis remettez-les aux familles.

### 14.6 Cas n° 6 : payer les salaires du mois
1. Verifiez la liste du personnel (page **Personnel & RH**) : salaires et statuts a jour.
2. Tableau de bord directeur → **Valider les Bulletins de Paie** : le bulletin affiche chaque salaire et la **masse salariale mensuelle**.
3. Encaissiere : page **Caisse** → **Nouvelle Depense**, motif « Paie du mois de ... », categorie **Salaires**, montant = masse salariale, mode choisi. **Valider** (reference `DEP-...`).

### 14.7 Cas n° 7 : auditer la caisse
Le **directeur** ouvre **Gestion Caisse** : il verifie les totaux d'entrees et de sorties, le solde, et le detail des operations de la periode (filtre par dates). Il peut **Exporter CSV** pour analyser dans Excel. Le gestionnaire, lui, saisit ; le directeur verifie : la separation des roles garantit le controle.

### 14.8 Cas n° 8 : recruter un enseignant en cours d'annee
1. Tableau de bord directeur → **+ Nouveaux Contrats / Enseignants** (ou page **Personnel & RH** → **+ Nouvel Employe**).
2. Renseignez nom, fonction (« Enseignant ... »), salaire et statut (Contrat, CDI, Vacataire, Stage).
3. **Affectez-le comme titulaire** d'une classe (page **Classes** → Modifier → Titulaire).
4. Il apparait dans les bulletins de paie et le rapport RH.

### 14.9 Cas n° 9 : un eleve quitte l'ecole
- **Transfert** ou **exclusion** : ne supprimez pas l'eleve (cela effacerait son historique de notes). Conservez son dossier pour reference ; le logiciel affiche son statut dans la liste.
- Si la suppression est vraiment necessaire (dossier cree par erreur) : bouton **Supprimer** avec confirmation, apres avoir verifie qu'aucune donnee utile ne sera perdue (notes supprimees en cascade).

### 14.10 Cas n° 10 : une classe est complete
La cellule **Effectif** devient **rouge** (« Classe complete ») quand l'effectif atteint la capacite. Deux options :
- inscrire les nouveaux eleves dans une autre classe ;
- ou augmenter la capacite de la classe (page **Classes** → **Modifier** → Capacite max).

### 14.11 Cas n° 11 : mot de passe oublie
1. Demandez a l'**administrateur** de reinitialiser le mot de passe : page **Gestion des Comptes** → bouton **Mdp** de la ligne du compte.
2. Le logiciel propose un nouveau mot de passe ; l'administrateur le transmet.
3. Connectez-vous avec ce mot de passe, puis changez-le (section 4.5).

### 14.12 Cas n° 12 : configuration des documents pour l'annee
1. Page **Parametres Etablissement** (directeur) : nom et titre du signataire (ex. Directeur General), ville, pays.
2. **Televersez** le bandeau d'en-tete, le bandeau de bas de page et la signature.
3. **Mettre a jour la configuration** : tous les documents generes ensuite (recus, certificats, bulletins) porteront ces informations.

---

## 15. Situations particulieres et depannage

### 15.1 Messages d'erreur et leur signification

| Message | Signification | Solution |
|---|---|---|
| « Veuillez saisir l'identifiant et le mot de passe. » | Champ de connexion vide | Saisissez vos identifiants |
| « Identifiant ou mot de passe incorrect. » | Mauvais identifiant ou mot de passe | Verifiez la saisie (ou l'email) ; sinon, demandez une reinitialisation a l'admin |
| « Ce compte est desactive. Contactez l'administrateur. » | Le compte a ete desactive | Contactez l'administrateur pour reactivation |
| « Le nom et le prenom sont obligatoires. » | Inscription incomplète | Renseignez le nom et le prenom |
| « Selectionnez une classe (ou creez-en une). » | Aucune classe choisie | Choisissez une classe ou creez-la |
| « Aucun eleve trouve avec le matricule {matricule}. » | Reinscription : matricule inconnu | Verifiez le matricule (ex. ELEV20260001) |
| « Le nom de la classe est obligatoire. » | Classe sans nom | Donnez un nom a la classe |
| « Choisissez une classe et une matiere. » | Notes : selection incomplete | Choisissez classe + matiere + periode |
| « Choisissez d'abord une classe. » / « Choisissez une classe. » | Planning ou bulletins sans classe | Selectionnez une classe |
| « Le montant doit etre superieur a 0. » | Transaction avec montant nul | Saisissez un montant positif |
| « Le nom complet et l'email sont obligatoires. » | Compte incomplet | Renseignez nom et email |
| « Les nouveaux mots de passe ne correspondent pas. » | Confirmation differente | Ressaisissez le nouveau mot de passe |
| « Mot de passe vide. » | Reinitialisation sans mot de passe | Le champ doit contenir un mot de passe |
| « Le nom est obligatoire. » | Employe sans nom | Renseignez le nom complet |
| « Erreur inattendue » (boite de dialogue) | Exception non geree | Notez le detail et contactez le support |

### 15.2 Le logiciel ne se lance pas
- Verifiez que le dossier `data/` est accessible en ecriture a cote de l'executable.
- Sous Windows, si l'antivirus bloque, autorisez l'execution.
- Depuis le code source, lancez depuis le terminal pour voir l'erreur eventuelle (`venv/bin/python main.py`).

### 15.3 Les documents ne s'ouvrent pas
Les documents necessitent un navigateur web. Si rien ne s'ouvre :
- verifiez que le dossier `data/documents/` existe et est accessible en ecriture ;
- ouvrez le fichier HTML directement depuis ce dossier dans un navigateur.

### 15.4 Sauvegarder et restaurer les donnees
Toutes les donnees sont dans le dossier `data/` :
1. **Fermez** le logiciel.
2. Copiez le dossier `data/` (ou au moins le fichier `data/ecole.db`) vers un support sur (cle USB, disque externe, cloud).
3. Pour **restaurer** : remplacez le fichier `ecole.db` par la sauvegarde, puis relancez le logiciel.

Pour **repartir d'une base vierge** : fermez le logiciel, supprimez (ou renommez) le fichier `data/ecole.db`, relancez : le logiciel recree une base neuve avec les comptes par defaut, les 8 matieres, les parametres et les 3 employes initiaux.

### 15.5 L'affichage est flou (Windows)
Le logiciel est fourni avec un manifeste de haute resolution (DPI) : l'affichage est net sur les ecrans haute densite. Si un ecran externe reste flou, verifiez que l'ecran principal est defini avec une echelle de 100 % dans les parametres d'affichage Windows.

### 15.6 Attention aux valeurs par defaut
- Le **frais de scolarite** par defaut est de **25 000 FCFA** (utilise pour le calcul du taux de recouvrement du directeur).
- Les **recus et certificats** utilisent la ville definie dans les Parametres (Brazzaville par defaut).

---

## 16. Bonnes pratiques

1. **Changez les mots de passe par defaut** des la premiere utilisation, et utilisez des mots de passe differents par role.
2. **Sauvegardez regulierement** le dossier `data/` (chaque semaine au minimum, et toujours avant une mise a jour).
3. **Saisissez les notes trimestre par trimestre** et enregistrez apres chaque seance de saisie (le bouton Enregistrer les Notes ecrase les valeurs d'un meme eleve/matiere/trimestre).
4. **Completez les dossiers des eleves** : cochez acte de naissance, photos et bulletin des l'arrivee des documents ; le tableau de bord gestionnaire vous rappelle les dossiers incomplets.
5. **Respectez la separation des roles** : le gestionnaire saisit la caisse et les notes, le directeur verifie et audite, l'administrateur gere uniquement les comptes.
6. **Verifiez le solde de caisse** regulierement et rapprochez avec les recus remis aux familles.
7. **Ne supprimez pas un eleve ou une classe** sans avoir exporte ou note les informations utiles (notes et paiements sont effaces en cascade).
8. **Documentez les references** : chaque operation de caisse porte une reference unique (REC-/DEP-) ; utilisez-les dans vos echanges avec les familles et fournisseurs.
9. **Mettez a jour les parametres** (signataire, ville, images) avant de generer des documents officiels.
10. **Conservez les HTML generes** : le dossier `data/documents/` constitue votre archive des bulletins, recus et paies.

---

## 17. Foire aux questions (FAQ)

**Q : Puis-je utiliser le logiciel sans connexion Internet ?**
R : Oui. Le logiciel est entierement local (base de donnees dans `data/ecole.db`). Il peut en plus se connecter a un petit serveur local de statistiques (`API`), mais si celui-ci n'est pas lance, la barre d'etat affiche « API : hors ligne (mode local) » et tout continue de fonctionner avec les donnees locales.

**Q : Combien d'eleves puis-je inscrire ?**
R : Sans limite. Chaque classe a une capacite affichee ; un excedent est signale par une cellule rouge.

**Q : Peut-on avoir plusieurs gestionnaires ou directeurs ?**
R : Oui. L'administrateur cree autant de comptes Gestionnaire ou Directeur que necessaire dans **Gestion des Comptes**.

**Q : Que se passe-t-il si je ressaisis des notes pour le meme eleve, la meme matiere et le meme trimestre ?**
R : Les anciennes notes sont **remplacees** (enregistrement/ecrasement). Ressaisissez en toute confiance pour corriger.

**Q : Comment sont calculées les moyennes ?**
R : Moyenne d'une matiere = (Devoir 1 + Devoir 2 + 2 × Composition) / 4. Moyenne generale = moyenne ponderee par les coefficients des matieres.

**Q : Les documents sont-ils imprimables ?**
R : Oui. Chaque document s'ouvre dans le navigateur : utilisez l'impression (Ctrl+P) ou « Enregistrer en PDF ».

**Q : Puis-je ouvrir le logiciel sur plusieurs ordinateurs ?**
R : L'application est mono-poste. Pour plusieurs postes, utilisez le fichier `ecole.db` sur un poste partage, ou pensez a une future version en reseau.

**Q : J'ai oublie le mot de passe administrateur.**
R : Il n'existe pas de porte de secours dans l'interface. Si la base est vierge, supprimez `data/ecole.db` et relancez : les comptes par defaut seront recrees. Sinon, contactez le support.

**Q : L'ecran de connexion affiche des identifiants de test. Sont-ils reels ?**
R : Ce sont les comptes par defaut livres avec le logiciel (admin, directeur, gestionnaire). Changez leurs mots de passe pour la production.

**Q : Une transaction a ete saisie par erreur. Que faire ?**
R : Supprimez-la depuis la page **Caisse** (bouton **Supprimer** de la ligne, apres confirmation). Le solde est recalcule immediatement.

---

**Fin du guide.** Pour toute autre question, consultez la documentation technique du projet (`DOCUMENTATION.pdf`) ou contactez le support de l'etablissement.
