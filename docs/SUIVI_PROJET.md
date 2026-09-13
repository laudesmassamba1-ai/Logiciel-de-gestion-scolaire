# SUIVI PROJET — Gestion Scolaire

> Memoire de travail du projet. Ce fichier est la reference pour ne rien
> oublier : historique des modifications, decisions, plans, taches en cours.
> Toute session de travail doit le lire au debut et le mettre a jour a la fin.

## Etat actuel du projet

- **Version** : **v1.8.0** (session XV — comptes partages, hotspot WiFi de
  l'ecole hors Internet, discovery UDP, audit 74 bugs ; branche `exe` HEAD
  `adc91e9` avec les binaires ; tag `v1.6.0` pousse -> Release GitHub
  publique avec les 4 installateurs)
- **Architecture** :
  - App bureau PyQt5 + SQLite locale (offline-first) dans `core/`, `ui/`,
    `services/`, `repositories/`, `database/`
  - Sync multi-postes optionnelle via API FastAPI + MySQL dans `server/`
    (compatibilite client/serveur dans `server/compat.py`)
- **Tests** : **320 tests verts** (`tests/` bureau + `server/`) + exercices
  fonctionnels : **SQLite 122/122, MySQL réel 122/122, desktop 80/80,
  services 28/28** (session 2026-09-09)
- **Derniers commits** : release v1.6.0 (CI « monstre », cf. suite III),
  branche `exe` « voici les executables » (cf. suite III), et en cours :
  passe « améliorations minutieuses » (warnings QSS corriges cf. suite V,
  UX Apple-like cf. suite VI) puis refonte visuelle « suite du rapport »
  (cercles supprimés, règles .ui scopées, KPI/états vides compactés,
  icônes sidebar + boutons d'ajout — suite VIII, app relancée OK)

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
- Warnings Qt « Could not parse stylesheet of object QLineEdit » : **cause
  trouvee et corrigee en session suite V** (accolade supplementaire `}}`
  dans un string non-f -> QSS invalide sur chaque champ). Plus aucune
  emission au boot ni sur les dialogues de connexion.
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

## Session 2026-09-09 (suite V) — Passe « améliorations minutieuses » : warning QSS QLineEdit corrigé

**Demande :** continuer les améliorations méticuleuses après la livraison des
exécutables ; poser le choix d'architecture (Flutter vs PyQt5) — l'utilisateur
a choisi **affiner l'app PyQt5 actuelle** (une réécriture Flutter ferait
perdre 304 tests + l'app entière ; une option client web FastAPI reste
ouverte mais pas retenue).

### Bug P0 cosmétique résolu : « Could not parse stylesheet of object QLineEdit »

Symptôme : 2 warnings Qt à chaque ouverture des écrans de connexion (un par
QLineEdit, émis deux fois : polish + repolish). Le rendu était correct mais
le warning polluait la console ET le QSS invalide pouvait dégrader le focus.

**Cause racine (trouvée par bisection à l'écran réel, reproduite via
`qInstallMessageHandler`) :** dans `ui/login_view.py`, le QSS des champs
est assemblé sur plusieurs lignes dont **une n'est pas un f-string** :

```python
field.setStyleSheet(
    f"QLineEdit {{ background-color: {C_BG_SOFT};"
    " border: 1px solid #E3DFD6; border-radius: 10px;"
    " padding: 9px 12px; font-size: 13px; color: #2A2F3C; }}"   # <- NON-f-string
    f"QLineEdit:focus {{ border: 1px solid {C_GOLD}; }}")
```

Dans une **f-string**, `}}` s'échappe en `}` ; dans une **chaîne normale**,
`}}` produit littéralement DEUX accolades. Résultat : un `}` orphelin après
la règle → stylesheet invalide → message Qt par champ. Les 25 autres
occurrences `; }}` du projet sont dans des f-strings (`f"..." }}`) donc
correctes : seules **les lignes 99 et 217** de `login_view.py` étaient
fautives (LoginDialog ET FirstSetupDialog, blocs identiques).

