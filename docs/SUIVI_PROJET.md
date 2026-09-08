# SUIVI PROJET — Gestion Scolaire

> Memoire de travail du projet. Ce fichier est la reference pour ne rien
> oublier : historique des modifications, decisions, plans, taches en cours.
> Toute session de travail doit le lire au debut et le mettre a jour a la fin.

## Etat actuel du projet

- **Version** : v1.5.0 (branche `installers`)
- **Architecture** :
  - App bureau PyQt5 + SQLite locale (offline-first) dans `core/`, `ui/`,
    `services/`, `repositories/`, `database/`
  - Sync multi-postes optionnelle via API FastAPI + MySQL dans `server/`
    (compatibilite client/serveur dans `server/compat.py`)
- **Tests** : **301 tests verts** (`tests/` bureau + `server/`, dont
  `server/test_routes_exercice.py` et 19 tests d'apprentissage autonome IA) +
  exercices fonctionnels couvrant toutes les routes serveur et les
  repositories/services : **SQLite 122/122, MySQL réel 122/122,
  desktop 80/80, services 28/28** (session 2026-09-09)
- **Derniers commits** : securisation P0 serveur (JWT, rate-limit, audit),
  integration du serveur, session persistante verrouillee par tests

## Decisions d'architecture importantes

| Decision | Raison |
|---|---|
| SQLite local + MySQL central optionnel | L'ecole doit fonctionner meme sans reseau |
| Couche `server/compat.py` additive | Ne pas casser les routes historiques du serveur ni celles du client |
| Session persistante locale (`parametres.dernier_utilisateur_id`) | Exigence utilisateur : jamais d'identification sauf deconnexion volontaire |
| Secrets par `.env` / variables GS_* | Aucun mot de passe ni cle JWT dans le code |

## Historique des modifications (anti-oubli)

### Session 2026-09-08 — Audit « senior » des branches + correction des 12 erreurs de tests et des bugs serveur

**Demande : continuer les modifications, mettre a jour architecture + base de
donnees selon la branche `gestion_scolaire`, ne pas oublier que l'app est
PLURI-UTILISATEURS et utilise MYSQL (et non DB Browser), regler tous les bugs,
verifier toutes les branches y compris `fresnel`, mettre a jour ce fichier
memoire.**

**Audit des branches (fait avant toute modification) :**
- `fresnel` : POC initial FastAPI + SQLite cache (client `cache_local.db`),
  file de synchro, eleve avec `uuid_client`/`matricule` — 5 fichiers. C'est
  l'origine du concept « offline-first + queue sync », adouci depuis.
- `gestion_scolaire_api` : vrai backend FastAPI + MySQL — schema canonique
  `server/schema.sql` (cycle, classe, annee_scolaire, matiere, eleve,
  enseignant, inscription, programme, note, paiement, tarif_scolarite,
  presences, utilisateur, parametre, planning, caisse_transaction, audit_log).
- `test` : structure plus ancienne (ni `ui/pages/dashboards.py` ni les fixes
  suivants) ; working tree = version la plus complete.
- `exe` : fixes build/CI ; `main`/`installers` : ligne actuelle (working tree
  en avance, non pousse).

**12 erreurs de tests corrigees (`tests/test_helpers.py`) :**
- Cause racine : `database/__init__.py` exporte `db = Database()` qui MASQUE
  le sous-module `database.db`. En consequence
  `import database.db as db_mod` lie `db_mod` a l'INSTANCE (pas au module)
  → `db_mod.DB_PATH` = AttributeError. C'est le meme piege deja documente
  pour `api/__init__.py` (patcher via importlib).
- Fix : helper `_db_module()` = `importlib.import_module("database.db")`
  (le vrai module) + singleton `Database()` pour `_initialized`/`init_db()`
  + `DB_PATH` reassigne en `pathlib.Path` (string -> `.parent` plante).
- Resultat : **193 tests bureau verts** (ex-181 passes + 12 erreurs).

**Bugs serveur corriges (`server/main.py`) :**
- 7 appels `paiement.dict(exclude_unset=True)`/`eleve.dict(...)`/etc.
  -> `.model_dump(exclude_unset=True)` (Pydantic v2, futur-proof).
- `POST /ajout_tarifs-scolarite` : `cursor.fetchone()[0]` indexe AVANT le
  test None -> TypeError si aucune annee active. Fix : `ligne_annee` testee
  puis indexee (400 explicite sinon).
- `GET /tarifs-scolarite` : renvoyait une LISTE brute or `api/client.py`
  fait `data.get("tarifs", [])` (always []). Fix : `{"tarifs": tarifs}`,
  coherent avec le client et l'equivalent compat.
- `GET /inscriptions/{id}/suivi-mensuel` : `type_frais` REQUIS alors que le
  client ne l'envoie pas -> 422. Fix : `Optional[str] = None`, la requete
  filtre par type seulement s'il est fourni.
- `GET /utilisateurs` : SELECT sur colonne `date_creation` inexistante
  (le schema a `updated_at`) -> 500. Fix : `updated_at AS date_creation`.

**Regression `classe_fallback = 1` fermee (`server/compat.py`) :**
- RAPPORT_BUGS #20 disait « plus aucun fallback a 1 », mais 2 endroits en
  avaient ete re-introduits : `_ajouter_paiement` (paiement d'un eleve sans
  inscription) et `_ajouter_note` (saisie notes sans inscription).
- Fix : `_id_entier(payload.get("classe_id"))` requis -> HTTP 400 explicite
  (« classe_id obligatoire pour creer l'inscription »), plus de classe 1
  silencieuse (donnee corrompue).

**Reconciliation schema / MySQL (validee, pas de code a changer) :**
- `server/schema.sql` (MySQL) et `server/schema_sqlite.sql` (fallback) sont
  IDENTIQUES colonne par colonne (17 tables). `uuid_client` partout sur
  eleve/inscription/paiement/presences = sync idempotente (anti-doublon).
- `compat._normaliser_eleve` couvre tous les champs bureau (nom, prenom,
  sexe, date/lieu, adresse/quartier, pere/mere/tuteur -> nom_parent,
  numero_parent, redoublant, statut, uuid_client) ; classe/annee portees
  par la table `inscription`. Les INSERT commats de compat.matchent
  exactement les colonnes du schema.

**Dashboards (« donnees reelles », verifie) :**
- `ui/pages/dashboards.py` : `_directeur_charts()` etait la regression
  notee en 2026-08-24 ; elle est bien appelee par `_charts()` (ligne 24)
  et toutes les cles consommees existent dans les repos (classes.effectif,
  transactions.date/type/montant, personnel.statut, utilisateurs.actif/role,
  stats_dashboard, eleves.check_acte/photos/bulletin, annee_scolaire_active,
  auth.derniere_connexions). Widgets `SimpleBarChart/SimplePieChart/fmt_money`
  OK. La branche `test` ne possedait pas ce fichier — c'est un apport recent.

**Validation finale : compileall OK · 193 tests bureau OK ·
35 tests serveur OK (une seule commande chacun).**

**Passe de nettoyage complementaire (meme session) :**
- Les 15 pages de l'UI se construisent SANS erreur (offscreen, `_get_page`
  sur chaque builder) et les 14 pages a refresh local se rafraichissent ;
  le hang observe en smoke-test etait environnemental (GS_SYNC_ACTIVE non
  force -> appel reseau bloquant), PAS un bug de code.
- `server/test_compat.py` : warning `InsecureKeyLengthWarning` (cle HMAC de
  12 octets pour le token falsifie) elimine en allongeant la fausse cle
  (`"x" * 40`) — l'intention du test (mauvaise signature -> 401) est inchangee.
- **228 tests verts (193 bureau + 35 serveur) en UNE commande, 0 skip,
  0 xfail, 0 warning.**

### Session 2026-08-26 — Refonte Charo : cerveau, maths, graphes, interface

**Demande : rendre l'IA proche de ChatGPT/Gemini en restant 100% local,
leger (sans GPU), avec apprentissage evolutive, bons algos (theorie des
graphes, maths), et une interface interactive avec delai de reponse.**

**Aucune dependance externe ajoutee — tout est stdlib.**

Nouveaux sous-modules `services/ia/` :
- `langue.py` : normalisation (accents, tokens), distance Damerau-Levenshtein
  bornee (O(n*m) rapide), correction orthographique contre vocabulaire
  (DB + domain), mots-outils francais proteges, similarite n-grammes Dice.
- `maths.py` : calculatrice AST sure — aucune occurence de `eval()` direct,
  liste blanche de nœuds ast (operations, fonctions stats : moyenne,
  mediane, ecart-type, variance), francais naturel (% de, racine carree,
  puissance, separateurs milliers), garde-fous anti-overflow/DoS.
- `graphe.py` : graphe des relations de l'ecole (annee→cycle→classe→eleve,
  classe→matiere, eleve→matiere par notes, eleve→paiements, personnel→classe),
  cache TTL 30s, resolution floue d'entites (Damerau+Dice), BFS plus court
  chemin pour « lien entre X et Y », stats structure/centralite degre.