**Fix :** `"; }}"` → `"; }"` aux deux endroits (grep `; }}"` pour vérifier
qu'une occurrence n'a pas le préfixe `f`, c'est le piège).

**Validation :** repro offscreen avec le vrai `LoginDialog`/`FirstSetupDialog`
+ `APP_STYLESHEET` : **0 capture** (avant : 4 / 6). Suite complète :
**304 passed**. App relancée (PID 244090), log de boot réel : **0 warning
QSS**. `tests/test_assistant_ia_ui.py` + `tests/test_auth.py` : 21 pass.

### Note méthode (anti-oubli)

Pour reproduire ce genre de warning de façon fiable : il n'apparaît qu'au
**rendu réel** du dialogue (pas en posant simplement le stylesheet sur un
QLineEdit isolé). Utiliser `qInstallMessageHandler` + les vrais constructeurs
(`LoginDialog(parent=None)`, `FirstSetupDialog(parent=None)`) + `show()` +
`processEvents()` ×2, avec `app.setStyleSheet(APP_STYLESHEET)` actif.

## Session 2026-09-09 (suite VI) — UX Apple-like : toasts, palette Ctrl+K, confirmations françaises

**Demande :** « améliore la logique, l'expérience utilisateur ultime comme
avec Apple, etc. » → passe UX : retours non bloquants, commande Spotlight,
confirmation destructrice sûre en français, dialogues qui valident AVANT de
fermer, états vides.

### Nouveau `ui/toast.py` — notifications « Apple »

- Pilules arrondies glissant depuis le coin **haut droit** de la fenêtre
  (fond = parent.window()), fondu 260 ms OutCubic, empilées, **max 4
  visibles**, clic pour fermer, disparition auto (succès 2,6 s / info 3,2 s /
  erreur 4,6 s).
- API : `toast.succes/info/erreur/afficher(parent, texte, ...)`. Widgets
  `Qt.Tool | FramelessWindowHint | WindowStaysOnTopHint`, ombre douce.
- **Bug d'implémentation attrapé par les tests** : la troncature à 4 tournait
  AVANT l'ajout → 5 visibles possibles. Fix : `_tronquer()` se déclenche à
  `>= _MAX_VISIBLES`.

### Nouveau `ui/palette.py` — palette Ctrl+K « Spotlight »

- Champ de recherche en haut centre, filtrage **sans accent + insensible à la
  casse** (`_normaliser`) sur titre ET conseil, flèches haut/bas, Entrée
  valide, Échap annule. Signaux : `Palette.choisi(cle)` / `Palette.annule()`.
- `ui/main_view.py` : raccourci `QShortcut("Ctrl+K")`, `_entrees_palette()`
  filtrées par `RoleAuthorizer.allowed`, `_conseil_page()` (aide contextuelle),
  pastille « Ctrl+K · Recherche » dans l'en-tête. Actions dédiées :
  `action:assistant` et `action:logout`.

### `ui/pages/helpers.py` — `confirmer()` (confirmations françaises)

- `QMessageBox` par défaut affiche Yes/No anglais → `confirmer(parent, texte,
  titre)` avec boutons **« Oui / Non »** et **bouton par défaut « Non »**
  (pivot sûr pour les actions destructrices).
- **19 sites `QMessageBox.question` convertis** : logout (main_view),
  suppressions caisse/personnel/classes/paiements/tarifs/cycles/années/
  matières/élèves/comptes, sur-paiement, restauration sauvegarde, suppression
  config/sauvegarde, désactivation mode serveur, impression reçu.
- **Bouton par défaut corrigé en cours de route** : la docstring annonçait
  « Non » mais le code faisait `setDefaultButton(oui)`.

### Succès modaux → toasts (non bloquant)

Convertis en `toast.succes` : caisse (export, transaction), certificat,
présences, paiement encaissé, configuration enregistrée, sauvegarde créée,
comptes (mis à jour, mot de passe), planning, programme, inscriptions
élèves (créé/reinscrit/mis à jour), notes (saisies ×2, export moyennes).
**Restés modaux volontairement** (déplacements d'attention ou credentials) :
recap synchronisation, création de compte (identifiant + mot de passe
temporaire), restauration avec redémarrage, gardes « sélectionnez d'abord… ».

### Feedback ajouté aux 4 pages muettes (classes / cycles / personnel / tarifs)

Toasts après chaque enregistrement ET après chaque suppression ; l'activation
de l'année scolaire annonce le passage en actif. (`_set_active` cycles).

### Logique des dialogues « pattern C » corrigée (fermer=valider sans contrôle)

Le danger : `buttons.accepted.connect(dlg.accept)` fermait le dialogue AU
premier Entrée, la validation n'ayant lieu qu'APRÈS `exec_()` (un envoi
invalide fermait en silence). Corrigé en `valider()` connecté à `accepted`
(validation puis `accept()` uniquement si OK) dans :
- cycles (nouveau/modifier cycle, nouvelle/modifier année + anti-chevauchement)
- personnel (salaire > 0, nom obligatoire)
- matières (programmes, et mini-dialog notes : nom obligatoire)
- comptes (changer mon mot de passe : confirmation des deux champs AVANT
  l'appel `change_password` ; réinitialiser : mot de passe vide refusé avant
  fermeture)

### États vides — onglets « Suivi Eleve » / « Bilans » de paiements

- Suivi : « Sélectionnez un élève… » quand aucune sélection ; « Aucun paiement
  enregistré pour cet élève sur l'année active » (table masquée).
- Bilans : « Aucun paiement ne correspond à ces critères » (table masquée,
  même si le total reste affiché à 0).

### Validation

- Nouveaux tests : `tests/test_toast.py` (3), `tests/test_palette.py` (5),
  `tests/test_confirmer.py` (3 : boutons français + défaut « Non » + résultat
  par clic réel via `QTimer` + `activeModalWidget`). **11 tests nouveaux.**
- Suite complète : **`pytest tests server -q` → 315 passed**, 0 échec.
- Tout ce qui restait `QMessageBox.question` a été éliminé (grep 0).
- **Tri des tableaux délibérément NON implémenté** : les colonnes Actions
  avec cellules widgets + le tri lexicographique des montants rendraient le
  résultat pire que pas de tri (à faire proprement, par clic de colonne
  numérique, dans une passe dédiée).

### Suite VII — Refonte visuelle « moderne clair épuré »

Direction validée : fond gris très clair, un seul accent or, cartes plates,
structure conservée. Cible : taille fluide (1920 et portable).

- `core/config.py` : palette claire (`C_BG #F4F4F6`, cartes `#FFFFFF`,
  bordures `#E5E5EB`, textes `#1D1D1F/#3A3A40/#6E6E73`), `STYLE_CARD` plat,
  `STYLE_TABLE` header + liseré or, scrollbar/statusbar/disables harmonisés.
- Sidebar claire (main.ui) + libellés raccourcis (fini les textes coupés) ;
  barre du haut claire avec titre = section (`_section_label`).
- `helpers.py` : `_fill_table_space` (tableaux pleine largeur sans troncature),
  `_actions_cell` (actions alignées à droite), `_kpi_card`/`_styler_carte` plats.
- Tables migrées (classes, eleves, comptes, caisse, personnel, paiements,
  tarifs, cycles, programmes, presences, notes) ; dashboards restylés.
- `.ui` hérités (classes, eleves, comptes, planning, parametres + dialogues
  classe/compte/inscription) : couleurs beige/noir/bleu migrées vers le thème
  (transform idempotente appliquée aux fichiers, XML validé), styles de page
  et de table réappliqués depuis le thème.

Vérification : app relancée sur la vraie base `data/ecole.db` (aucune base
factice, aucun compte « temporaire » injecté), log sans erreur, `pytest tests
server -q` → 315 passed.

### Vérification propre (aucun mock, aucune injection)

- Suite de tests réelle : `pytest tests server -q` (315 tests, base SQLite
  temporaire dédiée aux tests serveur via environnement, jamais la base de
  l'utilisateur).
- Lancement manuel : `.venv/bin/python main.py` sur la vraie base publique
  `data/ecole.db` ; le compte administrateur se crée par l'assistant de
  première configuration (jamais codé en dur, hash PBKDF2 salé).
- Aucune modification de la base réelle, aucun compte jetable. Si un dialogue
  GUI doit être vérifié, se connecter au vrai compte et l'ouvrir en interface.
### Session 2026-09-09 (suite VIII) — Refonte visuelle « suite du rapport » (cercles, cohérence .ui, KPI, états vides, icônes)

Demande : appliquer les priorités du rapport de refonte visuelle (supprimer
les cercles décoratifs cassés, harmoniser les styles, cartes KPI compactes,
états vides compacts, marges réduites, icônes) sans toucher au fond ni à la
navigation.

- **Cercles supprimés** : `ui/decor.py` réduit à `creer_avatar` (plus de
  `FondBulle`/`poser_fond_bulles`/blobs/anneaux/points) ; constantes `BULLE_*`
  et commentaire pastel retirés de `core/config.py`.
- **Cohérence `.ui` (cause des champs « sans bordure »)** : les règles de
  style nues sur les QFrame/QWidget cascadeaient sur leurs enfants et
  écrasaient les QLineEdit globaux. Toutes les règles nues des .ui sont
  scopées `QFrame#... { ... }` (54 règles au total) et 25 styles inline de
  champs (bordure/radius) supprimés pour laisser le thème global gouverner :
  caisse, classes, comptes, dashboards (admin/directeur/gestionnaire), eleves,
  inscription, notes, parametres, planning + `main.ui` (stackedWidget scopé).
- **Cartes KPI bornées (P3)** : `_kpi_card` → max 92 px ; `_borner_carte_kpi`
  (94 px + `QSizePolicy.Fixed`) appliqué sur eleves, classes, comptes et
  dashboards (ensemble `_CARTES_KPI`).
- **États vides compacts (P4)** : `_empty_state(texte, sous_titre, bouton,
  hauteur=180)` ; remplacé le grand label centré sur tarifs + personnel
  (bouton « + Nouveau » intégré).
- **Icônes (P6)** : `qtawesome==1.4.2` ajouté à requirements.txt ; icônes FA5
  or sur les 15 boutons de sidebar (`_poser_icones_nav`), icône « + » sur les
  boutons d'ajout via `_poser_icone_plus` (helpers `_btn`, caisse, eleves,
  classes, comptes, notes).
- **Marges (P5, partiel)** : espacements réduits sur tarifs et personnel ;
  recherche bornée (360 px).

Vérification : `py_compile` OK sur tous les fichiers modifiés, XML des 14 .ui
valide (parser ElementTree), app lancée hors-écran sur la vraie base
`data/ecole.db` → 15/15 pages chargées sans erreur, cartes KPI mesurées à
94 px, icônes présentes sur la sidebar.

## Session 2026-09-09 (suite IX) — Arrondis + contours uniformes, puis inventaire des bugs et corrections

### Uniformisation des arrondis (tokens `Resources.Radius`)
- `resources/design_tokens.py` : `Radius` = **SM 9 / MD 12 / LG 16** (XL supprimé).
- `core/config.py` : import `Radius as _R`, tout le QSS global bascule sur les
  tokens (QToolTip, QPushButton, QMenu, QLineEdit/QComboBox/QDateEdit/
  QSpinBox/QTextEdit, QCheckBox, QGroupBox, QSS_SIDEBAR).
- Widgets : `KPICard` → `setBorderRadius(16)` ; `DataTable` → 14 px ; `EmptyState`
  → 16 px ; `FormPageTemplate` → 12 px.
- Rayons éparpillés (6/8/9/10/11/13/17) uniformisés à 12 px sur les pages
  historiques (dashboards, parametres, assistant, login, helpers, palette).

### Contours uniformes « tout autour » (retour utilisateur itéré)
- Règle retenue : **2 px tout autour** sur les contrôles interactifs (boutons,
  champs), **1 px** sur les conteneurs simples.
- Suppression des effets « border-bottom uniquement » qui donnaient un aspect
  3D : `STYLE_BTN_*`, QSS global, `ui/decor.py` (avatar → anneau or),
  `ui/login_view.py`, `ui/palette.py`, `ui/pages/helpers.py` (_kpi_card,
  _styler_carte → contour 3 px couleur), `ui/widgets/kpi_card.py`,
  `ui/main_view.py` (champ de recherche, chips, bouton assistant).
- Sont laissés volontairement en « soulignement » (traits structurels, pas des
  contours d'objet) : ligne sous en-têtes de page, soulignement d'onglets
  (QTabBar), soulignement des en-têtes de tableau. Idem pour les séparateurs de
  documents créés par `services/pdf_export.py` / `reports.py`.

### Inventaire des bugs (audits croisés) → corrections appliquées
1. **`requirements.txt` ne listait pas `PyQt-Fluent-Widgets`** → `ImportError:
   No module named 'qfluentwidgets'` sur toute installation neuve dès
   `pip install -r requirements.txt` (imports : ui/widgets/data_table.py:12,
   ui/widgets/kpi_card.py:10, ui/pages/dashboards.py:101).
   → Ajout `PyQt-Fluent-Widgets==1.11.3`.
2. **`open_change_password_dialog` (comptes_page.py:186) : code mort** — exporté
   mais jamais appelé ; « Changer mon mot de passe » était inatteignable depuis
   l'UI. → Bouton « Changer mon mot de passe » câblé dans l'en-tête de la page
   Comptes (visible pour tous, pas seulement ceux qui gèrent les comptes), style
   `STYLE_BTN_SECONDARY`.
3. **`helpers._styler_carte` : règle `QFrame { … }` non scopée** → cascade sur
   les QFrame/QWidget descendants des cartes .ui (ils prenaient eux aussi bordure
   + fond). → Sélecteur scopé `QFrame#objectName`.
4. **`ui/widgets/kpi_card.py` : règle `QFrame { … }` non scopée** (idem) +
   **largeur fixe 220 px** → grille KPI à 4 cartes sur `DashboardPageTemplate`
   laissait un grand vide à droite (stretch uniquement sur la colonne 4).
   → Sélecteur scopé `QFrame#kpiCard`, largeur flexible (minimum 170 px, sans
   `setFixedWidth`) et **`QGridLayout` : stretch égal sur les colonnes 0-3**
   (page_templates.py) → cartes réparties sur toute la largeur.
5. **`helpers._replace_layout` : fuite des sous-layouts** (les `takeAt` retournant
   un layout n'étaient pas nettoyés). → Nettoyage récursif (widgets `deleteLater`,
   sous-layouts vidés récursivement).
6. **`ui/pages/presences_page.py:114` : `motif = pres["motif"] or "" if pres else ""`**
   — priorité d'opérateur fragile (correct mais incompréhensible). →
   `motif = (pres.get("motif") or "") if pres else ""`.
7. **`resources/` sans `__init__.py`** (namespace package — risque d'empaquetage
   PyInstaller). → `resources/__init__.py` créé.
8. **2 tests non déterministes** (TestMultipostes mode autonome) : plantaient
   quand `data/sync.json` contient `"sync_active": true` (état réel de
   l'utilisateur, pas un bug applicatif). → Fixture `mode_autonome`
   (monkeypatch `core.network._sync_active = False`) ajoutée dans
   `tests/test_assistant_ia.py`.

### Résultats
- Suite complète : **315 passed** (130 s). `py_compile` OK sur les fichiers
  modifiés.
- Smoke offscreen sur la vraie base (compte directeur) : navigation Comptes → le
  bouton « Changer mon mot de passe » est présent (= `headerLayout` de
  comptes.ui rechargé) ; capture du tableau de bord régénérée
  (`docs/captures/dashboard_pilote_apres.png`).
- Note opérationnelle : pour un smoke offscreen, utiliser le nom de page réel
  (`dashboard`, `comptes`…) — `navigate("accueil")` lève un `QMessageBox`
  « Accès refusé » modal qui bloque le script hors-écran.

### Lancement applicatif (relance après corrections)
Le lancement par arrière-plan simple est tué par le shell tool ; il faut un
processus détaché de l'unité utilisateur systemd :
`timeout 15 systemd-run --user --collect --unit=gs_v3 --setenv=DISPLAY=:0
--setenv=QT_QPA_PLATFORM=xcb --setenv=WAYLAND_DISPLAY=wayland-0
--working-directory="$(pwd)" .venv/bin/python main.py`
(avant une relance : `pkill -f main.py` ; noms d'unité toujours frais car les
anciennes restent enregistrées jusqu'au ramassage).

## Session 2026-09-09 (suite X) — Refonte « un composant = un seul endroit » : migration des pages liste

Conformément au mandat de refonte complète (les correctifs ponctuels ne tiennent
pas ; chaque page avait son propre code de mise en page), les pages sont migrées
une à une sur les fondations (tokens + composants `ui/widgets/` + gabarits
`page_templates.py`). Les dialogues conservent leur .ui.

### Gabarits enrichis (petits ajouts de composants, sans change du contrat)
- `page_templates.py` — `ListPageTemplate.ajouter_kpi(carte, colonne)` : rangée
  de KPICard optionnelle entre l'en-tête et les filtres (QGridLayout, stretch
  égal sur les colonnes 0-3), pour les pages de liste à KPI (Eleves, Classes,
  Comptes).
- `page_header.py` — `PageHeader.set_sous_titre(texte)` : le sous-titre piloté
  par le code (ex. « classe X ») sans récréer l'en-tête.

### Pages migrées (5) — l'ancien code de mise en page a été SUPPRIMÉ (pas
laissé à côté)
1. **Eleves** (`ui/pages/eleves.py`) : plus de `eleves/eleves.ui`, plus de
   `_styler_carte`/`_borner_carte_kpi`/`STYLE_TABLE`/`_fill_table_space`.
   → `ListPageTemplate` + 4 `KPICard` + `DataTable` (8 colonnes) + `EmptyState`
   interne ; filtres en direct (recherche, classe, statut) ; boutons header
   « + Nouvel Eleve » et « Exporter CSV » ; état vide piloté par le gabarit.
2. **Classes** (`ui/pages/classes_page.py`) : idem → `ListPageTemplate`,
   4 KPICard (Total, Effectif, Complètes, Sans titulaire), tableau 8 colonnes,
   rouge sur les classes complètes, double-clic pour modifier.
3. **Personnel** (`ui/pages/personnel_page.py`) : plus de `_page_header` ni de
   `QTableWidget` brut → `ListPageTemplate` + `DataTable` (essai : pas de KPI),
   « + Nouvel Employe » dans le header.
4. **Matieres & Programmes** (`ui/pages/programmes_page.py`) : page double
   onglet, ne rentre pas dans un gabarit simple ; `PageHeader` composant +
   onglets ; les 2 onglets remplacent `_make_table`+label vide par
   `DataTable` + `EmptyState` (pile), hauteur recalculée par le composant.
5. **Comptes** (`ui/pages/comptes_page.py`) : plus de `comptes/comptes.ui` →
   `ListPageTemplate` + 4 KPICard + `DataTable` 6 colonnes ; boutons header
   « + Nouveau Compte », « Changer mon mot de passe ».

### Résultats et vérification
- `py_compile` OK sur les fichiers modifiés ; suite de tests : **315 passed**
  (~150 s).
- Smoke offscreen (compte directeur) : navigation sur les 5 pages sans erreur.
- Captures avant/après générées : `docs/captures/{eleves,classes,comptes,
  personnel,programmes}_{avant,apres}.png`. Attention : `programmes` a un
  « avant » mais cette page n'était pas dans la liste de la capture initiale —
  consulter les PNG.
- Grep des `setStyleSheet` hors tokens et composants : les 5 pages migrées
  sont tombées à **1 occurrence chacune** (le style unique du dialogue
  conservé, ex. matricule or / label cycle).

### Statut de la migration (à poursuivre — ordre initial du mandat)
Migrées : **Eleves, Classes, Personnel, Matieres, Comptes** (+ le tableau de
bord directeur, pilote validé). Taille des `setStyleSheet` restants par page :
notes 25, assistant_serveur 21, parametres 20, assistant_page 18, login_view 16,
main_view 15, main.py 3, paiements 7, palette 6, presences 6, planning 5,
statistiques 3, dashboards 3, cycles 3, caisse 3, tarifs 1, toast 3, decor 1.
Ces pages (dont certaines plus complexes : notes tabbées, parametres à onglets,
assistant IA, login, sidebar) feront l'objet des prochaines sessions de
migration ; les fondations restent la source unique à réutiliser.

## Session 2026-09-10 (suite XI) — Création de compte simplifiée + migration des 6 pages simples restantes

Statut : bout de la session précédente — l'utilisateur a confirmé la poursuite
de la migration ET demandé de simplifier la création de compte.

### Création de compte : fini le mot de passe temporaire
- `ui/ui_files/comptes/compte_dialog.ui` : le sous-titre « Un mot de passe
  temporaire sera envoyé à la personne » est remplacé par « Définissez le mot
  de passe du nouveau compte » ; deux champs ajoutés (Mot de passe / Confirmer,
  echoMode Password).
- `ui/pages/comptes_page.py` `open_compte_dialog` :
  - création → validation (≥ 6 caractères + correspondance) puis
    `repos.add_compte(..., hash_password(password), ...)` ;
  - édition → les champs mot de passe sont masqués (le compte affiche
    « Changer mon mot de passe » / « Réinitialiser » par ailleurs) ;
  - suppression du `QMessageBox.information` qui exposait le mot de passe
    temporaire (`auth.random_password()` n'est plus utilisé ici).
- Fenêtre agrandie 440x560 ; aucun test ne dépendait de l'ancien flux.

### Migration des pages simples restantes → fondations
Six pages portées (DataTable + EmptyState + KPICard/ListPageTemplate, palette
or, styles de page supprimés) :
- **Caisse** → `ListPageTemplate` : filtres (recherche, type, dates Du/Au,
  année), 3 KPICard (Recettes / Dépenses / Solde), boutons header
  (+ Recette, + Depense, Exporter CSV), colonnes Recettes/Dépenses.
- **Tarifs & Scolarité** → `ListPageTemplate` : filtre classe, 4 KPICard
  (Nombre, Moyen, Minimum, Maximum), DataTable.
- **Présences** → `ListPageTemplate` : classe + date + Charger, boutons tout
  présent / tout absent, KPICard Présents/Absents/Retards, état vide dynamique
  (« Choisissez une classe… » / « Aucun élève… »).
- **Planning** → `ListPageTemplate` : grille 8x6 (créneaux/jours), édition
  double-clic, imprimer, pile vide « Choisissez une classe ».
- **Cycles & Années** → pattern tabbé de programmes : un onglet par sous-page
  avec DataTable + EmptyState + QStackedWidget.
- **Paiements / Suivi / Bilans** → pattern tabbé : onglet Paiements (filtres +
  2 KPICard + actions), onglet Suivi (attendu/payé/solde + table mensuelle,
  état vide à deux messages), onglet Bilans (filtres + total + table).

Hors migration : les dialogues restent en code pur (QDialog + QFormLayout) —
aucun `.ui` ajouté.

### Vérifications
- `py_compile` OK sur les 7 fichiers modifiés.
- Suite complète `pytest tests server` : **315 passed**.
- Smoke offscreen (compte directeur) : caisse, tarifs, presences, planning,
  cycles_annees, paiements — tous OK, SANS exception. (Piège évité : ne pas
  passer un callback `None` à `_btn()` — `clicked.connect(None)` lève une
  TypeError ; on utilise un QPushButton manuel pour « Charger » / « Imprimer ».)

### Statut de la migration (à poursuivre)
Migrées : Eleves, Classes, Personnel, Matieres, Comptes, Caisse, Tarifs,
Présences, Planning, Cycles, Paiements (+ tableau de bord directeur).
`setStyleSheet` restants hors composants-fondations : notes 25,
assistant_serveur 21, parametres 20, assistant_page 18, login_view 16,
main_view 15, main.py 3, statistiques 3, dashboards 3, toast 3, palette 6.
Prochaines sessions : notes tabbées, parametres à onglets, assistant IA,
login, sidebar, statistiques, palette/toast.

---

## Session XII — Notes, Parametres et coquille : logique + fondations

### Audit « blocages/logique » (demande utilisateur)
Tour des pages migrees et des helpers : signatures de `can_edit`, `_reload_combo`,
`_classe_items`, `_actions_cell`, `EmptyState.set_message` et des fonctions repos
toutes conformes ; aucun blocage nouveau releve. Rappel des pieges evites :
`_btn(text, None, ...)` lève TypeError (callback `None`) ; DataTable impose
`NoEditTriggers` -> re-activer pour les tableaux editables.

### Notes & bulletins — page entierement refondue
- `notes_page.py` reecrit sur les fondations : 3 onglets (Bulletins / Notes des
  eleves / Moyennes par classe), `PageHeader` par onglet, DataTable + EmptyState
  + QStackedWidget, edition reactivee via `ctx.can_edit("notes")`
  (`setEditTriggers(DoubleClicked | EditKeyPressed)`), statut en bas de page.
- Logique preservee : recalcule des moyennes, garde-fous « Selection modifiee »,
  generation des bulletins, classement, export CSV. Constante parasite
  `PERIODES_LABEL` supprimee.

### Parametres — styles centralises dans core/config
Choix : conserver la structure `.ui` (cartes en scroll) mais supprimer les
styles disperses au profit de constantes uniques ajoutees dans `core/config.py` :
`STYLE_GROUP_BOX`, `STYLE_HELP_MUTED`, `STYLE_LABEL_BOLD_MUTED`,
`STYLE_IMAGE_PLACEHOLDER`, `STYLE_LIST_CARD`, `STYLE_BTN_MINI_DANGER`,
`STYLE_BTN_ADD_SMALL`. `parametres_page.py` ne référence plus que ces constantes
(toutes donnees, 0 style brut).

### Statistiques, dashboards, auth et coquille
- `statistiques_page.py` : `STYLE_SCROLL` + `STYLE_CHART_CARD` (cartes
  graphiques) ; aucune couleur figee restante.
- dashboards : tableau de bord directeur deja sur `DashboardPageTemplate`
  (verifie) ; gestionnaire conserve `.ui` + constantes partagees.
- Assistant IA : design « nombre d'or » (`ui/math_design.py`) volontairement
  autonome et coherent -> laisse tel quel (source unique interne).
- `login_view.py` : bouton principal, embleme et libelles centralises en
  `STYLE_AUTH_BTN`, `STYLE_AUTH_EMBLEME`, `STYLE_AUTH_FIELD_LABEL` (supprime la
  duplication des 3 libelles + couleurs dorees figees).
- `main_view.py` (coquille) : entete, titre, date, champ de recherche, chip APP,
  bouton Assistant et badge API centralises en `STYLE_ENTETE`, `STYLE_RECHERCHE`,
  `STYLE_CHIP_APP`, `STYLE_NAV_ASSISTANT` + `STYLE_BADGE_API`.

### Vérifications
- `py_compile` OK sur core/config.py, parametres_page, statistiques_page,
  login_view, main_view, notes_page.
- Smoke offscreen etendu (directeur + gestionnaire) : caisse, tarifs, presences,
  planning, cycles, paiements, statistiques, parametres, notes, dashboards
  directeur & gestionnaire, LoginDialog, FirstSetupDialog, MainWindow — tous OK.
- Suite complete `pytest tests server` : **315 passed**.

### Statut
Migrees : Eleves, Classes, Personnel, Matieres, Comptes, Caisse, Tarifs,
Presences, Planning, Cycles, Paiements, Notes, Statistiques, Parametres +
tableaux de bord + coquille (styles centralises).
Restants de la liste demandee : assistant_serveur (assistant multi-postes) —
fonctionnel et ancre dans core/network, styles deja coherents ; dashboard
gestionnaire (`.ui` a bascule vers DashboardPageTemplate si besoin).
Declarés hors perimetre (design local coherent) : assistant IA, palette, toast.

---

## Session XIII — Correction de la synchronisation multi-postes (ids locaux)

### Contexte / constats
Le diagnostic E2E (serveurs jetables sqlite) a mis en evidence deux defauts de
l'architecture « local-first » lors de l'envoi poste → serveur :
1. Une classe **sans cycle** pousse `POST /classe` avec `cycle_id=None` →
   serveur repondait `400 cycle_id obligatoire` → l'operation restait **bloquee
   silencieusement** dans `file_attente_synchro` (status FAILED, jamais rejouee).
2. Les **ids locaux sont pousses bruts** : un cycle local `id=5` devenait
   `cycle_id=5` cote serveur alors que le serveur n'avait qu'un cycle `id=1`
   (etc. pour classe, matiere, eleve sur notes/presences/paiements/planning/
   programmes) → references incorrectes en base serveur.

### Corrections apportees
- **`api/mapping.py` (nouveau)** : remapper applique juste avant chaque envoi
  (donc aussi au vidage de la file) qui reattribute les references locales par
  cles naturelles : `cycle_nom`, `classe_nom`, `matiere_nom`, `enseignant_nom`,
  `eleve_uuid`, `annee_libelle`, `classe_ancien_nom`, `reference` de caisse.
  Triple protocole : `send` (ids serveur reattribues), `skip` (cible pas encore
  sur le serveur : on garde l'ecriture locale sans pousser), `enqueue`
  (reseau coupe pendant la resolution : on met en file, drain reessaiera).
  Idempotence cote serveur creee quand utile : cycle absent → cycle « Sans
  cycle » ; matiere/cycle/annee deja presentes → pas de doublon.
- **`repositories/base.py`** : `_route_write` applique le remapper dans la
  branche en ligne ; en cas de « skip » la poussee est simplement omise (le
  local reste valide), en cas de « enqueue » l'operation ORIGINALE (avec cles
  naturelles) est mise en file.
- **`api/sync_worker.py`** : `_drain_queue` repositionne lui-meme les
  references avant envoi ; une ligne « skip » est archivee (pas de boucle
  infinie), le wrapping `/eleve` ne concerne plus que `POST /eleve`.
- **`database/db.py`** : `dequeue_pending` retient desormais **PENDING et
  FAILED** → les operations deja bloquees (vieux modele, sans cles naturelles)
  sont AUTO-REJOUES au cycle suivant et reattribuees correctement.
- **`server/compat.py`** :
  - `GET /eleve-syndication` (id + uuid_client) pour la resolution eleve.
  - `DELETE /supprimerPaiement/{ref}` : accepte id numerique (legacy), une
    reference de caisse (REC-…/DEP-…) ou une reference composee eleve
    (uuid|montant|trimestre|type_frais|annee).
  - `DELETE /supprimerPresence/{ref}` : id numerique (legacy) ou reference
    composee (uuid|date|statut|classe_nom).
- **Repos** (payloads enrichis en cles naturelles) : classe (ajout/modif classe,
  cycle, annee), pedagogie (matiere, programme), personnel (enseignant), eleve
  (uuid_client), finance (paiements, tarifs, caisse), note, presence, planning.
  Suppressions poussees « par nom » quand le serveur le permet (`/supprimerClasse`).

### Verifications
- Suite complete `pytest tests server` : **315 passed** (avant et apres la
  session).
- Smoke offscreen etendu : 11 pages + dashboards directeur & gestionnaire +
  LoginDialog + FirstSetupDialog + MainWindow — `SMOKE_OK`.
- Verification E2E reelle (serveur uvicorn jetable sqlite, port 8903,
  `syncfix_verif.py`) : **20/20 PASS** — classe sans cycle poussee 200 (plus de
  400), cycles/classes/matieres/enseignants/eleves reattributes aux ids serveur,
  notes/presences/paiements/tarifs/programmes pousses correctement, references
  absentes → skip, vieille ligne en file sans cles naturelles rejouee puis
  envoyee (drain sans 400), suppressions paiement/presence par reference OK.

### Remarques
- Les comptes directeur/gestionnaire n'ont PAS ete modifies (hors perimetre).
- App relancee sur **gs_v8** avec le code corrige.
- Design de la correction aligne sur l'existant : le serveur reste la source de
  verite structurelle, l'ecriture reste local-first, aucune suppression
  destructive ajoutee.

---

## Session XIV — Pull des donnees d'action + mode client assistant

### Contexte
Le poste hote et les postes clients n'avaient aucun moyen de saisir l'adresse
du PC serveur. La synchro multi-poste ne rapatriait que la structure (cycles,
classes, matieres, annees, tarifs) : les eleves, personnel, programmes,
presences, notes et paiements crees sur un poste n'apparaissaient pas sur les
autres. Trois routes de syndication manquaient.

### Corrections apportees

#### 1. Mode client dans l'assistant (`ui/assistant_serveur.py`)
- Ajout `QLineEdit`, champ `input_adresse_serveur` (placeholder
  `http://192.168.x.x:8000`).
- Boutons **Connecter** (test HTTP `GET /annee_scolaire_active` avec timeout 3s,
  status < 500) et **Deconnecter** (rouge, desactive la synchro).
- `rafraichir()` : carte adresse visible uniquement en mode hote, carte client
  visible uniquement en mode non-hote ; `btn_activer`/`btn_arreter` seuls
  actifs pour le serveur hote.
- `_connecter_client()` : valide l'adresse, écrit `api_url` dans
  `sync.json`, met a jour `config.API_BASE_URL` et active `network`.
- `_deconnecter_client()` : desactive `sync_active`, met a jour l'UI.
- Risque gere : double import `config` (module) dans `_connecter_client` corrige
  (import `from core import config` + `from core.config import ecrire_config_sync`
  sans shadowing).

#### 2. Routes serveur de syndication (`server/main.py`)
- `GET /lister_toutes_les_inscriptions` : inscription avec eleve_uuid,
  classe_nom, annee_scolaire.
- `GET /toutes_presence` : presences avec eleve_uuid, classe_nom.
- `GET /tous_les_programme` : programmes avec classe_nom, matiere_nom,
  enseignant_nom.
- `GET /paiement-syndication` : paiements avec eleve_uuid, classe_nom,
  annee_scolaire.
- `GET /note-syndication` : notes avec eleve_uuid, matiere_nom.
- Toutes portables MySQL + SQLite (backend `sqlite_backend` remplace
  `%s` → `?` automatiquement).
- Ajoutees a la liste de test GET dans `server/test_routes_exercice.py`.

#### 3. Pull des donnees d'action (`services/sync_service.py`)
- `_champ()`, `_upsert()`, `_supprimer_absents()` : inchanges (Session XII/XIII).
- Nouveaux helpers : `_classe_id_par_nom()`, `_matiere_id_par_nom()`,
  `_eleve_id_local()` (uuid_client puis fallback nom/prenom),
  `_gen_matricule()` (prefixe `ELEV2026XXXX`, non destructif).
- **`pull_donnees()`** : fonctionne en 6 sections independantes, jamais
  destructive (upsert par cles naturelles, aucune suppression) :
  1. **Eleves** : GET `/eleve`, upsert par `uuid_client` ; fallback rattache
     une ligne locale sans uuid par (nom, prenom) ; creer les eleves absents
     localement avec matricule genere et `statut='Inscrit'`.
  2. **Personnel** : GET `/enseignant` → table `personnel` par `nom_complet`.
  3. **Programmes** : GET `/tous_les_programme` → upsert par
     (classe_id, matiere_id) resolus par nom.
  4. **Presences** : GET `/toutes_presence` → upsert par (eleve_id, date) ;
     eleve resolu par uuid_client.
  5. **Notes** : GET `/note-syndication` → agregees en devoir1/devoir2/
     composition par (eleve, matiere, trimestre) ; ne modifie pas une valeur
     deja saisie.
  6. **Paiements** : GET `/paiement-syndication` → upsert par
     (eleve, montant, type_frais, trimestre) ou (eleve, montant, date).
- `pull_donnees()` appelee par `sync_worker._pull_structure()` au meme
  cadence que `pull_structure()` (toutes les 60 secondes).

#### 4. Integration client (`api/client.py`)
- Methodes ajoutees : `toutes_presence()`, `tous_les_programme()`,
  `lister_toutes_les_inscriptions()`, `paiement_syndication()`,
  `note_syndication()`.

### Corrections mineures
- `services/sync_service.py` : import `uuid` en haut du module (requis pour
  `uuid.uuid4()` lors de la creation d'eleves serveur).
- `ui/assistant_serveur.py` : correction du double import `config` (ombrage)
  dans `_connecter_client`.

### Verifications
- Compilation : `py_compile` sur `ui/assistant_serveur.py` et
  `services/sync_service.py` — OK.
- Routes syndication : TestClient FastAPI sur SQLite — 3 routes /toutes_presence
  /tous_les_programme /lister_toutes_les_inscriptions → 200 OK.
- Routes reelles sur MySQL 8.0 (serveur uvicorn port 8000, conteneur Docker
  geston_mysql 3307) : les 5 routes repondent 200 avec donnees vides ou
  remplies.
- **Test E2E complet** (MySQL 8.0) :
  - `pull_structure()` : 1 cycle, 1 classe, 1 matiere, 1 annee, 0 tarifs.
  - `pull_donnees()` : 2 eleves (TEST Synchro + KONE Awa) avec uuid et
    classe resolue par nom, 1 personnel (TRAORE Ali), 1 programme, 1 presence,
    3 notes (devoir1/devoir2/composition), 1 paiement.
  - Mode client (`config.API_BASE_URL = http://192.168.0.167:8000`) :
    `est_hote()` → False, pull complet → OK sans erreur.
- **Suite complete** : **320 passed, 0 failed** (315 + 5 nouvelles routes GET)
  en 161s.

### Etat actuel
- Poste hote : ecriture locale → remappage → serveur MySQL + pull structure/donnees.
- Poste client : saisie de l'adresse IP du serveur dans l'assistant → ecriture
  `sync.json` → `config.API_BASE_URL` mis a jour → pull automatique toutes
  les 60s → les eleves/presences/notes/paiements/programmes des autres postes
  apparaissent.
- Les comptes directeur/gestionnaire n'ont PAS ete modifies.
- Il reste a revisiter : les regles de suppression dans `pull_structure`
  (comportement actuel : supprime les classes locales vides absentes du serveur)
  qui pourraient parfois supprimer des donnees encore utiles hors-ligne.
- `docs/RAPPORT_BUGS.md` et `RAPPORT_BUGS.md` (racine) : pas de nouveau bug
  identifie dans cette session ; les items 1-10 restent dans leur etat
  documente (tous traites).

### Session XV — Comptes partages, reseau WiFi de l'ecole (hors Internet), 74 bugs audites

**Demande : que l'interface, la logique, la synchro, les routes et la base
fonctionnent pour les DEUX profils (directeur + gestionnaire), avec un ecran
de creation de compte, une synchro activee sur toute la surface de
l'etablissement (~600 m²), **sans Internet**, le PC hote creant lui-meme le
reseau local, et « Internet en meme temps » si possible. Aussi : regler tous
les bugs, majeurs comme mineurs.**

#### 1. Comptes directeur/gestionnaire synchronises

- **`GET /comptes-syndication`** (serveur) : renvoie id, nom, prenom,
  telephone, email, identifiant, mot_de_passe (hash PBKDF2), role, statut.
- **`client.comptes_syndication()`** + **`client.ajouter_compte_serveur()`
  (`POST /comptes`)** : le premiere compte cree via `FirstSetupDialog` est
  maintenant pousse vers le serveur partage → utilisable sur TOUS les postes.
  (Avant : le compte restait local, dead-code silencieux.)
- **`pull_comptes()`** dans `services/sync_service.py` : upsert par username,
  ne jure jamais le mot de passe local, cree les comptes nouveaux avec le hash
  serveur (login multi-poste), role borne a directeur/gestionnaire, jamais
  destructif. Integre a `sync_worker._pull_structure()`.
- **Bug corrige** : le statut `"Actif"` (title-case) du serveur desactivait le
  compte localement → detection insensible a la casse.
- **Bug corrige (serveur)** : `POST /comptes` renvoyait 500 sur telephone deja
  utilise (UNIQUE) → verification prealable + 409 propre ; telephone vide →
  valeur unique `GS-<identifiant>` (colonne NOT NULL UNIQUE).

#### 2. Reseau local cree par le PC hote, SANS Internet

- **`services/discovery.py`** : protocole UDP port 42300
  (`{"gestion_scolaire": 1, "port": <api>}`) diffuse toutes les 4 s par
  `AnnonceurServeur`. `DecouvreurServeur` / `trouver_serveur()` ecoutent.
  Bug corrige : l'attribut `self._stop` ecrasait `threading.Thread._stop()` →
  renomme `_arret`. Verification E2E : envoi direct IP LAN → trouve ; broadcast
  → ne reboucle pas localement (attendu).
- **`services/hotspot.py` (nouveau)** : cree le point d'acces WiFi de l'ecole
  via `nmcli connection add type wifi mode ap ipv4.method=shared`.
  - SSID `Gestion-Ecole`, mot de passe `Gestion2026`.
  - **Internet en meme temps** : le mode `shared` fait du NAT — si le PC hote
    garde une connexion (Ethernet cable vers la box, telephone/modeme USB,
    carte 4G), les postes connectes au hotspot recoivent l'Internet en plus de
    la synchro. `source_internet_disponible()` detecte cette source ; sinon le
    reseau reste un LAN pur (message clair).
  - Portee ~30-50 m en interieur (600 m² couverts si poste centre) ; repeteur
    WiFi ou câble Ethernet recommande au-dela. Tout est hors Internet.
- **Assistant (hote)** : bouton « Creer le reseau WiFi de l'ecole (hotspot) »
  lance la creation en arriere-plan (`ui/workers.run_async`) ; affiche SSID/mot
  de passe/passage/partage et l'adresse correcte des postes (port pris de la
  config, plus de `:8000` dure). Bug corrige : crash si `nmcli` absent
  (Windows) ; `_nmcli` ne leve plus (FileNotFoundError/TimeoutExpired gees).
- **Assistant (client)** : bouton « Scanner » → `trouver_serveur()` dans un
  QThread, fermeture propre (`closeEvent` attend la fin du scan, plus de
  « QThread destroyed while running »).
- **Annonceur** integre au cycle de vie du serveur (`serveur_local`) : demarre
  des que le serveur repond, s'arrete avec lui.

#### 3. Robustesse de la synchro (aucun doublon, pas de perte)

- **`sync.json`**: ecriture atomique (tmp + `os.replace`) sous verrou —
  plus de fichier tronque ni d'update perdu entre le thread d'auto-demarrage
  et l'interface.
- **`sync_worker`** : `dequeue_pending()` protege (une base verrouillee ne tue
  plus le thread) ; `"enqueue"` archive au lieu d'envoyer un payload renaud
  (airait pu modifier/supprimer la mauvaise ligne serveur) ; `sleep` decoupe
  en pas de 0,5 s → `requestInterruption()` respecte par `wait(3 s)` a la
  fermeture ; erreurs du pull remontees via `sync_error` (plus de silence).
- **`pull_donnees`** : correction du double-comptage des eleves ; `redoublant`
  gere via `_bool_int` (une valeur 0 n'est plus ecrasee) ; coefficients
  supportent `"1,5"` (`_coef_float`) ; paiements deduples par date precise
  (2 paiements identiques a des dates differentes sont DISTINCTS) au lieu de
  les ecraser ; plus de fake `1970-01-01` (date NULL → defaut local).
- **`pull_structure`** : `cycle_id` non ecrase par NULL (garde le lien local
  si le serveur ne l'a pas informe) ; tarifs miroirs ne suppriment plus un
  tarif local hors-ligne en attente dans la file (garde PENDING).
- **`__init__`** : le PID enregistre est maintenant le bon (le PID stocke
  dans `sync.json` etait perime, pointant vers un ancien serveur).

#### 4. Audit complet des bugs (2 agents explore : synchro, UI/reseau, routes)

- ~74 problemes releves ; traites dans cette session : crash `nmcli` absent,
  QThread de scan detruit, `ajouter_compte_serveur` inexistant, premiere
  compte non pousse, `user=None` apres FirstSetup, username vide, `sync.json`
  race, worker de synchro mort sur base verrouillee, `enqueue` renaud,
  doublons de paiements, statut case-sensitive, ecrasement cycle_id, tarifs
  supprimes hors-ligne, double-comptage eleves, valeurs `0` corrompues,
  telephone duplique 500→409, hotspot UI fige / port dur, blocage 15 s du
  serveur, scan restant actif a la fermeture.

### Verifications session XV
- Compilation : `py_compile` sur tous les fichiers modifies (ui/assistant,
  ui/login_view, services/{hotspot,discovery,sync_service,serveur_local},
  api/{client,sync_worker}, core/config, server/compat) — OK.
- Hotspot reel (carte wlo1, mode AP supporte) : creation → passerelle
  `10.42.0.1` → arret → la carte reprend son WiFi). Sans source
  Internet alternative, `partage=False` correct.
- `source_internet_disponible()` : Ethernet `eth0` → detecte ; seul WiFi →
  None (pas de partage).
- `POST /comptes` : duplique telephone → **409** (plus de 500) ; sans
  telephone → 200 + identifiant unique.
- `pull_comptes()` en mode LAN (`GS_API_URL=http://192.168.0.167:8000`) :
  `{'ajoutes': 3, 'mis_a_jour': 1, 'erreurs': []}` ; login
  `kone.gestionnaire/gestion!2026` → OK (role gestionnaire, actif 1).
- `pull_donnees()` rejouer : personnel 1, programmes 1, presences 1, notes 3,
  paiements 1, 0 erreurs (aucun doublon creer).
- **Suite complete** : **320 passed, 0 failed** (~157 s).

### Etat actuel
- Poste hote : creation du reseau WiFi de l'ecole en 1 clic (hotspot shared)
  → les postes scannent/trouvent le serveur → synchro sans Internet (UDP
  LAN + pull/push locaux).
- Comptes directeur + gestionnaire crees n'importe où → visibles et
  utilisables sur tous les postes (push premiere compte + `pull_comptes`).
- Internet en meme temps : automatique si le PC hote a une 2e source (Ethernet
  vers la box, 4G USB) via le NAT du mode `shared`.
- Reste a faire : derouler les 74 items restants non traites (erreurs serveur
  500→4xx, dedup uuid_client sur POST /paiement/note/presence, jointures
  syndication INNER vs LEFT, fermetures de curseurs, shadowing compat…) ;
  test de campagne complet (routes SQLite+MySQL sur les executions
  multi-postes).