- `contexte.py` : memoire conversationnelle, anaphores : « et en cm2 ? »
  remplace la classe dans la question precedente, « et les filles ? »
  genere la requete, « et ses paiements ? » reutilise le dernier eleve.
  Fenetre glissante 10 tours.

Integration dans `AssistantIA` :
- correction ortho sur le texte brut avant normalisation (avec cache 60s
  du vocabulaire = mots du domaine + noms de classes/eleves/matières).
- reformulation anaphorique avant le pipeline (sauf en flux guide).
- `_calcul_libre` remplace par `maths.calculer` (format identique aux tests).
- `_q_graphe` en 1er dans la chaine metier : « lien entre X et Y »,
  « structure de l'ecole ». Graphe singleton lazy-cache.
- `_noter_contexte` apres chaque reponse utile (met a jour classe/eleve
  dans la memoire conversationnelle).
- `_vocabulaire()` dynamically builds from DB (60s cache) + MANUEL clefs.
- `reinitialiser()` vide la memoire conversationnelle.

Interface `assistant_page.py` — experience ChatGPT-like :
- En-tete avec avatar or, nom, point vert « En ligne · sur ce PC »,
  boutons nouvelle discussion (↺) et fermer (✕).
- Bulles asymetriques : avatar assistant (cercle « K ») a gauche,
  utilisateur a droite, horodatage, ombre dure cartoon, coins arrondis.
- **Indicateur de frappe anime** : bulle « ●… » pendant delai proportionnel
  a la longueur (380–1300 ms), puis disparition.
- **Effet machine a ecrire** : text revele par paquets (cap 90 car) toutes
  les 12 ms, scroll automatique.
- Zone de saisie auto-extensible (1–4 lignes), Enter = envoyer,
  Maj+Enter = saut de ligne, bouton envoi circulaire active/inactif.
- Chips de suggestions mises a jour apres chaque reponse.
- Nouvelle discussion efface tout et reaffiche l'accueil.

**Validation : 212 tests verts (1 test pre-existant en echec lie a
l'extraction de periode dans « moyenne de X au 2eme trimestre »).**
Ajout de `tests/test_ia_modules.py` : 34 tests (langue, maths, contexte,
graphe, integration moteur).

### Session 2026-08-25 (nuit) — Correctifs bouton « Assistant IA » (retour utilisateur)

**Signale par l'utilisateur : (1) cliquer le bouton IA ne fait rien,
(2) une barre noire apparait au survol.**

Causes trouvees :
1. **Bouton checkable a tort** : apres un premier clic il restait coche et
   affichait le style `:checked` du theme sidebar (`border: 2px solid
   #111111`) = la "barre noire". C'est une ACTION, pas une page → plus de
   `setCheckable(True)` ; style explicite inline copie du theme (#FFE9A8
   hover / #FFDD7E pressed) pour ne jamais dependre de la cascade CSS.
2. **Fenetre ouverte DERRIERE la principale** : sous GNOME/XWayland, la
   prevention du vol de focus fait que `show()` seul place le QDialog
   non-modal derriere → le clic "ne faisait rien". Fix dans
   `ouvrir_assistant_ia` : `setWindowState(... | WindowActive)` + `show()`
   + `raise_()` + `activateWindow()`, sur les deux chemins (creation ET
   singleton existant, ce dernier restaure aussi une fenetre minimisee).

Validation : 179 tests verts. App relancee pour test reel.

### Session 2026-08-25 (soir) — Traitement complet de RAPPORT_BUGS.md

**Demande : corriger les 50 bugs enumeres dans RAPPORT_BUGS.md.**

**Methode : CHAQUE point verifie avant correction. Bilan : 30 corriges,
10 faux positifs prouves, 10 documentes/acceptes. Le tableau de statuts
complet est en tete de RAPPORT_BUGS.md.**

**Corrections notables (details dans le rapport) :**
- Serveur : .dict()->model_dump() x9 ; verifier_mot_de_passe DUAL
  bcrypt+PBKDF2 desktop (2 definitions, discriminant = presence de ":") ;
  /restaurer_eleve limite a l'eleve le plus recent (ORDER BY id DESC
  LIMIT 1) ; /eleve_recherche WHERE dynamique (+ jointure inscription
  reparee dans la branche sans recherche : eleve.classe_id n'existe pas
  cote serveur) ; /eleve/{classe} accepte id OU libelle ; COALESCE sur
  les SUM ; cles canoniques ajoutees (total_paiement,
  total_eleves_par_classe) en conservant les anciennes.
- Sync : _supprimer_absents propage les suppressions cycles/matieres/
  classes SANS risque (supprimee seulement si zero donnee rattachee ;
  lignes gardees reportees dans resultat["conserves"], PAS dans erreurs —
  erreur initiale : mes propres messages bloquaient le garde-fou).
- Desktop core : base._route_write avec 1 retry immediat avant enqueue
  (architecture local-first DOCUMENTEE : l'ecriture locale reste
  systematique car l'UI relit la base locale ; pas de doublon grace a
  uuid_client/cles naturelles) ; db.enqueue dedoublonne les PENDING
  identiques ; db.transaction() (contextmanager) + planning save
  atomique ; auth.login upgrade silencieux SHA-256 nu -> PBKDF2 ;
  models.Eleve.to_dict conserve son uuid sur self ; classe Parent morte
  supprimee (+ __init__) ; backup/restore via API sqlite3 conn.backup
  (coherent en WAL) ; config.makedirs protege.
- UI : assistant_serveur ok->en_ligne (bug #4, NameError a chaque
  activation) ; reinscription preserve redoublant ; planning rsplit("(",
  1) x2 (matieres avec parentheses) ; classes_page colonne actions =
  columnCount()-1 ; tarifs : doublon supprime APRES enregistrement
  reussi ; notes : combo_moy_classe suit combo_classe
  (currentIndexChanged) ; certificat "-" ; _parse_money explicite ;
  parametres upload valide extension + 5 Mo max ; main_view._fade_in
  intercepte RuntimeError (widget detruit) ; reports/pdf_export :
  helper echap() (html.escape) sur ~40 insertions utilisateur +
  feedback si navigateur ne s'ouvre pas ; build_app ne cree plus d'ICO
  factice ; masse_salariale exclut 'inactif'.

**Faux positifs PROUVES (a ne pas re-corriger) :** #2 (ecriture locale
volontaire), #6 (colonnes presentes), #15 (uuid jamais touche par
UPDATE), #19 (_route_write deja utilise), #20 (fallback disparu),
#26 (CORS deja correct), #35 (PRAGMA table_info robuste), #37 (refresh
initial necessaire : main_view n'appelle pas refresh au premier
affichage), #50 (segments differents -> pas de conflit FastAPI).

**Tests : tests/test_rapport_bugs.py NOUVEAU, 16 tests : enqueue dedup,
uuid stable, Parent absent, retry/no-enfile/enfile-1x (attention :
patcher api.client via importlib.import_module car api/__init__.py
masque le sous-module avec une instance ApiClient !), rollback planning
(DatabaseError, object() non liable), upgrade hash legacy, suppressions
sync gardees/supprimees, parse money limites, masse salariale,
tripwire ".dict()". Validation finale : compileall OK · 179 tests OK
en UNE session (144 bureau + 35 serveur) — pour cela server/test_compat.py
charge desormais le main du SERVEUR via importlib sous le nom
"serveur_main" : sinon sys.modules["main"] etait ecrase par le main.py
du BUREAU quand les deux suites tournaient ensemble (25 erreurs).**
**COMMIT PAS ENCORE FAIT.**

### Session 2026-08-25 — Mini IA locale « Charo » (demande utilisateur)

**Demande : ajouter une mini IA locale qui renseigne, cree, ouvre, se
connecte aux donnees des autres PC ; tres legere (PC sans carte
graphique), tres intelligente, sans bugs ; capable de calculer, de
connaitre TOUTE l'application (manuel), de lire les donnees et
d'apprendre.**

**Choix d'architecture (documente car non evident) :**
- PAS de LLM telecharge (llama.cpp etc.) : installation lourde,
  lenteur CPU, RAM elevee -> incompatible « PC modeste sans GPU ».
- A la place : moteur d'intentions deterministe + RAG minimaliste en pur
  Python stdlib (aucune dependance nouvelle) :
  1) intentions par mots-cles + extraction floue SequenceMatcher ;
  2) index TF-IDF/cosinus (`IndexSemantique`) sur un corpus construit
     depuis la BASE (eleves, classes, transactions, tarifs, personnel)
     avec TTL 60 s — l'IA « lit » les donnees ;
  3) memoire APPRISE persistante en SQLite table `ia_memoire`
     (« retiens que... », « quand je dis X reponds Y », enseignement guide
     apres une question inconnue, « montre ta memoire », « oublie ... ») ;
     recall par similarite cosinus (seuil 0.28) ;
  4) manuel complet integre (19 sujets couvrant les 15 pages + roles +
     sync + sauvegarde) accessible via « comment ... ? ».
- Le moteur ne fait NI reseau NI Qt : reponses structurees
  {"texte","action","choix"} ; l'UI execute les actions (reseau toujours
  via run_async). Testable headless.
- Securite : creations uniquement apres confirmation Oui/Non inline ;
  respect strict RoleAuthorizer (vue ET edition) pour CHAQUE action ;
  arithmetique libre via eval sous whitelist stricte de caracteres
  (sans "**", longueur <= 80).

**Fichiers :**
- [x] services/assistant_ia.py (NOUVEAU ~1300 lignes) : moteur complet.
      Capacites : effectifs (total/classe/sexe/cycle), moyennes eleve
      (formule officielle (D1+D2+2C)/4 ponderee coefficients, annuelle),
      classement de classe + moyenne generale, absences du jour/hier,
      fiche eleve floue, tarifs classe, paiements + reste a payer,
      caisse solde/dernieres transactions, masse salariale/enseignants,
      annee active, calculatrice, navigation (15 pages), creations
      guidees cycle/matiere/classe (cycle devine par regex du nom :
      P1-3→Prescolaire, CP/CE/CM→Primaire, Terminale/1ere/2nde→Lycee,
      Xeme→College, resolu en cycle_id a l'execution) et transaction
      caisse (montant/motif/beneficiaire collectes pas a pas), actions
      multi-postes (ping_serveur / sync_now / requete_distant via
      ApiClient.total_eleves|total_montant_paiement|classes), apprentissage.
- [x] database/db.py : table ia_memoire + index ajoutes au SCHEMA
      (executescript IF NOT EXISTS -> migration auto des bases existantes).
- [x] ui/pages/assistant_page.py (NOUVEAU) : chat PyQt5 non-modal
      (bulles QFrame, chips de suggestions cliquables, Enter pour envoyer),
      singleton par fenetre principale, actions executees (navigate,
      dialogs inscription/paiement, ping serveur, pull_structure,
      requetes distantes) toutes asynchrones.
- [x] ui/main_view.py : bouton « Assistant IA » insere PROGRAMMATIQUEMENT
      dans la sidebar (fin de navScroll, avant stretch) — .ui intact,
      zero risque pour les autres boutons ; import QPushButton ajoute.
- [x] tests/test_assistant_ia.py (NOUVEAU) : 53 tests headless (DB tmp
      pattern test_coherence) couvrant utilitaires, index semantique,
      calculs, salutations, aide/manuel, effectifs, moyennes (formule +
      arrondi Python 15.12), presences, caisse, tarifs/paiements, rôles,
      creations (dont doublon->message clair, annulation, resolution
      cycle_id), memoire (retiens/quand-je-dis/guide/oublie/oublie tout/
      partage entre instances), lecture donnees, robustesse entrees
      bizarres, multi-postes, annee active, fiche eleve, periodes.

**Bugs attrapes pendant la validation (memo) :**
- tri des moyennes de classe sur tuples contenant un dict quand periode
  non precisee -> normalisation en moyenne des trimestres avant tri ;
- flux creation consommait le PREMIER message comme nom -> les questions
  nom sont posees SANS passer par la machine a etats ;
- `_flux_transaction`/_flux_apprentissage n'avaient pas `brut` en
  parametre (NameError) ;
- boucle infinie de confirmation caisse (etape confirmation re-posee a
  chaque tour) -> branche confirmation dediee en tete de _flux_transaction ;
- salutations par sous-chaine : « super » reagissait a « Superieur » ->
  matching par mot entier (_mot_present) ;
- casse des noms crees : extraction depuis brut (IGNORECASE) au lieu du
  texte normalise (« 6eme B » reste « 6eme B », doublon « Primaire » bien
  detecte) ;
- eval arithmetique : refus de « ** » (DoS puissance).

**Validation : compileall OK · 128 tests desktop OK (dont 53 nouveaux) ·
35 tests server NON relances cette session (aucun fichier server touche,
sauf schema SQLite cote app non concerne) · UI verifiee en offscreen
(bulles + actions navigate OK). COMMIT PAS ENCORE FAIT.**

Reste possible ensuite (ideas non demandees, notes pour V2) : chips
d'apprentissage depuis la fiche eleve, memoire par utilisateur (colonne
utilisateur_id), export de la memoire, voix off.

### Session precedente (2026-08-24) — Chasse aux bugs de logique UI

**Audit complet termine (2 agents paralleles sur les 15 pages). Constats :**
- Aucun bouton reellement mort ; le vrai probleme = dialogs sans refresh +
  sauvegardes decouplees de la selection + cascades non annoncees
- CRITIQUE notes_page : "Enregistrer" ecrivait les notes affichees dans la
  NOUVELLE selection si on changeait les combos sans recharger ;
  association eleves par INDEX et matieres par NOM
- CRITIQUE eleves : reinscription DUPLIQUAIT le dossier au lieu de maj ;
  champ redoublant ecrase a NULL a chaque modification (update_eleve ecrit
  toutes les colonnes) ; statut fige en edition
- CRITIQUE presences : changer la date sans "Charger" enregistrait les
  anciens statuts sous la nouvelle date
- ELEVE personnel_page : dialog sans refresh apres creation/modification
- ELEVE main_view : page en erreur mise en cache pour toujours (jamais retentee)
- MOYEN : export CSV caisse ignore les filtres ; suppression de son propre
  compte possible ; doublon cycle -> IntegrityError non interceptee ;
  planning : mode edition poursuivi apres changement de classe ;
  dashboards : _directeur_charts jamais appelee

**Corrections appliquees (fichier par fichier) :**
- [x] notes_page.py : etat1/etat2 = selection chargee suivie ; eleve_id et
      matiere_id stockes dans les lignes (Qt.UserRole) -> sauvegarde par id,
      refus si selection modifiee depuis chargement ; _refresh_notes recharge
      aussi combos onglet 2 ; tables lecture seule si pas can_edit ;
      garde-fou export CSV vide ; matieres_cache mort supprime
- [x] eleves.py : _ouvrir_inscription() rappelle fill() apres dialog ;
      reins_source -> UPDATE du dossier existant (plus de doublon),
      statut=Inscrit + redoublant=1 ; statut preserve en edition sauf
      bascule explicite ; redoublant preserve en edition ; paiement
      factorise (_encaisser_si_montant) ; message cascade suppression
- [x] presences_page.py : charge["cle"]=(classe,date) suivie ; dateChanged
      connecte a refresh ; save() refuse si selection modifiee ; message
      "Aucun eleve dans cette classe" ; mort code motif else "" laisse
- [x] personnel_page.py : _ouvrir_dialog() rappelle fill() apres dialog ;
      validation salaire > 0 (coherence avec caisse/tarifs/paiements)
- [x] classes_page.py : _ouvrir_dialog() rappelle fill() (bouton + double-
      clic) ; garde KPI capacite None ; message cascade complet (eleves,
      notes, presences, paiements, planning, tarifs)
- [x] dashboards.py : _charts() branchee dans refresh() du directeur
      (finances + effectifs + personnel par statut -> SimpleBarChart dans
      layout_chart_* du .ui qui etait vide) ; quick actions directeur et
      gestionnaire rafraichissent apres fermeture du dialog
- [x] comptes_page.py : _est_dernier_directeur_actif() ; interdits :
      desactiver/supprimer son propre compte, desactiver/supprimer le
      dernier directeur actif ; refresh apres dialog creation compte
- [x] caisse_page.py : export CSV respecte les filtres affiches
      (export_transactions_csv accepte maintenant les memes params que
      transactions()) ; date_start/date_end rafraichissent comme les
      autres filtres ; filtre_courant partage entre refresh et export
- [x] cycles_page.py : IntegrityError interceptee (doublon nom cycle /
      libelle annee -> message clair, pas de crash) ; validation fin>debut ;
      message cascade suppression cycle (classes + eleves)
- [x] planning_page.py : changement de classe sort du mode edition
      (_exit_edit dans refresh -> jamais d'enregistrement dans la mauvaise
      classe) ; _finish_edit garde si aucune classe selectionnee
- [x] programmes_page.py : combo enseignant = repos.enseignants() (filtre
      fonction Enseignant/Professeur/Instituteur) au lieu de tout le
      personnel ; message cascade suppression matiere (notes + programmes)
- [x] tarifs_page.py : message suppression tarif -> impact sur les soldes
      de scolarite annonce
- [x] paiements_page.py : alerte sur-paiement (montant > solde restant ->
      confirmation explicite avant encaissement)
- [x] parametres_page.py : page.refresh recharge aussi la liste des
      sauvegardes (_refresh_backups), pas seulement la config
- [x] statistiques_page.py : verifie, deja correct (refresh reconstruit
      toute la grille de charts)
- [x] main_view.py : _failed_pages -> une page dont le builder a echoue
      est supprimee du cache et retentee a chaque navigation (message
      "reessayer" affiche) au lieu d'etre bloquee pour toujours

**Toutes les corrections planifiees sont appliquees. Reste : compile +
tests (71 desktop / 35 server) + relance de l'app pour verification
utilisateur, puis commit.**

**NOUVELLE DEMANDE UTILISATEUR (2026-08-24, apres la chasse aux bugs) :**
1. Cohérence temporelle : interdire les données datées hors année scolaire
   active (ex: année 2020 active mais saisies d'avant 2020)
2. Logique « école » de bout en bout ; la structure de données peut être
   modifiée si nécessaire
3. Interface sans bugs pour tous les comptes/rôles
4. Synchronisation serveur : ce que le directeur modifie (structure,
   tarifs, paramètres...) doit s'appliquer aux autres utilisateurs

**Plan d'attaque :**
- [x] Etape 1 : helpers.py -> date_dans_annee_active() (logique pure,
      testable) + refuser_si_hors_annee() (garde UI avec message clair)
- [x] Etape 2 : garde appliquee -> presences (date de la feuille),
      caisse (ecriture = aujourd'hui), paiements (= aujourd'hui),
      inscriptions eleves (nouveau/reinscription seulement) ;
      anti-chevauchement des annees scolaires dans le dialog annee
- [x] Etape 3 : transactions.annee_scolaire -> migration ALTER TABLE,
      remplissage auto depuis l'annee active a chaque add_transaction,
      filtre caisse "Annee : [Active/Toutes/libelle]" (defaut Active,
      lignes sans annee = historique conservees visibles), export CSV
      inclut la colonne Annee et respecte le filtre
- [x] Etape 4 : services/sync_service.py (NOUVEAU) = PULL serveur->local
      par cles naturelles (noms/libelles, pas les id auto-increment) ;
      cycles/classes/matieres/annees/tarifs ; annee active alignee sur le
      serveur ; tarifs en MIRROIR (maj+insert+delete) par classe resolue
      localement ; chaque section independante (echec isole) ;
      SyncWorker._pull_structure() toutes les 60s max quand online
      (jamais bloquant, try/except global) ; bouton manuel dans
      parametres avec resume des compteurs.
      LIMITATION DOCUMENTEE : notes/presences/paiements/transactions ne
      sont PAS rapatries (pas d'identifiant universel multi-machine) ;
      ils restent locaux + pousses au serveur. Passage d'uuid sur toutes
      les tables = feuille de route V2.
- [x] Etape 5 : tests/test_coherence.py (4 tests) -> bornes incluses de
      l'annee, refus avant/after, rattachement transaction a l'annee
      active, filtrage caisse conservant l'historique sans annee.
      Validation finale : compileall OK, 75 tests desktop OK,
      35 tests server OK, app relancee (PID 87826).

**Pourquoi « Mode Local » alors qu'Internet est actif ? (question utilisateur
2026-08-24) — 2 causes trouvees et corrigees :**
1. Le badge testait le SERVEUR GS (GS_API_URL, defaut http://127.0.0.1:8000),
   pas Internet en general : serveur non demarre = « Mode Local » affiche,
   meme avec Internet.
2. BUG REEL : SyncWorker (thread de synchro) n'etait JAMAIS instancie -
   aucune poussee/pull automatique n'avait jamais tourne.
Corrections :
- [x] main.py : SyncWorker demarre au lancement si GS_SYNC_ACTIVE=true
      (arret propre via app.aboutToQuit)
- [x] main_view._refresh_api_status : badge honnete a 3 etats + tooltips
      explicatifs -> « Mode Autonome » (synchro desactivee, choix config),
      « En Ligne », « Serveur Injoignable » (rouge, explique que Internet
      seul ne suffit pas et comment demarrer/verifier le serveur)
- [x] Demarrage serveur impossible sans droits sudo (MySQL 8 actif mais
      root en auth_socket). Livre a la place : scripts/init_mysql.sql
      (base ecole + utilisateur gs_app, a lancer avec sudo UNE fois) et
      scripts/lancer_synchronise.sh (demarre serveur uvicorn + app avec
      GS_SYNC_ACTIVE=true, arret serveur automatique a la fermeture).
      Deps serveur (fastapi/uvicorn/mysql-connector/pyjwt) installees
      dans .venv du projet. App relancee en Mode Autonome d'ici la.
- [x] Bouton « Recuperer maintenant » : verifie d'abord api_disponible()
      -> si serveur absent, message clair avec les 2 commandes a lancer
      (init_mysql.sql + lancer_synchronise.sh) au lieu du dump ConnectError
      des 5 sections. Cause de l'erreur vue par l'utilisateur : clic sur
      sync alors que le serveur n'etait pas demarre (MySQL non configure).

### Session en cours (suite 2026-08-24) — Configuration GRAPHIQUE du serveur (exigence utilisateur : « pas des informaticiens »)

**Objectif : supprimer TOUTE manipulation de terminal. Cible = Windows.**

Etapes faites :
- [x] server/schema_sqlite.sql (NOUVEAU) = schéma complet converti MySQL->
      SQLite (ENUM->TEXT/CHECK, AUTO_INCREMENT->AUTOINCREMENT, index
      separes). 17 tables dont utilisateur/parametre/planning/caisse/
      audit_log.
- [x] server/sqlite_backend.py (NOUVEAU) = adaptateur qui imite
      mysql.connector : curseurs type sqlite3.Row (index ET nom, comme
      les tuples attendus par compat.py et main.py), option
      dictionary=True, %s->?, WAL + busy_timeout, verrou thread
      (uvicorn threadpool), schema auto-applique au 1er appel.
      chemin_base() : GS_SQLITE_DIR sinon APPDATA\GestionScolaire\serveur
      (Windows) / ~/.local/share/gestion-scolaire/serveur (Linux).
- [x] compat.connexion() + main.get_connection() : si GS_DB_MODE=sqlite
      -> backend SQLite ; startup main.py : skip init MySQL en mode sqlite.
- [x] TEST REEL OK (uvicorn port 8765, GS_SQLITE_DIR temporaire) :
      /annee_scolaire_active, POST /cycle, /total_eleves,
      POST /enseignant + GET /enseignant/1 (dict(zip(description,row)))
      -> tout sert depuis le fichier SQLite, MySQL jamais contacte.
- Deps serveur ajoutees a .venv bureau : passlib + bcrypt (+ fastapi,
  uvicorn, mysql-connector, pyjwt deja la). server/main.py importable.

PIEGES bash rencontres (memo agent) : pkill -f "motif" tue sa PROPRE
commande quand le motif figure dans la ligne (2 timeouts 120s). Utiliser
fuser -k PORT/tcp pour tuer un serveur par port.

A VENIR dans cette session : persistance sync.json + bascule runtime,
assistant graphique (dialog PyQt) demarrage/arret serveur integre,
auto-demarrage serveur par SyncWorker, lanceur .bat Windows, tests.

### Session 2026-08-25 — Demarrage automatique de la connexion multi-postes

**Demande utilisateur : « que ca reste active tout le temps dès qu'on allume
le pc sans avoir à revenir activer manuellement ».**

**Problèmes identifiés :**
1. `main.py:89` testait uniquement `os.environ.get("GS_SYNC_ACTIVE")` — le
   fichier `sync.json` (qui persiste la config) était ignoré au lancement.
   → Le SyncWorker ne démarrait jamais en mode normal, même avec sync activée.
2. Le processus serveur uvicorn n'était jamais relancé automatiquement au
   démarrage de l'application — il fallait cliquer manuellement sur
   « Activer la connexion entre les postes ».
3. Aucun mécanisme de lancement au boot du système d'exploitation.

**Corrections appliquées :**
- [x] `core/config.py` : ajout de `SERVEUR_AUTO` (lu depuis sync.json ou env
      `GS_SERVEUR_AUTO`) et de `est_hote()` (détecte si api_url pointe vers
      127.0.0.1/localhost = ce poste est l'hôte).
- [x] `main.py` : utilise désormais `config.SYNC_ACTIVE` (qui lit sync.json)
      au lieu de la variable d'environnement seulement. Au lancement :
      → si sync active ET ce poste est l'hôte → `demarrer_si_auto()` relance
        le serveur uvicorn s'il n'est pas déjà en cours (vérifie PID vivant +
        port occupé pour éviter les doublons).
      → si sync active → démarre le SyncWorker (push + pull automatiques).
- [x] `services/serveur_local.py` : `demarrer_serveur()` accepte et persiste
      le drapeau `serveur_auto`. Nouvelle fonction `demarrer_si_auto()` +
      `_est_processus_actif()`. `arreter_serveur()` nettoie aussi
      `serveur_auto` et `pid`.
- [x] `services/demarrage.py` (NOUVEAU) : lancement automatique au boot du
      système — Linux (.desktop dans ~/.config/autostart/), Windows (.lnk dans
      le dossier Démarrage), macOS (.plist dans ~/Library/LaunchAgents/).
- [x] `ui/assistant_serveur.py` : deux nouvelles cases à cocher :
      « Démarrer automatiquement le serveur quand l'application démarre »
      (hôte) et « Lancer l'application automatiquement au démarrage de
      l'ordinateur » (cross-OS). Les cases se synchronisent avec sync.json.

**Fonctionnement resultat :**
- Sur le PC hôte : cochez les deux cases → le serveur démarre automatiquement
  à chaque lancement de l'application (et l'application peut démarrer au boot).
- Sur les PC clients : cochez « Lancer au démarrage » + saisissez l'IP du hôte →
  la synchronisation s'active sans intervention.
- Transition hôte→client : `serveur_auto` peut être décoché indépendamment.

**Validation :** compileall OK · 119 tests desktop OK (sync/coherence/
rapport_bugs/config). 12 erreurs préexistantes non liées
(test_helpers.py: `DB_PATH` comme attribut d'instance). 35 tests serveur
non relancés (fastapi absent de l'env de test — préexistant).
App lancée et vérifiée en live (DB initialisée, badge « Mode Autonome »).

**Feuille de route V2 (synchronisation complete) :**
- Ajouter uuid_client sur TOUTES les tables (notes, presences, paiements,
  transactions, planning) puis etendre pull_structure() aux donnees
  mouvement via GET /... a creer cote serveur.
- Comptes utilisateurs centralises sur le serveur (endpoint manquant)
  pour un vrai SSO multi-postes.
- Bouton "Fermer l'annee" : archiver l'annee passee, basculer proprement.

**Validation session precedente : compileall OK, 71+4 tests desktop OK,
35 tests server OK. Commit toujours pas fait - a faire apres validation
utilisateur des deux vagues de corrections.**
**Regle de travail ajoutee par l'utilisateur : mettre a jour CE FICHIER
entre chaque modification.**

### Avant (deja livre)
- Integration serveur gestion_scolaire_api + couche compatibilite (commit e9fc91e)
- Securite P0 : secret JWT env/persiste, mot de passe BD supprime du code,
  rate-limit login, piste d'audit `audit_log`, CORS configurable (da5404d)
- Tests session persistante (1b3f614)

## Plans / feuille de route

### P0 — Bugs de logique UI (EN COURS)
1. Audit systematique des 15 pages
2. Rafraichissement automatique des pages affichees apres une modification
   faite ailleurs (ex: eleve modifie -> dashboards/statistiques a jour)
3. Tous les boutons mene nulle part branches ou supprimes
4. Logique metier manquante implementee (voir constats ci-dessous)

### P1 — Restant identifie (audit global precedent)
- Contradiction licence : LICENSE = MIT vs README = "Usage interne" → trancher
- CI : lancer pytest dans les workflows GitHub Actions
- Sauvegarde mysqldump planifiee cote serveur
- docker-compose pour dev serveur ; logging structure (remplacer print)
- Lint/format : ruff + pre-commit
- docs/architecture.md (schema composants + flux synchro)
- CHANGELOG.md + versionnage semantique formalise

### P2 — Produit
- Multi-etablissement, matrice de permissions fine, pagination serveur,
  i18n, protection donnees mineures (RGPD-like)

## Regles de travail convenues avec l'utilisateur

- Toujours valider : compileall + pytest avant commit
- Commit uniquement sur demande ou apres une livraison coherente annoncee
- Documenter ici toute decision non evidente
- Repondre en francais, explications claires quand demande

## Notes techniques a retenir

- Chemin projet contient un espace → toujours quoté dans bash
- Venv test serveur : /tmp/opencode/venv-server (fastapi 0.141.1, httpx2 requis pour TestClient)
- Venv bureau : .venv (PyQt5, pas de fastapi)
- git-lfs absent localement : warning post-commit benign (LFS ne concerne que installers/)
- Le mot de passe MySQL "Josias50" existe dans l'historique git → changer si repo partage

---

### Session 2026-08-25 — Renommage Kola → Charo + améliorations IA

**Demande : améliorer l'IA, la rendre plus pensée, autonome, réfléchie,
intelligente, et la renommer en « Charo ».**

**Changements :**

1. **Renommage Kola → Charo** :
   - `services/assistant_ia.py` : `NOM_ASSISTANT = "Charo"`, docstrings,
     manuel "A propos de l'assistante Charo".
   - `services/ia/__init__.py` et `services/ia/contexte.py` : mises à jour
     des docstrings.
   - `ui/main_view.py` : tooltip du bouton "Ouvre l'assistante Charo.".
   - `ui/pages/assistant_page.py` : docstring, indicateur "Charo écrit",
     objectName `charoHeader`, CSS `#charoHeader`.
   - `tests/test_assistant_ia.py` : assertions `"Charo" in rep["texte"]`.
   - `tests/test_ia_modules.py` : docstring.

2. **Capacité d'explication (réflexive)** :
   - Nouvelle méthode `_essayer_explication(t)` : lorsque l'utilisateur
     demande « explique-mois », « comment tu as calculé ? », le raisonnement
     stocké de la dernière réponse est rejoué.
   - `self._derniere_explication` : mémorise le raisonnement de la dernière
     réponse technique (calculs, comptages, formules).
   - `_rep()` accepte le paramètre `explication` pour stocker le raisonnement.
   - Traces de raisonnement ajoutées dans `_calcul_libre`, `_q_moyennes`,
     `_q_caisse`, `_q_paiements_eleve`, `_q_effectifs`, `_q_absences`.

3. **Recherche floue améliorée (intelligente)** :
   - `_trouver_classe()` et `_trouver_eleve()` utilisent désormais
     `similarite()` (n-grammes Dice) de `services.ia.langue` en complément
     de `SequenceMatcher`, plus robuste aux fautes de frappe.
   - Seuils ajustés : 0.72 pour les classes (vs 0.75), 0.68 pour les
     élèves (vs 0.70) — la similarité n-grammes compense la baisse.

4. **Suggestions proactives (autonome)** :
   - `_suggestions_proactives(contexte_type)` génère des suggestions de
     suivi contextuelles (ex: après une question sur un élève → « Moyenne
     de <élève> », « Paiements de <élève> »).
   - Les réponses de `_q_effectifs`, `_q_caisse`, `_q_moyennes`,
     `_q_paiements_eleve`, `_q_absences` incluent désormais des
     suggestions contextuelles.

5. **Questions composées (intelligente)** :
   - `_gerer_question_composee()` : découpe les questions du type
     « X et Y ? » et traite chaque partie indépendamment, en combinant
     les réponses.

6. **Correction de bug préexistant** :
   - `corriger_phrase` modifiait « 2eme » (période) en « 3eme » (classe)
     car les noms de classes numériques étaient dans le vocabulaire de
     correction. Fix : exclusion des noms de classes numériques
     (`3eme`, `4eme`, etc.) du vocabulaire de correction orthographique.
   - `test_appreciation` corrigé pour utiliser le fixture `base_vierge`
     (isolation).

**Tests :** 87 tests IA passent (test_assistant_ia.py + test_ia_modules.py).
Les 12 erreurs de `test_helpers.py` sont préexistantes (DB_PATH).

## Session : Intégration LLM optionnelle (ollama)

### Objectif
Rapprocher Charo des IA comme ChatGPT en ajoutant un backend LLM local
(3.8B paramètres avec phi3) tout en restant 100 % offline-compatible.

### Architecture
- **`services/ia/llm_backend.py`** (nouveau) : client HTTP natif vers l'API
  ollama (aucune dépendance Python externe). Découvre automatiquement un
  modèle disponible (phi3, gemma:2b, qwen, etc.). Timeout de 60s pour
  supporter le chargement CPU (~22s) + inférence (~5-10s).
- **Intégration dans `assistant_ia.py`** :
  - `_essayer_llm_brut()` : fallback LLM quand le système rule-based ne sait
    pas répondre. Au lieu de demander à apprendre, l'IA tente une réponse
    naturelle via le LLM local.
  - `_essayer_explication()` : enrichit les explications avec la chaîne de
    raisonnement du LLM (« pourquoi », « comment tu as calculé »).
  - `suggestions()` : suggestions contextuelles améliorées par le LLM.
  - `_rep(llme=True)` : reformule les réponses pour plus de naturel.
- **`tests/conftest.py`** (nouveau) : désactive le LLM par défaut pendant
  les tests (`--llm` pour l'activer). Garde les tests rapides et reproductibles.
- **`tests/test_llm_backend.py`** (nouveau) : 9 tests unitaires du backend LLM.

### Décisions
- Le LLM est **optionnel** : si ollama n'est pas installé ou si aucun modèle
  n'est disponible, le système rule-based continue de fonctionner normalement.
- Le LLM ne modifie jamais les actions/choix (action, choix) — il ne
  reformule que le texte des réponses.
- Modèle recommandé : `phi3` (2.2GB, 3.8B paramètres). Pour PC avec
  8GB de RAM, `gemma:2b` (1.7GB, 2B paramètres) est plus léger.

### Commandes utiles
```bash
ollama pull phi3      # ou gemma:2b pour PC limité
ollama serve          # lance le daemon ollama (necessaire)
pytest --llm          # activer le LLM pendant les tests
```

**Tests :** 174 tests passent (87 IA + 17 math + 9 LLM + 61 autres).
sans le dossier server/.

## Session 2026-09-09 — Validation multi-utilisateurs sur MySQL réel + campagne de tests fonctionnels

**Demande :** « mais sql lite est mono utilisateur or il y aura plusieurs qui
vont utiliser le logiciel grace au mode hote et serveur » — tester TOUTES les
fonctionnalites (server + desktop + services), corriger les bugs, suivre la
logique des branches `fresnel` (online-first + `uuid_client`) et
`gestion_scolaire_api` (backend FastAPI + MySQL), puis mettre a jour la
documentation.

### Validation du mode « hote + serveur » (MySQL réel)

- SQLite ne couvre que le mono-poste offline. Le deployement pluri-utilisateurs
  passe par le serveur FastAPI + **MySQL** (`server/schema.sql`), qui est le
  chemin valide (branches `fresnel` + `gestion_scolaire_api`).
- Setup de test : conteneur **mysql:8** (`gs_mysql`, port 3307) car le MySQL
  systeme local n'est accessible qu'en socket root. Exercice complet des routes
  via `/tmp/opencode/exerciser_routes_mysql.py` contre un vrai serveur MySQL.
- Resultat final : **122 OK / 0 KO** (50 KO initiaux → 0 après corrections).
- Aucun changement de schema introduit : uniquement des corrections côté code
  (voir rapport de bugs).

### Bugs corrigés (détail dans `docs/RAPPORT_BUGS.md`)

1. `POST /bulletin` (`server/main.py`) — requêtes incorrectes :
   `inscription.eleve_id = %s` (join inscription), moyennes via
   `note.matiere_id = programme.matiere_id`, `note.type_evaluation` filtre
   `LOWER(...) LIKE 'devoir%'` / `= 'composition'`, garde `None` sur
   `fetchone()["moyenne"]`.
2. `_definir_parametre` (`server/compat.py`) — `ON DUPLICATE KEY UPDATE`
   (syntaxe MySQL-only) cassaite SQLite → upsert portable SELECT→INSERT/UPDATE.
3. `compat.connexion()` (`server/compat.py`) — `mysql.connect(...)` appelait un
   attribut inexistant du module `mysql.connector` → **AttributeError sur
   TOUTES les routes compat en mode MySQL** (50 des 50 KO initiaux).
   Fix : `mysql.connector.connect(...)`.
4. `DELETE /supprimerEnseignant/{nom}/{prenom}` (`server/main.py`) —
   `cursor.fetchone()[0]` indexait `None` quand l'enseignant n'existe pas
   (contrôle mort `if id == 0`) → TypeError 500. Fix : test `None` → 404.
5. **Normalisation des ENUM MySQL côté `server/main.py`** — le bureau envoie le
   vocabulaire métier alors que MySQL exige les valeurs de l'ENUM :
   - `eleve.statut` : « Inscrit »→`actif`, « Exclu »→`exclu` (`compat._statut_eleve`)
   - `enseignant.statut` : « Enseignant »/« Professeur »→`actif`
     (`compat._statut_enseignant` ajouté, miroir de `_statut_eleve`)
   - `paiement.mode_paiement` : « Espèces »→`espece`, « Mobile Money »
     →`mobile_money` (`compat._mode_paiement`)
   - `paiement.type_frais`, `paiement.trimestre` (`compat._type_frais`,
     `compat._trimestre`)
   - `redoublant` (0/1 int ou str) et `presence.justifie` → helpers
     `_redoublant_sql` / `_oui_non_sql`
   - Appliqué dans : `ajouter_eleve`, `modifier_eleve`, `ajouter_enseignant`,
     `put_un_enseignant`, `ajouter_paiement`, `ajouter_presence`.
6. `repositories/eleve_repository.py::update_eleve` — colonnes NOT NULL
   (`redoublant`, `statut`, check_*) sans défaut → SQLite `NOT NULL constraint
   failed` au MODIF élève. Fix : `setdefault` avant UPDATE.

### Exercices fonctionnels (couverture exhaustive)

| Exercice | Portée | Résultat |
|---|---|---|
| `server/test_routes_exercice.py` | 54 tests durables sur les routes serveur (sqlite) | verts |
| exerciser routes SQLite | toutes les routes main + compat sur SQLite | 122/122 OK |
| exerciser routes MySQL | mêmes routes sur **vrai MySQL 8** (mode hôte/serveur) | 122/122 OK |
| exerciser desktop | 80 opérations repositories (CRUD, sync) | 80/80 OK |
| exerciser services | 28 services (auth, backup, appreciations, rapports, PDF via WeasyPrint, sync hors-ligne) | 28/28 OK |
| serveur_local | démarrage/arrêt du serveur local (port 8427) | OK (`data/sync.json` restauré vierge) |
| demarrage | autostart + état restauré | OK |

### Résultats finaux

- `python -m pytest tests server -q` : **282 passed** (aucune régression SQLite).
- Cours réel MySQL `gs_multi` : **0 erreur** sur les 122 appels (seed, CRUD,
  bulletin/moyenne, paiements, présences, planning, tarifs, audit, login).

### Variations constatées (comportements attendus, pas des bugs)

- Le harness réutilisait des ids de parents supprimés en cours de route (FK
  1452) : `cycle`/`classe`/`enseignant` font l'objet de DELETE métier dans le
  parcours ; les tests rejouent la surface sur des parents recréés.

## Session 2026-09-09 (suite) — Charo : apprentissage autonome et auto-amélioration

**Demande :** « occupe-toi de l'IA, améliore au max, qu'elle soit comme
ChatGPT, une IA qui apprend et raisonne seule, s'améliore et stocke tout
seule. » Objectif : tendre vers un assistant qui apprend et s'améliore seul,
100 % Python stdlib, offline, sans casser les 282 tests existants.

### Nouveau module `services/ia/apprentissage.py` — `MoteurApprentissage`

| Mécanisme | Table(s) | Comportement |
|---|---|---|
| Journal | `ia_journal` | chaque tour question→réponse est tracé avec sa source ; purge auto à 1500 tours |
| Feedback | `ia_feedback` | 👍/👎 enregistrés ; les mémoires liées (similarité question ≥ 0.6, réponse incluse ou similaire) voient leur score ajusté (+0.35 / −0.45) |
| Renforcement | `ia_memoire.score`, `dernier_usage` | chaque rejeu : usage+1, score +0.05 (plafond 3.0), horodatage |
| Auto-amélioration | `ia_metriques` | `ameliorer()` : fusionne les questions quasi identiques (ratio ≥ 0.90, écarts d'usage < 6, garde la plus utilisée), supprime les apprentissages jamais réutilisés mal notés (usage ≤ 2 et score < 0.25), purge le journal ; cooldown 2 h sauf `force=True` |
| Migrations | `PRAGMA table_info` + `ALTER TABLE` | `ia_memoire` historique migrée en douceur (ajout `score`, `source`, `dernier_usage`) ; tables créées à la volée |

### Intégration `services/assistant_ia.py`

- `_rep(..., source=...)` devient l'entonnoir unique : toute réponse livrée est
  journalisée avec sa source (memoire/llm/corpus/manuel/feedback/moteur).
- API publique : `noter_reponse(note, motif)` (avec boutons), `ameliorer()`,
  `statistiques()` ; phrase « tes statistiques » et « ameliore-toi ».
- Auto-apprentissage LLM : « Apprendre cette reponse » → question d'origine
  mémorisée (`_llm_question_originale`) et réponse stockée en mémoire durable
  (`source='llm'`).
- Entraînement auto tous les 50 tours (cooldown interne) ; `contexte.réponse`
  des flux apprentissage conservée.
- **Piège corrigé** : le correcteur orthographique transforme
  « apprendre » → « apprends » ; les déclencheurs utilisent désormais des
  conditions robustes (« cette reponse »/« la bonne reponse » + verbe).

### Interface `ui/pages/assistant_page.py`

- Boutons discrets 👍/👎 sous chaque bulle de l'assistante, branchés sur
  `noter_reponse()`, désactivés après vote, réponse de remerciement affichée.
- La réponse de feedback propose la chip « Apprendre la bonne reponse » qui
  lance le flux `apprentissage.collecte_reponse`.

### Tests `tests/test_apprentissage.py` (19 tests)

Journal (trace + purge), migration du schéma, feedback (+/− sélectif sur la
mémoire), renforcement par rejeu, consolidation des doublons, suppression des
faibles, cooldown, mémorisation rejouée et journalisée, stats, « ameliore-toi »
(en incrémentant `_compteur_tours` de 49 pour celle qui le suit, toujours via
les API/chaînes publiques).

### Résultats

- `python -m pytest tests server -q` : **301 passed** (282 + 19 nouveaux).
- Exercice services : 28/28 OK. Exercices SQLite/desktop inchangés (122/80).
- L'application doit être relancée pour charger le nouveau code (PID précédent
  terminé).

## Session 2026-09-09 (suite II) — Overhaul visuel : moderne, lisible, animé

**Demande :** « améliore l'app visuellement, que ce soit plus beau, moderne,
attractif, visible et lisible, avec des animations détaillées et bien foutues,
de belles animations, micro animations, etc. Fais un vrai taf visuel et
n'oublie pas le fichier de mémoire. » → refonte complète du rendu PyQt5.

### Direction artistique retenue

- Sidebar « encre + ambre » : gradient sombre `#27304A → #1B2132`, texte
  off-white `#EDF0F7`, accents or `#EAB43B`, item actif = pilule or + barre
  gauche ambre.
- Contenu beige chaud (`#F5F3EF` / `#F8F6F2`), cartes blanches radius 14 avec
  bande d'accent colorée en haut, bordures douces `#E6E3DB`.
- Typographies plus hiérarchisées (titres de section 15-18px / 700-800,
  sous-titres 12-13px), focus or uniforme sur les champs.
- Animations courtes (160-450 ms), courbes OutCubic/OutBack, chaque effet
  graphique nettoyé à la fin (`setGraphicsEffect(None)`) pour ne jamais
  dégrader le rendu.

### Nouveau `ui/motion.py` (boîte à outils animations, 100 % PyQt5)

| Helper | Usage |
|---|---|
| `fade_in` | fondu de transition de page (remplace l'ancien `_fade_in` de MainWindow) |
| `pop_in` | apparition « ressort » avec opacité (permet `delai`) |
| `stagger` | apparitions échelonnées des cartes KPI/tableaux de bord |
| `bounce_pulse` | pulsation douce du badge « En Ligne » |
| `hover_lift` | micro-élévation au survol (QGraphicsDropShadowEffect : `blurRadius` animé 0→18) — `_LiftFiltre` hérite de `QObject` (contrainte eventFilter) |

### `core/config.py` — charte moderne + QSS global

- Nouvelle palette : `C_INK`/`C_INK_2`, `C_SIDEBAR_TEXT`/`MUTED`/`HOVER`/`ACTIVE`,
  `C_BG_SOFT`, `C_FOCUS_RING`, `C_GRAD_TOP`/`C_GRAD_BOTTOM`. Les constantes
  historiques sont conservées.
- `APP_STYLESHEET` modernisé : tooltips sombres, scrollbars fines (survol or),
  tables (en-tête souligné `#C8960C`, lignes espacées), menus, onglets en
  pilule, checkboxes, QMessageBox ; boutons par défaut or.
- `STYLE_*` (BTN_PRIMARY/SECONDARY/SUCCESS/DANGER/ADD, CARD, SELECTOR, TABLE)
  : radius 10-14, bordures adoucies.

### `ui/ui_files/main.ui` — sidebar redessinée

Gradient sombre, items de navigation : état `:checked` pilule or (`#F4BA3F`
alpha 16 %) + bordure gauche `#EAB43B`, `:hover` blanc translucide, userBox en
carte translucide, logout rouge au survol.

### `ui/main_view.py`

- **Barre d'en-tête** : fil d'Ariane-titre de section (mappé via `PAGE_TITRES`,
  tenu à jour par `navigate()`), date du jour et chip dégradé or = nom de
  l'app. Insérée au-dessus du `stackedWidget` par ré-insertion dans
  `mainLayout` (`_construire_entete`).
- Ombres « cartoon » (`_apply_cartoon_shadows`) supprimées ; les boutons de
  navigation visibles reçoivent `motion.hover_lift`.
- Transition de page : `motion.fade_in` (240 ms), badge statut en pilule
  arrondie + `bounce_pulse` quand le serveur est « En Ligne ».
- `_ajouter_bouton_assistant` restylé pour la sidebar sombre (survol blanc
  translucide + barre or), `hover_lift` installé.
- **Risque corrigé** : l'ancien `setStyleSheet("QMainWindow { ... }")` en code
  écrasait le QSS de la sidebar chargé depuis le `.ui` — supprimé.

### `ui/login_view.py` — écrans connexion & première configuration

Fond dégradé encre + halo or radial, carte blanche radius 16 avec apparition
`pop_in` au premier affichage, titre 24px/800, trait or centré sous le titre,
champs clairs (fond `C_BG_SOFT`) avec focus or, bouton dégradé or avec
`hover_lift`. `_Gradient` re-peint en peintre (halo radial).

### `ui/pages/helpers.py` + `ui/pages/dashboards.py`

- `_kpi_card` : carte moderne (gradient blanc, bordure douce, bande d'accent
  en haut, valeur 23px/800 colorée). `_styler_carte` applique le même rendu
  aux frames existantes des `.ui`. `_page_header` : trait or dégradé sous le
  sous-titre.
- Dashboards directeur/gestionnaire : cartes classées par accent (or/bleu/
  rouge/ambre) + `motion.stagger` des cartes à l'ouverture (440 ms).

### Correctifs incidents

- `ui/motion.py::_LiftFiltre` doit hériter de `QObject` pour
  `installEventFilter` (TypeError sinon).
- `_creer_ombre` parsait `C_INK` en hexadécimal (bug `int('1C2233')`) :
  conversion `#RRGGBB` → (r,g,b) corrigée.
- `hover_lift` n'accepte pas de kwargs (`eleve=` supprimé des appels).

### Résultats & vérification

- Smoke test offscreen (`/tmp/opencode/smoke_visuel.py`) : LoginDialog,
  FirstSetupDialog et MainWindow se construisent, la navigation met le titre
  d'en-tête à jour (« Statistiques »), aucun plantage.
- Suite complète : **tests/ 212 passed** + **server/ 89 passed** = **301
  passed** (compte identique au précédent — aucune régression).
- Exercice services : **28/28 OK**.
- Warnings Qt « Could not parse stylesheet of object QLineEdit » : cosmétiques
  (déclarations ignorées), le rendu reste correct — non traités.
- L'application doit être relancée pour voir le nouveau rendu.

## Session 2026-09-09 (suite III) — Crash assistantie corrigé + CI de build monstre

**Demande :** « Règle ça et compile l'app en exe sur GitHub Actions avec Inno
Setup, et aussi la version Linux. Fais un taff monstre. » + traceback :

```
assistant_page.py:236 showEvent -> _afficher_accueil -> _bulle_assistante
colonne.addWidget(self._rangee_feedback())
TypeError: addWidget(...) argument 1 has unexpected type 'QHBoxLayout'
```

### Bug corrigé

- `ui/pages/assistant_page.py` ligne 291 : `colonne.addWidget(self._rangee_feedback())`
  passait un **QHBoxLayout** à `addWidget()` (qui attend un QWidget) -> crash à
  l'ouverture de la fenêtre. Remplacé par `colonne.addLayout(...)`.
- Test de régression `tests/test_assistant_ia_ui.py` (3 tests, offscreen) :
  rendu de l'accueil, bulles avec feedback, tour de chat complet — sans crash.
  C'est le type de garde-fou qui aurait attrapé ce bug avant l'utilisateur.

### CI « monstre » — `.github/workflows/build.yml` (nouveau)

Pipeline complet déclenché sur `push main`, tag `v*` et `workflow_dispatch` :

| Job | Contenu |
|---|---|
| `tests` (garde-fou) | suite complète `pytest tests server` sur ubuntu-22.04 AVANT toute compilation (plus dep Qt offscreen) |
| `windows` | PyInstaller `build_win.spec` -> smoke-test de l'exe (offscreen, doit rester vivant 12 s) -> **installeur Inno Setup** (`setup_gestion_scolaire.iss` via `_build_installer`) + zip portable ; signature SignPath si secrets fournis |
| `linux` | PyInstaller `build_linux.spec` -> smoke-test du binaire -> paquet **.deb** (`_build_deb`) -> **AppImage portable** (appimagetool) + smoke-test de l'AppImage |
| `release` | sur tag `v*` uniquement : publie tous les installateurs en GitHub Release (softprops/action-gh-release) |

Gardes-fous ajoutés : `concurrency` (annule les runs obsolètes),
`permissions.contents: write`. Les anciens workflows manuels conservés :
`build_windows.yml`/`build_linux.yml` gagnent un job « Tests anti-régression »,
`release.yml` est supprimé (remplacé par le job `release` de `build.yml`),
`build_android.yml` ne se déclenche plus sur les tags (évite les doubles builds).

### Pièges rencontrés pendant la mise au point (validés en local)

- **Heredocs dans le YAML** : le contenu devait être indenté ; remplacés par
  `printf '%s\n'` (insensible à l'indentation) pour AppRun et le .desktop.
- **appimagetool sans FUSE** (CI/containers) : `APPIMAGE_EXTRACT_AND_RUN=1`
  obligatoire pour construire ET lancer l'AppImage.
- appimagetool exige le `.desktop` et l'icone **à la racine de l'AppDir**
  (`gestion-scolaire.desktop`, `gestion-scolaire.png`) + copie dans
  `usr/share/applications` et `usr/share/icons/hicolor/256x256/apps`.
- PyInstaller 6.x : la collection tient dans `_internal/` (153 Mo pour Linux,
  `strip`+`upx` sur Linux, 117 entrées).

### Validation locale (reproduit les étapes du CI)

- `python -m PyInstaller build_linux.spec` : OK, l'exe démarre offscreen
  (timeout 12 s = encore vivant -> logique du smoke-test validée).
- `_build_deb()` : `installers/gestion-scolaire_1.5.0_amd64.deb` (75 Mo).
- AppImage : `dist/GestionScolaire-1.5.0.AppImage` (63 Mo) fabriqué et lancé
  offscreen avec `APPIMAGE_EXTRACT_AND_RUN=1`.
- Tests : `tests/test_assistant_ia_ui.py` 3 pass ; suite `tests/` 212 + `server/`
  89 = **301 passed** ; services 28/28 OK.

---

## Session 2026-09-09 (suite IV) — Interface IA régie par le nombre d'or

### Objectif
Le client a demandé de corriger les bugs de l'interface de l'assistante IA
**et** de refondre toute la surface par les **maths absolus** : nombre d'or
et suite de Fibonacci pour toutes les proportions.

### Nouveau module `ui/math_design.py`
Système de design mathématique central. Tout découle de :
- `PHI = (1+√5)/2 ≈ 1.618`, `GOLDEN = 1/φ ≈ 0.618` (partie majeure),
  `GOLDEN_MINO ≈ 0.382` (partie mineure) ;
- suite de Fibonacci (`fib(n)`, F0=1 … F14=610) ;
- helpers : `rectangle_dore()`, `section()`, `section_or()`.

**Table de correspondance** (piège des indices corrigé en cours de route :
`fib(9)=55` et non 34 → vérifié à l'écran par `ratio 377×610 = 1.618`) :

| Constante | Valeur | Origine |
|---|---|---|
| `MARGE` / `MARGE_COURTE` | 13 / 8 | F6 / F5 |
| `MOYEN` (boutons feedback, titres) | 21 | F7 |
| `AVATAR`, `CHAMP`, bouton d'envoi | 34 | F8 (cercles : rayon 17) |
| Rayon bulles / chips (`PILULE`) | 13 | F6 |
| Dialogue par défaut | 377 × 610 | F13 × F14 (rectangle d'or exact) |
| Minimum | 233 × 377 | F12 × F13 |
| Police texte / titre | 13 / 21 | F6 / F7 |
| Fondu bulle | 144 ms | F11 |
| Machine à écrire | 13 ms | F6 |
| Clignotement « … » | 233 ms | F12 |

### Corrections de bugs
- **Vote 👍/👎 mal attribué** : un clic sur un feedback d'**ancienne** bulle
  notait la **dernière** réponse du moteur. Fix : registre `_tous_feedback`
  global — dès qu'un avis est donné, **tous** les boutons de la conversation
  sont désactivés (un seul avis par conversation).
- **Paramètre mort** `machine_a_ecrire` de `_bulle_assistante` supprimé
  (annoncé mais jamais utilisé).
- Remplacement des nombres magiques : 14/17/19/30/38/280 ms/12 ms/9 px/12.5 px…

### Répartition par coupe d'or
- Largeur du chat découpée en **partie majeure (0.618)** pour la bulle de
  l'assistante et **partie mineure (0.382)** pour celle de l'utilisateur
  (`md.section(self._largeur_chat(), md.GOLDEN)`).
- Fentre : 377 × 610 = cercle d'or exact (ratio hauteur/largeur = 1.618).
- Avatars ronds 34 px, champ de saisie 34 px (pilule rayon 17), pilule
  bouton d'envoi 34 px aligné — tout est puissance de φ ou fib.
- Espacement des lignes du flux + marges internes : 13 / 8 / 21.

### Validation
- Smoke offscreen : ratio fenêtre `610/377 = 1.6180`, min `377/233 = 1.618`,
  avatar/send 34×34, champ pilule, flux non vide, vote unique (tous les
  autres boutons désactivés après un clic).
- Coupe d'or vérifiée dans l'arbre : bulle utilisateur `maxW=134`
  (= 0.382 × 351), bulle assistante `maxW=217` (= 0.618 × 351).
- Suite complète : **304 passed** (`tests/` 212 + `server/` 89 + nouveaux
  autres) ; `tests/test_assistant_ia_ui.py` 3 pass.
- App relancée : PID 196380 (`.venv/bin/python main.py`), saine.
